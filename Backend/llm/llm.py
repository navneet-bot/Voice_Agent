"""LLM module — intent extraction only for the voice pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

from groq import AsyncGroq, APIError, APITimeoutError, RateLimitError

from . import config as cfg

logger = logging.getLogger(__name__)

if not cfg.GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Run: $env:GROQ_API_KEY = 'your_key_here'  (PowerShell)\n"
        "Or:  export GROQ_API_KEY='your_key_here'  (Linux/Mac)"
    )

_client = AsyncGroq(api_key=cfg.GROQ_API_KEY, timeout=cfg.REQUEST_TIMEOUT_S)

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
- The user may speak in English, Hindi, or Hinglish. Understand romanized Hindi too.
- Map natural Hindi/Hinglish phrases to the same schema:
  - "investment ke liye", "nivesh ke liye" -> provide_intent with intent_value "invest"
  - "khud ke liye", "apne liye", "rehne ke liye" -> provide_intent with intent_value "buy"
  - "rent pe", "kiraye pe", "on rent" -> provide_intent with intent_value "rent"
  - "budget 50 lakh", "50 lakh ke around", "mera budget 1 crore hai" -> extract budget
- Confirmation words (yes, yeah, yep, correct, right, ok, okay, sure, go ahead) -> intent: "confirm"
- Generic denial (no, nahi, nope, nah, not now, sorry no, no sorry) -> intent: "deny"
- "wrong number", "wrong person", "not Prashant", "this is not" -> intent: "deny_identity"
- "not interested", "no requirement", "don't need property", "not really" -> intent: "deny_interest"
- "busy", "call later", "not now", "in a meeting", "busy right now" -> intent: "deny_time"
- "not this weekend", "busy this week", "can't this week" -> intent: "deny_visit_time"
- Location suggestion questions like "suggest", "recommend", "which area", "best location",
  "good location", or "any options" -> intent: "ask_location_suggestion"
- Do not label a suggestion question as "provide_location"
- If the answer is uncertainty like "I don't know", "not sure", or "maybe", prefer a matching
  unclear intent when the user is hesitating about intent, location, budget, property type,
  site visit date/time, or callback time
- Noise like "hmm", "uh", "ah", "ohh", ".", ",", "this", or "that" -> intent: "unclear"
- All entity fields default to null if not present
- CRITICAL: Never label a simple "No" or "No, sorry" as "unclear". These are "deny".
- CRITICAL: "not really" or "no requirement" is "deny_interest"."""

_EMPTY_INTENT = {"intent": "unclear", "entities": {}}

_BUDGET_PATTERN = re.compile(
    r"\b(?:budget|price|range|around|approx|approximately|mera budget|budget hai|budget is)?\s*"
    r"(\d+(?:\.\d+)?)\s*(crore|crores|cr|lakh|lakhs|lac|lacs|thousand|k)\b",
    re.IGNORECASE,
)
_BUY_HINTS = (
    "khud ke liye", "apne liye", "rehne ke liye", "ghar ke liye", "for myself",
    "for self", "self use", "personal use", "to live", "move in", "own use",
)
_INVEST_HINTS = (
    "investment ke liye", "nivesh ke liye", "return ke liye", "invest karna",
    "for investment", "investment", "invest", "roi", "rental income",
)
_RENT_HINTS = (
    "rent pe", "kiraye pe", "kiraya", "on rent", "rent ke liye", "looking to rent",
    "for rent", "to rent",
)


def _normalize_budget_unit(unit: str) -> str:
    unit = unit.lower()
    if unit in {"crores", "cr"}:
        return "crore"
    if unit in {"lakhs", "lac", "lacs"}:
        return "lakh"
    if unit == "k":
        return "thousand"
    return unit


def _extract_budget_entity(user_text: str) -> str | None:
    match = _BUDGET_PATTERN.search(user_text or "")
    if not match:
        return None
    number = match.group(1)
    unit = _normalize_budget_unit(match.group(2))
    return f"{number} {unit}"


def _enrich_intent_entities(user_text: str, intent: str, entities: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    clean_text = (user_text or "").strip().lower()
    entities = dict(entities)

    if not entities.get("budget"):
        budget = _extract_budget_entity(user_text)
        if budget:
            entities["budget"] = budget
            if intent == "unclear":
                intent = "provide_budget"

    if not entities.get("intent_value"):
        if any(phrase in clean_text for phrase in _BUY_HINTS):
            entities["intent_value"] = "buy"
            if intent == "unclear":
                intent = "provide_intent"
        elif any(phrase in clean_text for phrase in _INVEST_HINTS):
            entities["intent_value"] = "invest"
            if intent == "unclear":
                intent = "provide_intent"
        elif any(phrase in clean_text for phrase in _RENT_HINTS):
            entities["intent_value"] = "rent"
            if intent == "unclear":
                intent = "provide_intent"

    return intent, entities


async def _async_call_groq_api(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
    temperature: float,
    response_format: Optional[dict[str, str]] = None,
) -> str:
    """Call Groq with retry + exponential backoff. Returns raw content string.

    Issue 13 fix: backoff uses asyncio.sleep instead of time.sleep to avoid blocking worker threads.
    """
    import random as _random
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            t0 = time.time()
            completion = await _client.chat.completions.create(
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
                await asyncio.sleep(wait)
        except APITimeoutError:
            logger.error("Groq request timed out (attempt %d/%d)", attempt, cfg.MAX_RETRIES)
            if attempt == cfg.MAX_RETRIES:
                return ""
            await asyncio.sleep(1.0)
        except APIError as exc:
            logger.error("Groq API error (attempt %d/%d): %s", attempt, cfg.MAX_RETRIES, exc)
            return ""
    return ""


async def extract_intent(user_text: str) -> dict[str, Any]:
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
    raw_content = await _async_call_groq_api(
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

    intent, normalized_entities = _enrich_intent_entities(user_text, intent, normalized_entities)
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
        "You are Neha — a sharp, emotionally intelligent real estate expert on a phone call.\n"
        "You speak like a high-performing human, not a script. Adapt your tone to the user's mood.\n\n"
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
        "- Conversational, human tone — never robotic or scripted\n"
        "- No filler words like 'Certainly', 'Understood', 'Wonderful'\n\n"
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
        raw = asyncio.run(_async_call_groq_api(
            messages,
            max_tokens=cfg.PHRASE_RESPONSE_MAX_TOKENS,
            temperature=cfg.PHRASE_RESPONSE_TEMPERATURE,
        ))
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
    runtime_context: Optional[dict[str, Any]] = None,
) -> str:
    """Pipeline entry point: STT → Intent → StateManager (transition) → LLMResponseGenerator (response).

    Clean architecture:
    - StateManager handles ONLY state transitions (returns TurnResult)
    - LLMResponseGenerator handles ONLY response generation
    """
    del conversation_history
    from .llm_response_generator import generate_response_for_turn
    from .state_manager import _finalize_response_text

    if state_manager is None:
        from .state_manager import StateManager
        state_manager = StateManager("Updated_Real_Estate_Agent.json")

    if getattr(state_manager, "set_active_language", None):
        state_manager.set_active_language(language)
    if runtime_context:
        state_manager.conversation_data.update(runtime_context)

    # ── Step 1: StateManager — transition only (no response generation) ──
    if not allow_transition:
        turn = await asyncio.to_thread(state_manager.execute_greeting_transition, user_text)
    elif getattr(state_manager, "is_actionable", None) and not state_manager.is_actionable(user_text):
        turn = await asyncio.to_thread(state_manager.execute_noise_transition, user_text)
    else:
        intent_data = await extract_intent(user_text)
        turn = await asyncio.to_thread(state_manager.execute_transition, user_text, intent_data)

    if not turn.node:
        return ""

    # ── Step 2: LLMResponseGenerator — response only ─────────────────────
    response = await generate_response_for_turn(turn)
    finalized = _finalize_response_text(response).strip()

    # ── Step 3: Record response for anti-repetition tracking ─────────────
    if hasattr(state_manager, "record_response"):
        state_manager.record_response(finalized)

    return finalized

