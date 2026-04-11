"""Runtime processors for the local voice pipeline."""

import asyncio
from dataclasses import dataclass
from difflib import SequenceMatcher
import logging
import time
import concurrent.futures

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)
_ml_semaphore = asyncio.Semaphore(4)

try:
    from pipecat.frames.frames import AudioRawFrame, Frame, TextFrame
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
except ImportError:
    logging.error("pipecat-ai is not installed. Pipeline will fail.")
    FrameProcessor = object
    FrameDirection = None
    Frame = None
    TextFrame = None
    AudioRawFrame = None

from llm.llm import generate_response
from llm.language_utils import LanguageTracker, analyze_user_text
from llm.state_manager import StateManager
from llm.pipeline_logger import pipeline_logger
from pipecat.frames.frames import StartFrame
from stt import config as stt_cfg

STATE_SCHEMA_PATH = "Updated_Real_Estate_Agent.json"
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
    """Turn user transcriptions into short, stable LLM responses and manage node states."""

    def __init__(self):
        super().__init__()
        self.history: list[dict[str, str]] = []
        self.current_language = "en"
        self.language_tracker = LanguageTracker(initial_language=self.current_language)
        self.last_user_text = ""
        self.last_user_at = 0.0
        self._booted = False
        self.state_manager = StateManager(STATE_SCHEMA_PATH)

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        if isinstance(frame, StartFrame) and not self._booted:
            self._booted = True
            self.state_manager.reset_state()
            pipeline_logger.log_event("call_started", {"start_node": self.state_manager.start_node_id})
            
            logger.info("Triggering initial greeting from StateManager...")
            reply = await generate_response(
                user_text=CALL_CONNECTED_TRIGGER,
                conversation_history=self.history,
                language=self.current_language,
                state_manager=self.state_manager,
                allow_transition=False,
            )
            if reply:
                self.history.append({"role": "assistant", "content": reply})
                pipeline_logger.log_event("agent_reply", {"content": reply, "node": self.state_manager.current_node_id})
                await self.push_frame(AgentTextFrame(reply, language=self.current_language), direction)
                
            await super().process_frame(frame, direction)
            return
        if not isinstance(frame, TextFrame):
            await super().process_frame(frame, direction)
            return

        user_text = frame.text.strip()
        if not user_text:
            return

        user_analysis = analyze_user_text(user_text, fallback=self.current_language)
        if not user_analysis.actionable:
            logger.info("Ignoring unclear transcript (%s): %s", user_analysis.reason, user_text)
            return
        user_text = user_analysis.cleaned_text

        now = time.monotonic()
        if _is_duplicate_text(user_text, self.last_user_text) and (now - self.last_user_at) < stt_cfg.DUPLICATE_TEXT_WINDOW_S:
            logger.info("Skipping duplicate user turn: %s", user_text)
            return

        self.last_user_text = user_text
        self.last_user_at = now
        self.current_language, _ = self.language_tracker.observe(user_text)
        logger.info("LLM received text (%s): %s", self.current_language, user_text)
        
        pipeline_logger.log_event("user_reply", {"content": user_text, "node": self.state_manager.current_node_id})

        reply = await generate_response(
            user_text,
            self.history,
            self.current_language,
            state_manager=self.state_manager
        )
        self.history.append({"role": "user", "content": user_text})
        if not reply:
            if len(self.history) > 8:
                self.history = self.history[-8:]
            return

        pipeline_logger.log_event("agent_reply", {"content": reply, "node": self.state_manager.current_node_id})
        
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 8:
            self.history = self.history[-8:]

        await self.push_frame(AgentTextFrame(reply, language=self.current_language), direction)


class RealEstateSTTProcessor(FrameProcessor):
    """Low-latency STT chunker with resampling and duplicate suppression."""

    def __init__(self):
        super().__init__()
        self.audio_buffer = bytearray()
        self.min_chunk_bytes = _ms_to_bytes(stt_cfg.MIN_CHUNK_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.max_chunk_bytes = _ms_to_bytes(stt_cfg.MAX_CHUNK_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.trailing_window_bytes = _ms_to_bytes(stt_cfg.TRAILING_SILENCE_MS, stt_cfg.TARGET_SAMPLE_RATE)
        self.last_emitted_text = ""
        self.last_emit_at = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        if not isinstance(frame, AudioRawFrame):
            await super().process_frame(frame, direction)
            return

        pcm16 = _ensure_pcm16(frame.audio, frame.sample_rate, stt_cfg.TARGET_SAMPLE_RATE)
        if not pcm16:
            return

        self.audio_buffer.extend(pcm16)
        if len(self.audio_buffer) < self.min_chunk_bytes:
            return

        if len(self.audio_buffer) < self.max_chunk_bytes and not _has_trailing_silence(
            self.audio_buffer,
            self.trailing_window_bytes,
            stt_cfg.SILENCE_RMS_THRESHOLD,
        ):
            return

        chunk = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        
        async with _ml_semaphore:
            text = await asyncio.get_running_loop().run_in_executor(_executor, transcribe_audio, chunk)
            
        normalized_text = _normalize_text(text)
        if not normalized_text or len(normalized_text) < stt_cfg.MIN_TRANSCRIPT_CHARS:
            return

        now = time.monotonic()
        if _is_duplicate_text(text, self.last_emitted_text) and (now - self.last_emit_at) < stt_cfg.DUPLICATE_TEXT_WINDOW_S:
            logger.info("Skipping duplicate STT chunk: %s", text)
            return

        self.last_emitted_text = text
        self.last_emit_at = now
        await self.push_frame(TextFrame(text), direction)


class RealEstateTTSProcessor(FrameProcessor):
    """Turn assistant text into PCM audio with minimal extra latency."""

    def __init__(self):
        super().__init__()
        self.last_reply = ""
        self.last_reply_at = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        if not isinstance(frame, TextFrame):
            await super().process_frame(frame, direction)
            return

        text = frame.text.strip()
        now = time.monotonic()
        if not text:
            return
        if _is_duplicate_text(text, self.last_reply) and (now - self.last_reply_at) < 1.5:
            return

        preferred_language = getattr(frame, "language", None)
        logger.info("TTS synthesizing (%s): %s", preferred_language or "auto", text)
        
        speech_gen = generate_speech_stream(text, preferred_language)
        if not speech_gen:
            return

        try:
            self.last_reply = text
            self.last_reply_at = now
            async with _ml_semaphore:
                while True:
                    try:
                        chunk_bytes = await asyncio.get_running_loop().run_in_executor(_executor, next, speech_gen)
                        if chunk_bytes:
                            await self.push_frame(
                                AudioRawFrame(audio=chunk_bytes, sample_rate=24000, num_channels=1),
                                direction,
                            )
                    except StopIteration:
                        break
        except Exception as exc:
            logger.error("Error converting TTS audio: %s", exc)


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
