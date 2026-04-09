"""
STT configuration constants.

All tunable parameters for the faster-whisper speech-to-text pipeline.
Change values here to adjust model size, quantization, VAD behaviour,
and language detection without touching any logic code.
"""

from typing import Optional

MODEL_SIZE: str = "base"          # tiny | base | small | medium
COMPUTE_TYPE: str = "int8"         # CPU-optimized quantization
BEAM_SIZE: int = 1                 # 1 = fastest (greedy); increase for accuracy
DEVICE: str = "cpu"
LANGUAGE: Optional[str] = None     # None = auto-detect (Hindi / Marathi / English)
VAD_FILTER: bool = True            # skip silent audio chunks via Silero VAD
MIN_SILENCE_MS: int = 200          # silence threshold in milliseconds

# Runtime buffering tuned for low-latency local voice calls
TARGET_SAMPLE_RATE: int = 16000
MIN_CHUNK_MS: int = 450
MAX_CHUNK_MS: int = 900
TRAILING_SILENCE_MS: int = 180
SILENCE_RMS_THRESHOLD: float = 0.012
MIN_TRANSCRIPT_CHARS: int = 2
DUPLICATE_TEXT_WINDOW_S: float = 3.0
ENERGY_THRESHOLD: float = 0.004  # RMS threshold for mic silence detection (very sensitive)
