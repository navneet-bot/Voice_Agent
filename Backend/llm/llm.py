"""LLM module — intent extraction only for the voice pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from groq import APIError, APITimeoutError, Groq, RateLimitError

from . import config as cfg

logger = logging.getLogger(__name__)

if not cfg.GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Run: $env:GROQ_API_KEY = 'your_key_here'  (PowerShell)\n"
        "Or:  export GROQ_API_KEY='your_key_here'  (Linux/Mac)"
    )

_client = Groq(api_key=cfg.GROQ_API_KEY, timeout=cfg.REQUEST_TIMEOUT_S)

KNOWN_INTENTS = [
    "confirm_identity",
    "confirm",
    "deny",
    "deny_identity",
    "deny_interest",
    "deny_time",
    "deny_visit_time",
    "provide_intent",
    "provide_location",
    "provide_budget",
    "provide_property_type",
    "provide_timeline",
    "confirm_site_visit",
    "deny_site_visit",
    "provide_visit_datetime",
    "ask_location_suggestion",
    "ask_off_topic",
    "unclear_intent",
    "unclear_location",
    "unclear_budget",
    "unclear_property_type",
    "unclear_visit_datetime",
    "unclear_callback_time",
    "unclear",
]

INTENT_EXTRACTION_SYSTEM_PROMPT = """You are an intent classifier for a real estate voice agent.

Extract structured intent and entities from the user's message.
You must NOT generate conversational replies.
You only classify intent and extract entities for a JSON-driven state machine.
Respond ONLY with a valid JSON object. No markdown. No explanation. No prose.

Schema:
{
  "intent": "<exactly one intent from the list below>",
  "entities": {
    "location":      "<city or area name, or null>",
    "budget":        "<number + unit e.g. 25 lakh, or null>",
    "property_type": "<e.g. 2 BHK / villa / apartment, or null>",
    "intent_value":  "<buy / rent / invest, or null>",
    "timeline":      "<duration or date, or null>",
    "confirmation":  "<yes / no, or null>"
  }
}

KNOWN_INTENTS: confirm_identity, confirm, deny, deny_identity, deny_interest,
deny_time, deny_visit_time, provide_intent, provide_location,
provide_budget, provide_property_type, provide_timeline, confirm_site_visit,
deny_site_visit, provide_visit_datetime, ask_location_suggestion, ask_off_topic, unclear_intent,
unclear_location, unclear_budget, unclear_property_type, unclear_visit_datetime,
unclear_callback_time, unclear

Rules:
- Choose the single most specific intent
- Confirmation words (yes, yeah, yep, correct, right, ok, okay, sure, go ahead) -> intent: "confirm"
- Generic denial (no, nahi) without specific keywords -> intent: "deny"
- "wrong number", "wrong person", "not Prashant", "this is not" -> intent: "deny_identity"
- "not interested", "no requirement", "don't need property" -> intent: "deny_interest"
- "busy", "call later", "not now", "in a meeting" -> intent: "deny_time"
- "not this weekend", "busy this week", "can't this week" -> intent: "deny_visit_time"
- Location suggestion questions like "suggest", "recommend", "which area", "best location",
  "good location", or "any options" -> intent: "ask_location_suggestion"
- Do not label a suggestion question as "provide_location"
- If the answer is uncertainty like "I don't know", "not sure", or "maybe", prefer a matching
  unclear intent when the user is hesitating about intent, location, budget, property type,
  site visit date/time, or callback time
- Noise like "hmm", "uh", "ah", "ohh", ".", ",", "this", or "that" -> intent: "unclear"
- All entity fields default to null if not present"""

_EMPTY_INTENT = {"intent": "unclear", "entities": {}}


def _call_groq_api(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    response_format: Optional[dict[str, str]] = None,
) -> str:
    """Call Groq with retry + exponential backoff. Returns raw content string.

    Issue 13 fix: backoff uses time.sleep in this sync function (called via
    run_in_executor so it does NOT block the async event loop).
    """
    import random as _random
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            t0 = time.time()
            completion = _client.chat.completions.create(
                model=cfg.MODEL_NAME,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=cfg.TOP_P,
                response_format=response_format,
            )
            latency = time.time() - t0
            logger.info("LLM request completed in %.3fs (attempt %d/%d)", latency, attempt, cfg.MAX_RETRIES)
            return completion.choices[0].message.content or ""
        except RateLimitError:
            wait = (2 ** attempt) + _random.uniform(0, 0.5)   # jitter
            logger.warning("Groq rate limit hit (attempt %d/%d) — retrying in %.1fs", attempt, cfg.MAX_RETRIES, wait)
            if attempt < cfg.MAX_RETRIES:
                time.sleep(wait)
        except APITimeoutError:
            logger.error("Groq request timed out (attempt %d/%d)", attempt, cfg.MAX_RETRIES)
            if attempt == cfg.MAX_RETRIES:
                return ""
            time.sleep(1.0)
        except APIError as exc:
            logger.error("Groq API error (attempt %d/%d): %s", attempt, cfg.MAX_RETRIES, exc)
            return ""
    return ""


def extract_intent(user_text: str) -> dict[str, Any]:
    """
    Call Groq API for intent + entity extraction.
    Returns: {"intent": str, "entities": dict}
    Returns: {"intent": "unclear", "entities": {}} on any failure — never raises.
    """
    if not user_text or not user_text.strip():
        return dict(_EMPTY_INTENT)

    messages = [
        {"role": "system", "content": INTENT_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_text.strip()},
    ]
    raw_content = _call_groq_api(
        messages,
        max_tokens=80,
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    if not raw_content:
        return dict(_EMPTY_INTENT)

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        logger.error("[LLM] JSON parse failed")
        return dict(_EMPTY_INTENT)

    entities = data.get("entities")
    if not isinstance(entities, dict):
        entities = {}

    normalized_entities = {
        "location": entities.get("location"),
        "budget": entities.get("budget"),
        "property_type": entities.get("property_type"),
        "intent_value": entities.get("intent_value"),
        "timeline": entities.get("timeline"),
        "confirmation": entities.get("confirmation"),
    }

    intent = str(data.get("intent") or "unclear").strip()
    if intent not in KNOWN_INTENTS:
        intent = "unclear"

    return {"intent": intent, "entities": normalized_entities}


# ---------------------------------------------------------------------------
# Phrase-constrained LLM response — called ONLY when no JSON node matches
# ---------------------------------------------------------------------------

def _load_prompt_rules() -> str:
    """Load behavioral rules from prompt.txt once at module init."""
    prompt_path = Path(__file__).resolve().parent / "prompt.txt"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning("Could not load prompt.txt: %s", exc)
        return ""


_PROMPT_RULES: str = _load_prompt_rules()

_STATIC_FALLBACK = (
    "That's a great question. Let me continue with a few details to help you better."
)


def _build_phrase_constrained_system(phrase_bank: list[str]) -> str:
    """
    Build a system prompt that constrains the LLM to compose responses
    using ONLY phrases from the approved phrase bank.
    """
    bank_text = "\n".join(f"- {p}" for p in phrase_bank)
    system = (
        "You are Neha, a real estate assistant on a phone call.\n\n"
        "## RESPONSE CONSTRUCTION RULES\n"
        "You MUST construct your response using ONLY words, phrases, and sentences "
        "from the PHRASE BANK below.\n"
        "You may slightly modify grammar to make the response natural.\n"
        "You must NOT introduce new claims, facts, or sales statements not present "
        "in the PHRASE BANK.\n"
        "You must NOT change the meaning of any business messaging.\n\n"
        "## COMPOSITION RULES\n"
        "- Maximum 2 sentences per response\n"
        "- Maximum 25 words per sentence\n"
        "- Do NOT ask any question — the system will ask the next question automatically\n"
        "- Do NOT collect information like location, budget, or property type\n"
        "- Plain text only. No JSON. No markdown.\n"
        "- Professional, conversational tone\n"
        "- Avoid unnecessary filler words\n\n"
        f"## PHRASE BANK\n{bank_text}\n"
    )
    if _PROMPT_RULES:
        system += "\n## ADDITIONAL RULES\n" + _PROMPT_RULES
    return system


def generate_phrase_constrained_response(user_text: str, context: dict) -> str:
    """
    Generate a short response for off-topic or clarification questions,
    constrained to use phrases from the JSON conversation file's phrase bank.

    Called ONLY when _is_informational_query() returns True in state_manager.

    Constraints:
    - Response composed from approved phrase bank entries
    - Maximum 2 sentences, 25 words per sentence
    - Neutral, factual tone — not a sales pitch
    - Must NOT ask a new question (JSON node handles the next question)
    - Must NOT collect slot values (location, budget, etc.)
    - Plain text only — no JSON, no markdown
    - Falls back to _STATIC_FALLBACK on API failure — never raises

    Settings: max_tokens=cfg.PHRASE_RESPONSE_MAX_TOKENS,
              temperature=cfg.PHRASE_RESPONSE_TEMPERATURE
    """
    from .state_manager import get_phrase_bank
    phrase_bank = get_phrase_bank()

    system_prompt = _build_phrase_constrained_system(phrase_bank)

    prompt = (
        f'User asked: "{user_text}"\n'
        f"Context: {context}\n"
        "Compose a brief response using ONLY phrases from the PHRASE BANK. "
        "Do not invent new statements."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    logger.info("[LLM REASONING] Generating phrase-constrained response for: \"%s\"", user_text)

    try:
        raw = _call_groq_api(
            messages,
            max_tokens=cfg.PHRASE_RESPONSE_MAX_TOKENS,
            temperature=cfg.PHRASE_RESPONSE_TEMPERATURE,
        )
    except Exception as exc:
        logger.error("[LLM FALLBACK] API error — using static fallback: %s", exc)
        return _STATIC_FALLBACK

    if not raw or not raw.strip():
        return _STATIC_FALLBACK

    # Strip trailing question marks — JSON node owns the next question
    reply = raw.strip().rstrip("?").rstrip()
    if not reply:
        return _STATIC_FALLBACK

    # Log phrase matching
    from .state_manager import _match_phrases_used, _PHRASE_BANK
    matched = _match_phrases_used(reply, _PHRASE_BANK)
    if matched:
        logger.info("[JSON PHRASES USED] %s", "; ".join(f'"{p}"' for p in matched[:5]))
    logger.info("[FINAL RESPONSE] \"%s\"", reply)

    return reply


# Keep old name as alias for backward compatibility
generate_informational_response = generate_phrase_constrained_response


async def generate_response(
    user_text: str,
    conversation_history: Optional[list[dict]] = None,
    language: str = cfg.DEFAULT_LANGUAGE,
    state_manager: Optional[Any] = None,
    allow_transition: bool = True,
) -> str:
    """Async compatibility wrapper for the pipeline entry point."""
    del conversation_history, language

    if state_manager is None:
        from .state_manager import StateManager

        state_manager = StateManager("Updated_Real_Estate_Agent.json")

    if not allow_transition:
        return await asyncio.to_thread(state_manager.next_step, user_text, False)

    if getattr(state_manager, "is_actionable", None) and not state_manager.is_actionable(user_text):
        return await asyncio.to_thread(state_manager.process_noise_turn, user_text)

    intent_data = await asyncio.to_thread(extract_intent, user_text)

    return await asyncio.to_thread(state_manager.process_turn, user_text, intent_data)
