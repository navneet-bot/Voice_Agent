"""
Audio utility functions for recording, playback, and conversion using sounddevice.
Integration Note: Used by mic_conversation.py to handle microphone tasks.
"""

import logging
import io
import numpy as np
import sounddevice as sd
from scipy.io import wavfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def record_audio(duration_seconds: float, sample_rate: int = 16000) -> np.ndarray:
    """
    Record audio from the default microphone using sounddevice.

    Args:
        duration_seconds (float): Length of the recording in seconds.
        sample_rate (int): Sampling rate in Hz. Defaults to 16000.

    Returns:
        np.ndarray: Mono audio data as float32 array.

    Error Behavior: Logs [ERROR] and returns an empty float32 array on sounddevice failure.
    """
    try:
        # Record audio
        recording = sd.rec(
            int(duration_seconds * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()  # Wait for recording to finish
        return recording.flatten()
    except Exception as e:
        logger.error(f"[ERROR] Microphone recording failed: {e}")
        return np.array([], dtype='float32')

def play_audio(audio_bytes: bytes, sample_rate: int = 24000) -> None:
    """
    Play audio bytes through the default speaker using sounddevice.

    Args:
        audio_bytes (bytes): RAW or WAV bytes to play.
        sample_rate (int): Sampling rate in Hz. Defaults to 24000.

    Returns:
        None

    Error Behavior: Logs [WARN] and returns silently on empty bytes or decode error.
    """
    if not audio_bytes:
        logger.warning("[WARN] Empty audio bytes provided for playback.")
        return

    try:
        # Load WAV bytes into numpy array
        byte_io = io.BytesIO(audio_bytes)
        sr, audio_data = wavfile.read(byte_io)
        
        # Convert to float32 if integer
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32) / 32768.0

        # Squeeze stereo to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        sd.play(audio_data, samplerate=sr)
        sd.wait()
    except Exception as e:
        logger.warning(f"[WARN] Playback failed: {e}")

def convert_to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    """
    Convert a float32 numpy array to PCM16 WAV bytes in memory.

    Args:
        audio (np.ndarray): Float32 mono audio array.
        sample_rate (int): Sampling rate in Hz. Defaults to 16000.

    Returns:
        bytes: PCM16 WAV encoded bytes.

    Error Behavior: Returns empty bytes if audio is invalid.
    """
    if audio.size == 0:
        return b""
        
    try:
        # Ensure float32 range [-1, 1] and convert to PCM16
        audio_pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        
        buffer = io.BytesIO()
        wavfile.write(buffer, sample_rate, audio_pcm)
        return buffer.getvalue()
    except Exception:
        return b""

def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalize float32 audio array to [-1.0, 1.0] range.

    Args:
        audio (np.ndarray): Audio data array.

    Returns:
        np.ndarray: Normalized audio data.

    Error Behavior: Returns unchanged if already normalized, empty, or all zeros.
    """
    if audio.size == 0:
        return audio
        
    max_val = np.max(np.abs(audio))
    if max_val > 0.0:
        return audio / max_val
    return audio
