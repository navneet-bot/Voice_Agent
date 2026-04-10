import json
import logging
from typing import Optional, Dict, Any, List

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
            
            # Map nodes for O(1) traversal
            for node in flow.get("nodes", []):
                self.nodes[node["id"]] = node
                
            self.current_node_id = self.start_node_id
            logger.info(f"Loaded {len(self.nodes)} nodes. Start node: {self.start_node_id}")
        except Exception as e:
            logger.error(f"Failed to load StateManager schema from {self.json_path}: {e}")

    def reset_state(self):
        """Resets the state back to the first node. Useful per-call/session."""
        self.current_node_id = self.start_node_id

    def get_current_node(self) -> Optional[dict]:
        return self.nodes.get(self.current_node_id)

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

    def get_system_prompt(self) -> str:
        """
        Builds the unified system prompt for the Groq LLM:
        1. The global prompt character rules.
        2. The specific task for the current node.
        3. The strict instruction payload to trigger [TRANSITION: <edge_id>] based on matching conditions.
        """
        node = self.get_current_node()
        if not node:
            return self.global_prompt

        node_name = node.get("name", "Unknown Task")
        node_instruction = node.get("instruction", {}).get("text", "")
        
        edges = node.get("edges", [])
        
        # Build Transition Rules
        transition_rules = ""
        if edges:
            transition_rules += "\n### NODE TRANSITION RULES ###\n"
            transition_rules += "Evaluate if the user's intent matches ANY condition below:\n"
            for edge in edges:
                e_id = edge.get("id")
                cond = edge.get("condition", "")
                t_cond = edge.get("transition_condition", {}).get("prompt", cond)
                transition_rules += f"- IF user intent matches '{t_cond}' -> transition_edge_id MUST be '{e_id}'\n"

        persona_rules = """
### PERSONALITY & CHARISMA (Neha) ###
- Tone: Sweet, warm, and highly charismatic. You are Neha, a professional real estate expert.
- Charisma: Use natural conversational fillers like "I see," "Perfect," "Absolutely," or "Right."
- Language Agility (CRITICAL): Start strictly with a professional English greeting. DO NOT assume Hinglish/Hindi in your first sentence. Once the user speaks, detect their language automatically and switch to mirror them perfectly. 
- Urgency/Rude Customers: If a user is rushing you or being rude, pivot to a "Concise Professional" mode. Give short, direct answers and don't push the full script. Offer to call back if they are in an urgency.

### CONVERSATION FLOW (STRICT) ###
- Sequence: Initial Hello -> Name Confirmation -> Interest Discovery -> Domain Q&A.
- DO NOT hallucinate that the user said something they didn't. 
- If the user text is unclear or junk (like "Atamente"), politely ask them to repeat: "I'm sorry, I didn't catch that. Could you say that again?"
"""

        json_schema = """
### OUTPUT FORMAT (STRICT JSON) ###
You MUST return ONLY valid JSON with this exact structure:
{
  "thought": "Brief internal logic evaluating user intent, language, and current flow position.",
  "transition_edge_id": "The exact edge_id from the rules above, or null if no transition rule matches.",
  "response_text": "Your charismatic, sweet voice reply."
}
"""

        prompt = f"""{self.global_prompt}
{persona_rules}

### CURRENT TASK: {node_name} ###
{node_instruction}
{transition_rules}
{json_schema}
"""
        return prompt
