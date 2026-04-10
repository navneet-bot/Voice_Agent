"""
TTS module powered by Microsoft Edge-TTS API.

Replaces local CPU-bound Kokoro engine with a fully cloud-hosted API.
Features a charismatic Indian-English bilingual voice natively.
Latency target is immediate stream yield.
"""

import asyncio
import logging
import io
import warnings

import edge_tts
import numpy as np

logger = logging.getLogger(__name__)

# The user requested a charismatic Indian female voice that can speak English/Hindi
DEFAULT_VOICE = "en-IN-NeerjaNeural"

def generate_speech_stream(text: str, preferred_language: str | None = None):
    """
    Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly plugs
    into the existing mic_conversation.py and flows/runtime.py pipeline loops without async breakage.
    """
    if not text or not text.strip():
        yield b""
        return

    # Edge-TTS streams mp3 chunks usually. We must decode them to raw PCM16 for Pipecat/sounddevice.
    # We will use miniaudio to decode the mp3 payloads in memory instantly.
    try:
        import miniaudio
    except ImportError:
        logger.error("miniaudio not installed. Please `pip install miniaudio` for Edge TTS streaming.")
        yield b""
        return

    try:
        # Run asynchronously and collect stream blocks
        communicate = edge_tts.Communicate(text, DEFAULT_VOICE)
        
        # Helper to run async Edge-TTS stream in an isolated sync loop
        async def _collect_mp3():
            audio_buffer = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.extend(chunk["data"])
            return bytes(audio_buffer)

        # Execute
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We are presumably inside an executor thread 
                # (via run_in_executor in flows/runtime) so we need a new loop or just to run it
                new_loop = asyncio.new_event_loop()
                mp3_bytes = new_loop.run_until_complete(_collect_mp3())
                new_loop.close()
            else:
                mp3_bytes = loop.run_until_complete(_collect_mp3())
        except RuntimeError:
            mp3_bytes = asyncio.run(_collect_mp3())

        if not mp3_bytes:
            yield b""
            return

        # Convert the MP3 bytes payload directly into 24kHz PCM16 using miniaudio
        decoded_audio = miniaudio.decode(mp3_bytes, sample_rate=24000, nchannels=1)
        
        # Extract native byte stream
        pcm_bytes = bytes(decoded_audio.samples)

        # Yield in sensible chunks (e.g. 4096 bytes) for streaming
        chunk_size = 4096
        for i in range(0, len(pcm_bytes), chunk_size):
            yield pcm_bytes[i:i + chunk_size]

    except Exception as e:
        logger.error("Edge TTS Cloud Generation failed: %s", e)
        yield b""
