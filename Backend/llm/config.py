"""
LLM configuration constants.

All tunable parameters for the LLM (Groq) integration.
Change values here to adjust model, temperature, token limits, etc.
without touching any logic code.

Set GROQ_API_KEY via the environment variable:
  Windows:  $env:GROQ_API_KEY = "your_key_here"
  Linux:    export GROQ_API_KEY="your_key_here"
"""

import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env if it exists

# ── API ────────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# ── Model ──────────────────────────────────────────────────────────────────────
# Available Groq models (fast, free-tier):
#   "llama-3.1-8b-instant"   - fastest, low latency 
#   "llama-3.3-70b-versatile"  - most capable
#   "mixtral-8x7b-32768" - 32k context
MODEL_NAME: str = "llama-3.1-8b-instant"

# ── Generation Parameters ──────────────────────────────────────────────────────
TEMPERATURE: float = 0.0       # deterministic replies for stable script following
MAX_TOKENS: int = 80           # short voice turns reduce latency and rambling
TOP_P: float = 0.9             # slight nucleus cap for consistency

# ── Retry & Timeout ────────────────────────────────────────────────────────────
REQUEST_TIMEOUT_S: int = 8     # Max seconds to wait for a Groq response
MAX_RETRIES: int = 2           # Number of retries on transient failure

# Runtime response shaping
MAX_HISTORY_MESSAGES: int = 8
MAX_RESPONSE_SENTENCES: int = 2
MAX_RESPONSE_WORDS: int = 25

# Phrase-constrained LLM response composition
PHRASE_RESPONSE_MAX_TOKENS: int = 120
PHRASE_RESPONSE_TEMPERATURE: float = 0.3

# ── Supported Languages ────────────────────────────────────────────────────────
# Matches the STT module's language support
SUPPORTED_LANGUAGES: list[str] = ["en", "hi", "mr", "hinglish"]
DEFAULT_LANGUAGE: str = "en"
