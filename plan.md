# Implementation Plan

1. **Modify `llm/state_manager.py`:**
   - Define `is_noise_input(text: str) -> bool` following all specific rules from Task 1.
   - Add tracking for `self.consecutive_noise_count` in `StateManager`.
   - Create `process_noise_turn(self, user_text: str)` to handle noise logging, incrementing count, and resolving clarity prompts.
   - Add entity value checks in `_merge_entities()` to apply the rule sets from Task 3 and Task 4, and log `[PARTIAL SPEECH IGNORED]` or `[LOW CONFIDENCE INPUT]`.
   - Ensure `consecutive_noise_count` resets automatically in `process_turn()`.

2. **Modify `llm/llm.py`:**
   - Modify `generate_response()` to detect `is_noise_input(user_text)`.
   - If true, completely bypass `extract_intent` and strictly route to `state_manager.process_noise_turn(user_text)`.

3. **Validation & Edge cases:**
   - Single word confirmations ("yes", "no") will bypass noise checks explicitly.
   - "n property" will be rejected correctly by vowel/digit character checks.
