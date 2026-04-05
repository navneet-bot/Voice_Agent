"""
STT configuration constants.

All tunable parameters for the faster-whisper speech-to-text pipeline.
Change values here to adjust model size, quantization, VAD behaviour,
and language detection without touching any logic code.
"""

from typing import Optional

MODEL_SIZE: str = "small"          # tiny | base | small | medium
COMPUTE_TYPE: str = "int8"         # CPU-optimized quantization
BEAM_SIZE: int = 1                 # 1 = fastest (greedy); increase for accuracy
DEVICE: str = "cpu"
LANGUAGE: Optional[str] = None     # None = auto-detect (Hindi / Marathi / English)
VAD_FILTER: bool = True            # skip silent audio chunks via Silero VAD
MIN_SILENCE_MS: int = 300          # silence threshold in milliseconds
