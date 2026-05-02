"""LLM-powered spoken response generator — the SOLE response path.

Architecture:
    STT → Intent Extraction → StateManager (transitions ONLY) → LLMResponseGenerator (responses ONLY) → TTS

This module is the ONLY place that generates spoken responses.
StateManager handles transitions and returns a TurnResult.
This module takes that TurnResult and produces the spoken text.

Design:
    - JSON phrases = guidance (style + vocabulary)
    - LLM = sentence construction (final output)
    - Template fill = fast path for predictable nodes (greeting, goodbye)
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── TurnResult: what StateManager returns after a transition ──────────────────

@dataclass
class TurnResult:
    """Structured output from StateManager after executing a state transition.

    StateManager produces this. LLMResponseGenerator consumes it.
    """
    node: dict[str, Any]            # The resolved node after transition
    node_id: str = ""               # Node ID shortcut
    context: dict[str, Any] = field(default_factory=dict)  # Conversation data
    user_input: str = ""            # What the user said
    language: str = "en"            # Detected language
    is_terminal: bool = False       # Conversation ended
    user_question: Optional[str] = None  # "identity" | "purpose" | "confusion" | None
    response_type: str = "normal"   # "normal" | "noise_repeat" | "deescalation" | "greeting"
    asked_flags: dict[str, bool] = field(default_factory=dict)  # What has been asked already
    last_response: str = ""         # Previous agent response (for anti-repetition)
    node_changed: bool = False      # True if a state transition occurred (skip LLM, use template)

    def __post_init__(self):
        if not self.node_id:
            self.node_id = str(self.node.get("id", ""))


# ─── Load the response system prompt ──────────────────────────────────────────

def _load_response_prompt() -> str:
    prompt_path = Path(__file__).resolve().parent / "response_prompt.txt"
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning("Could not load response_prompt.txt: %s", exc)
        return ""


_RESPONSE_SYSTEM_PROMPT: str = _load_response_prompt()


# ─── Node classification ─────────────────────────────────────────────────────

# Nodes where the LLM generates dynamic responses using JSON phrases as guidance.
# DISABLED: All nodes now use their pre-written JSON templates directly.
# This ensures strict adherence to the 7 flow states with the exact same question every time.
_LLM_RESPONSE_NODES: set[str] = set()  # Empty = all nodes use templates

# Nodes that always use fast template responses (no LLM call needed)
_TEMPLATE_ONLY_NODES = {
    "node-1767592854176",       # Smart Greeting
    "node-1735264873079",       # Availability Check
    "node-1735265209472",       # Save Lead & Confirm
    "node-1736567518748",       # Confirm Callback
    "node-1736492485610",       # Polite Goodbye
    "node-1736492925252",       # Confirm and End
    "node-1735969972303",       # End Conversation
    "node-1736492520068",       # Immediate End Call
    "node-wrong-person-end",    # Wrong Person End
}


def _classify_node_goal(node: dict[str, Any], *, location: str | None, budget: str | None) -> str:
    """Classify the current node's goal for the LLM prompt."""
    node_id = str(node.get("id") or "")
    node_name = str(node.get("name") or "").lower()

    if node_id == "node-1767592854176":
        return "greet_and_confirm_identity"
    if node_id in {"node-1735264873079", "node-1735970090937"}:
        return "ask_availability"
    if node_id in {"node-1735264921453", "fallback_intent"} or "intent" in node_name or "purpose" in node_name:
        return "ask_intent"
    if node_id == "node-1735267546732":
        if location and not budget:
            return "ask_budget"
        return "ask_location"
    if node_id in {"fallback_location"} or "location" in node_name:
        return "ask_location"
    if node_id in {"fallback_budget"} or "budget" in node_name:
        return "ask_budget"
    if node_id == "node-1736323961832":
        return "share_property"
    if node_id in {"node-1735265015507", "fallback_visit_datetime"}:
        return "ask_visit_time"
    if node_id in {"node-1736492391269", "fallback_callback_time"}:
        return "ask_callback_time"
    if node_id in {"node-1735265209472", "node-1736567518748"}:
        return "confirm_and_close"
    if node.get("type") == "end":
        return "end_conversation"
    if "objection" in node_name:
        return "handle_objection"
    if "seller" in node_name:
        return "seller_flow"
    return "generic"


# ─── Phrase extraction from nodes ─────────────────────────────────────────────

def _extract_node_phrases(node: dict[str, Any]) -> list[str]:
    """Extract all relevant phrases from a conversation node for LLM guidance."""
    phrases: list[str] = []

    resp = node.get("response")
    if isinstance(resp, str) and resp.strip():
        phrases.append(resp.strip())

    msr = node.get("missing_slot_responses")
    if isinstance(msr, dict):
        for v in msr.values():
            if isinstance(v, str) and v.strip():
                phrases.append(v.strip())

    instruction = node.get("instruction", {})
    if isinstance(instruction, dict):
        text = instruction.get("text", "")
        if isinstance(text, str) and text.strip():
            phrases.append(text.strip())

    return phrases


# ─── User message building ───────────────────────────────────────────────────

def _build_llm_user_message(
    *,
    node_goal: str,
    json_phrases: list[str],
    purpose: str | None,
    location: str | None,
    budget: str | None,
    memory: Any,
    user_input: str,
    language: str,
    asked_flags: dict[str, bool] | None = None,
    last_response: str = "",
) -> str:
    """Build the user message matching the clean prompt format."""
    phrases_block = "\n".join(f"- {p}" for p in json_phrases) if json_phrases else "(none)"

    # Build compact context line
    ctx_parts = []
    if purpose:
        ctx_parts.append(f"purpose={purpose}")
    if location:
        ctx_parts.append(f"location={location}")
    if budget:
        ctx_parts.append(f"budget={budget}")
    context_line = ", ".join(ctx_parts) if ctx_parts else "no context yet"

    # Build asked flags line (only show what's been asked)
    already_asked = ""
    if asked_flags:
        asked_items = [k for k, v in asked_flags.items() if v]
        if asked_items:
            already_asked = f"\nAlready asked: {', '.join(asked_items)}"

    # Anti-repetition line
    last_line = ""
    if last_response:
        last_line = f'\nLast response: "{last_response}"'

    return (
        f"Node goal: {node_goal}\n"
        f"User: \"{user_input}\"\n"
        f"Context: {context_line}\n"
        f"Language: {language}"
        f"{already_asked}"
        f"{last_line}\n\n"
        f"Reference phrases:\n{phrases_block}"
    )


# ─── User question handling (structured, no LLM needed) ──────────────────────

def _answer_user_question(question_type: str, language: str) -> str:
    """Return a brief answer to a user's meta-question (identity, purpose, confusion)."""
    if language in ("hi", "hinglish"):
        if question_type == "identity":
            return "Neha bol rahi hoon, Real Estate team se."
        if question_type == "purpose":
            return "Aapki earlier property interest ke baare mein call kiya hai."
        return "Thoda clear bolenge?"
    if language == "mr":
        if question_type == "identity":
            return "Neha बोलतेय, Real Estate team मधून."
        if question_type == "purpose":
            return "तुमच्या earlier property interest बद्दल call केला आहे."
        return "थोडं clear सांगाल का?"
    # English
    if question_type == "identity":
        return "Neha here from the Real Estate team."
    if question_type == "purpose":
        return "It's about your earlier property interest."
    return "Could you say that differently?"


# ─── Template response (fast path for predictable nodes) ─────────────────────

def _resolve_template_response(
    node: dict[str, Any],
    context: dict[str, Any],
    language: str,
) -> str:
    """Fill {{placeholders}} in a node's template response. Fast path, no LLM."""
    from .language_utils import localize_template

    template = node.get("response", "")
    if not template:
        template = (node.get("instruction") or {}).get("text", "")
    if not template:
        return ""

    def fill(match: re.Match[str]) -> str:
        key = match.group(1)
        if key == "name":
            val = context.get("name") or context.get("lead_name") or context.get("lead") or "Prashant"
        else:
            val = context.get(key)
        return str(val) if val else ""

    localized = localize_template(template, language)
    resolved = re.sub(r"\{\{(\w+)\}\}", fill, localized).strip()
    resolved = re.sub(r" +", " ", resolved)
    return resolved


# ─── Response finalization ───────────────────────────────────────────────────

_FILLER_OPENERS = (
    "sure,", "sure -", "sure —", "sure.",
    "great,", "great -", "great —", "great.",
    "absolutely,", "absolutely -", "absolutely —",
    "certainly,", "certainly -", "certainly —",
    "wonderful,", "wonderful -", "wonderful —",
    "understood,", "understood -", "understood —",
)


def _finalize_response(text: str) -> str:
    """Apply production constraints: max 2 sentences, 30 words (sentence-boundary-aware), 1 question, no fillers, complete sentences."""
    if not text or not text.strip():
        return text

    cleaned = text.strip()

    # Strip accidental JSON/markdown/label formatting
    if (cleaned.startswith('"') and cleaned.endswith('"')) or \
       (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    cleaned = re.sub(
        r"^(?:response|output|answer|reply)\s*[:—-]\s*",
        "", cleaned, flags=re.IGNORECASE,
    ).strip()

    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove filler openers
    lowered = cleaned.lower()
    for filler in _FILLER_OPENERS:
        if lowered.startswith(filler):
            cleaned = cleaned[len(filler):].lstrip(" ,.-—")
            break

    # Max 2 sentences
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", cleaned) if p.strip()]
    if len(parts) > 2:
        parts = parts[:2]
    cleaned = " ".join(parts)

    # Single question mark
    if cleaned.count("?") > 1:
        first = cleaned.find("?")
        cleaned = cleaned[:first + 1] + cleaned[first + 1:].replace("?", ".")

    # Max 30 words — truncate to nearest complete sentence boundary
    words = cleaned.split()
    if len(words) > 30:
        # Find the last sentence-ending punctuation within the first 30 words
        truncated = " ".join(words[:30])
        last_period = max(truncated.rfind("."), truncated.rfind("?"), truncated.rfind("!"))
        if last_period > 10:  # Found a sentence boundary
            cleaned = truncated[:last_period + 1]
        else:
            # No good boundary found — hard cut at 25 words and add punctuation
            cleaned = " ".join(words[:25]).rstrip(" ,;:-")
            if "?" in truncated:
                cleaned = cleaned.rstrip(".") + "?"
            else:
                cleaned = cleaned.rstrip(".") + "."
        words = cleaned.split()

    # ── Completeness validation (HARD CONSTRAINT) ─────────────────────
    # Strip trailing connectors that signal an incomplete sentence
    _trailing = {"and", "or", "but", "to", "for", "with", "the", "a", "an",
                 "is", "are", "in", "on", "at", "of", "so", "—", "-",
                 "it's", "let", "me", "that", "like"}
    while words and words[-1].lower().rstrip(".,;:-—") in _trailing:
        words.pop()

    if not words:
        return ""

    cleaned = " ".join(words)

    # Ensure terminal punctuation
    if cleaned and cleaned[-1] not in ".!?":
        question_starters = ("what", "which", "where", "when", "how", "who",
                             "are", "is", "do", "does", "can", "could", "would",
                             "kya", "kahan", "kaun", "kab", "kitna")
        if words[0].lower() in question_starters:
            cleaned += "?"
        else:
            cleaned += "."

    return cleaned


# ─── LLM call ────────────────────────────────────────────────────────────────

async def _call_llm_for_response(
    node: dict[str, Any],
    *,
    purpose: str | None,
    location: str | None,
    budget: str | None,
    memory: Any,
    user_input: str,
    language: str,
    asked_flags: dict[str, bool] | None = None,
    last_response: str = "",
) -> str:
    """Call the LLM to generate a response using JSON phrases as guidance.

    Returns empty string on failure (caller should fall back to template).
    """
    from . import config as cfg
    from .llm import _async_call_groq_api

    if not _RESPONSE_SYSTEM_PROMPT:
        logger.warning("[LLM RESPONSE] No system prompt loaded")
        return ""

    json_phrases = _extract_node_phrases(node)
    node_goal = _classify_node_goal(node, location=location, budget=budget)

    user_message = _build_llm_user_message(
        node_goal=node_goal,
        json_phrases=json_phrases,
        purpose=purpose,
        location=location,
        budget=budget,
        memory=memory,
        user_input=user_input,
        language=language,
        asked_flags=asked_flags,
        last_response=last_response,
    )

    messages = [
        {"role": "system", "content": _RESPONSE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    logger.info(
        "[LLM RESPONSE] Generating for node=%s goal=%s user=\"%s\"",
        node.get("id", "?"), node_goal, (user_input or "")[:60],
    )

    try:
        raw = await _async_call_groq_api(
            messages,
            max_tokens=cfg.PHRASE_RESPONSE_MAX_TOKENS,
            temperature=cfg.PHRASE_RESPONSE_TEMPERATURE,
        )
    except Exception as exc:
        logger.error("[LLM RESPONSE] API error: %s", exc)
        return ""

    if not raw or not raw.strip():
        logger.warning("[LLM RESPONSE] Empty LLM output")
        return ""

    return raw.strip()


# ─── Main entry point: generate response for a TurnResult ────────────────────

async def generate_response_for_turn(turn: TurnResult) -> str:
    """Generate the final spoken response for a completed state transition.

    This is the SOLE response generation path. Called by the pipeline orchestrator.

    Routing:
    1. User question → structured answer + node continuation
    2. LLM response nodes → LLM generates using JSON phrases as guidance
    3. Template nodes → fast {{placeholder}} fill
    4. Fallback → node template if LLM fails
    """
    node = turn.node
    node_id = turn.node_id
    context = turn.context
    user_input = turn.user_input
    language = turn.language
    asked_flags = turn.asked_flags
    last_response = turn.last_response

    purpose = context.get("intent_value") or context.get("purpose")
    location = context.get("location")
    budget = context.get("budget")
    memory = context.get("memory")

    # ── Path 1: User is asking a meta-question ────────────────────────────
    if turn.user_question:
        answer = _answer_user_question(turn.user_question, language)

        # If the node goal needs a follow-up question, generate it via LLM
        if node_id in _LLM_RESPONSE_NODES:
            follow_up = await _call_llm_for_response(
                node,
                purpose=purpose,
                location=location,
                budget=budget,
                memory=memory,
                user_input=f"[User asked: {turn.user_question}] {user_input}",
                language=language,
                asked_flags=asked_flags,
                last_response=last_response,
            )
            if follow_up:
                combined = f"{answer} {_finalize_response(follow_up)}"
                logger.info("[LLM RESPONSE] Question+Continue: \"%s\"", combined)
                return _finalize_response(combined)

        # Fallback: answer + template
        template = _resolve_template_response(node, context, language)
        if template:
            combined = f"{answer} {template}"
            return _finalize_response(combined)
        return _finalize_response(answer)

    # ── Path 2: Noise / non-actionable input → repeat current node ────────
    if turn.response_type == "noise_repeat":
        response = _resolve_template_response(node, context, language)
        logger.info("[TEMPLATE] Noise repeat for %s", node_id)
        return _finalize_response(response) if response else ""

    # ── Path 3: Deescalation (hostile input) ──────────────────────────────
    if turn.response_type == "deescalation":
        from .state_manager import DEESCALATION_RESPONSES
        idx = hash(user_input) % len(DEESCALATION_RESPONSES)
        return DEESCALATION_RESPONSES[idx]

    # ── Path 4: LLM-powered response for qualification/fallback nodes ─────
    # ONLY use LLM when staying on the same node (needs clarification/rephrasing).
    # If the node changed (user answered correctly), skip LLM and use template directly.
    if node_id in _LLM_RESPONSE_NODES and not turn.node_changed:
        llm_response = await _call_llm_for_response(
            node,
            purpose=purpose,
            location=location,
            budget=budget,
            memory=memory,
            user_input=user_input,
            language=language,
            asked_flags=asked_flags,
            last_response=last_response,
        )
        if llm_response:
            finalized = _finalize_response(llm_response)
            if finalized:
                # ── Anti-repetition guard ─────────────────────────────
                if last_response and _is_repetition(finalized, last_response):
                    logger.warning("[ANTI-REPEAT] LLM repeated last response, generating nudge instead")
                    # Generate a short contextual nudge instead of falling back to broken template
                    nudge = _get_anti_repeat_nudge(node, language)
                    if nudge:
                        logger.info("[ANTI-REPEAT NUDGE] \"%s\"", nudge)
                        return nudge
                else:
                    _log_phrase_usage(finalized)
                    logger.info("[LLM RESPONSE] \"%s\"", finalized)
                    return finalized
        # LLM failed → fall through to template
        logger.warning("[LLM RESPONSE] Falling back to template for %s", node_id)
    elif node_id in _LLM_RESPONSE_NODES and turn.node_changed:
        logger.info("[SKIP LLM] Node changed, using template directly for %s", node_id)

    # ── Path 5: Template response (fast path) ────────────────────────────
    response = _resolve_template_response(node, context, language)
    logger.info("[TEMPLATE] %s: \"%s\"", node_id, (response or "")[:60])
    return _finalize_response(response) if response else ""


def _get_anti_repeat_nudge(node: dict[str, Any], language: str) -> str:
    """Generate a short contextual nudge when the LLM repeats itself.

    Instead of falling back to a template with potentially missing placeholders,
    produce a clean, short follow-up based on the node's goal.
    """
    node_id = str(node.get("id", ""))
    node_name = str(node.get("name", "")).lower()

    # Goal-specific nudges (English defaults, extend for other languages as needed)
    nudges = {
        "share_property": "Would you like to see it in person?",
        "ask_intent": "Are you looking to buy or rent?",
        "ask_location": "Which area works best for you?",
        "ask_budget": "What budget range works for you?",
        "ask_visit_time": "Would a weekend or weekday work better?",
        "ask_availability": "Do you have a couple of minutes right now?",
        "handle_objection": "Would you be open to hearing about other options?",
    }

    # Classify the node goal
    goal = _classify_node_goal(node, location=None, budget=None)

    nudge = nudges.get(goal, "")
    if not nudge:
        # Generic fallback nudge
        nudge = "Would you like to know more?"

    # Basic language adaptation
    if language in ("hi", "hinglish"):
        hi_nudges = {
            "share_property": "Kya aap ise personally dekhna chahenge?",
            "ask_intent": "Aap buy karna chahte ho ya rent?",
            "ask_location": "Kaun sa area prefer karenge?",
            "ask_budget": "Roughly kitna budget hai aapka?",
            "ask_visit_time": "Weekend better rahega ya weekday?",
        }
        nudge = hi_nudges.get(goal, nudge)

    return nudge


def _is_repetition(new_response: str, last_response: str) -> bool:
    """Check if new_response is essentially the same as last_response."""
    a = new_response.lower().strip().rstrip("?.!,")
    b = last_response.lower().strip().rstrip("?.!,")
    if not a or not b:
        return False
    # Exact match
    if a == b:
        return True
    # High overlap (>80% of words shared)
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    return overlap > 0.8


def _log_phrase_usage(response: str) -> None:
    """Log which phrase bank entries were used (for debugging)."""
    try:
        from .state_manager import _match_phrases_used, _PHRASE_BANK
        matched = _match_phrases_used(response, _PHRASE_BANK)
        if matched:
            logger.info("[JSON PHRASES USED] %s", "; ".join(f'"{p}"' for p in matched[:5]))
    except Exception:
        pass


# ─── Sync wrapper (for backward compatibility) ──────────────────────────────

def generate_response_for_turn_sync(turn: TurnResult) -> str:
    """Synchronous wrapper for generate_response_for_turn.

    Handles the case where we're already inside an async event loop
    (common in the pipeline's to_thread() calls).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, generate_response_for_turn(turn))
            return future.result(timeout=10)
    else:
        return asyncio.run(generate_response_for_turn(turn))
