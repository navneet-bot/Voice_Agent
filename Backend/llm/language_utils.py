"""Shared language detection and routing helpers for voice responses."""

from __future__ import annotations

from dataclasses import dataclass
import re


SUPPORTED_LANGUAGES = {"en", "hi", "mr", "hinglish"}
DEVANAGARI_RANGE = ("\u0900", "\u097F")
HINDI_MARKERS = ("है", "नहीं", "मुझे", "आप", "क्या", "जी", "चाहिए", "करना", "बोलिए")
MARATHI_MARKERS = ("आहे", "नाही", "माझ", "तुम्ह", "काय", "होय", "पाहिजे", "करू", "बोला")
HINGLISH_MARKERS = (
    "aap", "apka", "apki", "haan", "han", "ji", "nahi", "nahin",
    "achha", "acha", "kya", "kaise", "karna", "chahiye", "chahiye",
    "thik", "theek", "boliye", "bataiye", "mera", "meri", "mujhe",
)


@dataclass(frozen=True)
class UserTextAnalysis:
    original_text: str
    cleaned_text: str
    detected_language: str
    confidence: float
    actionable: bool
    reason: str
    latin_letters: int
    devanagari_letters: int
    unsupported_letters: int


class LanguageTracker:
    """Keep language switching stable across noisy turns."""

    def __init__(self, initial_language: str = "en"):
        self.current_language = initial_language if initial_language in SUPPORTED_LANGUAGES else "en"
        self._pending_language: str | None = None
        self._pending_hits = 0

    def observe(self, text: str) -> tuple[str, UserTextAnalysis]:
        analysis = analyze_user_text(text, fallback=self.current_language)
        if not analysis.actionable:
            self._pending_language = None
            self._pending_hits = 0
            return self.current_language, analysis

        detected = analysis.detected_language
        if detected == self.current_language:
            self._pending_language = None
            self._pending_hits = 0
            return self.current_language, analysis

        strong_switch = analysis.confidence >= 0.9 or (
            detected in {"hi", "mr"} and analysis.confidence >= 0.82
        )
        if strong_switch:
            self.current_language = detected
            self._pending_language = None
            self._pending_hits = 0
            return self.current_language, analysis

        if detected == self._pending_language:
            self._pending_hits += 1
        else:
            self._pending_language = detected
            self._pending_hits = 1

        if self._pending_hits >= 2:
            self.current_language = detected
            self._pending_language = None
            self._pending_hits = 0

        return self.current_language, analysis


def analyze_user_text(text: str, fallback: str = "en") -> UserTextAnalysis:
    """Classify user text for language and whether it is safe to act on."""
    normalized_fallback = fallback if fallback in SUPPORTED_LANGUAGES else "en"
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return UserTextAnalysis(text, "", normalized_fallback, 0.0, False, "empty", 0, 0, 0)

    latin_letters = 0
    devanagari_letters = 0
    unsupported_letters = 0
    for ch in cleaned:
        if not ch.isalpha():
            continue
        if DEVANAGARI_RANGE[0] <= ch <= DEVANAGARI_RANGE[1]:
            devanagari_letters += 1
        elif ch.isascii():
            latin_letters += 1
        else:
            unsupported_letters += 1

    if latin_letters == 0 and devanagari_letters == 0 and unsupported_letters == 0:
        return UserTextAnalysis(
            text, cleaned, normalized_fallback, 0.0, False, "punctuation_only", 0, 0, 0
        )

    if unsupported_letters > 0 and unsupported_letters >= max(latin_letters, devanagari_letters):
        return UserTextAnalysis(
            text,
            cleaned,
            normalized_fallback,
            0.0,
            False,
            "unsupported_script",
            latin_letters,
            devanagari_letters,
            unsupported_letters,
        )

    if devanagari_letters > 0:
        marathi_hits = _count_markers(cleaned, MARATHI_MARKERS)
        hindi_hits = _count_markers(cleaned, HINDI_MARKERS)
        if marathi_hits > hindi_hits and marathi_hits > 0:
            return UserTextAnalysis(text, cleaned, "mr", 0.96, True, "clear_marathi", latin_letters, devanagari_letters, unsupported_letters)
        if hindi_hits > 0:
            return UserTextAnalysis(text, cleaned, "hi", 0.96, True, "clear_hindi", latin_letters, devanagari_letters, unsupported_letters)
        return UserTextAnalysis(text, cleaned, "hi", 0.84, True, "devanagari", latin_letters, devanagari_letters, unsupported_letters)

    latin_text = cleaned.casefold()
    hinglish_hits = _count_markers(latin_text, HINGLISH_MARKERS)
    english_words = re.findall(r"\b[a-z]{2,}\b", latin_text)

    if hinglish_hits >= 2:
        return UserTextAnalysis(text, cleaned, "hinglish", 0.92, True, "clear_hinglish", latin_letters, devanagari_letters, unsupported_letters)
    if hinglish_hits == 1:
        return UserTextAnalysis(text, cleaned, "hinglish", 0.78, True, "possible_hinglish", latin_letters, devanagari_letters, unsupported_letters)

    confidence = 0.87 if len(english_words) >= 2 else 0.68
    return UserTextAnalysis(text, cleaned, "en", confidence, True, "latin_text", latin_letters, devanagari_letters, unsupported_letters)


def detect_language_from_text(text: str, fallback: str = "en") -> str:
    """Infer the user's language from a short utterance."""
    return analyze_user_text(text, fallback=fallback).detected_language


def is_actionable_user_text(text: str, fallback: str = "en") -> bool:
    """Return whether a transcript is safe to send into the conversation state machine."""
    return analyze_user_text(text, fallback=fallback).actionable


def get_language_label(language: str) -> str:
    normalized = language if language in SUPPORTED_LANGUAGES else "en"
    return {
        "en": "English",
        "hi": "Hindi",
        "mr": "Marathi",
        "hinglish": "Hinglish",
    }[normalized]


def get_language_instruction(language: str) -> str:
    """Return a concise generation directive for the active language."""
    normalized = language if language in SUPPORTED_LANGUAGES else "en"
    instructions = {
        "en": (
            "Respond in clear, natural English. Start in English and stay there unless the user clearly and consistently uses another supported language."
        ),
        "hi": (
            "Respond in natural spoken Hindi using standard Devanagari script. Keep the phrasing fluid and professional, not textbook or rigid."
        ),
        "mr": (
            "Respond in conversational, respectful Marathi. Keep it natural, polished, and easy to follow."
        ),
        "hinglish": (
            "Respond in natural professional Hinglish. Mix English real-estate terms naturally, keep the tone polished, and avoid exaggerated slang."
        ),
    }
    return instructions[normalized]


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if re.search(rf"\b{re.escape(marker)}\b", text))
