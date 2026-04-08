"""
Kokoro-82M Text-to-Speech Engine
================================

Why Kokoro-82M:
    - Lightweight: only 82M parameters — runs comfortably on CPU.
    - Open-source: Apache-licensed weights; deploy anywhere.
    - Conversational quality: comparable to larger proprietary models.
    - Multilingual: supports English, Hindi, Japanese, Chinese, and more.
    - Cost-efficient: under $1/M characters when served over API.

Latency target:
    - Under 1 second for 1–2 sentences on modern CPU.
    - 2 seconds is acceptable for longer passages.

RAM estimate:
    - ~500 MB – 1 GB loaded on CPU (model weights + runtime overhead).

How to swap TTS engine later:
    1. Create a new file (e.g. tts/tts_xyz.py) that implements:
           def generate_speech(text: str) -> bytes
    2. Update tts/__init__.py to import from the new module.
    3. No other changes required — the rest of the pipeline depends only
       on the generate_speech() signature.
"""

import io
import re
import logging

import torch
import numpy as np
import soundfile as sf

from kokoro import KPipeline

from tts.config import (
    CHANNELS,
    ENABLE_LANGUAGE_AUTO_DETECT,
    LANG_CODE_MAP,
    MAX_TEXT_LENGTH,
    SAMPLE_RATE,
    SPEECH_SPEED,
    VOICE_MAP,
    VOICE_NAME,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level pipeline cache (loaded once, reused across requests)
# ---------------------------------------------------------------------------
# We lazily initialise per lang_code because KPipeline is bound to a single
# language at construction time.  The dict avoids re-creating a pipeline
# when the same language is requested again.
_pipelines: dict[str, KPipeline] = {}


def _get_pipeline(lang_code: str) -> KPipeline:
    """Return a cached KPipeline for the given Kokoro lang_code.

    If this is the first request for *lang_code*, a new KPipeline is
    constructed (which downloads / loads model weights on first run) and
    cached for subsequent calls.

    Args:
        lang_code: Single-character Kokoro language code (e.g. ``'a'``,
            ``'h'``).

    Returns:
        A ready-to-use ``KPipeline`` instance.
    """
    if lang_code not in _pipelines:
        logger.info("Initialising Kokoro KPipeline for lang_code='%s' …", lang_code)
        _pipelines[lang_code] = KPipeline(lang_code=lang_code)
        logger.info("KPipeline for lang_code='%s' ready.", lang_code)
    return _pipelines[lang_code]


# Eagerly load the default (English) pipeline at import time so the first
# request doesn't pay the cold-start cost.
try:
    _get_pipeline(LANG_CODE_MAP.get("en", "a"))
except Exception:
    logger.warning(
        "Failed to pre-load Kokoro pipeline at import time.  "
        "The model will be loaded on the first generate_speech() call.",
        exc_info=True,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_speech(text: str) -> bytes:
    """Convert plain text to WAV audio bytes using Kokoro-82M.

    This is the only public function in this module.  It accepts raw text
    (typically the output of an LLM) and returns mono 24 kHz WAV bytes
    suitable for LiveKit / VoIP telephony playback.

    Args:
        text: Plain-text string to synthesise.  May contain English,
            Hindi (Devanagari), or Hinglish (mixed script).

    Returns:
        ``bytes`` containing a valid WAV file (mono, 24 000 Hz), or
        ``b""`` when the input is empty, unspeakable, or an error occurs
        during inference.  This function **never raises**.
    """
    try:
        from tts.speech_formatter import optimize_for_tts
        text = optimize_for_tts(text)

        # --- pre-process ------------------------------------------------
        processed = _preprocess_text(text)
        if not processed:
            logger.debug("generate_speech: empty after preprocessing, returning b''")
            return b""

        # Strip out anything that is not a letter, digit, or common punct.
        speakable = re.sub(r"[^\w\s]", "", processed, flags=re.UNICODE).strip()
        if not speakable:
            logger.debug("generate_speech: no speakable content, returning b''")
            return b""

        # --- language detection ------------------------------------------
        if ENABLE_LANGUAGE_AUTO_DETECT:
            detected_lang = _detect_language(processed)
        else:
            detected_lang = "en"
        logger.debug("Detected language: %s", detected_lang)

        lang_code = LANG_CODE_MAP.get(detected_lang, "a")
        voice = VOICE_MAP.get(detected_lang, VOICE_NAME)

        # --- inference ---------------------------------------------------
        pipeline = _get_pipeline(lang_code)
        
        sentences = _split_sentences(processed)
        if len(sentences) > 4:
            logger.warning("generate_speech: response exceeds 4 sentences. Processing first 4 only.")
            sentences = sentences[:4]

        audio_segments = []
        silence = _generate_silence(duration_ms=180)   # 180ms between sentences

        def _run_kokoro(sentence_text: str) -> np.ndarray:
            generator = pipeline(sentence_text, voice=voice, speed=SPEECH_SPEED)
            chunks = [aud for _gs, _ps, aud in generator if aud is not None and len(aud) > 0]
            return np.concatenate(chunks) if chunks else np.array([])

        with torch.no_grad():
            for sentence in sentences:
                if sentence.strip():
                    audio = _run_kokoro(sentence)
                    if len(audio) > 0:
                        audio_segments.append(audio)
                        audio_segments.append(silence)

        if not audio_segments:
            logger.warning("Kokoro returned no audio chunks for input: %.80s…", processed)
            return b""

        final_audio = np.concatenate(audio_segments) if audio_segments else np.array([])
        return _to_wav_bytes(final_audio, SAMPLE_RATE)

    except Exception:
        logger.error("generate_speech failed", exc_info=True)
        return b""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _detect_language(text: str) -> str:
    """Detect script/language of *text* using Unicode range heuristics.

    Detection priority:
        1. Contains **both** Devanagari (U+0900–U+097F) **and** Latin
           characters → ``"hinglish"``
        2. Contains only Devanagari → ``"hi"``
        3. Contains only Latin → ``"en"``
        4. Fallback → ``"hinglish"``

    No external libraries are used — detection is purely based on Unicode
    code-point ranges, which is deterministic and zero-dependency.

    Args:
        text: Input text string.

    Returns:
        One of ``"en"``, ``"hi"``, or ``"hinglish"``.
    """
    has_devanagari = False
    has_latin = False

    for ch in text:
        cp = ord(ch)
        # Devanagari block: U+0900 – U+097F
        if 0x0900 <= cp <= 0x097F:
            has_devanagari = True
        # Basic Latin letters (A-Z, a-z)
        elif (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
            has_latin = True

        # Short-circuit: if both are found, it's Hinglish.
        if has_devanagari and has_latin:
            return "hinglish"

    if has_devanagari:
        return "hi"
    if has_latin:
        return "en"

    # Fallback (e.g. only digits / symbols / other scripts)
    return "hinglish"


def _preprocess_text(text: str) -> str:
    """Clean and normalise *text* before sending it to the TTS model.

    Steps:
        1. Strip leading / trailing whitespace.
        2. Collapse multiple spaces and newlines into a single space.
        3. Remove repeated punctuation (e.g. ``"!!!"`` → ``"!"``).
        4. Truncate to ``MAX_TEXT_LENGTH`` characters at a word boundary.

    Devanagari script is preserved as-is — no transliteration or removal.
    The language of the text is never changed.

    Args:
        text: Raw input text.

    Returns:
        Cleaned text string, or ``""`` if the input was empty / whitespace
        only.
    """
    if not text:
        return ""

    # 1. Strip
    cleaned = text.strip()
    if not cleaned:
        return ""

    # 2. Collapse whitespace (spaces, tabs, newlines)
    cleaned = re.sub(r"\s+", " ", cleaned)

    # 3. Collapse repeated punctuation (keep one)
    #    Matches any run of the *same* punctuation character.
    cleaned = re.sub(r"([!?.,;:…])\1+", r"\1", cleaned)

    # 4. Truncate at word boundary
    if len(cleaned) > MAX_TEXT_LENGTH:
        truncated = cleaned[:MAX_TEXT_LENGTH]
        # Walk backwards to the last space to avoid cutting mid-word.
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        cleaned = truncated.rstrip()

    return cleaned


def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    """Encode a float32 numpy audio array into WAV bytes.

    Output specification:
        - Format: WAV (RIFF)
        - Channels: 1 (mono) — required for telephony
        - Sample rate: *sample_rate* Hz (typically 24 000)

    Args:
        audio: 1-D ``np.float32`` array of audio samples.
        sample_rate: Target sample rate in Hz.

    Returns:
        ``bytes`` containing a complete WAV file.
    """
    # Ensure the array is 1-D float32
    audio = np.asarray(audio, dtype=np.float32).ravel()

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return buf.read()


def _split_sentences(text: str) -> list[str]:
    """Split input text on ., ?, ! or \\n while preserving punctuation."""
    parts = re.split(r'([.!?\n])', text)
    sentences = []
    current = ""
    for i in range(0, len(parts) - 1, 2):
        sentence = parts[i].strip()
        punct = parts[i+1]
        
        if not sentence and punct in ['\n', '.', '?', '!']:
            # Punctuation alone or consecutive newlines
            current += punct
        else:
            current += (" " if current and not current.endswith('\n') else "") + sentence + punct
            
        if punct in ['.', '?', '!', '\n']:
            if current.strip():
                sentences.append(current.strip())
            current = ""
            
    if len(parts) % 2 != 0:
        last = parts[-1].strip()
        if last:
            current += (" " if current and not current.endswith('\n') else "") + last
            
    if current.strip():
        sentences.append(current.strip())
        
    return [s for s in sentences if s.strip()]


def _generate_silence(duration_ms: int = 180) -> np.ndarray:
    """Generate numpy float32 zeros for the given duration in ms."""
    length = int((max(120, min(duration_ms, 250)) / 1000.0) * SAMPLE_RATE)
    return np.zeros(length, dtype=np.float32)
