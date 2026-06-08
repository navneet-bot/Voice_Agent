# ---------------------------------------------------------------------------
# TTS Configuration
# All tunable constants live here. No logic, no imports.
# ---------------------------------------------------------------------------

# ── Audio output ───────────────────────────────────────────────────────────
SAMPLE_RATE = 24000          # Hz — LiveKit and VoIP compatible
CHANNELS = 1                 # mono required for telephony

# ── Edge-TTS cloud engine ─────────────────────────────────────────────────
# Percentage offset from neutral pace.  Valid range: "+0%" … "+12%".
# "+8%" is the sweet spot — noticeably snappier but still clear on a phone.
EDGE_SPEECH_RATE = "+10%"

# ── Text preprocessing ────────────────────────────────────────────────────
MAX_TEXT_LENGTH = 500         # characters — truncate beyond this

# ── Feature flags ─────────────────────────────────────────────────────────
ENABLE_LANGUAGE_AUTO_DETECT = True
MAX_SENTENCES = 2
SENTENCE_PAUSE_MS = 80
