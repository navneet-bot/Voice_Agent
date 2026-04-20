"""Runtime processors for the local voice pipeline."""

import asyncio
from dataclasses import dataclass
from difflib import SequenceMatcher
import logging
import os
import time
import concurrent.futures

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)

# ── TTS generator sentinel (Fix #1: StopIteration in run_in_executor) ─────
# PEP 479 converts StopIteration raised inside a Future into RuntimeError.
# We catch it inside the thread before it can escape.
_GENERATOR_SENTINEL = object()


def _safe_next(gen):
    """Call next(gen) inside a thread. Returns _GENERATOR_SENTINEL on StopIteration."""
    try:
        return next(gen)
    except StopIteration:
        return _GENERATOR_SENTINEL
_ml_semaphore = asyncio.Semaphore(4)

try:
    from pipecat.frames.frames import AudioRawFrame, Frame, TextFrame, CancelFrame
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
except ImportError:
    logging.error("pipecat-ai is not installed. Pipeline will fail.")
    FrameProcessor = object
    FrameDirection = None
    Frame = None
    TextFrame = None
    AudioRawFrame = None
    CancelFrame = None

from llm.llm import generate_response
from llm.language_utils import LanguageTracker, analyze_user_text
from llm.state_manager import StateManager
from llm.pipeline_logger import pipeline_logger
from pipecat.frames.frames import StartFrame
from stt import config as stt_cfg

# Root-relative path for the agent schema
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_SCHEMA_PATH = os.path.join(_ROOT, "Updated_Real_Estate_Agent.json")
CALL_CONNECTED_TRIGGER = "[System: The call has just been connected. No user has spoken yet. Speak only for the current conversation node and do not transition.]"

try:
    from stt.stt import transcribe_audio
except ImportError:
    logging.warning("stt.stt.transcribe_audio not available yet. Using mock STT.")

    def transcribe_audio(audio_chunk: bytes) -> str:
        return "mock transcription"

try:
    from tts import generate_speech_stream
except ImportError:
    logging.warning("tts engine not found. Using mock TTS.")

    def generate_speech_stream(text: str, preferred_language: str | None = None):
        return iter([])

logger = logging.getLogger(__name__)


@dataclass
class AgentTextFrame(TextFrame):
    language: str = "en"


class RealEstateLLMProcessor(FrameProcessor):
    """Turn user transcripts into LLM responses and manage node states with GenID sync."""

    def __init__(self):
        super().__init__()
        self.history: list[dict[str, str]] = []
        self.current_language = "en"
        self.language_tracker = LanguageTracker(initial_language=self.current_language)
        self.last_user_text = ""
        self.last_user_at = 0.0
        self._booted = False
        self.state_manager = StateManager(STATE_SCHEMA_PATH)
        self._current_gen_id = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        await super().process_frame(frame, direction)
        
        if isinstance(frame, StartFrame) and not self._booted:
            self._booted = True
            self.state_manager.reset_state()
            pipeline_logger.log_event("call_started", {"start_node": self.state_manager.start_node_id})
            await self.push_frame(frame, direction)

            logger.info("[PIPELINE] LLM -> Received StartFrame. Triggering initial greeting...")
            try:
                # 2. CIRCUIT BREAKER (Timeout)
                reply = await asyncio.wait_for(generate_response(
                    user_text=CALL_CONNECTED_TRIGGER,
                    conversation_history=self.history,
                    language=self.current_language,
                    state_manager=self.state_manager,
                    allow_transition=False,
                ), timeout=3.5)
            except (asyncio.TimeoutError, Exception):
                reply = "Hello, how can I help you today?"

            if reply:
                self.history.append({"role": "assistant", "content": reply})
                frame_out = AgentTextFrame(reply, language=self.current_language)
                frame_out.gen_id = self._current_gen_id
                await self.push_frame(frame_out, direction)
            return

        if not isinstance(frame, TextFrame):
            await self.push_frame(frame, direction)
            return

        user_text = frame.text.strip()
        if not user_text:
            return

        # 1. INCREMENT GEN_ID on new valid user turn
        self._current_gen_id += 1
        logger.info("New User Turn: gen_id = %d", self._current_gen_id)

        user_analysis = analyze_user_text(user_text, fallback=self.current_language)
        if not user_analysis.actionable:
            return
        user_text = user_analysis.cleaned_text

        now = time.monotonic()
        if _is_duplicate_text(user_text, self.last_user_text) and (now - self.last_user_at) < stt_cfg.DUPLICATE_TEXT_WINDOW_S:
            return

        self.last_user_text = user_text
        self.last_user_at = now
        self.current_language, _ = self.language_tracker.observe(user_text)
        
        # Sync User Text Frame with current GenID
        frame.gen_id = self._current_gen_id
        await self.push_frame(frame, direction)

        try:
            # 2. CIRCUIT BREAKER (Timeout)
            reply = await asyncio.wait_for(generate_response(
                user_text,
                self.history,
                self.current_language,
                state_manager=self.state_manager
            ), timeout=4.0)
        except asyncio.TimeoutError:
            logger.warning("LLM Timeout — emitting system busy signal.")
            reply = "Give me just one moment..."
        except Exception:
            reply = None

        if reply:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": reply})
            if len(self.history) > 8: self.history = self.history[-8:]
            
            frame_out = AgentTextFrame(reply, language=self.current_language)
            frame_out.gen_id = self._current_gen_id # TAG THE REPLY
            await self.push_frame(frame_out, direction)


class RealEstateSTTProcessor(FrameProcessor):
    """Low-latency STT with Adaptive VAD (Noise Floor Calibration)."""

    def __init__(self):
        super().__init__()
        self.audio_buffer = bytearray()
        self.min_chunk_bytes = _ms_to_bytes(stt_cfg.MIN_CHUNK_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.max_chunk_bytes = _ms_to_bytes(stt_cfg.MAX_CHUNK_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.trailing_window_bytes = _ms_to_bytes(stt_cfg.TRAILING_SILENCE_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.last_emitted_text = ""
        self.last_emit_at = 0.0
        # 6. ADAPTIVE VAD (Continuous Calibration)
        self.noise_floor = 0.010 # Start low and adapt
        self._rms_history = []

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        await super().process_frame(frame, direction)
        if not isinstance(frame, AudioRawFrame):
            await self.push_frame(frame, direction)
            return

        pcm16 = _ensure_pcm16(frame.audio, frame.sample_rate, stt_cfg.TARGET_SAMPLE_RATE)
        if not pcm16: return

        # Calculate current RMS
        samples = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
        chunk_rms = float(np.sqrt(np.mean(samples**2)) / 32768.0)
        
        # Continuous Calibration: Track bottom 10% of energy as noise floor
        self._rms_history.append(chunk_rms)
        if len(self._rms_history) > 50: # tracking ~1s window for faster startup
            self._rms_history.pop(0)
            self.noise_floor = float(np.percentile(self._rms_history, 10))
        
        # threshold = noise_floor + safety_margin
        # Use a more sensitive safety margin (0.01) if floor is low
        dynamic_threshold = self.noise_floor + 0.012

        if chunk_rms > dynamic_threshold and not self.is_speaking:
            self.is_speaking = True
            logger.info("[PIPELINE] STT -> Voice Detected (RMS=%.4f, Floor=%.4f). Emitting CancelFrame.", chunk_rms, self.noise_floor)
            await self.push_frame(CancelFrame(), direction)

        self.audio_buffer.extend(pcm16)
        if len(self.audio_buffer) < self.min_chunk_bytes:
            return

        if len(self.audio_buffer) < self.max_chunk_bytes and not _has_trailing_silence(
            self.audio_buffer,
            self.trailing_window_bytes,
            dynamic_threshold,
        ):
            return

        chunk = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        
        try:
            # 2. CIRCUIT BREAKER (STT Timeout)
            async with _ml_semaphore:
                text = await asyncio.wait_for(
                    asyncio.get_running_loop().run_in_executor(_executor, transcribe_audio, chunk),
                    timeout=3.5
                )
        except asyncio.TimeoutError:
            logger.error("STT Timeout (Skipping chunk)")
            return
        except Exception:
            return
            
        normalized_text = _normalize_text(text)
        if not normalized_text or len(normalized_text) < stt_cfg.MIN_TRANSCRIPT_CHARS:
            return

        now = time.monotonic()
        if _is_duplicate_text(text, self.last_emitted_text) and (now - self.last_emit_at) < stt_cfg.DUPLICATE_TEXT_WINDOW_S:
            return

        self.last_emitted_text = text
        self.last_emit_at = now
        self.is_speaking = False
        await self.push_frame(TextFrame(text), direction)


class RealEstateTTSProcessor(FrameProcessor):
    """Turn assistant text into speech, tagged with generation_id for client-side filtering."""

    def __init__(self):
        super().__init__()
        self.last_reply = ""
        self.last_reply_at = 0.0
        self._tts_task = None
        self._active_gen_id = 0

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        await super().process_frame(frame, direction)
        
        if isinstance(frame, CancelFrame):
            logger.info("[PIPELINE] TTS -> Caught CancelFrame. Stopping current task.")
            if self._tts_task and not self._tts_task.done():
                self._tts_task.cancel()
            await self.push_frame(frame, direction)
            return

        if not isinstance(frame, TextFrame):
            await self.push_frame(frame, direction)
            return

        # Read the gen_id injected by the LLM layer
        gen_id = getattr(frame, "gen_id", 0)
        self._active_gen_id = gen_id

        text = frame.text.strip()
        now = time.monotonic()
        if not text or (_is_duplicate_text(text, self.last_reply) and (now - self.last_reply_at) < 1.5):
            return

        preferred_language = getattr(frame, "language", None)
        logger.info("[PIPELINE] TTS -> gen_id=%d text=%s", gen_id, text)
        
        await self.push_frame(frame, direction)
        
        if self._tts_task and not self._tts_task.done():
            self._tts_task.cancel()
            
        self._tts_task = asyncio.create_task(self._run_tts(text, preferred_language, gen_id, direction))
        
    async def _run_tts(self, text, preferred_lang, gen_id, direction):
        speech_gen = generate_speech_stream(text, preferred_lang)
        if not speech_gen: return

        try:
            self.last_reply = text
            self.last_reply_at = time.monotonic()
            async with _ml_semaphore:
                while True:
                    # 2. CIRCUIT BREAKER (Executor Timeout)
                    try:
                        chunk_bytes = await asyncio.wait_for(
                            asyncio.get_running_loop().run_in_executor(_executor, _safe_next, speech_gen),
                            timeout=3.0
                        )
                    except asyncio.TimeoutError:
                        logger.error("TTS Generator Timeout (Timeout at source)")
                        break

                    if chunk_bytes is _GENERATOR_SENTINEL:
                        break
                    if chunk_bytes:
                        # 1. TAG AUDIO WITH GEN ID
                        out_frame = AudioRawFrame(audio=chunk_bytes, sample_rate=24000, num_channels=1)
                        out_frame.gen_id = gen_id
                        await self.push_frame(out_frame, direction)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("[PIPELINE] TTS -> Error: %s", exc)


def _ms_to_bytes(duration_ms: int, sample_rate: int) -> int:
    return int(sample_rate * (duration_ms / 1000.0) * 2)


def _ensure_pcm16(audio: bytes, source_rate: int, target_rate: int) -> bytes:
    samples = np.frombuffer(audio, dtype=np.int16)
    if samples.size == 0:
        return b""
    if source_rate == target_rate:
        return audio

    gcd = np.gcd(source_rate, target_rate)
    up = target_rate // gcd
    down = source_rate // gcd
    resampled = resample_poly(samples.astype(np.float32), up, down)
    resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
    return resampled.tobytes()


def _has_trailing_silence(audio_buffer: bytearray, trailing_window_bytes: int, threshold: float) -> bool:
    if len(audio_buffer) < trailing_window_bytes:
        return False
    tail = np.frombuffer(bytes(audio_buffer[-trailing_window_bytes:]), dtype=np.int16).astype(np.float32) / 32768.0
    if tail.size == 0:
        return False
    rms = float(np.sqrt(np.mean(np.square(tail))))
    return rms <= threshold


def _normalize_text(text: str) -> str:
    cleaned = text.casefold()
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in cleaned)
    return " ".join(cleaned.split())


def _is_duplicate_text(current: str, previous: str) -> bool:
    current_norm = _normalize_text(current)
    previous_norm = _normalize_text(previous)
    if not current_norm or not previous_norm:
        return False
    if current_norm == previous_norm:
        return True
    if current_norm in previous_norm or previous_norm in current_norm:
        return True
    return SequenceMatcher(None, current_norm, previous_norm).ratio() >= 0.88
