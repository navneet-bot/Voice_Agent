from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SHORT_NOISE = {".", ",", "uh", "ah", "hmm", "hm", "um"}
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
    if len(t) < 2:
        return False
    if t in SHORT_NOISE:
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
    if template is None:
        template = node.get("instruction", {}).get("text", "") or "I can help with real estate."

    def fill(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(data.get(key) or "that")

    resolved = re.sub(r"\{\{(\w+)\}\}", fill, template).strip()
    return resolved or "I can help with real estate."


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

        if intent_data is None:
            _log("STT", f"Non-actionable input — skipping LLM call: '{user_text}'")
            response = _resolve_response(current_node, self.conversation_data, user_text)
            self._log_response(current_node, response)
            return response

        intent = str(intent_data.get("intent") or "unclear").strip() or "unclear"
        entities = intent_data.get("entities") or {}
        intent = self._normalize_intent_for_context(current_node, intent, entities, user_text)
        _log("INTENT", self._format_intent_log(intent, entities))
        self._merge_entities(entities)

        if intent in {"confirm", "deny"}:
            _log("STATE", "Confirmation handled via edge — not intent index")
            next_node = self._handle_confirmation(current_node, intent)
        else:
            next_node = self._resolve_by_intent(current_node, intent)

        next_node = self._apply_forward_guard(next_node or current_node)
        self.current_node_id = next_node["id"]
        if next_node.get("type") != "fallback":
            self.visited_nodes.add(next_node["id"])

        response = _resolve_response(next_node, self.conversation_data, self._last_user_text)
        self._log_response(next_node, response)
        return response

    def _resolve_by_intent(self, current_node: dict[str, Any], intent: str) -> dict[str, Any]:
        candidate = find_node_by_intent(intent)
        if not candidate:
            _log("STATE", f"No node for intent '{intent}' — staying on {current_node['id']}")
            return current_node

        if current_node["id"] == candidate["id"]:
            next_node = self._advance_from_node(current_node)
            _log("STATE", f"→ {next_node['id']}  (intent: {intent})")
            return next_node

        path = self._find_path(current_node["id"], candidate["id"])
        if path:
            for node_id in path[1:]:
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
            "buy or rent or invest",
            "wants to visit",
            "mentions specific date or time",
            "mentions a date or time for callback",
            "details provided",
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

        if intent == "confirm":
            return edges[0]
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
            self.conversation_data[key] = value
            _log("ENTITY", f"{key} = {value}")

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

        if intent in {"unclear", "ask_off_topic"}:
            if current_node["id"] == "node-1735264921453":
                return "unclear_intent"
            if current_node["id"] == "node-1735267546732":
                if self.conversation_data.get("location"):
                    return "unclear_budget"
                if self.conversation_data.get("budget"):
                    return "unclear_location"
                return "unclear_location"
            if current_node["id"] == "node-1767420514711":
                return "unclear_property_type"
            if current_node["id"] == "node-1735265015507":
                return "unclear_visit_datetime"
            if current_node["id"] == "node-1736492391269":
                return "unclear_callback_time"
        return intent

    def _format_intent_log(self, intent: str, entities: dict[str, Any]) -> str:
        pairs = [f"{key}: {value}" for key, value in entities.items() if value not in (None, "")]
        if pairs:
            return f"intent={intent}  entities={{" + ", ".join(pairs) + "}"
        return f"intent={intent}"

    def _log_response(self, node: dict[str, Any], response: str) -> None:
        source = "JSON"
        _log("RESPONSE SOURCE", source)
        _log("RESPONSE TEXT", f"\"{response}\"")
