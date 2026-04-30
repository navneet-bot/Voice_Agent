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
ROMAN_HINDI_MARKERS = (
    "main", "mai", "mera", "meri", "mere", "mujhe", "mje", "mujhko",
    "aap", "ap", "aapka", "aapki", "aapke", "tum", "tumhara", "tumhari",
    "haan", "han", "nahi", "nahin", "nhi", "kya", "kaunsa", "kaunsi",
    "kaise", "kitna", "kitni", "kitne", "chahiye", "dekh", "dekh raha",
    "dekh rahi", "raha", "rahi", "liye", "ke liye", "ke", "hai", "hoon",
    "khud", "apne liye",
    "rehne", "rehna", "ghar", "flat", "plot", "batao", "bolo", "samjha",
    "samajh", "thoda", "clear", "bolo", "bolenge", "pata", "abhi", "baad",
)
ENGLISH_STYLE_MARKERS = (
    "budget", "investment", "invest", "self use", "location", "property",
    "project", "site visit", "callback", "schedule", "timeline", "area",
    "price", "range", "premium", "options", "rent", "rental", "apartment",
)
LOCALIZED_TEMPLATE_MAP = {
    "Hey, this is Neha — am I speaking with {{name}}?": {
        "hi": "Hi, Neha bol rahi hoon. Kya main {{name}} se baat kar rahi hoon?",
        "hinglish": "Hi, Neha bol rahi hoon. Kya main {{name}} se baat kar rahi hoon?",
    },
    "Is this a good time to speak?": {
        "hi": "Abhi baat karne ke liye do minute milenge?",
        "hinglish": "Abhi baat karne ke liye 2 minute milenge?",
    },
    "I actually came across your interest in property. Are you exploring for yourself or as an investment?": {
        "hi": "Aap property khud ke liye dekh rahe ho ya investment ke liye?",
        "hinglish": "Aap property khud ke liye dekh rahe ho ya investment ke liye?",
    },
    "Hello, this is Neha from the Real Estate AI team. Am I speaking with you?": {
        "hi": "Hi, Neha bol rahi hoon Real Estate team se. Kya main aapse baat kar rahi hoon?",
        "hinglish": "Hi, Neha bol rahi hoon Real Estate team se. Kya main aapse baat kar rahi hoon?",
    },
    "I'm calling about some premium property options. Would you have a moment?": {
        "hi": "Premium property options ke baare mein call kiya hai. Ek minute mil jayega?",
        "hinglish": "Premium property options ke baare mein call kiya hai. Ek minute milega?",
    },
    "Thank you for your time. Have a great day!": {
        "hi": "Time dene ke liye thanks. Aapka din achha rahe.",
        "hinglish": "Time dene ke liye thanks. Have a great day.",
    },
    "Quick question — do you have two minutes right now? I came across something that might actually be relevant for you.": {
        "hi": "Bas do minute milenge? Aapke liye ek relevant option tha.",
        "hinglish": "Bas 2 minute milenge? Aapke liye ek relevant option tha.",
    },
    "Got it — are you mainly looking for something to move into, or more of an investment angle?": {
        "hi": "Samajh gayi. Aap khud rehne ke liye dekh rahe ho ya investment angle se?",
        "hinglish": "Got it. Aap khud ke liye dekh rahe ho ya investment angle se?",
    },
    "Yeah, totally fair — budget matters. We do have some options in Hinjewadi and Mamurdi that are more accessible, with flexible payment plans. Worth a look?": {
        "hi": "Bilkul, budget matter karta hai. Hinjewadi aur Mamurdi mein kuch options hain jahan payment plan bhi flexible hai, dekhna chahoge?",
        "hinglish": "Bilkul, budget matter karta hai. Hinjewadi aur Mamurdi mein kuch options hain with flexible payment plans, dekhna chahoge?",
    },
    "Got it, no worries. Just so I'm not wasting your time — would it be okay if I sent you something on WhatsApp? You can look at it whenever it suits you.": {
        "hi": "Theek hai, koi issue nahi. Main WhatsApp par details bhej doon? Aap jab time mile tab dekh lena.",
        "hinglish": "No worries. Main WhatsApp par details bhej doon? Aap jab convenient ho tab dekh lena.",
    },
    "Which part of the city are you looking at — and roughly what budget should I work with?": {
        "hi": "Kaunsi location side dekh rahe ho, aur budget roughly kitna socha hai?",
        "hinglish": "Kaunsi location side dekh rahe ho, aur budget roughly kitna hai?",
    },
    "Which city or area are you considering?": {
        "hi": "Kaunsa city ya area dekh rahe ho?",
        "hinglish": "Kaunsa city ya area dekh rahe ho?",
    },
    "What budget range should I keep in mind?": {
        "hi": "Budget range roughly kitni rakhun?",
        "hinglish": "Budget range roughly kitni rakhun?",
    },
    "Actually, I have something in {{location}} that fits your budget well — it's a {{property_type}} that's quite well-suited for what you're looking for. Would you want to see it in person?": {
        "hi": "{{location}} mein ek option hai jo aapke budget mein achha fit hota hai. Ye {{property_type}} hai, dekhna chahoge site par?",
        "hinglish": "{{location}} mein ek option hai jo aapke budget mein kaafi achha fit hota hai. Ye {{property_type}} hai, site visit karna chahoge?",
    },
    "What works better for you — weekend or a weekday? And any time preference?": {
        "hi": "Aapke liye weekend better rahega ya weekday? Time ka bhi koi preference hai?",
        "hinglish": "Weekend better rahega ya weekday? Time ka bhi koi preference hai?",
    },
    "Done — I'll send you the location and directions on WhatsApp before {{timeline}}. Looking forward to it.": {
        "hi": "Perfect, {{timeline}} se pehle main location aur directions WhatsApp par bhej dungi. Milte hain.",
        "hinglish": "Perfect, {{timeline}} se pehle main location aur directions WhatsApp par bhej dungi. Looking forward.",
    },
    "All set — see you then. Have a good one!": {
        "hi": "Perfect, phir milte hain. Aapka din achha rahe.",
        "hinglish": "All set, phir milte hain. Have a good one.",
    },
    "No worries. When's a better time to catch you — morning, afternoon, or evening?": {
        "hi": "Koi baat nahi. Callback ke liye morning, afternoon ya evening mein kya better rahega?",
        "hinglish": "No worries. Callback ke liye morning, afternoon ya evening mein kya better rahega?",
    },
    "I'll ping you around {{timeline}} then. Take care!": {
        "hi": "Theek hai, main aapko {{timeline}} ke around call kar lungi. Take care.",
        "hinglish": "Theek hai, main aapko {{timeline}} ke around call kar lungi. Take care.",
    },
    "Alright, take care. Talk soon!": {
        "hi": "Theek hai, take care. Jaldi baat karte hain.",
        "hinglish": "Alright, take care. Jaldi baat karte hain.",
    },
    "Sure, I can help with that. Which area is the property in, and what kind of price are you targeting?": {
        "hi": "Bilkul, usmein help kar sakti hoon. Property kis area mein hai, aur aap kya price expect kar rahe ho?",
        "hinglish": "Sure, usmein help kar sakti hoon. Property kis area mein hai, aur aap kya price target kar rahe ho?",
    },
    "Got it — what type of property is it, roughly how old, and any standout features? I'll have someone from our team reach out with a proper eval.": {
        "hi": "Samajh gayi. Property ka type kya hai, roughly kitni purani hai, aur koi key feature? Hamari team ka koi person proper eval ke saath connect karega.",
        "hinglish": "Got it. Property type kya hai, roughly kitni purani hai, aur koi standout feature? Hamari team proper eval ke saath connect karegi.",
    },
    "No worries, I'll be quick — it's about a property inquiry from earlier. Do you have two minutes, or should I call back later?": {
        "hi": "Koi baat nahi, main jaldi bolti hoon. Ye pehle wali property inquiry ke baare mein hai, do minute hain ya main baad mein call karun?",
        "hinglish": "No worries, main quick rahoongi. Ye earlier property inquiry ke baare mein hai, 2 minute hain ya baad mein call karun?",
    },
    "Thanks for chatting — have a great rest of your day!": {
        "hi": "Baat karne ke liye thanks. Aapka din achha rahe.",
        "hinglish": "Baat karne ke liye thanks. Have a great day ahead.",
    },
    "No problem at all — take care!": {
        "hi": "Bilkul theek hai. Take care.",
        "hinglish": "No problem at all. Take care.",
    },
    "I'm sorry, I didn't quite catch that! Could you please let me know, are you exploring for yourself or as an investment?": {
        "hi": "Thoda clear bolenge? Aap khud ke liye dekh rahe ho ya investment ke liye?",
        "hinglish": "Thoda clear bolenge? Aap khud ke liye dekh rahe ho ya investment ke liye?",
    },
    "I'm sorry, I didn't quite catch that! If you are unsure, popular areas include Wakad, Baner, Hinjewadi, and Kharadi. Which part of the city are you looking at?": {
        "hi": "Thoda clear bolenge? Agar open ho to Wakad, Baner, Hinjewadi ya Kharadi achhe options hain. Aap kis side dekh rahe ho?",
        "hinglish": "Thoda clear bolenge? Agar open ho to Wakad, Baner, Hinjewadi ya Kharadi achhe options hain. Aap kis side dekh rahe ho?",
    },
    "I'm sorry, I didn't quite catch that! If you are unsure, we have great options ranging from 50 lakhs to 2 crores. Roughly what budget should I work with?": {
        "hi": "Thoda clear bolenge? 50 lakh se 2 crore tak options hain. Aapka budget roughly kitna hai?",
        "hinglish": "Thoda clear bolenge? 50 lakh se 2 crore tak options hain. Aapka budget roughly kitna hai?",
    },
    "I'm sorry, I didn't quite catch that! Could you please let me know, are you looking for a 1 BHK, 2 BHK, or something else?": {
        "hi": "Thoda clear bolenge? Aap 1 BHK, 2 BHK ya kuch aur dekh rahe ho?",
        "hinglish": "Thoda clear bolenge? Aap 1 BHK, 2 BHK ya kuch aur dekh rahe ho?",
    },
    "I'm sorry, I didn't quite catch that! Could you please let me know, what works better for you — weekend or a weekday? And any time preference?": {
        "hi": "Thoda clear bolenge? Weekend better rahega ya weekday? Time ka bhi koi preference hai?",
        "hinglish": "Thoda clear bolenge? Weekend better rahega ya weekday? Time ka bhi koi preference hai?",
    },
    "That's alright. When would be a convenient time for a callback?": {
        "hi": "Koi baat nahi. Callback ke liye kaunsa time convenient rahega?",
        "hinglish": "Koi baat nahi. Callback ke liye kaunsa time convenient rahega?",
    },
    "No problem — are you thinking more budget-friendly, mid-range, or premium?": {
        "hi": "Koi issue nahi. Aap budget-friendly, mid-range ya premium mein kya prefer karoge?",
        "hinglish": "No problem. Aap budget-friendly, mid-range ya premium mein kya prefer karoge?",
    },
    "Popular areas include Wakad, Baner, Hinjewadi, and Kharadi. Which location interests you?": {
        "hi": "Popular options Wakad, Baner, Hinjewadi aur Kharadi mein hain. Aapko kaunsi location better lag rahi hai?",
        "hinglish": "Popular options Wakad, Baner, Hinjewadi aur Kharadi mein hain. Aapko kaunsi location better lag rahi hai?",
    },
    "Would next week work better for the visit?": {
        "hi": "Agar aapko theek lage to next week visit rakh lete hain?",
        "hinglish": "Agar theek lage to next week visit rakh lete hain?",
    },
    "Sorry about that. Thank you for your time. Goodbye.": {
        "hi": "Theek hai, time dene ke liye thanks. Namaste.",
        "hinglish": "Theek hai, time dene ke liye thanks. Bye.",
    },
    "Could you help me understand what you're looking for?": {
        "hi": "Aap exactly kis type ka option dekh rahe ho?",
        "hinglish": "Aap exactly kis type ka option dekh rahe ho?",
    },
    "Sorry, I didn't catch that clearly. Could you repeat that once?": {
        "hi": "Thoda clear bolenge? Main wahi se continue karti hoon.",
        "hinglish": "Thoda clear bolenge? Main wahi se continue karti hoon.",
    },
    "Give me just one moment...": {
        "hi": "Ek second dijiye...",
        "hinglish": "Ek second dijiye...",
    },
}


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

    # Whitelist common Unicode punctuation Whisper sometimes inserts
    # (curly apostrophes/quotes, em-dashes, ellipsis) — these are NOT
    # foreign scripts and should not cause a transcript to be rejected.
    _PUNCT_WHITELIST = {
        '\u2019', '\u2018',  # curly apostrophes
        '\u201c', '\u201d',  # curly double quotes
        '\u2013', '\u2014',  # en-dash / em-dash
        '\u2026',            # ellipsis
        '\u00e9', '\u00e8', '\u00e0', '\u00e2',  # French accented vowels (common in names)
    }
    # Count only truly foreign-alphabet letters (not the whitelisted punctuation)
    adjusted_unsupported = sum(
        1 for ch in cleaned
        if ch.isalpha()
        and ch not in _PUNCT_WHITELIST
        and not (DEVANAGARI_RANGE[0] <= ch <= DEVANAGARI_RANGE[1])
        and not ch.isascii()
    )
    total_letters = latin_letters + devanagari_letters + adjusted_unsupported
    unsupported_ratio = adjusted_unsupported / total_letters if total_letters > 0 else 0.0

    # Only reject as unsupported_script if foreign chars dominate (>60%)
    # AND there is very little usable Latin or Devanagari content (<3 chars each).
    # This prevents over-dropping Hinglish turns that happen to contain a
    # curly apostrophe or a single accented character.
    if adjusted_unsupported > 0 and unsupported_ratio > 0.60 and latin_letters < 3 and devanagari_letters < 3:
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
    roman_hindi_hits = _count_markers(latin_text, ROMAN_HINDI_MARKERS)
    english_style_hits = _count_markers(latin_text, ENGLISH_STYLE_MARKERS)
    english_words = re.findall(r"\b[a-z]{2,}\b", latin_text)

    if roman_hindi_hits >= 2 and english_style_hits == 0:
        return UserTextAnalysis(text, cleaned, "hi", 0.86, True, "roman_hindi", latin_letters, devanagari_letters, unsupported_letters)
    if roman_hindi_hits >= 2 and english_style_hits >= 1:
        return UserTextAnalysis(text, cleaned, "hinglish", 0.93, True, "clear_hinglish", latin_letters, devanagari_letters, unsupported_letters)
    if hinglish_hits >= 2 or (hinglish_hits >= 1 and english_style_hits >= 1):
        return UserTextAnalysis(text, cleaned, "hinglish", 0.9, True, "clear_hinglish", latin_letters, devanagari_letters, unsupported_letters)
    if roman_hindi_hits == 1 and english_style_hits == 0:
        return UserTextAnalysis(text, cleaned, "hi", 0.72, True, "possible_roman_hindi", latin_letters, devanagari_letters, unsupported_letters)
    if hinglish_hits == 1:
        return UserTextAnalysis(text, cleaned, "hinglish", 0.76, True, "possible_hinglish", latin_letters, devanagari_letters, unsupported_letters)

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
            "Respond in natural spoken Hindi using standard Devanagari script. Keep it casual, warm, and human. Avoid textbook or overly formal Hindi."
        ),
        "mr": (
            "Respond in conversational, respectful Marathi. Keep it natural, polished, and easy to follow."
        ),
        "hinglish": (
            "Respond in natural Indian Hinglish. Mirror the user's style, keep real-estate terms in English when that sounds natural, and avoid stiff translations."
        ),
    }
    return instructions[normalized]


def localize_template(template: str, language: str) -> str:
    """Map shared-flow English templates to Hindi/Hinglish without changing the flow."""
    normalized = language if language in SUPPORTED_LANGUAGES else "en"
    if normalized not in {"hi", "hinglish"}:
        return template
    variants = LOCALIZED_TEMPLATE_MAP.get(template)
    if not variants:
        return template
    return variants.get(normalized, template)


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if re.search(rf"\b{re.escape(marker)}\b", text))
