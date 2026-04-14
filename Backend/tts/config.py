# ---------------------------------------------------------------------------
# TTS Configuration — Kokoro-82M
# All tunable constants live here. No logic, no imports.
# ---------------------------------------------------------------------------

# ── Model ──────────────────────────────────────────────────────────────────
MODEL_NAME = "hexgrad/Kokoro-82M"
DEVICE = "cpu"

# ── Audio output ───────────────────────────────────────────────────────────
SAMPLE_RATE = 24000          # Hz — LiveKit and VoIP compatible
CHANNELS = 1                 # mono required for telephony

# ── Voice ──────────────────────────────────────────────────────────────────
VOICE_NAME = "af_heart"      # Kokoro voice preset (American female)

# Language → voice mapping (used when auto-detect picks a non-English lang)
VOICE_MAP = {
    "en": "af_heart",        # American English female
    "hi": "hf_alpha",        # Hindi female
    "hinglish": "hf_alpha",  # Hindi female (best fit for code-mixed text)
}

# ── Kokoro language codes ─────────────────────────────────────────────────
# KPipeline(lang_code=...) expects single-char codes.
LANG_CODE_MAP = {
    "en": "a",               # American English
    "hi": "h",               # Hindi
    "hinglish": "h",         # Hinglish → treated as Hindi by the model
}

# ── Inference ──────────────────────────────────────────────────────────────
SPEECH_SPEED = 1.15                # Kokoro local engine multiplier
TEMPERATURE = 0.82

# ── Edge-TTS cloud engine ─────────────────────────────────────────────────
# Percentage offset from neutral pace.  Valid range: "+0%" … "+12%".
# "+8%" is the sweet spot — noticeably snappier but still clear on a phone.
EDGE_SPEECH_RATE = "+8%"

# ── Text preprocessing ────────────────────────────────────────────────────
MAX_TEXT_LENGTH = 500         # characters — truncate beyond this

# ── Feature flags ─────────────────────────────────────────────────────────
ENABLE_LANGUAGE_AUTO_DETECT = True
MAX_SENTENCES = 2
SENTENCE_PAUSE_MS = 80
