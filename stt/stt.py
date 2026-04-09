"""
Speech-to-Text module powered by faster-whisper.

Why faster-whisper over openai-whisper
--------------------------------------
faster-whisper uses the CTranslate2 inference engine, which provides:
  - 4x lower memory footprint compared to the original openai-whisper.
  - 2-4x faster CPU inference through INT8 quantization and optimised
    CTranslate2 kernels, making real-time voice agent latency feasible
    without a GPU.

Why the "small" model
---------------------
  - tiny / base: Poor accuracy on Hindi and Marathi; frequent
    hallucinations and missed words in code-mixed speech.
  - medium: Accurate but too slow on CPU (~2-3 s per chunk), breaking
    the real-time latency budget.
  - small + int8: Best balance — accurate multilingual transcription
    within 0.3-0.8 s per 1-3 s audio chunk on a modern CPU.

How to swap models
------------------
Edit MODEL_SIZE and COMPUTE_TYPE in stt/config.py.  No changes to this
file are required.  For example, switch to "medium" + "float32" if you
move to a GPU-backed deployment and need higher accuracy.

Latency target
--------------
0.3-0.8 seconds per 1-3 second audio chunk on CPU (Apple M-series or
modern x86-64 with AVX2).
"""

import io
import logging
import time

import numpy as np
import scipy.io.wavfile as wavfile
from faster_whisper import WhisperModel

from . import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model initialisation — happens once at import time so every subsequent
# call to transcribe_audio() reuses the same loaded weights.
# ---------------------------------------------------------------------------
_model = WhisperModel(
    config.MODEL_SIZE,
    device=config.DEVICE,
    compute_type=config.COMPUTE_TYPE,
)


def _bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Convert raw audio bytes to a float32 NumPy array normalised to [-1, 1].

    Supports three input formats:
      1. WAV container (starts with RIFF header) — parsed via scipy.
      2. Raw PCM 16-bit signed integers (16 kHz, mono).
      3. Raw 32-bit floats (16 kHz, mono).

    The heuristic for distinguishing (2) and (3) is byte-length divisibility:
    PCM16 frames are 2 bytes each, float32 frames are 4 bytes each.  If the
    length is divisible by 4 but the sample magnitudes exceed [-1, 1] it is
    treated as PCM16.

    Args:
        audio_bytes: Raw audio data as bytes.

    Returns:
        1-D float32 NumPy array with samples in [-1, 1].
    """
    # --- WAV container ---
    if audio_bytes[:4] == b"RIFF":
        sample_rate, data = wavfile.read(io.BytesIO(audio_bytes))
        if data.dtype == np.int16:
            return data.astype(np.float32) / 32768.0
        if data.dtype == np.float32:
            return data
        # Fallback for other WAV bit-depths
        return data.astype(np.float32) / np.iinfo(data.dtype).max

    # --- Raw float32 ---
    if len(audio_bytes) % 4 == 0:
        candidate = np.frombuffer(audio_bytes, dtype=np.float32)
        # float32 audio sits in [-1, 1]; PCM16 reinterpreted as float32 won't
        if candidate.size > 0 and np.max(np.abs(candidate)) <= 1.0:
            return candidate

    # --- Raw PCM16 (default) ---
    return np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_audio(audio_chunk: bytes) -> str:
    """Transcribe a short audio chunk to text.

    Accepts raw audio bytes (16 kHz, mono — PCM16, float32, or WAV) and
    returns the transcribed string.  Returns an empty string for silence,
    empty input, or when no speech is detected.

    Args:
        audio_chunk: Raw audio bytes.  Expected sample rate is 16 kHz,
                     mono channel.  Supports PCM 16-bit signed, 32-bit
                     float, and WAV container formats.

    Returns:
        Transcribed text as a plain string, or "" if nothing was
        recognised.
    """
    if not audio_chunk:
        return ""

    try:
        audio_array = _bytes_to_float32(audio_chunk)
    except Exception:
        logger.warning("Failed to decode audio bytes — returning empty string.")
        return ""

    if audio_array.size == 0:
        return ""

    try:
        t0 = time.perf_counter()
        segments, _info = _model.transcribe(
            audio_array,
            language=config.LANGUAGE,         # None = auto-detect
            beam_size=config.BEAM_SIZE,       # 1 = greedy search, fastest
            vad_filter=config.VAD_FILTER,     # Silero VAD skips non-speech frames
            condition_on_previous_text=False, # reduce repeated text across chunked turns
            vad_parameters=dict(
                min_silence_duration_ms=config.MIN_SILENCE_MS,
            ),
        )

        # segments is a generator — materialise and join texts
        text_parts = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
        text = " ".join(text_parts).strip()
        latency = time.perf_counter() - t0
        if text:
            logger.info("STT produced '%s' in %.3fs", text, latency)
        return text

    except Exception:
        logger.exception("Transcription failed — returning empty string.")
        return ""
