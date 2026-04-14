"""LLM module — intent extraction only for the voice pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

from groq import APIError, APITimeoutError, Groq, RateLimitError

import llm.config as cfg

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

KNOWN_INTENTS: confirm_identity, confirm, deny, provide_intent, provide_location,
provide_budget, provide_property_type, provide_timeline, confirm_site_visit,
deny_site_visit, provide_visit_datetime, ask_location_suggestion, ask_off_topic, unclear_intent,
unclear_location, unclear_budget, unclear_property_type, unclear_visit_datetime,
unclear_callback_time, unclear

Rules:
- Choose the single most specific intent
- Confirmation words (yes, yeah, yep, correct, right, ok, okay, sure, go ahead) -> intent: "confirm"
- Denial words (no, not now, busy, later, nahi) -> intent: "deny"
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
    """Call Groq with retry logic and return the raw content string."""
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
            logger.error("Groq rate limit hit on attempt %d.", attempt)
            time.sleep(2**attempt)
        except APITimeoutError:
            logger.error("Groq request timed out on attempt %d.", attempt)
            if attempt == cfg.MAX_RETRIES:
                return ""
        except APIError as exc:
            logger.error("Groq API error on attempt %d: %s", attempt, exc)
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
# Informational LLM fallback — called ONLY when no JSON node matches intent
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

_INFORMATIONAL_SYSTEM = (
    "You are Neha, a real estate assistant on a phone call. "
    "Answer the user's question in 1–2 sentences, maximum 25 words. "
    "Be factual and neutral — do not pitch or persuade. "
    "Do NOT ask any question — the system will ask the next question automatically. "
    "Do NOT collect information like location, budget, or property type. "
    "Plain text only. No JSON. No markdown."
)
if _PROMPT_RULES:
    _INFORMATIONAL_SYSTEM += "\n\n" + _PROMPT_RULES

_STATIC_FALLBACK = (
    "That's a great question. Let me continue with a few details to help you better."
)


def generate_informational_response(user_text: str, context: dict) -> str:
    """
    Generate a short informational reply for off-topic or clarification questions.
    Called ONLY when _is_informational_query() returns True in state_manager.

    Constraints:
    - Maximum 2 sentences, 25 words total
    - Neutral, factual tone — not a sales pitch
    - Must NOT ask a new question (JSON node handles the next question)
    - Must NOT collect slot values (location, budget, etc.)
    - Plain text only — no JSON, no markdown
    - Falls back to _STATIC_FALLBACK on API failure — never raises

    Settings: max_tokens=60, temperature=0.3
    """
    prompt = (
        f'User asked: "{user_text}"\n'
        f"Context: {context}\n"
        "Provide a brief factual answer only."
    )
    messages = [
        {"role": "system", "content": _INFORMATIONAL_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    try:
        raw = _call_groq_api(messages, max_tokens=60, temperature=0.3)
    except Exception as exc:
        logger.error("[LLM FALLBACK] API error — using static fallback: %s", exc)
        return _STATIC_FALLBACK

    if not raw or not raw.strip():
        return _STATIC_FALLBACK

    # Strip trailing question marks — JSON node owns the next question
    reply = raw.strip().rstrip("?").rstrip()
    return reply or _STATIC_FALLBACK


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
        from llm.state_manager import StateManager

        state_manager = StateManager("Updated_Real_Estate_Agent.json")

    if not allow_transition:
        return await asyncio.to_thread(state_manager.next_step, user_text, False)

    if getattr(state_manager, "is_actionable", None) and not state_manager.is_actionable(user_text):
        return await asyncio.to_thread(state_manager.process_noise_turn, user_text)

    intent_data = await asyncio.to_thread(extract_intent, user_text)

    return await asyncio.to_thread(state_manager.process_turn, user_text, intent_data)
