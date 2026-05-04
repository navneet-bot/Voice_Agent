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
import warnings

import edge_tts
import numpy as np

from tts.config import EDGE_SPEECH_RATE

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-IN-NeerjaExpressiveNeural"

def generate_speech_stream(text: str, preferred_language: str | None = None):
    """
    Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly plugs
    into the existing mic_conversation.py and flows/runtime.py pipeline loops without async breakage.
    """
    if not text or not text.strip():
        yield b""
        return

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
        # Run asynchronously and collect stream blocks.
        communicate = edge_tts.Communicate(text, DEFAULT_VOICE, rate=EDGE_SPEECH_RATE)
        
        async def _collect_mp3():
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            return bytes(audio_buffer)

        # Execute — always use asyncio.run() since this function is called
        # from a ThreadPoolExecutor where no event loop is running.
        mp3_bytes = asyncio.run(_collect_mp3())

        if not mp3_bytes:
            yield b""
            return

        # Decode MP3 to PCM using soundfile (which supports MP3 since v1.1.0)
        with io.BytesIO(mp3_bytes) as mp3_file:
            # We explicitly specify the format to help soundfile
            data, samplerate = sf.read(mp3_file)

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
        for i in range(0, len(pcm_bytes), chunk_size):
            yield pcm_bytes[i:i + chunk_size]

    except Exception as e:
        logger.error("Edge TTS Cloud Generation failed: %s", e)
        yield b""
