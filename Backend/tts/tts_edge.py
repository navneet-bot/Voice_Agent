"""
TTS module powered by Microsoft Edge-TTS API.

Replaces local CPU-bound engine with a fully cloud-hosted API.
Features a charismatic Indian-English bilingual voice natively.
Latency target is immediate stream yield.
"""

from __future__ import annotations

import asyncio
import logging
import io
import time
import warnings
from collections import deque

import edge_tts
import numpy as np

from tts.config import EDGE_SPEECH_RATE
from metrics.provider_metrics import record_provider_metric

logger = logging.getLogger(__name__)
_tts_ttfb_samples = deque(maxlen=200)
_tts_total_samples = deque(maxlen=200)


def _percentile(values, percentile: float) -> float:
    """Return a simple nearest-rank percentile for small rolling samples."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[index]


def _record_tts_latency(
    *,
    provider: str,
    voice: str,
    ttfb_s: float,
    total_s: float,
    chunks: int,
    bytes_out: int,
) -> None:
    _tts_ttfb_samples.append(ttfb_s)
    _tts_total_samples.append(total_s)
    logger.info(
        "[TTS METRICS] provider=%s voice=%s ttfb_ms=%.1f total_ms=%.1f "
        "p50_total_ms=%.1f p95_total_ms=%.1f chunks=%d bytes=%d samples=%d",
        provider,
        voice,
        ttfb_s * 1000.0,
        total_s * 1000.0,
        _percentile(_tts_total_samples, 0.50) * 1000.0,
        _percentile(_tts_total_samples, 0.95) * 1000.0,
        chunks,
        bytes_out,
        len(_tts_total_samples),
    )
    record_provider_metric("tts_ttfb", provider, ttfb_s * 1000.0)
    record_provider_metric("tts_total", provider, total_s * 1000.0)

VOICE_MAP = {
    "en": "en-IN-NeerjaExpressiveNeural",
    "hi": "hi-IN-SwaraNeural",
    "hinglish": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural"
}

DEFAULT_VOICE = VOICE_MAP["en"]

def generate_speech_stream(text: str, preferred_language: str | None = None):
    """
    Synchronous wrapper that yields PCM16 bytes chunks sequentially.
    Uses language-aware voice selection to ensure correct pronunciation.
    """
    if not text or not text.strip():
        yield b""
        return
    started_at = time.perf_counter()
    first_yield_at = None
    chunk_count = 0
    bytes_out = 0

    # Select the best voice for the active language
    voice = VOICE_MAP.get(preferred_language, DEFAULT_VOICE)
    if preferred_language == "mr" and "mr-IN" not in voice:
         voice = VOICE_MAP["mr"]
    elif preferred_language in ("hi", "hinglish") and "hi-IN" not in voice:
         voice = VOICE_MAP["hi"]

    # ── Text normalisation for faster-paced speech ──────────────────────
    # Expand abbreviations and clean up text so the neural voice stays
    # clear even at an elevated speaking rate.
    try:
        from tts.speech_formatter import optimize_for_tts
        text = optimize_for_tts(text)
    except Exception:
        logger.debug("speech_formatter unavailable, using raw text")

    # Edge-TTS streams mp3 chunks usually. We must decode them to raw PCM16 for Pipecat/sounddevice.
    # We will use soundfile (libsndfile) to decode the mp3 payloads in memory.
    try:
        import soundfile as sf
    except ImportError:
        logger.error("soundfile not installed. Please `pip install soundfile`.")
        yield b""
        return

    try:
        logger.info(f"[TTS] Started synthesis for text length: {len(text)}, voice: {voice}")
        # Run asynchronously and collect stream blocks.
        communicate = edge_tts.Communicate(text, voice, rate=EDGE_SPEECH_RATE)
        
        async def _collect_mp3():
            try:
                audio_buffer = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.extend(chunk["data"])
                logger.info("[TTS] Edge TTS received mp3 stream of %d bytes", len(audio_buffer))
                return bytes(audio_buffer)
            except Exception as e:
                logger.exception("[TTS] Edge TTS _collect_mp3 failed internally: %s", e)
                return b""

        # Execute — always use asyncio.run() since this function is called
        # from a ThreadPoolExecutor where no event loop is running.
        mp3_bytes = asyncio.run(_collect_mp3())

        if not mp3_bytes:
            logger.error("[TTS] Edge TTS mp3_bytes is empty.")
            yield b""
            return

        # Decode MP3 to PCM using soundfile (which supports MP3 since v1.1.0)
        logger.info("[TTS] Decoding MP3 with soundfile...")
        try:
            with io.BytesIO(mp3_bytes) as mp3_file:
                # We explicitly specify the format to help soundfile
                data, samplerate = sf.read(mp3_file)
            logger.info("[TTS] Completed: Soundfile decoded MP3 to PCM. shape=%s samplerate=%d duration=%.2fs", data.shape, samplerate, len(data)/samplerate)
        except Exception as sfe:
            logger.exception("[TTS] ERROR: Soundfile sf.read failed internally! This often means libsndfile lacks MP3 support in the deployed OS. Error: %s", sfe)
            yield b""
            return

        # Apply a 50ms fade-in and fade-out to prevent audio pops/clicks at start and end
        fade_samples = int(samplerate * 0.05)
        if len(data) > fade_samples * 2:
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            if data.ndim == 1:
                data[:fade_samples] *= fade_in
                data[-fade_samples:] *= fade_out
            else:
                data[:fade_samples, :] *= fade_in[:, np.newaxis]
                data[-fade_samples:, :] *= fade_out[:, np.newaxis]
        
        # soundfile returns float arrays. Convert to PCM16.
        # Ensure we target 24000Hz if the output wasn't already (though Edge usually is)
        pcm16 = (data * 32767).astype(np.int16)
        pcm_bytes = pcm16.tobytes()

        # Yield in sensible chunks (e.g. 4096 bytes) for streaming
        chunk_size = 4096
        logger.info(f"[TTS] Audio Bytes Generated: {len(pcm_bytes)} bytes. Beginning chunking.")
        for i in range(0, len(pcm_bytes), chunk_size):
            chunk = pcm_bytes[i:i + chunk_size]
            if first_yield_at is None:
                first_yield_at = time.perf_counter()
            chunk_count += 1
            bytes_out += len(chunk)
            # logger.info("[TTS] Yielding PCM chunk %d, size %d", chunk_count, len(chunk))
            yield chunk
            
        logger.info(f"[TTS] Completed yielding {chunk_count} chunks, total bytes: {bytes_out}.")

        total_s = time.perf_counter() - started_at
        ttfb_s = (first_yield_at - started_at) if first_yield_at is not None else total_s
        _record_tts_latency(
            provider="edge",
            voice=voice,
            ttfb_s=ttfb_s,
            total_s=total_s,
            chunks=chunk_count,
            bytes_out=bytes_out,
        )

    except Exception as e:
        logger.exception("Edge TTS Cloud Generation failed: %s", e)
        yield b""
