import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("GROQ_API_KEY", "test-key")

from llm.language_utils import analyze_user_text
from llm.llm import _extract_budget_entity, _enrich_intent_entities
from llm.state_manager import StateManager


class MultilingualSupportTests(unittest.TestCase):
    def setUp(self) -> None:
        schema_path = PROJECT_ROOT / "Updated_Real_Estate_Agent.json"
        self.state_manager = StateManager(str(schema_path))
        self.state_manager.reset_state()

    def test_detects_roman_hindi(self) -> None:
        analysis = analyze_user_text("main ghar dekh raha hoon", fallback="en")
        self.assertEqual(analysis.detected_language, "hi")

    def test_detects_hinglish(self) -> None:
        analysis = analyze_user_text("budget 50 lakh ke around hai", fallback="en")
        self.assertEqual(analysis.detected_language, "hinglish")

    def test_localizes_shared_flow_response(self) -> None:
        self.state_manager.set_active_language("hinglish")
        response = self.state_manager.next_step("", allow_transition=False)
        self.assertIn("Neha bol rahi hoon", response)

    def test_ask_intent_understands_hindi_phrase(self) -> None:
        self.state_manager.current_node_id = "node-1735264921453"
        self.state_manager.set_active_language("hinglish")
        response = self.state_manager.process_turn(
            "investment ke liye dekh raha hoon",
            {"intent": "unclear", "entities": {}},
        )
        self.assertEqual(self.state_manager.current_node_id, "node-1735267546732")
        self.assertEqual(self.state_manager.conversation_data.get("intent_value"), "invest")
        self.assertIn("budget", response.lower())

    def test_budget_entity_is_extracted_from_hinglish(self) -> None:
        self.assertEqual(_extract_budget_entity("budget 50 lakh hai"), "50 lakh")
        intent, entities = _enrich_intent_entities("budget 50 lakh hai", "unclear", {})
        self.assertEqual(intent, "provide_budget")
        self.assertEqual(entities.get("budget"), "50 lakh")


if __name__ == "__main__":
    unittest.main()
