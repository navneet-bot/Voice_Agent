import json
import logging
from typing import Optional, Dict, Any

from llm.language_utils import get_language_instruction, get_language_label

logger = logging.getLogger(__name__)

class StateManager:
    """
    Parses a conversation agent JSON schema to provide state-machine capabilities.
    Tracks the `current_node_id` and exposes available transitions dynamically.
    """
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.schema: Dict[str, Any] = {}
        self.nodes: Dict[str, dict] = {}
        self.tools: Dict[str, dict] = {}
        self.global_prompt = ""
        self.start_node_id = ""
        
        self.current_node_id = ""
        self.load_schema()

    def load_schema(self):
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
                
            flow = self.schema.get("conversationFlow", {})
            self.global_prompt = flow.get("global_prompt", "")
            self.start_node_id = flow.get("start_node_id", "")
            self.nodes = {}
            self.tools = {}
            
            # Map nodes for O(1) traversal
            for node in flow.get("nodes", []):
                self.nodes[node["id"]] = node
            for tool in flow.get("tools", []):
                tool_id = tool.get("tool_id")
                if tool_id:
                    self.tools[tool_id] = tool
                
            self.current_node_id = self.start_node_id
            logger.info(f"Loaded {len(self.nodes)} nodes. Start node: {self.start_node_id}")
        except Exception as e:
            logger.error(f"Failed to load StateManager schema from {self.json_path}: {e}")

    def reset_state(self):
        """Resets the state back to the first node. Useful per-call/session."""
        self.current_node_id = self.start_node_id

    def get_current_node(self) -> Optional[dict]:
        return self.nodes.get(self.current_node_id)

    def is_terminal_node(self, node_id: Optional[str] = None) -> bool:
        node = self.nodes.get(node_id or self.current_node_id)
        return bool(node and node.get("type") == "end")

    def transition_to(self, edge_id: str) -> bool:
        """
        Attempt to transition to the destination of `edge_id` from the current node.
        Returns True if successful, False otherwise.
        """
        current_node = self.get_current_node()
        if not current_node:
            return False

        for edge in current_node.get("edges", []):
            if edge.get("id") == edge_id:
                dest = edge.get("destination_node_id")
                if dest in self.nodes:
                    self.current_node_id = dest
                    logger.info(f"[State Transition] Moving to node '{self.nodes[dest].get('name', dest)}'")
                    return True
        logger.warning(f"[State Transition] Invalid edge_id {edge_id} requested from node {self.current_node_id}")
        return False

    def get_system_prompt(self, language: Optional[str] = None, allow_transition: bool = True) -> str:
        """
        Build the active system prompt from the JSON flow definition.
        """
        node = self.get_current_node()
        if not node:
            prompt = self.global_prompt
            if language:
                prompt = f"{prompt}\n\n### ACTIVE LANGUAGE ###\n- {get_language_instruction(language)}"
            if not allow_transition:
                prompt += (
                    "\n\n### AGENT-LED TURN ###\n"
                    "- No user reply has been received yet.\n"
                    "- transition_edge_id MUST be null.\n"
                    "- Speak only for the current node.\n"
                )
            return prompt

        node_name = node.get("name", "Unknown Task")
        node_instruction = node.get("instruction", {}).get("text", "")
        node_type = node.get("type", "conversation")
        is_start_node = self.current_node_id == self.start_node_id
        
        edges = node.get("edges", [])
        
        # Build Transition Rules
        transition_rules = ""
        if edges:
            transition_rules += "\n### NODE TRANSITION RULES ###\n"
            transition_rules += "Evaluate ONLY the user's latest supported utterance against the rules below:\n"
            for edge in edges:
                e_id = edge.get("id")
                cond = edge.get("condition", "")
                t_cond = edge.get("transition_condition", {}).get("prompt", cond)
                dest_id = edge.get("destination_node_id")
                dest_node = self.nodes.get(dest_id, {})
                dest_name = dest_node.get("name", dest_id or "unknown")
                dest_instruction = dest_node.get("instruction", {}).get("text", "")
                transition_rules += (
                    f"- IF user intent matches '{t_cond}' -> transition_edge_id MUST be '{e_id}'. "
                    f"The spoken reply must follow destination node '{dest_name}': {dest_instruction}\n"
                )
        tool_context = ""
        tool_id = node.get("tool_id")
        tool = self.tools.get(tool_id) if tool_id else None
        if tool:
            tool_name = tool.get("name", tool_id)
            tool_type = tool.get("type", "tool")
            tool_context = (
                "\n### NODE TOOL CONTEXT ###\n"
                f"- This node is linked to tool '{tool_name}' ({tool_type}).\n"
                "- Collect the details required by this node cleanly and keep the reply aligned to the current step.\n"
            )

        language_context = ""
        if language:
            language_context = (
                "\n### LANGUAGE LOCK ###\n"
                f"- Active reply language for this turn: {get_language_label(language)}.\n"
                f"- {get_language_instruction(language)}\n"
                "- Do NOT switch languages because of punctuation-only text, garbled audio, unsupported scripts, or low-confidence transcription.\n"
                "- If the latest user input is unclear, keep the current language and ask a short clarification tied to the current node.\n"
            )

        strict_rules = """
### STRICT EXECUTION RULES ###
- `Updated_Real_Estate_Agent.json` is the single source of truth. Treat this as a strict state machine.
- Follow only the CURRENT NODE unless you clearly select one allowed transition.
- If `transition_edge_id` is `null`, `response_text` must stay on the CURRENT NODE and either perform that node or briefly clarify it.
- If `transition_edge_id` is set, `response_text` must follow the DESTINATION NODE instruction for that edge, not the current node and not any later node.
- Never skip multiple nodes, merge multiple future nodes, or restart the script on your own.
- Transition only on clear evidence from the user's latest utterance. If the utterance is unclear, partial, unsupported, or likely an ASR mistake, keep `transition_edge_id` as `null`.
- Use one short spoken response, 1-2 sentences max, and ask only one question.
"""
        if not allow_transition:
            strict_rules += (
                "- This is an agent-led turn before the user has answered.\n"
                "- transition_edge_id MUST be null.\n"
                "- Speak only the CURRENT NODE instruction.\n"
            )
        if is_start_node:
            strict_rules += "- In Smart Greeting, start in English. After the first greeting has been spoken, do not repeat the full introduction again; only clarify whether you are speaking with Prashant.\n"
        if node_type == "end":
            strict_rules += "- This is an end node. Close politely and do not ask a new question.\n"

        json_schema = """
### OUTPUT FORMAT (STRICT JSON) ###
You MUST return ONLY valid JSON with this exact structure:
{
  "thought": "Brief internal logic evaluating user intent, language, and current flow position.",
  "transition_edge_id": "The exact edge_id from the rules above, or null if no transition rule matches.",
  "response_text": "Your short spoken reply for the current step."
}
"""

        prompt = f"""{self.global_prompt}

### CURRENT NODE ###
- Name: {node_name}
- Type: {node_type}
- Instruction: {node_instruction}
{transition_rules}{tool_context}{language_context}
{strict_rules}
{json_schema}
"""
        return prompt
