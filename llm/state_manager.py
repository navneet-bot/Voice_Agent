from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

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
LOCATION_NORMALIZATION = {
    "banner": "Baner",
    "wakud": "Wakad",
    "hinjewdi": "Hinjewadi",
    "kharady": "Kharadi"
}
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


def _log(tag: str, message: str) -> None:
    logger.info("[%s] %s", tag, message)


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

    def reset_state(self) -> None:
        self.current_node_id = self.start_node_id
        self.conversation_data = {}
        self.visited_nodes = {self.start_node_id} if self.start_node_id else set()
        self._last_user_text = ""

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
        node = self.get_current_node()
        if not node:
            return ""
        if allow_transition:
            return self.process_turn(user_text, None)
        response = _resolve_response(node, self.conversation_data, user_text)
        self._log_response(node, response)
        return response

    def process_turn(self, user_text: str, intent_data: Optional[dict[str, Any]]) -> str:
        self._last_user_text = user_text or ""
        _log("STT", f"\"{user_text}\"")

        current_node = self.get_current_node()
        if not current_node:
            return ""

        if current_node.get("type") == "end":
            _log("END NODE REACHED", "Conversation terminated gracefully.")
            raise KeyboardInterrupt

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
        self._merge_entities(entities)

        # ── Phase 2: node resolution ──
        supplemental = ""  # optional LLM informational reply
        stayed_on_current = False

        if intent in {"confirm", "deny"}:
            _log("STATE", "Confirmation handled via edge — not intent index")
            next_node = self._handle_confirmation(current_node, intent)
        else:
            next_node = self._resolve_by_intent(current_node, intent)

        next_node = self._apply_forward_guard(next_node or current_node)

        # Detect whether the state actually moved
        if next_node["id"] == current_node["id"]:
            stayed_on_current = True

        self.current_node_id = next_node["id"]
        if next_node.get("type") != "fallback":
            self.visited_nodes.add(next_node["id"])

        # ── Phase 3: informational LLM fallback (only when no node matched) ──
        if stayed_on_current and _is_informational_query(user_text, raw_intent):
            from llm.llm import generate_informational_response
            supplemental = generate_informational_response(
                user_text, self.conversation_data
            )
            _log("LLM FALLBACK", f'"{supplemental}"')

        # ── Phase 4: resolve JSON response (always present) ──
        json_response = _resolve_response(
            next_node, self.conversation_data, self._last_user_text
        )

        # ── Phase 5: combine supplemental + JSON ──
        if supplemental:
            final_response = f"{supplemental} {json_response}"
            _log("RESPONSE", f'[FALLBACK + JSON] "{final_response}"')
        else:
            final_response = json_response
            _log("RESPONSE", f'[JSON] "{final_response}"')

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

    def _handle_confirmation(self, current_node: dict[str, Any], intent: str) -> dict[str, Any]:
        edge = self._select_confirmation_edge(current_node, intent)
        if not edge:
            return current_node
        destination_id = edge.get("destination_node_id")
        destination = self.nodes.get(destination_id)
        if not destination:
            return current_node
        next_node = self._advance_from_node(destination)
        _log("STATE", f"→ {next_node['id']}")
        return next_node

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

    def _merge_entities(self, entities: dict[str, Any]) -> None:
        for key in ENTITY_KEYS:
            value = entities.get(key)
            if value in (None, ""):
                continue
            if key in self.conversation_data and self.conversation_data.get(key):
                continue
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
        return text

    def _is_valid_location(self, value: str) -> bool:
        lowered = value.strip().lower()
        return len(lowered) > 2 and any(char.isalpha() for char in lowered) and lowered not in INVALID_LOCATION_VALUES

    def _is_valid_budget(self, value: str) -> bool:
        lowered = value.strip().lower()
        return lowered not in INVALID_BUDGET_VALUES and any(char.isdigit() for char in lowered)

    def _normalize_property_type(self, value: str) -> str:
        normalized = re.sub(r"\b([123])\s*bhk\b", r"\1 BHK", value, flags=re.IGNORECASE)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if normalized.lower() == "apartment":
            return "flat"
        return normalized

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

    def _format_intent_log(self, intent: str, entities: dict[str, Any]) -> str:
        pairs = [f"{key}: {value}" for key, value in entities.items() if value not in (None, "")]
        if pairs:
            return f"intent={intent}  entities={{" + ", ".join(pairs) + "}"
        return f"intent={intent}"

    def _log_response(self, node: dict[str, Any], response: str) -> None:
        """Used only by non-process_turn callers (noise, greeting, next_step)."""
        _log("RESPONSE", f'[JSON] "{response}"')
