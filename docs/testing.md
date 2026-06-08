# Testing

## Test Directories

| Directory | Count | Type |
|-----------|-------|------|
| `Backend/test/` | 7 files | Simple unit tests |
| `Backend/tests/` | 26 files | Comprehensive QA / contract tests |

## Unit Tests (`test/`)

| File | Tests What |
|------|------------|
| `chat_test.py` | Chat interaction flow |
| `check_voice.py` | Voice output verification |
| `test_llm.py` | LLM module functions |
| `test_multilingual_support.py` | Hindi/Hinglish/Marathi support |
| `test_pipeline.py` | Pipeline integration |
| `test_stt.py` | STT module |
| `test_tts.py` | TTS module |

## QA / Contract Tests (`tests/`)

| File | Tests What |
|------|------------|
| `test_smoke.py` | Basic smoke tests |
| `test_phase0_contracts.py` | Phase 0 contract validation |
| `test_phase1_contracts.py` | Phase 1 contract validation |
| `test_flow_v2.py` | FlowSpec v2 schema & validation |
| `test_auth_context.py` | Auth context / tenant manifests (~228KB) |
| `test_stt_provider.py` | STT provider abstraction |
| `test_tts_provider.py` | TTS provider abstraction |
| `test_feature_flags.py` | Feature flag system |
| `test_campaign_lifecycle.py` | Campaign lifecycle (start/stop/archive) |
| `test_campaign_worker_v2.py` | Campaign worker v2 control plane |
| `test_campaign_e2e_qa.py` | Campaign end-to-end QA |
| `test_agent_db_update.py` | Agent database updates |
| `test_agent_memory_isolation.py` | Memory service tenant isolation |
| `test_crm_sync_foundation.py` | CRM sync foundation (~88KB) |
| `test_crm_frontend_readiness_ui.py` | CRM UI readiness |
| `test_website_intelligence.py` | Website crawler + extraction |
| `test_tenant_data_migration.py` | Tenant data migration |
| `test_tenant_security_audit.py` | Tenant security audit |
| `test_telephony_live_qa.py` | Telephony live QA |
| `test_telephony_tenant_numbers.py` | Tenant phone number scoping |
| `test_demo_runtime_qa.py` | Demo runtime QA |
| `test_session_recorder.py` | Session recording |
| `test_runtime_conversation_guards.py` | Conversation guard logic |
| `test_ws_hub_scoping.py` | WebSocket hub tenant scoping |
| `test_repository_cleanup_audit.py` | Repository cleanup audit |
| `test_final_canary_rollback.py` | Final canary rollback test |

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `verify_pipeline.py` | Tests Groq API + Edge-TTS connectivity (use for new-laptop setup) |
| `mic_test.py` | Tests PyAudio mic + Groq access locally |
| `patch_json_disconnect.py` | Patches agent JSON schema to add universal disconnect node |

## How to Run

```bash
# Unit tests
cd Backend
python -m pytest test/

# QA tests
python -m pytest tests/

# Specific test
python -m pytest tests/test_flow_v2.py

# Pipeline verification
python verify_pipeline.py

# Mic test
python mic_test.py
```
