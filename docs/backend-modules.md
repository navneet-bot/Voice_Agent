# Backend Modules

## Core Server Files

| File | Size | Role |
|------|------|------|
| `main.py` | ~327KB / ~7,300 lines | Production FastAPI server. All REST/WS routes. Lifespan DB init. API key auth middleware. |
| `main_working.py` | ~52KB | Leaner variant with subset of endpoints. |
| `main_pipeline.py` | ~2KB | Pipecat pipeline wiring — `run_agent()` entry point. |
| `start_production.py` | ~2KB | Gunicorn + UvicornWorker launcher (4 workers). |
| `ws_hub.py` | ~7KB | WebSocket broadcast hub — per-client connection pools, `broadcast_all()`, `broadcast_to_client()`. |
| `demo_runner.py` | ~16KB | Demo call engine — simulates calls through real AI pipeline with fake human responses. |
| `agent_runner.py` | ~12KB | Production call orchestration — resolves agent schemas, multi-provider telephony. |
| `call_recording.py` | ~8KB | Session audio recorder — stereo WAV (L=user, R=agent), scipy resampling. |
| `verify_pipeline.py` | ~2KB | Groq API + Edge-TTS connectivity test. |
| `mic_test.py` | ~4KB | PyAudio microphone test. |
| `requirequirements.txt` | — | Python dependencies list. |

---

## `flows/` — Pipecat Pipeline Processors

| File | Size | Role |
|------|------|------|
| `runtime.py` | ~33KB | Main runtime: `RealEstateSTTProcessor` (adaptive VAD), `RealEstateLLMProcessor` (state machine + GenID), `RealEstateTTSProcessor` (GenID-tagged audio, barge-in). |
| `runtime_working.py` | ~30KB | Working variant with slightly different VAD params. |
| `conversation.py` | ~6KB | Legacy conversation handler — re-exports improved processors from runtime.py. |
| `mic_conversation.py` | ~11KB | Local mic loopback test — listen → STT → LLM → TTS → playback. |
| `v2/__init__.py` | <1KB | FlowSpec v2 package exports. |
| `v2/spec.py` | ~9KB | FlowSpec v2 schema validation — node reachability, transition targets. |
| `v2/preview.py` | ~9KB | Read-only preview graph generator for admin UI. |
| `v2/shadow_runner.py` | ~3KB | Deterministic shadow transitions without affecting v1 runtime. |

---

## `llm/` — Language Model

| File | Size | Role |
|------|------|------|
| `llm.py` | ~22KB | Groq API client — intent extraction, 40+ known intents, multilingual prompts, retry logic. |
| `state_manager.py` | ~102KB / ~2,250 lines | Conversation state machine — node traversal, entity extraction, location normalization, deny routing, visit/callback scheduling. |
| `conversation_response.py` | ~19KB | Determines inline vs state-machine responses for user questions. |
| `llm_response_generator.py` | ~26KB | Response orchestration — `TurnResult` dataclass, `generate_response()`. |
| `language_utils.py` | ~23KB | Multilingual utilities — `LanguageTracker`, `localize_template`, transliteration (Hindi/Marathi). |
| `config.py` | ~3KB | LLM config: model `llama-3.1-8b-instant`, temp 0.0, max 80 tokens, 8s timeout, 2 retries. |

---

## `stt/` — Speech-to-Text

| File | Size | Role |
|------|------|------|
| `provider.py` | ~7KB | Provider selection — routes to Groq or Deepgram based on agent config / env. |
| `stt_groq.py` | ~10KB | Groq Whisper adapter — rate-limit cooldown, PCM16→WAV→API, latency tracking. |
| `stt_deepgram.py` | ~6KB | Deepgram Nova-2 adapter — REST-based, hallucination filtering, PCM16@16kHz. |
| `config.py` | ~1KB | STT config: 16kHz, min 250ms/max 800ms chunks, energy threshold 0.015. |

---

## `tts/` — Text-to-Speech

| File | Size | Role |
|------|------|------|
| `provider.py` | ~7KB | Provider selection — routes to Edge or Cartesia based on agent config / env. |
| `tts_edge.py` | ~6KB | Microsoft Edge-TTS adapter — Indian voices (en-IN-NeerjaNeural), PCM16 output. |
| `tts_cartesia.py` | ~9KB | Cartesia Sonic adapter — WebSocket streaming TTS, higher quality voices. |
| `speech_formatter.py` | ~6KB | Sentence splitting, silence insertion, pacing adjustments. |
| `response_formatter.py` | ~4KB | Prepends system responses, handles multi-locale. |
| `config.py` | ~1KB | TTS config: 24kHz, max 500 chars, sentence pause 80ms, speed +10%. |

---

## `telephony/` — Telephony Providers

| File | Size | Role |
|------|------|------|
| `provider_registry.py` | ~13KB | Abstract `TelephonyProvider` base + 5 implementations: Twilio, VoBiz, Exotel, Knowlarity, Demo. |
| `twilio_handler.py` | ~15KB | Twilio webhook — Media Streams over WS, TwiML gen, call lifecycle, audio bridging. |
| `vobiz.py` | ~5KB | VoBiz SIP handler (stubbed). |

**Provider Costs:**

| Provider | Type | Cost/min |
|----------|------|----------|
| Twilio | Global CPaaS | ~$1.20 |
| VoBiz | India SIP | ~$0.40 |
| Exotel | India CPaaS | ~$0.50 |
| Knowlarity | India Enterprise | ~$0.60 |
| Demo | Free simulation | $0 |

---

## `crm/` — CRM Integration

| File | Size | Role |
|------|------|------|
| `integration.py` | ~68KB | HubSpot, Salesforce, Zoho, Custom Webhook. Dry-run sync plans, outbox queues, delivery approvals. **Audit-only** — no data sent until explicitly enabled. Tenant-scoped. |

---

## `intelligence/` — Website Intelligence

| File | Size | Role |
|------|------|------|
| `crawler.py` | ~6KB | Bounded HTTP crawler — `CrawledPage` dataclass, `_LinkExtractor` HTML parser, max pages/bytes/timeout. |
| `extraction.py` | ~16KB | Knowledge extraction — industry detection, page classification, products/services/FAQs. `assess_website_knowledge()` quality scoring. |
| `pipeline.py` | ~9KB | Orchestration — crawl → extraction → script draft. Creates scrape jobs with status tracking. |
| `script_generation.py` | ~8KB | Generates FlowSpec v2 drafts from extracted website knowledge. |
| `url_guard.py` | ~3KB | SSRF protection — validates scheme, credentials, ports, DNS resolution. |

---

## `campaigns/` — Campaign Worker

| File | Size | Role |
|------|------|------|
| `worker_v2.py` | ~3KB | `CampaignWorkerV2ControlPlane` — execution metadata (pause/resume/cancel, retry limits, tenant ownership). Wraps v1 call runner. |

---

## `memory/` — Agent Memory

| File | Size | Role |
|------|------|------|
| `isolated_store.py` | ~4KB | `AgentMemoryService` — CRUD for memory collections/items. Scoped by `client_id + agent_id`. `seed_from_agent()` creates collections from agent profiles. |

---

## `metrics/` — Provider Metrics

| File | Size | Role |
|------|------|------|
| `provider_metrics.py` | ~2KB | Thread-safe deque (200 samples). Records STT latency, TTS TTFB, TTS total. P50/P95 percentiles. Warning thresholds via env vars. |

---

## `platform_migration/` — Phased Rollout

| File | Size | Role |
|------|------|------|
| `feature_flags.py` | ~7KB | ~80 central feature flags. Profiles: `live` (all on), `shadow` (all off). Individual env var overrides. |
| `auth_context.py` | ~196KB / ~4,600 lines | HTTP/WS tenant context extraction. Builds readiness manifests for tenant-scoped reads, recording access, transcript access. |
| `repository_cleanup.py` | ~21KB | Non-destructive cleanup audit — scans orphaned/unused files, staged deprecation pipeline. |

---

## `db/` — Database Layer

| File | Size | Role |
|------|------|------|
| `db_manager.py` | ~209KB / ~4,700 lines | Async SQLite interface over `platform.db`. ~20 tables, full CRUD. JSON file fallback for legacy. Agent schemas as `.json` files. |

**Tables:** clients, agents, campaigns, leads, phone_numbers, call_results, live_call_state, assignments, crm_connections, scrape_jobs, agent_memory.

---

## `integrations/` — External Integrations

| File | Size | Role |
|------|------|------|
| `whatsapp.py` | ~4KB | WhatsApp message formatting — property messages via httpx. Contains mock property data. |

---

## `audio/` — Audio Utilities

| File | Size | Role |
|------|------|------|
| `mic_utils.py` | ~4KB | `record_audio()` with early-stop on silence. `play_audio()` for playback. `convert_to_wav_bytes()`. Uses sounddevice. |
