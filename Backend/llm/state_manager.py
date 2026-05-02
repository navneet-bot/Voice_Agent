from __future__ import annotations
import copy

import json
import logging
import uuid
import os
import re
import random
from pathlib import Path
from typing import Any, Dict, Optional

from . import config as cfg
from .conversation_response import should_answer_user_question
from .llm_response_generator import TurnResult
from .language_utils import localize_template

logger = logging.getLogger(__name__)

SHORT_NOISE = {".", ",", "uh", "ah", "hmm", "hm", "um", "oh", "ohh", "this", "that"}
NON_SKIPPABLE_NAMES = {
    "Smart Greeting",
    "Confirm and End",
    "Confirm Callback",
    "Polite Goodbye",
    "End Conversation",
    "Immediate End Call",
}
ENTITY_KEYS = ("location", "budget", "property_type", "intent_value", "timeline")
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "Updated_Real_Estate_Agent.json"
INVALID_LOCATION_VALUES = {"location", "place", "area", "there", "nek", "city", "property", "this"}
INVALID_BUDGET_VALUES = {"budget", "price", "amount"}
INVALID_PROPERTY_TYPE_VALUES = {"property", "home", "n property", "bhk"}
KNOWN_LOCATION_WHITELIST = {
    "wakad", "baner", "hinjewadi", "kharadi", "pune", "mumbai",
    "kothrud", "viman nagar", "hadapsar", "aundh", "pimpri",
    "chinchwad", "bavdhan", "pashan", "sus", "lavale",
    "magarpatta", "kondhwa", "undri", "katraj", "sinhagad road",
    "deccan", "shivajinagar",
}
INVALID_TIMELINE_VALUES = {
    "yesterday", "last week", "last month", "last year",
    "ago", "previous", "past",
}
LOCATION_NORMALIZATION = {
    # Baner variants
    "banner": "Baner",
    "banar": "Baner",
    "baner": "Baner",
    "banr": "Baner",
    # Wakad variants
    "wakud": "Wakad",
    "wakad": "Wakad",
    "waked": "Wakad",
    "vakad": "Wakad",
    # Hinjewadi variants
    "hinjewdi": "Hinjewadi",
    "hinjwadi": "Hinjewadi",
    "hinjewadi": "Hinjewadi",
    # Kharadi variants
    "kharady": "Kharadi",
    "karate": "Kharadi",
    "kharadi": "Kharadi",
    "karadi": "Kharadi",
    "kharad": "Kharadi",
}
HINDI_LOCATION_TRANSLITERATION = {
    "वाकड़": "Wakad",
    "वाकड": "Wakad",
    "बानेर": "Baner",
    "बानर": "Baner",
    "बनर": "Baner",
    "बॅनर": "Baner",
    "हिंजवडी": "Hinjewadi",
    "हिंजेवाडी": "Hinjewadi",
    "हिंजवाडी": "Hinjewadi",
    "खराडी": "Kharadi",
    "खरादी": "Kharadi",
    "खारडी": "Kharadi",
}
VISIT_SCHEDULING_NODES = {"node-1736323961832", "node-1735265015507"}
CALLBACK_SCHEDULING_NODE_ID = "node-1736492391269"

# ── Context-aware deny routing ────────────────────────────────────────────────
WRONG_PERSON_END_NODE_ID = "node-wrong-person-end"
POLITE_END_NODE_ID = "node-1735969972303"       # End Conversation
RESCHEDULE_VISIT_NODE_ID = "node_fallback_reschedule"

# Node sets where each deny sub-type applies
DENY_IDENTITY_NODES = {"node-1767592854176"}                        # Smart Greeting
DENY_TIME_NODES = {"node-1735264873079", "node-1735970090937"}      # Availability Check, Re-engage
DENY_INTEREST_NODES = {"node-1735264921453"}                        # Ask Intent
DENY_VISIT_NODES = {"node-1736323961832", "node-1735265015507"}     # Share Property, Site Visit

ALL_DENY_INTENTS = {"deny", "deny_identity", "deny_interest", "deny_time", "deny_visit_time"}
# Edges with these condition keywords auto-advance without user input
SKIP_EDGE_MARKERS = {"skip", "skip response"}
# Nodes that should auto-advance through skip edges after delivering response
AUTO_ADVANCE_NODES = {
    "node-1736492925252",  # Confirm and End
    "node-1736567518748",  # Confirm Callback
    "node-1736492485610",  # Polite Goodbye
}
FALLBACK_ESCALATION = {
    "fallback_location": "You can choose Wakad, Baner, Hinjewadi or Kharadi.",
    "fallback_budget": "Typical budgets range from 20 lakh to 1.5 crore. What range works for you?",
    "fallback_visit_datetime": "Would Saturday or Sunday this week work for you?",
    "fallback_callback_time": "Would morning or evening be more convenient?",
}
MAX_FALLBACK_ATTEMPTS = 2
LOCATION_SUGGESTION_PHRASES = (
    "suggest",
    "recommend",
    "which area",
    "best location",
    "good location",
    "any options",
)
UNCERTAIN_PHRASES = (
    "i don't know",
    "dont know",
    "don't know",
    "not sure",
    "maybe",
    "not certain",
    "unsure",
)

# ── Behavioral refinement configuration ──────────────────────────────────────
BRIDGE_ENABLED           = False
VAGUE_DETECTION_ENABLED  = False
HOSTILE_DETECTION_ENABLED = False

# Bridge words are ONLY used for unclear / fallback / noise situations.
# Normal flow responses are returned verbatim from the JSON schema.
FALLBACK_BRIDGE_PHRASES = {
    "unclear":                "Sorry, I didn't catch that.",
    "unclear_intent":         "Got it, just to clarify —",
    "unclear_location":       "Got it, just to clarify —",
    "unclear_budget":         "Got it, just to clarify —",
    "unclear_property_type":  "Got it, just to clarify —",
    "unclear_visit_datetime": "Sorry, I didn't catch that.",
    "unclear_callback_time":  "Sorry, I didn't catch that.",
}

CLARIFICATION_TEMPLATES = {
    "provide_location": "Did you mean you're looking in a specific city?",
    "provide_budget":   "Did you mean a particular budget range?",
    "provide_intent":   "Did you mean you're looking to buy or rent?",
    "unclear":          "Could you say that again in a different way?",
}

GUIDANCE_RESPONSES = {
    "budget":   "No problem — are you thinking more budget-friendly, mid-range, or premium?",
    "location": "Sure — are you open to areas near IT hubs, or do you prefer quieter residential zones?",
}

DEESCALATION_RESPONSES = [
    "Understood. Let me focus on what's most useful for you.",
    "Fair enough. I'll keep this brief and practical.",
    "Noted. What would be most helpful right now?",
]

FILLER_STARTERS = {"uh", "um", "ah", "like", "so", "er", "hmm"}

VAGUE_TOKENS = {
    "budget":   ["flexible", "not sure", "reasonable", "affordable", "depends",
                 "whatever", "not too much", "moderate", "medium"],
    "location": ["anywhere", "not sure", "somewhere", "any area", "near",
                 "doesn't matter", "flexible", "good area"],
}

HOSTILE_TOKENS = [
    "stupid", "idiot", "useless", "waste", "shut up", "stop",
    "terrible", "worst", "hate", "awful", "rubbish", "garbage",
    "don't want", "leave me", "go away", "not helpful",
    "fuck", "shit", "bitch", "ass", "damn", "screw you",
    "die", "kill", "bloody", "bastard", "crap",
]
GOODBYE_PHRASES = (
    "bye",
    "bye bye",
    "goodbye",
    "good bye",
    "good night",
    "have a good night",
    "have good night",
    "see you",
    "talk later",
)

OPENING_NODE_RESPONSES = {
    # Step 1: identity confirmation
    "node-1767592854176": "Hey, this is Neha — am I speaking with {{name}}?",
    # Step 2: availability check
    "node-1735264873079": "Is this a good time to speak?",
    # Step 3 + Step 4: context + intent discovery
    "node-1735264921453": "I actually came across your interest in property. Are you exploring for yourself or as an investment?",
    "node-1736567518748": "Thank you, we'll call you around {{timeline}}. Have a great day!",
}

BUSY_TIME_HINTS = (
    # Core
    "busy", "meeting", "call later", "not now", "later", "driving", "occupied",
    # Extended busy signals
    "in a meeting", "on a call", "at work", "at office", "working",
    "cant talk", "can't talk", "cant speak", "can't speak",
    "not a good time", "bad time", "wrong time", "bad moment",
    "call back", "call me back", "call me later", "ring me later",
    "travelling", "traveling", "in traffic", "on the way",
    "eating", "having lunch", "having dinner", "having breakfast",
    "sleeping", "resting", "tired", "not free", "not available",
    "hospital", "doctor", "emergency", "out of station",
    "thoda time de", "baad mein", "abhi nahi", "baad mein call karo",
    "give me some time", "give me a minute", "two minutes", "five minutes",
    "little busy", "bit busy", "slightly busy", "kinda busy",
    "weekend", "evening", "tonight", "tomorrow",
    "in a rush", "rushing", "hurrying", "very busy", "super busy",
)

NOT_INTERESTED_HINTS = (
    "not interested",
    "not looking",
    "no requirement",
    "dont need",
    "don't need",
    "not now",
)

INTERESTED_HINTS = (
    # Core
    "yes", "yeah", "sure", "go ahead", "tell me", "interested", "ok", "okay",
    # Extended available/interested signals
    "yep", "yup", "of course", "absolutely", "definitely", "certainly",
    "please", "please tell me", "i'm free", "i am free", "free now",
    "available", "available now", "speak now", "go on", "continue",
    "what is it", "what did you want", "what's it about", "what is it about",
    "haan", "haan bolo", "bolo", "batao", "theek hai", "bilkul",
    "i have time", "have two minutes", "have a minute", "have some time",
    "few minutes", "two minutes", "couple minutes", "quick call is fine",
    "good time", "perfect time", "right time",
    "hi yes", "yes hi", "speaking", "yes speaking", "yes this is",
    "it's me", "its me", "that's me", "thats me", "yes it is", "yes i am",
    "fine go ahead", "alright go ahead", "sure go ahead",
    "not busy", "not in a meeting", "i'm available", "i'm listening",
)

CALLBACK_PART_OF_DAY_WINDOWS = {
    "morning": (10 * 60 + 15, 11 * 60 + 45),      # 10:15 AM - 11:45 AM
    "afternoon": (14 * 60 + 15, 16 * 60 + 45),    # 2:15 PM - 4:45 PM
    "evening": (18 * 60 + 15, 20 * 60 + 45),      # 6:15 PM - 8:45 PM
    "night": (20 * 60 + 15, 21 * 60 + 45),        # 8:15 PM - 9:45 PM
}

PURPOSE_CLARIFICATION_PHRASES = (
    "who is this",
    "who are you",
    "what is this about",
    "what is it about",
    "whats this about",
    "what's this about",
    "why are you calling",
    "why did you call",
    "purpose of call",
    "kya hai",
    "kis baare",
)


def _log(tag: str, message: str) -> None:
    logger.info("[%s] %s", tag, message)


# ── Behavioral refinement helpers ────────────────────────────────────────────

def _normalise_stt(text: str) -> str:
    """
    Clean common STT artefacts before intent extraction.
    Operates on words only — no regex for performance.
    Steps (in order):
      1. Collapse immediate word repetitions: "I I want" → "I want"
      2. Strip leading filler words: "uh", "um", "ah", "like", "so", "you know"
      3. Collapse multiple spaces
    Never removes content words. Never translates or corrects spelling.
    """
    words = text.strip().split()

    # Step 1 — deduplicate adjacent identical words (case-insensitive)
    deduped = []
    for word in words:
        if not deduped or word.lower() != deduped[-1].lower():
            deduped.append(word)

    # Step 2 — strip leading fillers (one pass only — preserve content)
    while deduped and deduped[0].lower().strip(".,") in FILLER_STARTERS:
        deduped.pop(0)

    return " ".join(deduped).strip()


def _is_vague_answer(text: str, field: str) -> bool:
    """
    Return True if user gave a vague non-answer for a specific field.
    Used to offer guided defaults instead of repeating the same question.
    """
    t = text.lower()
    return any(v in t for v in VAGUE_TOKENS.get(field, []))


def _get_guidance_response(field: str) -> str:
    """Return a static guidance response for a vague slot answer."""
    return GUIDANCE_RESPONSES.get(field, "Could you give me a rough idea to help narrow it down?")


def _get_bridge(intent: str) -> str:
    """Return a short bridge phrase for unclear/fallback intents only. Empty string otherwise."""
    return FALLBACK_BRIDGE_PHRASES.get(intent, "")


def _is_hostile(text: str) -> bool:
    """
    Detect clearly hostile or dismissive input.
    Lightweight keyword check — no ML, no API call.
    """
    t = text.lower()
    return any(token in t for token in HOSTILE_TOKENS)


def _load_default_flow() -> dict[str, Any]:
    try:
        with DEFAULT_SCHEMA_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        logger.error("Failed to load state schema from %s: %s", DEFAULT_SCHEMA_PATH, exc)
        return {}
    return data.get("conversationFlow", {})


_FLOW = _load_default_flow()
_NODE_MAP: dict[str, dict[str, Any]] = {node["id"]: node for node in _FLOW.get("nodes", []) if "id" in node}


def _build_intent_index(nodes: list[dict[str, Any]]) -> dict[str, str]:
    """
    Map intent_trigger -> node_id for all nodes.
    If two nodes share a trigger, last one wins.
    """
    intent_index: dict[str, str] = {}
    for node in nodes:
        for trigger in node.get("intent_triggers") or []:
            previous = intent_index.get(trigger)
            if previous and previous != node["id"]:
                _log("WARN", f"intent trigger '{trigger}' remapped from {previous} to {node['id']}")
            intent_index[trigger] = node["id"]
    return intent_index


_INTENT_INDEX: dict[str, str] = _build_intent_index(_FLOW.get("nodes", []))


# ── Phrase Bank ───────────────────────────────────────────────────────────────

def _build_phrase_bank(nodes: list[dict[str, Any]]) -> list[str]:
    """
    Extract all approved phrases from the JSON conversation file and
    hardcoded constants.  Returns a deduplicated, ordered list of strings
    that the LLM is allowed to draw from when composing responses.
    """
    phrases: list[str] = []

    # 1. Node responses and missing-slot overrides
    for node in nodes:
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
            itext = instruction.get("text", "")
            if isinstance(itext, str) and itext.strip():
                phrases.append(itext.strip())

    # 2. Hardcoded behavioural phrases
    for v in FALLBACK_BRIDGE_PHRASES.values():
        phrases.append(v)
    for v in CLARIFICATION_TEMPLATES.values():
        phrases.append(v)
    for v in GUIDANCE_RESPONSES.values():
        phrases.append(v)
    for v in DEESCALATION_RESPONSES:
        phrases.append(v)
    for v in FALLBACK_ESCALATION.values():
        phrases.append(v)

    # 3. Standard acknowledgements
    phrases.extend(["Got it.", "Understood.", "Okay.", "Sure.", "No problem.", "Makes sense."])

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in phrases:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


_PHRASE_BANK: list[str] = _build_phrase_bank(_FLOW.get("nodes", []))


def get_phrase_bank() -> list[str]:
    """Return the list of approved phrases from the JSON conversation file."""
    return list(_PHRASE_BANK)


def _match_phrases_used(response: str, bank: list[str]) -> list[str]:
    """
    Return which phrase bank entries appear (fully or partially) in the response.
    Used for [JSON PHRASES USED] logging.
    """
    resp_lower = response.lower()
    matched: list[str] = []
    for phrase in bank:
        # Check if a meaningful fragment (4+ words) of the phrase is in the response
        words = phrase.split()
        if len(words) <= 3:
            if phrase.lower().rstrip(".!?,") in resp_lower:
                matched.append(phrase)
        else:
            # Check sliding windows of 4 words from the phrase
            for i in range(len(words) - 3):
                fragment = " ".join(words[i:i + 4]).lower()
                if fragment in resp_lower:
                    matched.append(phrase)
                    break
    return matched


def find_node_by_intent(intent: str) -> dict[str, Any] | None:
    """Return the node mapped to the given intent, if any."""
    node_id = _INTENT_INDEX.get(intent)
    return _NODE_MAP.get(node_id) if node_id else None


def _is_actionable(text: str) -> bool:
    """
    Return False for input too weak to extract intent from.
    Allow short confirmations through. Block empty, punctuation-only, or noise.
    """
    t = (text or "").strip().lower()
    if not t:
        return False
    if t in {"yes", "yeah", "yep", "ok", "okay", "sure", "no", "nope", "nah"}:
        return True
    if len(t) < 2:
        return False
    if t in SHORT_NOISE:
        return False
    if re.fullmatch(r"[\W_]+", t):
        return False
    if not any(c.isalpha() for c in t):
        return False
    return True


def _detect_user_question(user_text: str) -> str | None:
    """Return question type if user is asking a meta-question, else None."""
    if should_answer_user_question(user_text):
        from .conversation_response import _detect_user_question as _detect
        return _detect(user_text)
    return None


def _resolve_template(
    node: dict[str, Any],
    data: dict[str, Any],
    language: str = "en",
) -> str:
    """Fill {{placeholders}} in a node's template response. No LLM. No generation logic."""
    template = OPENING_NODE_RESPONSES.get(str(node.get("id") or ""), node.get("response"))
    missing_slot_responses = node.get("missing_slot_responses")
    if isinstance(missing_slot_responses, dict):
        collects = node.get("collects")
        missing_slots: list[str] = []
        if isinstance(collects, list):
            missing_slots = [slot for slot in collects if not data.get(slot)]
        if len(missing_slots) == 1:
            override = missing_slot_responses.get(missing_slots[0])
            if isinstance(override, str) and override.strip():
                template = override
    if template is None:
        template = node.get("instruction", {}).get("text", "")

    def fill(match: re.Match[str]) -> str:
        key = match.group(1)
        if key == "name":
            val = data.get("name") or data.get("lead_name") or data.get("lead") or "Prashant"
        else:
            val = data.get(key)
        return str(val) if val else ""

    localized_template = localize_template(template, language)
    resolved = re.sub(r"\{\{(\w+)\}\}", fill, localized_template).strip()
    resolved = re.sub(r" +", " ", resolved)
    return resolved


_FILLER_OPENERS = (
    "sure,",
    "sure -",
    "sure —",
    "great,",
    "great -",
    "great —",
    "absolutely,",
    "absolutely -",
    "absolutely —",
)


def _enforce_single_question(text: str) -> str:
    question_count = text.count("?")
    if question_count <= 1:
        return text
    first_seen = False
    chars: list[str] = []
    for ch in text:
        if ch == "?":
            if first_seen:
                chars.append(".")
            else:
                chars.append("?")
                first_seen = True
        else:
            chars.append(ch)
    return "".join(chars)


def _remove_filler_openers(text: str) -> str:
    cleaned = text.strip()
    lowered = cleaned.lower()
    for filler in _FILLER_OPENERS:
        if lowered.startswith(filler):
            cleaned = cleaned[len(filler):].lstrip(" ,.-—")
            break
    return cleaned


def _finalize_response_text(text: str) -> str:
    """Apply production response constraints before TTS."""
    if not text or not text.strip():
        return text
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = _remove_filler_openers(cleaned)
    cleaned = _enforce_single_question(cleaned)
    cleaned = _truncate_response(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# ---------------------------------------------------------------------------
# Informational-query gate — decides if LLM fallback is permitted
# ---------------------------------------------------------------------------

_QUESTION_STARTERS = (
    "what", "which", "where", "how", "why",
    "is", "are", "does", "do", "can", "should",
)


def _is_informational_query(text: str, intent: str) -> bool:
    """
    Return True only if the user is asking an informational question
    that is not a structured slot-filling response.

    Conditions (ALL must be true):
    1. intent is "ask_off_topic" or "unclear"
    2. text contains a question indicator:
       - ends with "?"  OR
       - starts with a question word
    3. text is at least 4 words long (avoids noise like "what?")
    """
    if intent not in ("ask_off_topic", "unclear"):
        return False
    t = text.strip().lower()
    words = t.split()
    if len(words) < 4:
        return False
    has_question_mark = t.endswith("?")
    has_question_word = any(t.startswith(w) for w in _QUESTION_STARTERS)
    return has_question_mark or has_question_word


class StateManager:
    """Conversation state tracker backed by Updated_Real_Estate_Agent.json."""

    def __init__(self, json_path: str):
        self.json_path = json_path
        self.schema: Dict[str, Any] = {}
        self.nodes: Dict[str, dict[str, Any]] = {}
        self.tools: Dict[str, dict[str, Any]] = {}
        self.global_prompt = ""
        self.start_node_id = ""
        self.current_node_id = ""
        self.conversation_data: Dict[str, Any] = {}
        self.visited_nodes: set[str] = set()
        self._last_user_text = ""
        # Behavioral refinement state
        self._last_node_id: Optional[str] = None
        self._deescalation_index: int = 0
        self._has_apologised: bool = False
        # Acknowledgement repetition tracking
        self._last_ack: str = ""
        # Session termination flag (Issue 5)
        self._session_ended: bool = False
        # Fallback escalation counters (Issue 6)
        self._fallback_counts: dict[str, int] = {}
        self.active_language: str = "en"
        # Anti-repetition: track what questions have been asked
        self._asked_flags: dict[str, bool] = {
            "availability": False,
            "intent": False,
            "location": False,
            "budget": False,
            "visit_time": False,
            "callback_time": False,
            "property_type": False,
        }
        self._last_response: str = ""
        self.load_schema()

    def load_schema(self) -> None:
        try:
            with open(self.json_path, "r", encoding="utf-8") as handle:
                self.schema = json.load(handle)
        except Exception as exc:
            logger.error("Failed to load StateManager schema from %s: %s", self.json_path, exc)
            return

        flow = self.schema.get("conversationFlow", {})
        self.global_prompt = flow.get("global_prompt", "")
        self.start_node_id = flow.get("start_node_id", "")
        self.nodes = {node["id"]: node for node in flow.get("nodes", []) if "id" in node}
        self.tools = {}
        for tool in flow.get("tools", []):
            tool_id = tool.get("tool_id")
            if tool_id:
                self.tools[tool_id] = tool
        self.reset_state()
        logger.info("Loaded %d nodes. Start node: %s", len(self.nodes), self.start_node_id)

    @classmethod
    def template_new_agent(cls, name: str, script: str, voice_id: str, data_fields: list[str]) -> dict[str, Any]:
        """Creates a new agent JSON schema based on a generic template and admin inputs."""
        # Use a simplified version of the standard flow with Neha as default persona if name is matching
        template = {
            "agent_name": name or "Neha — Real Estate Specialist",
            "voice_id": voice_id or "en-IN-NeerjaNeural",
            "conversation_flow_id": f"flow_{uuid.uuid4().hex[:8]}",
            "global_prompt": script,
            "conversationFlow": {
                "global_prompt": script,
                "start_node_id": "root_greeting",
                "nodes": [
                    {
                        "id": "root_greeting",
                        "name": "Initial Greeting",
                        "type": "conversation",
                        "instruction": {"type": "prompt", "text": "Greet the user warmly as Neha and confirm identity."},
                        "response": "Hello, this is Neha from the Real Estate AI team. Am I speaking with you?",
                        "intent_triggers": ["call_connected"],
                        "edges": [
                            {"id": "to_discovery", "condition": "user responds", "destination_node_id": "discovery"}
                        ]
                    },
                    {
                        "id": "discovery",
                        "name": "Information Discovery",
                        "type": "conversation",
                        "instruction": {"type": "prompt", "text": "Qualify lead interest and collect data fields."},
                        "response": "I'm calling about some premium property options. Would you have a moment?",
                        "collects": data_fields,
                        "edges": [
                            {"id": "to_end", "condition": "conversation finished", "destination_node_id": "end_node"}
                        ]
                    },
                    {
                        "id": "end_node",
                        "name": "Conclusion",
                        "type": "end",
                        "instruction": {"type": "prompt", "text": "End the call politely."},
                        "response": "Thank you for your time. Have a great day!"
                    }
                ]
            }
        }
        return template

    def reset_state(self) -> None:
        self.current_node_id = self.start_node_id
        self.conversation_data = {}
        self.visited_nodes = {self.start_node_id} if self.start_node_id else set()
        self._last_user_text = ""
        # Behavioral refinement state reset
        self._last_node_id = None
        self._deescalation_index = 0
        self._has_apologised = False
        self._last_ack = ""
        self._session_ended = False
        self._fallback_counts = {}
        self._whatsapp_sent = False
        self.active_language = "en"
        self._asked_flags = {k: False for k in self._asked_flags}
        self._last_response = ""

    def _record_asked(self, node_id: str) -> None:
        """Mark the question type for a node as asked."""
        _FLAG_MAP = {
            "node-1735264873079": "availability",
            "node-1735970090937": "availability",
            "node-1735264921453": "intent",
            "fallback_intent": "intent",
            "node-1735267546732": "location",  # also budget but tracked via context
            "fallback_location": "location",
            "fallback_budget": "budget",
            "node-1735265015507": "visit_time",
            "fallback_visit_datetime": "visit_time",
            "node-1736492391269": "callback_time",
            "fallback_callback_time": "callback_time",
            "node-1767420514711": "property_type",
            "fallback_property_type": "property_type",
        }
        flag = _FLAG_MAP.get(node_id)
        if flag:
            self._asked_flags[flag] = True
            _log("ASKED FLAG", f"{flag} = True")

    def _build_turn_result(self, node: dict[str, Any], **kwargs: Any) -> TurnResult:
        """Build a TurnResult with asked_flags and last_response always included."""
        return TurnResult(
            node=node,
            context=dict(self.conversation_data),
            language=self.active_language,
            asked_flags=dict(self._asked_flags),
            last_response=self._last_response,
            **kwargs,
        )

    def record_response(self, response: str) -> None:
        """Called after response generation to update last_response for anti-repetition."""
        if response and response.strip():
            self._last_response = response.strip()

    def set_active_language(self, language: str) -> None:
        self.active_language = language or "en"

    def _trigger_whatsapp_if_needed(self, intent: str, next_node: dict[str, Any]) -> None:
        """Asynchronously triggers WhatsApp property details based on intent or node."""
        node_id = next_node.get("id", "")
        
        # Trigger conditions
        trigger_nodes = {"confirm_interest", "schedule_site_visit", "share_details", "send_property_details"}
        trigger_intents = {"interested", "site_visit_requested"}
        
        is_trigger_node = node_id in trigger_nodes
        is_trigger_name = next_node.get("name", "").replace(" ", "_").lower() in trigger_nodes
        
        if not (is_trigger_node or is_trigger_name or intent in trigger_intents):
            return
            
        phone = self.conversation_data.get("phone")
        if not phone:
            _log("WHATSAPP", "Cannot send message: no phone number found in conversation data.")
            return
            
        # Prevent duplicate sends in the same session
        if getattr(self, "_whatsapp_sent", False):
            return
            
        try:
            import asyncio
            import sys
            from pathlib import Path
            
            # Ensure integrations can be imported
            backend_dir = str(Path(__file__).resolve().parent.parent)
            if backend_dir not in sys.path:
                sys.path.append(backend_dir)
                
            from integrations.whatsapp import send_whatsapp_message, format_property_message, MOCK_PROPERTIES
            
            message = format_property_message(self.conversation_data, MOCK_PROPERTIES)
            
            _log("WHATSAPP", f"Triggering async background task to send details to {phone}")
            asyncio.create_task(send_whatsapp_message(phone, message))
            self._whatsapp_sent = True
        except Exception as e:
            _log("WHATSAPP", f"Error triggering WhatsApp integration: {e}")

    def get_current_node(self) -> Optional[dict[str, Any]]:
        return self.nodes.get(self.current_node_id)

    def is_terminal_node(self, node_id: Optional[str] = None) -> bool:
        node = self.nodes.get(node_id or self.current_node_id)
        return bool(node and node.get("type") == "end")

    def transition_to(self, edge_id: str) -> bool:
        current_node = self.get_current_node()
        if not current_node:
            return False

        for edge in current_node.get("edges", []):
            if edge.get("id") != edge_id:
                continue
            destination_id = edge.get("destination_node_id")
            destination = self.nodes.get(destination_id)
            if not destination:
                return False
            next_node = self._apply_forward_guard(destination)
            self.current_node_id = next_node["id"]
            if next_node.get("type") != "fallback":
                self.visited_nodes.add(next_node["id"])
            _log("STATE", f"-> {next_node['id']}")
            return True

        logger.warning("Invalid edge_id %s requested from node %s", edge_id, self.current_node_id)
        return False

    def get_system_prompt(self, language: Optional[str] = None, allow_transition: bool = True) -> str:
        del language, allow_transition
        return self.global_prompt

    def is_actionable(self, text: str) -> bool:
        return _is_actionable(text)

    def _reactivate_if_needed(self, user_text: str) -> None:
        if not self._session_ended:
            return
        if not _is_actionable(user_text or ""):
            return
        _log("SESSION ENDED", "Reactivating session for new user input")
        self._session_ended = False
        current = self.get_current_node()
        if current and current.get("type") == "end":
            self.current_node_id = self.start_node_id
            self._last_node_id = self.current_node_id

    def execute_noise_transition(self, user_text: str) -> TurnResult:
        """Handle noise/non-actionable input. Returns TurnResult (no response)."""
        self._reactivate_if_needed(user_text)
        if self._session_ended:
            _log("SESSION ENDED", "Ignoring further input")
            return self._build_turn_result({}, is_terminal=True, user_input=user_text)
        self._last_user_text = user_text or ""
        _log("STT", f"\"{user_text}\"")

        current_node = self.get_current_node()
        if not current_node:
            return self._build_turn_result({}, is_terminal=True, user_input=user_text)

        # Recover callback scheduling even when intent extraction is unavailable.
        node_id = current_node.get("id")
        if node_id in {"node-1736492391269", "fallback_callback_time"}:
            clean_text = re.sub(r"[^\w:\s]", " ", (user_text or "").lower())
            callback_time_keywords = (
                "morning", "afternoon", "evening", "night",
                "am", "pm", "after", "post", "around",
                "later", "tomorrow", "today",
            )
            has_callback_time_hint = any(re.search(rf"\b{kw}\b", clean_text) for kw in callback_time_keywords)
            has_callback_number = any(char.isdigit() for char in clean_text)
            if has_callback_time_hint or has_callback_number:
                timeline = self._synthesize_callback_timeline((user_text or "").strip())
                _log("NOISE RECOVERY", f'Callback time detected -> "{timeline}"')
                return self.execute_transition(
                    user_text,
                    {"intent": "provide_timeline", "entities": {"timeline": timeline}},
                )

        _log("NOISE FILTERED", f"\"{user_text}\"")
        return self._build_turn_result(
            current_node, user_input=user_text, response_type="noise_repeat",
        )

    def execute_greeting_transition(self, user_text: str = "") -> TurnResult:
        """Return TurnResult for the greeting/current node without transitioning."""
        self._reactivate_if_needed(user_text)
        node = self.get_current_node()
        if not node:
            return self._build_turn_result({}, is_terminal=True, user_input=user_text)
        self._record_asked(node.get("id", ""))
        return self._build_turn_result(
            node, user_input=user_text, response_type="greeting",
        )

    def execute_transition(self, user_text: str, intent_data: Optional[dict[str, Any]]) -> TurnResult:
        """Execute a state transition and return TurnResult.

        This is the CORE method. It handles:
        - STT normalization
        - User question detection
        - Intent normalization
        - Entity extraction and merging
        - Node transition
        - Auto-advance through skip edges

        It does NOT generate any response text. That's LLMResponseGenerator's job.
        """
        self._reactivate_if_needed(user_text)
        if self._session_ended:
            _log("SESSION ENDED", "Ignoring further input")
            return self._build_turn_result(
                self.get_current_node() or {}, is_terminal=True, user_input=user_text,
            )

        self._last_user_text = user_text or ""
        _log("STT", f"\"{user_text}\"")

        original_text = user_text or ""
        user_text = _normalise_stt(original_text)
        if user_text != original_text:
            _log("STT CLEAN", f'"{original_text}" -> "{user_text}"')

        current_node = self.get_current_node()
        if not current_node:
            return self._build_turn_result({}, is_terminal=True, user_input=user_text)

        # ── User is asking a meta-question → stay on current node ────────
        user_question = _detect_user_question(user_text)
        if user_question:
            _log("STATE", f"{current_node['id']} unchanged (user question: {user_question})")
            self._last_node_id = self.current_node_id
            return self._build_turn_result(
                current_node, user_input=user_text, user_question=user_question,
            )

        # ── End node → terminal ──────────────────────────────────────────
        if current_node.get("type") == "end":
            _log("END NODE REACHED", "Conversation terminated gracefully.")
            self._session_ended = True
            self._last_node_id = self.current_node_id
            return self._build_turn_result(
                current_node, user_input=self._last_user_text, is_terminal=True,
            )

        # ── Hostile input → deescalation ─────────────────────────────────
        if HOSTILE_DETECTION_ENABLED and _is_hostile(user_text):
            _log("TONE", "Hostile input detected")
            self._deescalation_index = (self._deescalation_index + 1) % len(DEESCALATION_RESPONSES)
            self._last_node_id = self.current_node_id
            return self._build_turn_result(
                current_node, user_input=user_text, response_type="deescalation",
            )

        # ── No intent data → noise ──────────────────────────────────────
        if intent_data is None:
            return self.execute_noise_transition(user_text)

        # ── Intent processing ────────────────────────────────────────────
        intent = str(intent_data.get("intent") or "unclear").strip() or "unclear"
        entities = intent_data.get("entities") or {}
        if not isinstance(entities, dict):
            entities = {}

        raw_intent = intent
        intent = self._normalize_intent_for_context(current_node, intent, entities, user_text)
        if intent != raw_intent:
            _log("INTENT NORMALIZED", f"{raw_intent} -> {intent}")

        if intent in {"confirm", "deny"}:
            entities = {"confirmation": entities.get("confirmation")}

        _log("INTENT", self._format_intent_log(intent, entities))
        self._merge_entities(entities, intent=intent)

        # Callback time recovery from fallback
        if current_node.get("id") == "fallback_callback_time" and intent == "provide_timeline":
            resume_node_id = self._first_destination(current_node)
            resume_node = self.nodes.get(resume_node_id) if resume_node_id else None
            if resume_node:
                _log("STATE", f"{current_node['id']} -> {resume_node['id']} (resume callback)")
                current_node = resume_node

        # Vague detection
        if VAGUE_DETECTION_ENABLED:
            collect_slots = self._collect_slots(current_node)
            for slot in collect_slots:
                if self.conversation_data.get(slot):
                    continue
                if _is_vague_answer(user_text, slot):
                    _log("VAGUE", f"Vague answer for '{slot}'")
                    self._last_node_id = self.current_node_id
                    return self._build_turn_result(
                        current_node, user_input=user_text,
                    )

        # ── Resolve next node ────────────────────────────────────────────
        if intent in {"confirm"} or intent in ALL_DENY_INTENTS:
            _log("STATE", "Confirmation handled via edge")
            next_node, bypass_guard = self._handle_confirmation(current_node, intent)
        else:
            next_node = self._resolve_by_intent(current_node, intent, raw_intent=raw_intent)
            bypass_guard = False

        if not bypass_guard:
            next_node = self._apply_forward_guard(next_node or current_node)

        # Track whether a state transition occurred (node changed)
        node_changed = next_node.get("id") != current_node.get("id")

        self.current_node_id = next_node["id"]
        if next_node.get("type") != "fallback":
            self.visited_nodes.add(next_node["id"])

        self._trigger_whatsapp_if_needed(intent, next_node)

        if next_node.get("type") == "fallback":
            node_id = next_node["id"]
            self._fallback_counts[node_id] = self._fallback_counts.get(node_id, 0) + 1
            _log("FALLBACK COUNT", f"{node_id} = {self._fallback_counts[node_id]}")

        is_terminal = False
        if next_node.get("type") == "end":
            _log("END NODE REACHED", "Conversation terminated gracefully.")
            self._session_ended = True
            is_terminal = True

        # Auto-advance through skip edges
        if not is_terminal and next_node["id"] in AUTO_ADVANCE_NODES:
            terminal = self._auto_advance_skip_edges(next_node)
            if terminal and terminal["id"] != next_node["id"]:
                self.current_node_id = terminal["id"]
                self.visited_nodes.add(terminal["id"])
                if terminal.get("type") == "end":
                    _log("END NODE REACHED", f"Auto-advanced -> {terminal['id']}")
                    self._session_ended = True
                    is_terminal = True

        self._last_node_id = self.current_node_id
        self._record_asked(next_node["id"])
        _log("STATE", f"Transition complete -> {next_node['id']}")

        return self._build_turn_result(
            next_node, user_input=self._last_user_text, is_terminal=is_terminal,
            node_changed=node_changed,
        )

    # ── Backward-compatible wrappers (call execute_transition + generate response) ──

    def process_noise_turn(self, user_text: str) -> str:
        """DEPRECATED: Use execute_noise_transition() + LLMResponseGenerator instead."""
        turn = self.execute_noise_transition(user_text)
        if not turn.node:
            return ""
        from .llm_response_generator import generate_response_for_turn_sync
        response = generate_response_for_turn_sync(turn)
        self.record_response(response)
        self._log_response(turn.node, response)
        return _finalize_response_text(response)

    def next_step(self, user_text: str = "", allow_transition: bool = True) -> str:
        """DEPRECATED: Use execute_greeting_transition() + LLMResponseGenerator instead."""
        self._reactivate_if_needed(user_text)
        if self._session_ended:
            return ""
        if allow_transition:
            return self.process_turn(user_text, None)
        turn = self.execute_greeting_transition(user_text)
        from .llm_response_generator import generate_response_for_turn_sync
        response = generate_response_for_turn_sync(turn)
        self.record_response(response)
        self._log_response(turn.node, response)
        return _finalize_response_text(response)

    def process_turn(self, user_text: str, intent_data: Optional[dict[str, Any]]) -> str:
        """DEPRECATED: Use execute_transition() + LLMResponseGenerator instead."""
        turn = self.execute_transition(user_text, intent_data)
        if not turn.node:
            return ""
        from .llm_response_generator import generate_response_for_turn_sync
        response = generate_response_for_turn_sync(turn)
        self.record_response(response)
        _log("FINAL RESPONSE", f'"{response}"')
        self._last_node_id = self.current_node_id
        return _finalize_response_text(response).strip()

    def _resolve_by_intent(self, current_node: dict[str, Any], intent: str, raw_intent: str = "") -> dict[str, Any]:
        """Resolve next node strictly from current node edges."""
        node_id = current_node.get("id", "")

        # ── Intent shortcut from Ask Intent or fallback_intent ──────────────────
        # When user gives a valid intent (buy/invest/rent/sell) on either the Ask
        # Intent node OR its fallback, skip intermediate steps and jump directly
        # to the correct destination.
        if node_id in {"node-1735264921453", "fallback_intent"}:
            if intent == "provide_intent":
                target = self.nodes.get("node-1735267546732")  # Ask Location & Budget
                if target:
                    _log("STATE", f"{node_id} -> {target['id']} (provide_intent shortcut)")
                    return target
            if intent == "seller_interest":
                target = self.nodes.get("node-1736510533232")  # Seller Flow Start
                if target:
                    _log("STATE", f"{node_id} -> {target['id']} (seller shortcut)")
                    return target
            if intent in {"deny_interest", "not_looking_now"}:
                target = self.nodes.get("node-objection-not-looking")
                if target:
                    _log("STATE", f"{node_id} -> {target['id']} (objection shortcut)")
                    return target


        edges = current_node.get("edges", []) or []
        if not edges:
            _log("STATE", f"No outgoing edges from {current_node['id']} - staying on current node")
            return current_node

        intents_to_match = [intent]
        if raw_intent and raw_intent not in intents_to_match:
            intents_to_match.append(raw_intent)

        for edge in edges:
            destination_id = edge.get("destination_node_id")
            if not destination_id:
                continue
            destination = self.nodes.get(destination_id)
            if not destination:
                continue

            destination_triggers = destination.get("intent_triggers") or []
            if any(i in destination_triggers for i in intents_to_match):
                if destination.get("type") == "fallback":
                    expected = destination.get("expected_input_type")
                    if expected and self.conversation_data.get(expected):
                        _log("SKIP FALLBACK", f"{destination['id']} ignored because '{expected}' is already collected")
                        continue
                _log(
                    "STATE",
                    f"{current_node['id']} -> {destination['id']} (intent={intent}, edge='{edge.get('condition', '')}')",
                )
                return destination

        _log(
            "STATE",
            f"No matching edge from {current_node['id']} for intent '{intent}' - staying on current node",
        )

        # Callback scheduling should still progress once timeline exists.
        if current_node.get("id") in {"node-1736492391269", "fallback_callback_time"} and self.conversation_data.get("timeline"):
            for edge in edges:
                destination_id = edge.get("destination_node_id")
                destination = self.nodes.get(destination_id) if destination_id else None
                if destination and "provide_timeline" in (destination.get("intent_triggers") or []):
                    _log("STATE", f"{current_node['id']} -> {destination['id']} (timeline recovery)")
                    return destination

        # Never stall on unclear intents: prefer a connected fallback edge from current node.
        if intent.startswith("unclear") or raw_intent.startswith("unclear") or intent == "ask_off_topic":
            for edge in edges:
                destination_id = edge.get("destination_node_id")
                destination = self.nodes.get(destination_id) if destination_id else None
                if destination and destination.get("type") == "fallback":
                    _log("STATE", f"{current_node['id']} -> {destination['id']} (unclear fallback edge)")
                    return destination

            # Availability node has no fallback edge; move to re-engage path instead of stalling.
            if current_node.get("id") == "node-1735264873079":
                for edge in edges:
                    condition = (edge.get("condition", "") or "").lower()
                    if "busy" in condition or "reject" in condition:
                        destination_id = edge.get("destination_node_id")
                        destination = self.nodes.get(destination_id) if destination_id else None
                        if destination:
                            _log("STATE", f"{current_node['id']} -> {destination['id']} (unclear -> re-engage)")
                            return destination
        return current_node

    def _handle_confirmation(self, current_node: dict[str, Any], intent: str) -> tuple[dict[str, Any], bool]:
        """Returns (next_node, bypass_forward_guard)."""
        if intent in ALL_DENY_INTENTS:
            target = self._route_deny_subtype(current_node, intent)
            if target:
                return target, False

        edge = self._select_confirmation_edge(current_node, intent)

        if not edge:
            return current_node, False
        destination_id = edge.get("destination_node_id")
        destination = self.nodes.get(destination_id)
        if not destination:
            return current_node, False
        _log("STATE", f"{current_node['id']} -> {destination['id']} (confirm edge)")
        return destination, False

    def _route_deny_subtype(
        self, current_node: dict[str, Any], intent: str
    ) -> Optional[dict[str, Any]]:
        """
        Route deny intent based on conversation context (current node).
        Returns target node if a contextual override applies, None otherwise.

        Deny sub-type is determined by:
        1. The LLM-classified sub-type (deny_identity, deny_interest, etc.)
        2. OR the current node context (which question was asked)
        """
        node_id = current_node["id"]

        # Determine effective deny sub-type from LLM intent or node context
        if intent == "deny":
            # Generic deny → resolve from current node context
            if node_id in DENY_IDENTITY_NODES:
                intent = "deny_identity"
            elif node_id in DENY_TIME_NODES:
                intent = "deny_time"
            elif node_id in DENY_INTEREST_NODES:
                intent = "deny_interest"
            elif node_id in DENY_VISIT_NODES:
                intent = "deny_visit_time"
            else:
                return None  # no contextual override — fall through to edge matching

        _log("DENY TYPE", f"{intent} at {node_id} ({current_node.get('name', '')})")

        # deny_identity → wrong person end
        if intent == "deny_identity":
            target = self.nodes.get(WRONG_PERSON_END_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_identity -> {target['id']} (wrong person)")
                return target

        # deny_time → callback scheduling
        if intent == "deny_time":
            target = self.nodes.get(CALLBACK_SCHEDULING_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_time -> {target['id']} (busy/not available)")
                return target

        # deny_interest → polite end
        if intent == "deny_interest":
            target = self.nodes.get(POLITE_END_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_interest -> {target['id']} (not interested)")
                return target

        # deny_visit_time → offer alternate date
        if intent == "deny_visit_time":
            target = self.nodes.get(RESCHEDULE_VISIT_NODE_ID)
            if not target:
                target = self.nodes.get(CALLBACK_SCHEDULING_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_visit_time -> {target['id']} (offering alternate)")
                return target

        return None  # no contextual override

    def _select_confirmation_edge(self, node: dict[str, Any], intent: str) -> Optional[dict[str, Any]]:
        edges = node.get("edges", [])
        if not edges:
            return None

        positive_markers = (
            "correct person",
            "correct",
            "user is free",
            "user is",
            "agrees",
            "agree",
            "hear more",
            "wants to visit",
            "finished confirmation",
            "done",
            "speak",
            "confirms identity",
            "confirms",
        )
        negative_markers = (
            "wrong person",
            "busy",
            "reject",
            "not looking",
            "not interested",
            "still rejects",
            "uncertain",
            "tell later",
            "later",
            "refuses",
            "busy or rejects now",
        )

        markers = positive_markers if intent == "confirm" else negative_markers
        for edge in edges:
            condition = " ".join(
                filter(
                    None,
                    [
                        edge.get("condition", ""),
                        edge.get("transition_condition", {}).get("prompt", ""),
                    ],
                )
            ).lower()
            if any(marker in condition for marker in markers):
                return edge

        return None

    def _advance_from_node(self, node: dict[str, Any]) -> dict[str, Any]:
        current = node
        seen: set[str] = set()
        while self._should_skip_node(current):
            _log("SKIP", f"{current['id']} - {self._skip_reason(current)}")
            next_id = self._first_destination(current)
            if not next_id or next_id in seen:
                return current
            seen.add(next_id)
            next_node = self.nodes.get(next_id)
            if not next_node:
                return current
            current = next_node
        return current

    def _find_path(self, start_id: str, target_id: str) -> list[str]:
        if start_id == target_id:
            return [start_id]

        queue: list[tuple[str, list[str]]] = [(start_id, [start_id])]
        seen = {start_id}
        while queue:
            node_id, path = queue.pop(0)
            node = self.nodes.get(node_id)
            if not node:
                continue
            for edge in node.get("edges", []):
                next_id = edge.get("destination_node_id")
                if not next_id or next_id in seen or next_id not in self.nodes:
                    continue
                next_path = path + [next_id]
                if next_id == target_id:
                    return next_path
                seen.add(next_id)
                queue.append((next_id, next_path))
        return []

    def _apply_forward_guard(self, next_node: dict[str, Any]) -> dict[str, Any]:
        # Strict flow mode: always honor the edge-selected destination node.
        return next_node

    def _merge_entities(self, entities: dict[str, Any], intent: str = "") -> None:
        for key in ENTITY_KEYS:
            value = entities.get(key)
            if value in (None, ""):
                continue
            existing = self.conversation_data.get(key)
            if existing:
                # Allow overwrite when user explicitly provides via provide_* intent
                is_explicit_provide = intent.startswith("provide_")
                # Allow overwrite when existing value is a known-invalid timeline
                is_stale_timeline = (
                    key == "timeline"
                    and any(inv in str(existing).lower() for inv in INVALID_TIMELINE_VALUES)
                )
                if not is_explicit_provide and not is_stale_timeline:
                    continue
                _log("ENTITY OVERWRITE", f"{key}: \"{existing}\" -> \"{value}\"")
            cleaned = self._clean_entity_value(key, value)
            if cleaned is None:
                _log("ENTITY SKIPPED", f'{key}="{value}"')
                continue
            self.conversation_data[key] = cleaned
            _log("ENTITY", f"{key} = {cleaned}")

    def _should_skip_node(self, node: dict[str, Any]) -> bool:
        if node.get("name") in NON_SKIPPABLE_NAMES or node.get("type") == "end":
            return False
        collects = self._collect_slots(node)
        if not collects:
            return False
        return all(self.conversation_data.get(slot) for slot in collects)

    def _skip_reason(self, node: dict[str, Any]) -> str:
        slots = self._collect_slots(node)
        if not slots:
            return "already collected"
        if len(slots) == 1:
            return f"{slots[0]} already collected"
        return f"{', '.join(slots)} already collected"

    def _collect_slots(self, node: dict[str, Any]) -> list[str]:
        collects = node.get("collects")
        if isinstance(collects, str) and collects:
            return [collects]
        if isinstance(collects, list):
            return [slot for slot in collects if isinstance(slot, str) and slot]
        return []

    def _missing_slots(self, node: dict[str, Any]) -> list[str]:
        return [slot for slot in self._collect_slots(node) if not self.conversation_data.get(slot)]

    def _first_destination(self, node: dict[str, Any]) -> str:
        edge = next(iter(node.get("edges", [])), None)
        return edge.get("destination_node_id", "") if edge else ""

    def _normalize_intent_for_context(
        self,
        current_node: dict[str, Any],
        intent: str,
        entities: dict[str, Any],
        user_text: str,
    ) -> str:
        text = (user_text or "").strip().lower()
        # Remove punctuation for signal matching
        clean_text = re.sub(r'[^\w\s]', ' ', text).strip()
        clean_text = re.sub(r'\s+', ' ', clean_text)
        clean_words = clean_text.split()
        asks_call_purpose = any(phrase in clean_text for phrase in PURPOSE_CLARIFICATION_PHRASES)
        asks_call_purpose = asks_call_purpose or (
            ("what" in clean_words or "why" in clean_words or "who" in clean_words)
            and ("about" in clean_words or "call" in clean_words or "calling" in clean_words)
        )

        node_id = current_node.get("id")
        if asks_call_purpose:
            return intent

        # ── buyer_requirements_ready: auto-transition when both location+budget collected ──
        if node_id == "node-1735267546732":
            loc_ready = self.conversation_data.get("location") or entities.get("location")
            bud_ready = self.conversation_data.get("budget") or entities.get("budget")
            
            def is_valid_val(v):
                if not v or not isinstance(v, str): return False
                s = v.lower().strip()
                if s in ("", "null", "none", "preference", "no preference", "anywhere", "flexible", "open"): return False
                return True
                
            if is_valid_val(loc_ready) and is_valid_val(bud_ready):
                _log("INTENT NORMALIZED", "Both location+budget collected -> buyer_requirements_ready")
                return "buyer_requirements_ready"

        # ── Ask Intent node: map purchase/investment answers to provide_intent ──────
        # The LLM sometimes returns confirm_identity/unclear for "for myself",
        # "investment", "personal use" etc. We intercept here to keep the flow moving.
        if node_id in {"node-1735264921453", "fallback_intent"}:
            _BUY_SIGNALS = (
                # Personal use
                "for myself", "myself", "personal use", "own use", "personal",
                "self use", "for self", "for me", "my own", "own home",
                "end use", "end-use", "residential", "to live", "to stay",
                "to reside", "living", "my family", "my wife", "my husband",
                "for us", "for our family", "for staying", "to settle",
                "primary residence", "primary home", "first home",
                "to move in", "we want to buy", "i want to buy",
                "buying for myself", "buying for us", "purchase",
                "apne liye", "khud ke liye", "ghar chahiye", "rehne ke liye",
                "own house", "want a house", "need a house", "need a home",
                "flat for myself", "flat for us", "apartment for myself",
                "house for myself", "villa for myself", "2bhk for myself",
                "3bhk for myself", "buying it", "buy it", "want to buy",
                "looking to buy", "planning to buy", "planning to purchase",
                "self occupied", "self-occupied", "owner occupied",
                "not investment", "not for rent", "not for renting",
            )
            _INVEST_SIGNALS = (
                # Investment / rental
                "investment", "invest", "as an investment", "for investment",
                "rental income", "rental", "renting out", "to rent",
                "for rent", "as rental", "rental property", "yield",
                "returns", "return on investment", "roi", "passive income",
                "for tenants", "for renting", "tenant", "lease out",
                "nikivesh", "nivesh", "kiraya", "rent ke liye",
                "buy to let", "buy to rent", "rental yield", "commercial use",
                "not for myself", "not to stay", "to let out", "to give out",
                "portfolio", "real estate portfolio", "property investment",
                "second property", "additional property",
            )
            _SELL_SIGNALS = (
                # Seller signals
                "sell", "selling", "want to sell", "seller", "i am selling",
                "i'm selling", "my property", "selling my flat",
                "selling my house", "selling my property", "want to sell my",
                "looking to sell", "planning to sell", "list my property",
                "bechna hai", "bechna chahta", "apna ghar bechna",
                "property for sale", "sale my flat", "sell my apartment",
            )
            _RENT_SIGNALS = (
                "for rent", "to rent", "looking to rent", "renting",
                "need on rent", "want to rent", "rental home",
                "rent a flat", "rent an apartment", "on lease",
                "lease", "rented accommodation", "rented flat",
                "kiraaye pe", "rent pe lena", "kiraya par lena",
            )
            if any(sig in clean_text for sig in _BUY_SIGNALS):
                if not entities.get("intent_value"):
                    entities["intent_value"] = "buy"
                _log("INTENT NORMALIZED", "Ask Intent: buy/personal detected -> provide_intent")
                return "provide_intent"
            if any(sig in clean_text for sig in _INVEST_SIGNALS):
                if not entities.get("intent_value"):
                    entities["intent_value"] = "invest"
                _log("INTENT NORMALIZED", "Ask Intent: investment detected -> provide_intent")
                return "provide_intent"
            if any(sig in clean_text for sig in _RENT_SIGNALS):
                if not entities.get("intent_value"):
                    entities["intent_value"] = "rent"
                _log("INTENT NORMALIZED", "Ask Intent: rent detected -> provide_intent")
                return "provide_intent"
            if any(sig in clean_text for sig in _SELL_SIGNALS):
                _log("INTENT NORMALIZED", "Ask Intent: seller detected -> seller_interest")
                return "seller_interest"

        if entities.get("location") and not intent.startswith("provide"):
            return "provide_location"
        if entities.get("budget") and not intent.startswith("provide"):
            return "provide_budget"

        if current_node.get("id") in VISIT_SCHEDULING_NODES:
            is_visit_rejection = any(rej in clean_text for rej in [
                "not interested", "don't want", "no visit"
            ])
            if not is_visit_rejection:
                datetime_keywords = [
                    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                    "today", "tomorrow", "tonight",
                    "next week", "this week", "weekend",
                    "morning", "afternoon", "evening", "night",
                    "am", "pm"
                ]
                has_datetime_keyword = any(re.search(rf"\b{kw}\b", clean_text) for kw in datetime_keywords)
                has_date_number = any(char.isdigit() for char in clean_text)
                
                if entities.get("timeline") or has_datetime_keyword or has_date_number:
                    if not entities.get("timeline") and not entities.get("visit_time"):
                        entities["timeline"] = user_text.strip()
                    return "provide_visit_datetime"

        # Callback scheduling accepts broad natural time expressions and normalizes
        # them into a specific callback time so we don't loop on fallback prompts.
        if node_id in {"node-1736492391269", "fallback_callback_time"}:
            callback_time_keywords = [
                "morning", "afternoon", "evening", "night",
                "am", "pm", "after", "post", "around",
                "later", "tomorrow", "today",
            ]
            has_callback_time_hint = any(re.search(rf"\b{kw}\b", clean_text) for kw in callback_time_keywords)
            has_callback_number = any(char.isdigit() for char in clean_text)
            if entities.get("timeline") or has_callback_time_hint or has_callback_number:
                timeline_raw = str(entities.get("timeline") or user_text).strip()
                entities["timeline"] = self._synthesize_callback_timeline(timeline_raw)
                return "provide_timeline"

        if clean_text in {"ok", "okay", "alright", "fine", "cool", "great", "sure", "thanks", "thank you", "done"}:
            if intent.startswith("unclear"):
                return "confirm"

        uncertain = {
            "i don't know", "dont know", "don't know", "not sure", "maybe",
            "not certain", "unsure", "i'm not sure", "im not sure",
            "hard to say", "hard to tell", "difficult to say", "can't say",
            "cant say", "no idea", "have no idea", "not really sure",
            "haven't decided", "havent decided", "still thinking",
            "still deciding", "not decided yet", "yet to decide",
            "pata nahi", "abhi pata nahi", "soch raha hoon", "socha nahi",
            "not fixed", "not finalized", "not finalised", "open",
            "anywhere", "anything", "whatever", "don't mind",
            "dont mind", "no specific preference", "not particular",
        }
        if any(phrase in text for phrase in uncertain):
            if current_node["id"] == "node-1735264921453":
                return "unclear_intent"
            if current_node["id"] == "node-1735267546732":
                if self.conversation_data.get("location") or entities.get("location"):
                    return "unclear_budget"
                if self.conversation_data.get("budget") or entities.get("budget"):
                    return "unclear_location"
                if "budget" in text or "price" in text:
                    return "unclear_budget"
                return "unclear_location"
            if current_node["id"] == "node-1767420514711":
                return "unclear_property_type"
            if current_node["id"] == "node-1735265015507":
                return "unclear_visit_datetime"
            if current_node["id"] == "node-1736492391269":
                return "unclear_callback_time"

        # ── Catch-all: signals ───────────────────────────────────────────
        _AFFIRMATIVE_SIGNALS = {
            # English
            "yes", "yeah", "yep", "yup", "ok", "okay", "sure", "alright",
            "correct", "right", "go ahead", "fine", "sounds good", "of course",
            "absolutely", "definitely", "certainly", "exactly", "precisely",
            "that is correct", "thats right", "thats correct", "yes indeed",
            "indeed", "affirmative", "agreed", "i agree", "i do", "of course yes",
            "please", "please do", "yes please", "sure please",
            "speaking", "yes speaking", "yes this is", "yes i am", "yes it is",
            "it is", "it's me", "its me", "thats me", "thats right",
            # Hindi / Indian English
            "haan", "han", "ha", "ji", "theek", "bilkul", "zaroor",
            "theek hai", "haan ji", "bilkul theek", "haan bilkul",
            "sahi hai", "sahi baat", "zaroor karo", "haan karo",
        }
        _NEGATIVE_SIGNALS = {
            # English
            "no", "nope", "nah", "never", "not", "sorry no", "no sorry",
            "no thanks", "no thank you", "i dont", "i don't", "i do not",
            "not really", "not at all", "absolutely not", "definitely not",
            "certainly not", "no way", "nah thanks",
            # Hindi / Indian English
            "nahi", "na", "nako", "nai", "nahi ji", "bilkul nahi",
            "nahi chahiye", "nahi kar sakta", "nahi hoga", "nahi karunga",
            "mat karo", "band karo",
        }
        
        has_affirmative = any(
            signal in clean_words or clean_text == signal
            for signal in _AFFIRMATIVE_SIGNALS
        )
        has_negative = any(
            signal in clean_words or clean_text == signal
            for signal in _NEGATIVE_SIGNALS
        )
        
        # Immediate hang-up routing for real world scenarios
        HANGUP_PHRASES = (
            "cut the call", "hang up", "hanging up", "phone rakh", "call cut",
            "disconnect", "do not call", "don't call me", "stop calling", "stop talking",
            "i am driving", "driving right now", "call later", "call me back later",
            "busy right now", "i am busy", "dont have time", "don't have time"
        )
        if any(phrase in clean_text for phrase in HANGUP_PHRASES):
            target = self.nodes.get("node-universal-disconnect")
            if target:
                _log("INTENT NORMALIZED", "Universal disconnect triggered by user")
                return target
        has_goodbye = any(
            phrase == clean_text or phrase in clean_text
            for phrase in GOODBYE_PHRASES
        )

        # ── No-preference detection for location/budget (must come before generic deny) ──
        _NO_LOCATION_PREFERENCE_PHRASES = (
            # Core no-preference
            "no preference", "no preference in city", "no preference for city",
            "don't have any preference", "dont have any preference",
            "no preference in area", "no preference for area",
            "any area", "any location", "any city", "any place",
            "doesn't matter", "does not matter", "doesn't matter where",
            "open to any", "flexible on location", "no specific area",
            "not considering any area", "not particular about area",
            "no area preference",
            # Extended no-preference
            "anywhere", "anywhere is fine", "anywhere works", "any location works",
            "no fixed location", "no specific location", "no particular area",
            "not specific about", "not particular about", "not fixed on",
            "open to all", "open to any area", "open to all areas",
            "you can suggest", "you suggest", "suggest me", "whatever you suggest",
            "as per your suggestion", "whatever is available", "whatever suits",
            "not bothered about location", "not fussy about area",
            "no location preference", "no city preference",
            "koi bhi area", "koi bhi jagah", "kahi bhi",
            "not tied to any area", "not fixed on area", "not restricted to area",
            "flexible", "flexible location", "flexible about location",
            "any locality", "any suburb", "any neighbourhood", "any neighborhood",
            "not particular", "no particular place", "no particular city",
            "doesn't matter to me", "does not matter to me",
            "not considering", "no consideration for area",
            "i'll consider anywhere", "will consider anywhere",
        )
        _NO_BUDGET_PREFERENCE_PHRASES = (
            # Core no-budget
            "no budget preference", "no preference for budget", "flexible budget",
            "any budget", "no fixed budget", "doesn't matter budget",
            "not sure about budget",
            # Extended
            "budget flexible", "budget is flexible", "i am flexible on budget",
            "flexible on budget", "no strict budget", "no hard budget",
            "open on budget", "open to budget", "depends on property",
            "depends on the property", "depends what's available",
            "can discuss", "can talk about it", "let's discuss",
            "will adjust", "can adjust budget", "adjustable budget",
            "no limit", "no particular budget", "no specific budget",
            "budget nahi pata", "budget fix nahi hai", "abhi pata nahi",
            "not sure yet", "haven't decided on budget", "still deciding",
            "budget toh discuss kar lete", "baat karte hai",
            "price toh dekh lete", "price dekh lete", "cost dekh lenge",
        )
        if node_id in {"node-1735267546732", "fallback_location", "fallback_budget"}:
            has_no_loc_pref = any(phrase in clean_text for phrase in _NO_LOCATION_PREFERENCE_PHRASES)
            has_no_budget_pref = any(phrase in clean_text for phrase in _NO_BUDGET_PREFERENCE_PHRASES)
            if has_no_loc_pref and not self.conversation_data.get("location"):
                _log("INTENT NORMALIZED", "No location preference detected -> unclear_location")
                return "unclear_location"
            if has_no_budget_pref and not self.conversation_data.get("budget"):
                _log("INTENT NORMALIZED", "No budget preference detected -> unclear_budget")
                return "unclear_budget"

        if has_negative:
            return "deny"
        if has_goodbye:
            return "deny_interest"
        if has_affirmative:
            return "confirm"

        # Prevent unclear stalls at opening/availability:
        # busy -> callback path, interested -> continue, neutral -> clarify/re-engage.
        if (intent.startswith("unclear") or intent == "ask_off_topic") and node_id == "node-1735264873079":
            if any(hint in clean_text for hint in BUSY_TIME_HINTS):
                return "deny_time"
            if any(hint in clean_text for hint in NOT_INTERESTED_HINTS):
                return "deny_time"
            if any(hint in clean_text for hint in INTERESTED_HINTS):
                return "confirm_identity"
            return "deny_time"

        if intent.startswith("unclear") or intent == "ask_off_topic":
            if current_node["id"] in ("node-1735265209472", "node-1736567518748", "node-1736492485610"):
                return "confirm"
            if current_node["id"] in ("node-1735264921453", "fallback_intent"):
                return "unclear_intent"
            if current_node["id"] in ("node-1735267546732", "fallback_location", "fallback_budget"):
                if self.conversation_data.get("location") or entities.get("location"):
                    return "unclear_budget"
                if self.conversation_data.get("budget") or entities.get("budget"):
                    return "unclear_location"
                return "unclear_location"
            if current_node["id"] in ("node-1767420514711", "fallback_property_type"):
                return "unclear_property_type"
            if current_node["id"] in ("node-1735265015507", "fallback_visit_datetime"):
                return "unclear_visit_datetime"
            if current_node["id"] in ("node-1736492391269", "fallback_callback_time"):
                return "unclear_callback_time"
            # Removed the dangerous default return "confirm" here

        if intent in {"provide_timeline", "provide_visit_datetime"}:
            if current_node["id"] in {"node-1735265015507", "node-1736323961832"}:
                return "provide_visit_datetime"
            if current_node["id"] in {"node-1736492391269", "fallback_callback_time"}:
                return "provide_timeline"

        return intent

    def _contextual_unclear_intent(self, current_node: dict[str, Any], entities: dict[str, Any], text: str) -> str:
        node_id = current_node.get("id")
        if node_id in {"node-1735264921453", "fallback_intent"}:
            return "unclear_intent"
        if node_id in {"node-1735267546732", "fallback_location", "fallback_budget"}:
            if self.conversation_data.get("location") or entities.get("location"):
                return "unclear_budget"
            if self.conversation_data.get("budget") or entities.get("budget"):
                return "unclear_location"
            if "budget" in text or "price" in text or "amount" in text:
                return "unclear_budget"
            return "unclear_location"
        if node_id in {"node-1767420514711", "fallback_property_type"}:
            return "unclear_property_type"
        if node_id in {"node-1735265015507", "fallback_visit_datetime"}:
            return "unclear_visit_datetime"
        if node_id in {"node-1736492391269", "fallback_callback_time"}:
            return "unclear_callback_time"
        return "unclear"

    def _is_location_suggestion(self, text: str, current_node: dict[str, Any]) -> bool:
        if current_node.get("id") not in {"node-1735267546732", "fallback_location"}:
            return False
        return any(phrase in text for phrase in LOCATION_SUGGESTION_PHRASES)

    def _clean_entity_value(self, key: str, value: Any) -> Optional[str]:
        text = re.sub(r"\s+", " ", str(value).strip())
        if not text:
            return None

        if key == "location":
            # ── Issue 2: Hindi script transliteration ──
            if text in HINDI_LOCATION_TRANSLITERATION:
                transliterated = HINDI_LOCATION_TRANSLITERATION[text]
                _log("TRANSLITERATED LOCATION", f"{text} -> {transliterated}")
                text = transliterated
            # ── Issue 3: phonetic STT normalization ──
            lowered = text.lower()
            if lowered in LOCATION_NORMALIZATION:
                normalized = LOCATION_NORMALIZATION[lowered]
                _log("NORMALIZED LOCATION", f"{text} -> {normalized}")
                text = normalized
            return text if self._is_valid_location(text) else None
        if key == "budget":
            return text if self._is_valid_budget(text) else None
        if key == "property_type":
            normalized = self._normalize_property_type(text)
            return normalized if normalized and self._is_valid_property_type(normalized) else None
        if key == "timeline":
            normalized = self._normalize_timeline(text)
            if normalized != text:
                _log("NORMALIZED TIMELINE", f"{text} -> {normalized}")
            return normalized if self._is_valid_timeline(normalized) else None
        return text

    def _is_valid_location(self, value: str) -> bool:
        lowered = value.strip().lower()
        if len(lowered) <= 2 or not any(char.isalpha() for char in lowered):
            return False
        if lowered in INVALID_LOCATION_VALUES:
            return False
        # Accept if it matches the known location whitelist or normalization maps
        if lowered in KNOWN_LOCATION_WHITELIST:
            return True
        if lowered in LOCATION_NORMALIZATION:
            return True
        # Reject multi-word strings that don't match any known location
        words = lowered.split()
        if len(words) > 2:
            _log("LOCATION REJECTED", f"Multi-word non-location: \"{value}\"")
            return False
        # Accept single/double word values that pass basic checks
        return True

    def _is_valid_budget(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered not in INVALID_BUDGET_VALUES and any(char.isdigit() for char in lowered)

    def _normalize_property_type(self, value: str) -> str:
        normalized = re.sub(r"\b([123])\s*bhk\b", r"\1 BHK", value, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if normalized.lower() == "apartment":
            return "flat"
        return normalized

    def _normalize_timeline(self, value: str) -> str:
        lowered = value.strip().lower()
        
        if lowered == "yesterday":
            return "tomorrow"
            
        if "last" in lowered:
            return re.sub(r"\blast\b", "next", value, flags=re.IGNORECASE)
            
        if "previous" in lowered:
            return re.sub(r"\bprevious\b", "next", value, flags=re.IGNORECASE)
            
        if "ago" in lowered:
            return re.sub(r"\bago\b", "from now", value, flags=re.IGNORECASE)
            
        if "past" in lowered:
            return re.sub(r"\bpast\b", "upcoming", value, flags=re.IGNORECASE)
            
        return value

    def _synthesize_callback_timeline(self, value: str) -> str:
        """
        Convert loose callback time phrases into a concrete, friendly time.
        Examples:
          - "post 6 PM" -> "6:45 PM" (randomized after 6 PM)
          - "evening"   -> random time in evening window
        """
        text = value.strip()
        lowered = text.lower()
        normalized_lowered = re.sub(r"\b([ap])\s*\.?\s*m\.?\b", r"\1m", lowered)

        # Pattern: after/post <hour>[:minute] <am/pm>
        m = re.search(r"\b(?:after|post)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", normalized_lowered)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            meridiem = (m.group(3) or "").lower()
            base_minutes = self._to_24h_minutes(hour, minute, meridiem, normalized_lowered)
            # Pick a random slot after mentioned time.
            delta = random.choice([15, 30, 45, 60, 75, 90])
            return self._format_minutes_12h(base_minutes + delta)

        # If user gave part-of-day only, pick a random concrete time in that window.
        for part, (start_min, end_min) in CALLBACK_PART_OF_DAY_WINDOWS.items():
            if re.search(rf"\b{part}\b", normalized_lowered):
                return self._format_minutes_12h(random.randint(start_min, end_min))

        # Extract explicit times from a longer sentence (e.g. "6 p.m. would work").
        explicit_time = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", normalized_lowered)
        if explicit_time:
            hour = int(explicit_time.group(1))
            minute = int(explicit_time.group(2) or 0)
            meridiem = explicit_time.group(3)
            return self._format_minutes_12h(self._to_24h_minutes(hour, minute, meridiem, normalized_lowered))

        return text

    def _to_24h_minutes(self, hour: int, minute: int, meridiem: str, context_text: str) -> int:
        hour = max(0, min(hour, 23))
        minute = max(0, min(minute, 59))
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        elif not meridiem:
            # Infer PM for common callback evening contexts.
            if ("evening" in context_text or "night" in context_text or "post" in context_text or "after" in context_text) and hour <= 11:
                hour += 12
        return (hour * 60) + minute

    def _format_minutes_12h(self, total_minutes: int) -> str:
        total_minutes %= (24 * 60)
        hour_24 = total_minutes // 60
        minute = total_minutes % 60
        meridiem = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12
        if hour_12 == 0:
            hour_12 = 12
        return f"{hour_12}:{minute:02d} {meridiem}"

    def _is_valid_timeline(self, value: str) -> bool:
        lowered = value.strip().lower()
        if any(inv in lowered for inv in INVALID_TIMELINE_VALUES):
            _log("TIMELINE REJECTED", f"Past or invalid timeline: \"{value}\"")
            return False
        return True

    def _is_valid_property_type(self, value: str) -> bool:
        lowered = value.strip().lower()
        allowed_patterns = (
            r"\b1\s*bhk\b",
            r"\b2\s*bhk\b",
            r"\b3\s*bhk\b",
            r"\bstudio\b",
            r"\bvilla\b",
            r"\bplot\b",
            r"\bflat\b",
        )
        return lowered not in INVALID_PROPERTY_TYPE_VALUES and any(
            re.search(pattern, lowered) for pattern in allowed_patterns
        )

    def _auto_advance_skip_edges(self, node: dict[str, Any]) -> dict[str, Any]:
        """Walk through skip edges to reach terminal nodes after response delivery."""
        current = node
        seen: set[str] = {current["id"]}
        while True:
            edges = current.get("edges", [])
            if not edges:
                return current
            # Check if the only edge is a skip edge
            if len(edges) == 1:
                condition = (edges[0].get("condition", "") or "").lower().strip()
                if condition in SKIP_EDGE_MARKERS:
                    dest_id = edges[0].get("destination_node_id")
                    dest = self.nodes.get(dest_id) if dest_id else None
                    if not dest or dest["id"] in seen:
                        return current
                    _log("SKIP EDGE", f"{current['id']} -> {dest['id']}")
                    seen.add(dest["id"])
                    self.visited_nodes.add(dest["id"])
                    current = dest
                    continue
            return current

    def _format_intent_log(self, intent: str, entities: dict[str, Any]) -> str:
        pairs = [f"{key}: {value}" for key, value in entities.items() if value not in (None, "")]
        if pairs:
            return f"intent={intent}  entities={{" + ", ".join(pairs) + "}"
        return f"intent={intent}"

    def _log_response(self, node: dict[str, Any], response: str) -> None:
        """Used only by non-process_turn callers (noise, greeting, next_step)."""
        _log("RESPONSE", f'[JSON] "{response}"')


# ---------------------------------------------------------------------------
# Issue 4 — Response truncation for TTS latency
# ---------------------------------------------------------------------------

def _truncate_response(
    text: str,
    max_words: int = cfg.MAX_RESPONSE_WORDS,
    max_sentences: int = cfg.MAX_RESPONSE_SENTENCES,
) -> str:
    """
    Enforce word and sentence limits on the final response text
    to keep TTS output short and reduce TTFB.

    Rules:
      1. Split on sentence-ending punctuation (. ! ?).
      2. Keep at most `max_sentences`.
      3. If total word count exceeds `max_words`, truncate to that limit.
      4. Rejoin sentences with newline for natural TTS pause.
    """
    if not text or not text.strip():
        return text

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    # Limit sentence count
    sentences = sentences[:max_sentences]

    # Rejoin and check word count
    joined = "\n".join(sentences)
    words = joined.split()
    if len(words) > max_words:
        truncated = " ".join(words[:max_words])
        # Ensure it ends with punctuation
        if not truncated.rstrip().endswith((".", "!", "?")):
            truncated = truncated.rstrip().rstrip(".,;:") + "."
        _log("TRUNCATE", f"Response trimmed from {len(words)} to {max_words} words")
        return truncated

    return joined
