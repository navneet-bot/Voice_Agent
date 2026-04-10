"""
Speech-to-Text module powered by Groq Cloud API.

Replaces local CPU-bound faster-whisper with lightning-fast cloud offloading.
Latency target is <200ms per audio chunk.
"""

import io
import logging
import time
import wave

import numpy as np
import scipy.io.wavfile as wavfile
from groq import Groq

from llm.config import GROQ_API_KEY
from . import config

logger = logging.getLogger(__name__)

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. STT cannot start.")

_client = Groq(api_key=GROQ_API_KEY)


def _bytes_to_pcm16(audio_bytes: bytes) -> np.ndarray:
    """Convert raw audio bytes to a 16-bit PCM NumPy array.
    Supports WAV container, Float32, and raw PCM16 formats.
    """
    if audio_bytes[:4] == b"RIFF":
        sample_rate, data = wavfile.read(io.BytesIO(audio_bytes))
        if data.dtype == np.int16:
            return data
        if data.dtype == np.float32:
            return (np.clip(data, -1.0, 1.0) * 32767).astype(np.int16)
        return (data.astype(np.float32) * 32767).astype(np.int16)

    if len(audio_bytes) % 4 == 0:
        candidate = np.frombuffer(audio_bytes, dtype=np.float32)
        if candidate.size > 0 and np.max(np.abs(candidate)) <= 1.0:
            clipped = np.clip(candidate, -1.0, 1.0)
            return (clipped * 32767).astype(np.int16)

    # Default PCM16 fallback
    return np.frombuffer(audio_bytes, dtype=np.int16)


def transcribe_audio(audio_chunk: bytes) -> str:
    """Transcribe a short audio chunk to text using Groq Cloud STT.

    Accepts raw audio bytes (16 kHz, mono) and routes it to `whisper-large-v3-turbo`.
    """
    if not audio_chunk:
        return ""

    try:
        pcm_array = _bytes_to_pcm16(audio_chunk)
    except Exception:
        logger.warning("Failed to decode audio bytes.")
        return ""

    if pcm_array.size == 0:
        return ""

    # Generate an explicitly formatted WAV container strictly in-memory
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) # 16-bit
        wf.setframerate(config.TARGET_SAMPLE_RATE)
        wf.writeframes(pcm_array.tobytes())
    
    buffer.name = "chunk.wav"  # Required by API for MIME type extraction

    try:
        t0 = time.perf_counter()
        buffer.seek(0)
        
        kwargs = {
            "file": (buffer.name, buffer.read()),
            "model": "whisper-large-v3-turbo",
            "response_format": "json"
        }
        
        # Lock language ONLY if strictly set in config, otherwise auto-detect for code-mixing
        if config.LANGUAGE:
            kwargs["language"] = config.LANGUAGE

        transcription = _client.audio.transcriptions.create(**kwargs)
        
        latency = time.perf_counter() - t0
        text = transcription.text.strip()
        
        if text:
            logger.info("STT (Groq Cloud) produced '%s' in %.3fs", text, latency)
        return text

    except Exception as e:
        logger.exception("Groq Transcription failed: %s", e)
        return ""
