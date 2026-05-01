"""Structured spoken response composer for qualification steps."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .language_utils import detect_language_from_text


PURPOSE_ALIASES = {
    "invest": "investment",
    "investment": "investment",
    "self_use": "self_use",
    "self use": "self_use",
    "buy": "self_use",
    "own_use": "self_use",
    "own use": "self_use",
    "personal use": "self_use",
    "rent": "rent",
}

INVEST_HINTS = (
    "investment", "invest", "returns", "return", "roi", "rental income",
    "appreciation", "future value", "asset", "passive income",
    "nivesh", "returns ke liye", "investment ke liye",
)
SELF_USE_HINTS = (
    "self use", "own use", "personal use", "for family", "family",
    "for myself", "for self", "to live", "move in", "stay",
    "khud ke liye", "apne liye", "rehne ke liye", "ghar ke liye",
)
RENT_HINTS = (
    "rent", "rental", "lease", "kiraye", "kiraya", "rent pe",
)
LOCATION_OPTIONS = ("Wakad", "Baner", "Hinjewadi")
BUDGET_EXAMPLES = {
    "en": "40 lakh, 80 lakh, or 1 crore",
    "hi": "40 लाख, 80 लाख, या 1 करोड़",
    "hinglish": "40 lakh, 80 lakh, ya 1 crore",
    "mr": "40 लाख, 80 लाख, की 1 कोटी",
}


@dataclass(frozen=True)
class PurposeInference:
    value: str | None
    confidence: str


def should_answer_user_question(user_input: str) -> bool:
    """Return True when the user needs a brief answer before flow continues."""
    return _detect_user_question(user_input) is not None


def generate_spoken_response(
    current_node: dict[str, Any] | str,
    purpose: str | None = None,
    location: str | None = None,
    budget: str | None = None,
    memory: Any = None,
    user_input: str = "",
    rag_context: Any = None,
    language: str | None = None,
) -> str:
    """Return a production-safe spoken response for the active qualification step."""
    node = _normalize_node(current_node)
    step = _classify_step(node, location=location, budget=budget)
    lang = _normalize_language(language or detect_language_from_text(user_input or "", "en"))
    inferred = _infer_purpose(purpose, user_input, memory, rag_context)
    question = _detect_user_question(user_input)

    if question:
        return _finalize(
            _answer_question_then_continue(
                lang,
                question,
                step,
                purpose=inferred.value,
                location=location,
                budget=budget,
            )
        )

    if step == "ask_purpose":
        if inferred.value and inferred.confidence == "high":
            return _finalize(_purpose_to_next_step(lang, inferred.value))
        return _finalize(_purpose_clarification(lang, memory, rag_context))

    if step == "ask_location":
        if location:
            return _finalize(_ack_location_then_budget(lang, location))
        return _finalize(_location_prompt(lang, user_input, memory, rag_context))

    if step == "ask_budget":
        if budget:
            return _finalize(_ack_budget_then_move(lang, budget, location))
        return _finalize(_budget_prompt(lang, location))

    return _finalize(_generic_prompt(lang, location=location, budget=budget))


def _normalize_node(current_node: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(current_node, dict):
        return current_node
    return {"id": str(current_node), "name": str(current_node)}


def _classify_step(node: dict[str, Any], *, location: str | None, budget: str | None) -> str:
    node_id = str(node.get("id") or "")
    node_name = str(node.get("name") or "").lower()
    expected = str(node.get("expected_input_type") or "").lower()

    if node_id == "node-1767592854176":
        return "ask_identity"
    if node_id in {"node-1735264873079", "node-1735970090937"}:
        return "ask_availability"
    if node_id in {"node-1735264921453", "fallback_intent"} or "intent" in node_name or "purpose" in node_name:
        return "ask_purpose"
    if node_id == "fallback_location" or expected == "location":
        return "ask_location"
    if node_id == "fallback_budget" or expected == "budget":
        return "ask_budget"
    if node_id == "node-1735267546732":
        if location and not budget:
            return "ask_budget"
        return "ask_location"
    return "generic"


def _detect_user_question(user_input: str) -> str | None:
    text = re.sub(r"[^\w\s'?]", " ", (user_input or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return None

    identity_markers = (
        "who are you", "who is this", "who's this", "your name",
        "kaun ho", "kaun bol", "aap kaun", "kon bol",
    )
    purpose_markers = (
        "why are you calling", "why did you call", "what is this about",
        "what is it about", "what's it about", "whats this about",
        "what are you talking about", "what is this", "what is it",
        "purpose of call", "reason for call", "kis baare", "kyu call",
        "kyun call", "kya baat", "kya hai",
    )
    confusion_markers = (
        "i don't understand", "i dont understand", "not clear",
        "what do you mean", "what are you saying", "confused",
        "samajh nahi", "samjha nahi", "clear nahi",
    )

    if any(marker in text for marker in identity_markers):
        return "identity"
    if any(marker in text for marker in purpose_markers):
        return "purpose"
    if any(marker in text for marker in confusion_markers):
        return "confusion"
    return None


def _answer_question_then_continue(
    language: str,
    question: str,
    step: str,
    *,
    purpose: str | None,
    location: str | None,
    budget: str | None,
) -> str:
    answer = _question_answer(language, question)
    follow_up = _next_step_question(language, step, purpose=purpose, location=location, budget=budget)
    return f"{answer} {follow_up}".strip()


def _question_answer(language: str, question: str) -> str:
    if language == "hi":
        if question == "identity":
            return "Neha bol rahi hoon, Real Estate team se."
        return "Aapki earlier property interest ke baare mein call kiya hai."
    if language == "hinglish":
        if question == "identity":
            return "Neha bol rahi hoon, Real Estate team se."
        return "Aapki earlier property interest ke baare mein call kiya hai."
    if language == "mr":
        if question == "identity":
            return "Neha बोलतेय, Real Estate team मधून."
        return "तुमच्या earlier property interest बद्दल call केला आहे."
    if question == "identity":
        return "Neha here from the Real Estate team."
    return "It's about your earlier property interest."


def _next_step_question(
    language: str,
    step: str,
    *,
    purpose: str | None,
    location: str | None,
    budget: str | None,
) -> str:
    del purpose, budget
    if step == "ask_availability":
        if language == "hi":
            return "Do minute baat kar sakte hain?"
        if language == "hinglish":
            return "Do minute baat kar sakte hain?"
        if language == "mr":
            return "दोन मिनिटं बोलू शकतो का?"
        return "Do you have two minutes?"
    if step == "ask_identity":
        if language == "hi":
            return "Kya main Prashant se baat kar rahi hoon?"
        if language == "hinglish":
            return "Kya main Prashant se baat kar rahi hoon?"
        if language == "mr":
            return "मी Prashant शी बोलतेय का?"
        return "Am I speaking with Prashant?"
    if step == "ask_purpose":
        if language == "hi":
            return "Investment ke liye dekh rahe ho ya khud ke liye?"
        if language == "hinglish":
            return "Investment ke liye dekh rahe ho ya personal use ke liye?"
        if language == "mr":
            return "Investment साठी बघत आहात की स्वतःसाठी?"
        return "Is this for investment or your own use?"
    if step == "ask_budget":
        if language == "hi":
            return f"{location} ke liye budget roughly kitna hai?" if location else "Budget roughly kitna hai?"
        if language == "hinglish":
            return f"{location} ke liye budget roughly kitna hai?" if location else "Budget roughly kitna hai?"
        if language == "mr":
            return f"{location} साठी budget roughly किती आहे?" if location else "Budget roughly किती आहे?"
        return f"For {location}, what budget should I keep in mind?" if location else "What budget should I keep in mind?"
    if language == "hi":
        return "Aap kis area mein dekh rahe ho?"
    if language == "hinglish":
        return "Aap kis area mein dekh rahe ho?"
    if language == "mr":
        return "कोणत्या area मध्ये बघत आहात?"
    return "Which area are you considering?"


def _infer_purpose(
    purpose: str | None,
    user_input: str,
    memory: Any,
    rag_context: Any,
) -> PurposeInference:
    normalized = PURPOSE_ALIASES.get((purpose or "").strip().lower())
    if normalized:
        return PurposeInference(normalized, "high")

    combined = " ".join(filter(None, [user_input, _flatten_context(memory), _flatten_context(rag_context)])).lower()
    invest_score = sum(1 for hint in INVEST_HINTS if hint in combined)
    self_use_score = sum(1 for hint in SELF_USE_HINTS if hint in combined)
    rent_score = sum(1 for hint in RENT_HINTS if hint in combined)

    scores = {
        "investment": invest_score,
        "self_use": self_use_score,
        "rent": rent_score,
    }
    best_value = max(scores, key=scores.get)
    best_score = scores[best_value]
    second_score = sorted(scores.values(), reverse=True)[1]

    if best_score <= 0:
        return PurposeInference(None, "low")
    if best_score >= second_score + 1:
        return PurposeInference(best_value, "high")
    return PurposeInference(None, "low")


def _flatten_context(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_flatten_context(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten_context(v) for v in value)
    return str(value)


def _purpose_to_next_step(language: str, purpose: str) -> str:
    if language == "hi":
        lead = "Theek hai, investment ke hisaab se dekhenge." if purpose == "investment" else "Theek hai, khud ke use ke hisaab se dekhenge."
        return f"{lead} Aap kis area mein dekh rahe ho?"
    if language == "hinglish":
        lead = "Theek hai, investment angle ke hisaab se dekhenge." if purpose == "investment" else "Theek hai, self-use ke hisaab se dekhenge."
        return f"{lead} Aap kis area mein dekh rahe ho?"
    if language == "mr":
        lead = "ठीक आहे, investment angle ने पाहू." if purpose == "investment" else "ठीक आहे, self-use साठी पाहू."
        return f"{lead} कोणत्या area मध्ये बघत आहात?"
    lead = "Investment angle noted." if purpose == "investment" else "For your own use, noted."
    return f"{lead} Which area are you considering?"


def _purpose_clarification(language: str, memory: Any, rag_context: Any) -> str:
    context = f"{_flatten_context(memory)} {_flatten_context(rag_context)}".lower()
    if "return" in context or "investment" in context or "roi" in context:
        if language == "hi":
            return "Aapne returns mention kiye the. Ye investment ke liye dekh rahe ho?"
        if language == "hinglish":
            return "Aapne returns mention kiye the. Ye investment ke liye dekh rahe ho?"
        if language == "mr":
            return "तुम्ही returns mention केले होते. हे investment साठी बघत आहात?"
        return "You mentioned returns earlier. Is this mainly for investment?"
    if language == "hi":
        return "Bas confirm kar loon, aap investment ke liye dekh rahe ho ya khud ke liye?"
    if language == "hinglish":
        return "Bas confirm kar loon, investment ke liye dekh rahe ho ya personal use ke liye?"
    if language == "mr":
        return "फक्त confirm करू, investment साठी बघत आहात की स्वतःसाठी?"
    return "Just to confirm, is this for investment or your own use?"


def _ack_location_then_budget(language: str, location: str) -> str:
    if language == "hi":
        return f"{location} noted. Budget roughly kitna socha hai?"
    if language == "hinglish":
        return f"{location} noted. Budget roughly kitna socha hai?"
    if language == "mr":
        return f"{location} noted. Budget roughly किती ठेवलाय?"
    return f"{location} works. What budget range should I keep in mind?"


def _location_prompt(language: str, user_input: str, memory: Any, rag_context: Any) -> str:
    context = f"{user_input} {_flatten_context(memory)} {_flatten_context(rag_context)}".lower()
    if any(token in context for token in ("anywhere", "not sure", "open", "suggest", "recommend", "any area", "best location")):
        options = ", ".join(LOCATION_OPTIONS)
        if language == "hi":
            return f"Aap {options} mein dekh sakte ho. Inmein se kaunsa area better lagega?"
        if language == "hinglish":
            return f"Aap {options} dekh sakte ho. Inmein se kaunsa area better lagega?"
        if language == "mr":
            return f"{options} हे चांगले options आहेत. यापैकी कोणता area जास्त suit होईल?"
        return f"You can consider {options}. Which area feels closest to what you want?"
    if language == "hi":
        return "Aap kis city ya area mein dekh rahe ho?"
    if language == "hinglish":
        return "Aap kis city ya area mein dekh rahe ho?"
    if language == "mr":
        return "तुम्ही कोणत्या city किंवा area मध्ये बघत आहात?"
    return "Which city or area are you considering?"


def _budget_prompt(language: str, location: str | None) -> str:
    examples = BUDGET_EXAMPLES[language]
    if location:
        if language == "hi":
            return f"{location} ke liye budget roughly kitna rakhna hai, jaise {examples}?"
        if language == "hinglish":
            return f"{location} ke liye budget roughly kitna rakhna hai, jaise {examples}?"
        if language == "mr":
            return f"{location} साठी budget roughly किती आहे, जसं {examples}?"
        return f"For {location}, what budget should I work with, maybe {examples}?"
    if language == "hi":
        return f"Budget exact na ho to bhi chalega. Roughly {examples} mein kya socha hai?"
    if language == "hinglish":
        return f"Budget exact na ho to bhi chalega. Roughly {examples} mein kya socha hai?"
    if language == "mr":
        return f"Exact budget नसलं तरी चालेल. Roughly {examples} मध्ये काय ठेवलंय?"
    return f"It doesn't have to be exact. Roughly, should I think {examples}?"


def _ack_budget_then_move(language: str, budget: str, location: str | None) -> str:
    if not location:
        return _generic_prompt(language, budget=budget)
    if language == "hi":
        return f"{budget} noted for {location}. Main matching options shortlist karti hoon."
    if language == "hinglish":
        return f"{budget} noted for {location}. Main matching options shortlist karti hoon."
    if language == "mr":
        return f"{location} साठी {budget} noted. Matching options shortlist करते."
    return f"{budget} works for {location}. I'll shortlist matching options."


def _generic_prompt(language: str, location: str | None, budget: str | None) -> str:
    if location and not budget:
        return _budget_prompt(language, location)
    if budget and not location:
        return _location_prompt(language, "", None, None)
    if language == "hi":
        return "Aap kis area mein dekh rahe ho?"
    if language == "hinglish":
        return "Aap kis area mein dekh rahe ho?"
    if language == "mr":
        return "तुम्ही कोणत्या area मध्ये बघत आहात?"
    return "Which area are you considering?"


def _normalize_language(language: str) -> str:
    return language if language in {"en", "hi", "hinglish", "mr"} else "en"


def _finalize(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\b(Sure|Great|Absolutely|Certainly)\b[, ]*", "", cleaned, flags=re.IGNORECASE).strip()
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if len(parts) > 2:
        parts = parts[:2]
    cleaned = " ".join(parts)
    if cleaned.count("?") > 1:
        first = cleaned.find("?")
        cleaned = cleaned[: first + 1] + cleaned[first + 1 :].replace("?", ".")
    words = cleaned.split()
    if len(words) > 20:
        trimmed = " ".join(words[:20]).rstrip(" ,;:-")
        if "?" in cleaned[: len(trimmed) + 5]:
            return trimmed.rstrip(".") + "?"
        return trimmed.rstrip(".") + "."
    return cleaned
