"""Runtime processors for the local voice pipeline."""

import asyncio
from dataclasses import dataclass
from difflib import SequenceMatcher
import io
import logging
import time

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

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
from stt import config as stt_cfg

try:
    from stt.stt import transcribe_audio
except ImportError:
    logging.warning("stt.stt.transcribe_audio not available yet. Using mock STT.")

    def transcribe_audio(audio_chunk: bytes) -> str:
        return "mock transcription"

try:
    from tts import generate_speech
except ImportError:
    logging.warning("tts engine not found. Using mock TTS.")

    def generate_speech(text: str, preferred_language: str | None = None) -> bytes:
        return b""


logger = logging.getLogger(__name__)


@dataclass
class AgentTextFrame(TextFrame):
    language: str = "en"


class RealEstateLLMProcessor(FrameProcessor):
    """Turn user transcriptions into short, stable LLM responses."""

    def __init__(self):
        super().__init__()
        self.history: list[dict[str, str]] = []
        self.current_language = "en"
        self.last_user_text = ""
        self.last_user_at = 0.0

    async def process_frame(self, frame: Frame, direction: FrameDirection = None):  # type: ignore
        if not isinstance(frame, TextFrame):
            await super().process_frame(frame, direction)
            return

        user_text = frame.text.strip()
        if not user_text:
            return

        now = time.monotonic()
        if _is_duplicate_text(user_text, self.last_user_text) and (now - self.last_user_at) < stt_cfg.DUPLICATE_TEXT_WINDOW_S:
            logger.info("Skipping duplicate user turn: %s", user_text)
            return

        self.last_user_text = user_text
        self.last_user_at = now
        self.current_language = _detect_language_from_text(user_text, fallback=self.current_language)
        logger.info("LLM received text (%s): %s", self.current_language, user_text)

        reply = await asyncio.to_thread(
            generate_response,
            user_text,
            self.history,
            self.current_language,
        )
        if not reply:
            return

        self.history.append({"role": "user", "content": user_text})
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
        text = await asyncio.to_thread(transcribe_audio, chunk)
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
        wav_bytes = await asyncio.to_thread(generate_speech, text, preferred_language)
        if not wav_bytes:
            return

        try:
            data, samplerate = sf.read(io.BytesIO(wav_bytes))
            pcm16_data = (np.asarray(data, dtype=np.float32) * 32767).astype(np.int16).tobytes()
            self.last_reply = text
            self.last_reply_at = now
            await self.push_frame(
                AudioRawFrame(audio=pcm16_data, sample_rate=samplerate, num_channels=1),
                direction,
            )
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


def _detect_language_from_text(text: str, fallback: str = "en") -> str:
    if not text.strip():
        return fallback

    marathi_markers = ("आहे", "नाही", "माझ", "तुम्ह", "काय", "होय")
    hindi_markers = ("है", "नहीं", "मुझे", "आप", "क्या", "जी")

    if any("\u0900" <= ch <= "\u097F" for ch in text):
        if any(marker in text for marker in marathi_markers):
            return "mr"
        if any(marker in text for marker in hindi_markers):
            return "hi"
        return "hi"

    latin = text.casefold()
    if any(word in latin for word in ("aap", "apka", "apki", "haan", "nahi", "acha", "achha", "kya", "kaise")):
        return "hinglish"
    return fallback if fallback in {"en", "hi", "mr", "hinglish"} else "en"
