from __future__ import annotations
import copy

import json
import logging
import uuid
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import llm.config as cfg

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
BRIDGE_ENABLED           = True
VAGUE_DETECTION_ENABLED  = True
HOSTILE_DETECTION_ENABLED = True

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


def _resolve_response(node: dict[str, Any], data: dict[str, Any], user_text: str = "") -> str:
    """
    Return node["response"] with {{placeholders}} filled from data.
    Never returns an empty string.
    """
    del user_text
    template = node.get("response")
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
        template = node.get("instruction", {}).get("text", "") or "I can help with real estate."

    def fill(match: re.Match[str]) -> str:
        key = match.group(1)
        val = data.get(key)
        if val:
            return str(val)
        if key == "property_type":
            return ""
        return "that"

    resolved = re.sub(r"\{\{(\w+)\}\}", fill, template).strip()
    resolved = re.sub(r" +", " ", resolved)
    return resolved or "I can help with real estate."


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
            _log("STATE", f"→ {next_node['id']}")
            return True

        logger.warning("Invalid edge_id %s requested from node %s", edge_id, self.current_node_id)
        return False

    def get_system_prompt(self, language: Optional[str] = None, allow_transition: bool = True) -> str:
        del language, allow_transition
        return self.global_prompt

    def is_actionable(self, text: str) -> bool:
        return _is_actionable(text)

    def process_noise_turn(self, user_text: str) -> str:
        if self._session_ended:
            _log("SESSION ENDED", "Ignoring further input")
            return ""
        self._last_user_text = user_text or ""
        _log("STT", f"\"{user_text}\"")

        current_node = self.get_current_node()
        if not current_node:
            return ""

        _log("NOISE FILTERED", f"\"{user_text}\"")
        response = _resolve_response(current_node, self.conversation_data, user_text)
        self._log_response(current_node, response)
        return response

    def next_step(self, user_text: str = "", allow_transition: bool = True) -> str:
        if self._session_ended:
            _log("SESSION ENDED", "Ignoring further input")
            return ""
        node = self.get_current_node()
        if not node:
            return ""
        if allow_transition:
            return self.process_turn(user_text, None)
        response = _resolve_response(node, self.conversation_data, user_text)
        self._log_response(node, response)
        return response

    def process_turn(self, user_text: str, intent_data: Optional[dict[str, Any]]) -> str:
        if self._session_ended:
            _log("SESSION ENDED", "Ignoring further input")
            return ""

        self._last_user_text = user_text or ""
        _log("STT", f"\"{user_text}\"")

        # ── Refinement 1: STT normalisation ──
        original_text = user_text or ""
        user_text = _normalise_stt(original_text)
        if user_text != original_text:
            _log("STT CLEAN", f'"{original_text}" → "{user_text}"')

        current_node = self.get_current_node()
        if not current_node:
            return ""

        if current_node.get("type") == "end":
            _log("END NODE REACHED", "Conversation terminated gracefully.")
            self._session_ended = True
            raise KeyboardInterrupt

        # ── Refinement 4: hostile input detection ──
        if HOSTILE_DETECTION_ENABLED and _is_hostile(user_text):
            _log("TONE", "Hostile input detected — applying de-escalation response")
            response = DEESCALATION_RESPONSES[self._deescalation_index]
            self._deescalation_index = (self._deescalation_index + 1) % len(DEESCALATION_RESPONSES)
            self._last_node_id = self.current_node_id
            return response

        if intent_data is None:
            return self.process_noise_turn(user_text)

        # ── Phase 1: intent extraction & normalization ──
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

        # ── Refinement 2: vague answer detection ──
        if VAGUE_DETECTION_ENABLED:
            collect_slots = self._collect_slots(current_node)
            for slot in collect_slots:
                if self.conversation_data.get(slot):
                    continue  # slot already filled — don't offer guidance for it
                if _is_vague_answer(user_text, slot):
                    response = _get_guidance_response(slot)
                    _log("VAGUE", f"Vague answer for '{slot}' — offering guidance")
                    self._last_node_id = self.current_node_id
                    return response

        # ── Phase 2: node resolution ──
        supplemental = ""  # optional LLM informational reply
        stayed_on_current = False

        if intent in {"confirm"} or intent in ALL_DENY_INTENTS:
            _log("STATE", "Confirmation handled via edge — not intent index")
            next_node, bypass_guard = self._handle_confirmation(current_node, intent)
        else:
            next_node = self._resolve_by_intent(current_node, intent)
            bypass_guard = False

        if not bypass_guard:
            next_node = self._apply_forward_guard(next_node or current_node)

        # Detect whether the state actually moved
        if next_node["id"] == current_node["id"]:
            stayed_on_current = True

        self.current_node_id = next_node["id"]
        if next_node.get("type") != "fallback":
            self.visited_nodes.add(next_node["id"])

        # ── Issue 6: fallback escalation ──
        if next_node.get("type") == "fallback":
            node_id = next_node["id"]
            self._fallback_counts[node_id] = self._fallback_counts.get(node_id, 0) + 1
            _log("FALLBACK COUNT", f"{node_id} = {self._fallback_counts[node_id]}")

        # ── Phase 3: phrase-constrained LLM fallback (only when no node matched) ──
        if stayed_on_current and _is_informational_query(user_text, raw_intent):
            from llm.llm import generate_phrase_constrained_response
            supplemental = generate_phrase_constrained_response(
                user_text, self.conversation_data
            )
            _log("LLM FALLBACK", f'"{supplemental}"')

        # ── Phase 4: resolve JSON response (always present) ──
        json_response = _resolve_response(
            next_node, self.conversation_data, self._last_user_text
        )

        # ── Issue 6: substitute escalation response if fallback exceeded ──
        if (next_node.get("type") == "fallback"
                and self._fallback_counts.get(next_node["id"], 0) > MAX_FALLBACK_ATTEMPTS):
            escalation = FALLBACK_ESCALATION.get(next_node["id"])
            if escalation:
                json_response = escalation
                _log("FALLBACK ESCALATE", f'{next_node["id"]} → "{escalation}"')

        # ── Refinement 5: flow continuity — same node as last turn ──
        # Suppress when:
        #   - state actually moved (confirm edge followed correctly)
        #   - intent was a deny type
        #   - fallback escalation is active
        #   - a supplemental LLM response was generated
        state_moved = next_node["id"] != current_node["id"]
        is_genuine_repeat = (
            not state_moved                         # node did NOT change this turn
            and self._last_node_id == self.current_node_id  # AND it didn't change last turn either
            and intent not in {"confirm", *ALL_DENY_INTENTS}  # AND it wasn't a handled confirm/deny
        )
        is_fallback_escalated = (
            next_node.get("type") == "fallback"
            and self._fallback_counts.get(next_node["id"], 0) > MAX_FALLBACK_ATTEMPTS
        )
        if (is_genuine_repeat
                and not supplemental
                and not is_fallback_escalated):
            json_response = f"Just to confirm \u2014 {json_response}"
            _log("REPEAT NODE", 'Prepending "Just to confirm \u2014" \u2014 genuine repeat node (no transition)')

        # ── Phase 5: combine supplemental + JSON ──
        if supplemental:
            final_response = f"{supplemental} {json_response}"
            _log("RESPONSE", f'[FALLBACK + JSON] "{final_response}"')
        else:
            final_response = json_response

            # ── Refinement 3: bridge phrase injection ──
            # Bridges are ONLY added for unclear / fallback situations.
            # Normal-flow responses are returned exactly as the JSON schema
            # defines them — no filler words, no extra latency.
            is_fallback_node = next_node.get("type") == "fallback"
            is_unclear_intent = intent.startswith("unclear")
            if BRIDGE_ENABLED and (is_fallback_node or is_unclear_intent):
                bridge = _get_bridge(intent)
                if bridge:
                    final_response = f"{bridge} {final_response}"
                    _log("BRIDGE", f'Added bridge: "{bridge}"')

            _log("RESPONSE", f'[JSON] "{final_response}"')

        # ── Structured logging: [JSON PHRASES USED] ──
        matched = _match_phrases_used(final_response, _PHRASE_BANK)
        if matched:
            _log("JSON PHRASES USED", "; ".join(f'"{p}"' for p in matched[:5]))

        # ── Issue 4: truncate response for TTS latency ──
        final_response = _truncate_response(final_response)
        _log("FINAL RESPONSE", f'"{final_response}"')

        # ── Issue 5: check if we just arrived at an end node ──
        if next_node.get("type") == "end":
            _log("END NODE REACHED", "Conversation terminated gracefully.")
            self._session_ended = True
            self._last_node_id = self.current_node_id
            return final_response.strip()

        # ── Auto-advance through skip edges to reach end nodes ──
        if next_node["id"] in AUTO_ADVANCE_NODES:
            terminal = self._auto_advance_skip_edges(next_node)
            if terminal and terminal["id"] != next_node["id"]:
                self.current_node_id = terminal["id"]
                self.visited_nodes.add(terminal["id"])
                if terminal.get("type") == "end":
                    _log("END NODE REACHED", f"Auto-advanced through skip edges → {terminal['id']}")
                    self._session_ended = True
                    self._last_node_id = self.current_node_id
                    return final_response.strip()

        # ── Track last node for Refinement 5 ──
        self._last_node_id = self.current_node_id

        return final_response.strip()

    def _resolve_by_intent(self, current_node: dict[str, Any], intent: str) -> dict[str, Any]:
        candidate = find_node_by_intent(intent)
        
        if candidate and candidate.get("type") == "fallback":
            expected = candidate.get("expected_input_type")
            if expected and self.conversation_data.get(expected):
                _log("SKIP FALLBACK", f"{candidate['id']} ignored because '{expected}' is already collected")
                candidate = None

        if not candidate:
            _log("STATE", f"No node for intent '{intent}' — staying on {current_node['id']}")
            return current_node

        if current_node["id"] == candidate["id"]:
            next_node = self._advance_from_node(current_node)
            _log("STATE", f"→ {next_node['id']}  (intent: {intent})")
            return next_node

        path = self._find_path(current_node["id"], candidate["id"])
        if path:
            for node_id in path[1:-1]:
                node = self.nodes.get(node_id)
                if not node:
                    continue
                if self._should_skip_node(node):
                    _log("SKIP", f"{node['id']} — {self._skip_reason(node)}")
                    continue
                _log("STATE", f"→ {node['id']}  (intent: {intent})")
                return node
            next_node = self._advance_from_node(candidate)
            _log("STATE", f"→ {next_node['id']}  (intent: {intent})")
            return next_node

        if self._should_skip_node(current_node):
            next_node = self._advance_from_node(current_node)
            _log("STATE", f"→ {next_node['id']}  (intent: {intent})")
            return next_node

        _log("STATE", f"Intent '{intent}' is not reachable from {current_node['id']} — staying on current node")
        return current_node

    def _handle_confirmation(self, current_node: dict[str, Any], intent: str) -> tuple[dict[str, Any], bool]:
        """Returns (next_node, bypass_forward_guard)."""
        # ── Context-aware deny routing (overrides edge matching) ──
        if intent in ALL_DENY_INTENTS:
            override = self._route_deny_subtype(current_node, intent)
            if override:
                return override, True  # bypass forward guard

        edge = self._select_confirmation_edge(current_node, intent)

        if not edge:
            return current_node, False
        destination_id = edge.get("destination_node_id")
        destination = self.nodes.get(destination_id)
        if not destination:
            return current_node, False
        next_node = self._advance_from_node(destination)
        _log("STATE", f"→ {next_node['id']}")
        return next_node, False

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
                _log("DENY ROUTE", f"deny_identity → {target['id']} (wrong person)")
                return target

        # deny_time → callback scheduling
        if intent == "deny_time":
            target = self.nodes.get(CALLBACK_SCHEDULING_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_time → {target['id']} (busy/not available)")
                return target

        # deny_interest → polite end
        if intent == "deny_interest":
            target = self.nodes.get(POLITE_END_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_interest → {target['id']} (not interested)")
                return target

        # deny_visit_time → offer alternate date
        if intent == "deny_visit_time":
            target = self.nodes.get(RESCHEDULE_VISIT_NODE_ID)
            if not target:
                target = self.nodes.get(CALLBACK_SCHEDULING_NODE_ID)
            if target:
                _log("DENY ROUTE", f"deny_visit_time → {target['id']} (offering alternate)")
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
            "agrees",
            "agree",
            "hear more",
            "wants to visit",
            "finished confirmation",
            "done",
            "speak",
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
            _log("SKIP", f"{current['id']} — {self._skip_reason(current)}")
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
        current = self.get_current_node()
        if next_node.get("type") == "fallback":
            return next_node
        if current and current.get("type") == "fallback":
            return next_node
        if next_node["id"] in self.visited_nodes and next_node["id"] != self.current_node_id:
            _log("STATE", "Backward transition blocked")
            return current or next_node
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
                _log("ENTITY OVERWRITE", f"{key}: \"{existing}\" → \"{value}\"")
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
        clean_text = text.strip(" .!,?")

        if entities.get("location") and not intent.startswith("provide"):
            return "provide_location"
        if entities.get("budget") and not intent.startswith("provide"):
            return "provide_budget"

        if clean_text in {"ok", "okay", "alright", "fine", "cool", "great", "sure", "thanks", "thank you", "done"}:
            if intent.startswith("unclear"):
                return "confirm"

        uncertain = {
            "i don't know",
            "dont know",
            "don't know",
            "not sure",
            "maybe",
            "not certain",
            "unsure",
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
            return "confirm"

        # ── Catch-all: unclear/off-topic ─────────────────────────────────
        # ONLY upgrade unclear intent to 'confirm' if the user's text actually
        # contains an affirmative signal. Without this guard, inputs like
        # "for music" or "maybe" get misrouted through the confirm edge.
        _AFFIRMATIVE_SIGNALS = {
            "yes", "yeah", "yep", "yup", "ok", "okay", "sure", "alright",
            "correct", "right", "go ahead", "fine", "sounds good", "of course",
            # Hinglish affirmatives
            "haan", "han", "ha", "ji", "theek", "bilkul", "zaroor",
        }
        has_affirmative = any(
            signal in clean_text.split() or clean_text == signal
            for signal in _AFFIRMATIVE_SIGNALS
        )
        if has_affirmative:
            return "confirm"

        if intent in {"provide_timeline", "provide_visit_datetime"}:
            if current_node["id"] in {"node-1735265015507", "node-1736323961832"}:
                return "provide_visit_datetime"
            if current_node["id"] == "node-1736492391269":
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
                    _log("SKIP EDGE", f"{current['id']} → {dest['id']}")
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
