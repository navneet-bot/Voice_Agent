"""
STT configuration constants.

All tunable parameters for the faster-whisper speech-to-text pipeline.
Change values here to adjust model size, quantization, VAD behaviour,
and language detection without touching any logic code.
"""

from typing import Optional

LANGUAGE: Optional[str] = None     # None = auto-detect (Hindi / Marathi / English)

# Runtime buffering tuned for low-latency local voice calls
TARGET_SAMPLE_RATE: int = 16000
MIN_CHUNK_MS: int = 450
MAX_CHUNK_MS: int = 900
TRAILING_SILENCE_MS: int = 180
SILENCE_RMS_THRESHOLD: float = 0.012
MIN_TRANSCRIPT_CHARS: int = 1
DUPLICATE_TEXT_WINDOW_S: float = 3.0
ENERGY_THRESHOLD: float = 0.015  # Raised to 0.015 to reject background hum/noise
