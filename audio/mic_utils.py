"""
Audio utility functions for recording, playback, and conversion using sounddevice.
Integration Note: Used by mic_conversation.py to handle microphone tasks.
"""

import logging
import io
import numpy as np
import sounddevice as sd
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def record_audio(duration_seconds: float, sample_rate: int = 16000) -> np.ndarray:
    """
    Record audio from the default microphone with energy-based early stop.
    Stops early if silence (RMS below threshold) is detected for 1.2s.
    """
    from stt.config import ENERGY_THRESHOLD
    chunk_size = 1024
    threshold = ENERGY_THRESHOLD  # Use config threshold
    silence_duration = 1.2        # Relaxed from 0.8s
    max_silent_chunks = int(silence_duration * sample_rate / chunk_size)
    
    recorded_chunks = []
    silent_chunks = 0
    speech_started = False
    
    print("\nListening (early stop enabled)...", end="", flush=True)
    
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='float32') as stream:
            for _ in range(int(duration_seconds * sample_rate / chunk_size)):
                chunk, overflowed = stream.read(chunk_size)
                recorded_chunks.append(chunk)
                
                # Check for silence (RMS)
                rms = np.sqrt(np.mean(chunk**2))
                
                if rms > threshold:
                    speech_started = True
                    silent_chunks = 0
                else:
                    silent_chunks += 1
                
                # If we've had enough silence AFTER speech started, stop early
                if speech_started and silent_chunks > max_silent_chunks:
                    print(" (detected end of speech)", end="", flush=True)
                    break
            
        print(" (done)")
        if not recorded_chunks:
            return np.array([], dtype='float32')
        return np.concatenate(recorded_chunks).flatten()
        
    except Exception as e:
        logger.error(f"[ERROR] Microphone recording failed: {e}")
        return np.array([], dtype='float32')

def play_audio(audio_bytes: bytes, sample_rate: int = 24000) -> None:
    """
    Play audio bytes through the default speaker using sounddevice.
    """
    if not audio_bytes:
        logger.warning("[WARN] Empty audio bytes provided for playback.")
        return

    try:
        # Load audio bytes into numpy array using soundfile
        byte_io = io.BytesIO(audio_bytes)
        audio_data, sr = sf.read(byte_io, dtype='float32')
        
        # Squeeze stereo to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        sd.play(audio_data, samplerate=sr)
        sd.wait()
    except Exception as e:
        logger.warning(f"[WARN] Playback failed: {e}")

def convert_to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    """
    Convert a float32 numpy array to PCM16 WAV bytes using soundfile.
    """
    if audio.size == 0:
        return b""
        
    try:
        buffer = io.BytesIO()
        # soundfile handles the PCM16 conversion internally if subtype is set or implied
        sf.write(buffer, audio, sample_rate, format='WAV', subtype='PCM_16')
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"Failed to convert to WAV: {e}")
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
