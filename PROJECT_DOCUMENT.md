# Project Document: Cosmic Chameleon — Voice AI Calling SaaS Platform

**Version:** 2.1 (Production Hardened)  
**Status:** Production Live (May 30, 2026)  
**Repository root:** `D:\Project\Jobjockey\voice_agent\Voice_Agent`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Backend Structure & Modules](#3-backend-structure--modules)
4. [Frontend Structure & Pages](#4-frontend-structure--pages)
5. [Voice Pipeline](#5-voice-pipeline)
6. [Database Layer](#6-database-layer)
7. [Telephony Integration](#7-telephony-integration)
8. [State Machine & LLM](#8-state-machine--llm)
9. [Performance & Benchmarking](#9-performance--benchmarking)
10. [Deployment](#10-deployment)
11. [Testing Infrastructure](#11-testing-infrastructure)
12. [Security & Multi-tenancy](#12-security--multi-tenancy)
13. [Key Reports & Documents](#13-key-reports--documents)

---

## 1. Project Overview

Cosmic Chameleon is a full-stack AI voice calling SaaS platform. It enables businesses to run automated outbound voice campaigns using a real-time AI pipeline (Deepgram → Groq → Cartesia) orchestrated by Pipecat. The platform includes a Next.js admin dashboard for campaign management, agent configuration, live monitoring, website intelligence scraping, CRM integration, and telephony number management.

### Core Capabilities

- **AI-Powered Voice Calls** — Real-time conversational AI with low-latency streaming
- **Multi-Provider Telephony** — Twilio, VoBiz, Exotel, Knowlarity, plus browser-based demo mode
- **Campaign Management** — Lead upload (CSV), campaign lifecycle (start/pause/resume/archive)
- **Website Intelligence** — Crawl client websites to auto-generate agent scripts and conversation flows
- **Conversation Flow Editor** — Visual FlowSpec v2 editor with publish-to-runtime pipeline
- **Multilingual Support** — English, Hindi, Hinglish, Marathi
- **CRM Integration** — HubSpot, Salesforce, Zoho, Custom Webhook (audit-first, no data sent until enabled)
- **Agent Memory** — Tenant-scoped RAG collections for future fine-tuning
- **Real-time Dashboard** — WebSocket-powered live monitoring of active calls
- **Feature Flag System** — ~80 flags for phased rollout with `live`/`shadow` profiles

---

## 2. Architecture

### High-Level Diagram

```
[Browser / Web App]
       │
       ├── HTTP REST ──────► [Next.js Frontend :3000] ──proxy──► [FastAPI Backend :8000]
       │                                                              │
       └── WebSocket ──────► [Next.js Rewrite] ────────proxy──────► [WebSocket Hub]
                                                                          │
                                                                    ┌─────┴──────┐
                                                                    │  Pipecat   │
                                                                    │  Pipeline  │
                                                                    │ STT→LLM→TTS│
                                                                    └─────┬──────┘
                                                                          │
                                              [Twilio/Telephony] ◄───────┘
                                                                          │
                                                                    ┌─────┴──────┐
                                                                    │  SQLite DB  │
                                                                    │  + JSON     │
                                                                    └────────────┘
```

### Tech Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Backend Framework** | FastAPI (Python 3.11) | ASGI async, auto-docs at /docs |
| **Frontend Framework** | Next.js 16.2.4 | App Router, React 19.2.4 |
| **Styling** | Bootstrap 5 + Tailwind CSS (tw- prefix) | Dual framework |
| **Authentication** | Firebase Auth | Email/password + Google OAuth |
| **Voice Pipeline** | Pipecat AI | Async frame-based streaming |
| **STT** | Deepgram Nova-2 | WebSocket streaming, <300ms |
| **LLM** | Groq Llama-3.1-70B | 250+ tokens/sec |
| **TTS** | Cartesia Sonic | WebSocket streaming, <150ms TTFB |
| **Database** | SQLite (platform.db) + JSON files | Dual storage layer |
| **Telephony** | Twilio / VoBiz / Exotel / Knowlarity | Multi-provider abstraction |
| **Deployment** | Railway (backend) | Procfile + railway.json |

### File Tree

```
Voice_Agent/
├── Backend/                          # FastAPI server (Python)
│   ├── main.py                       # Production server (~7,300 lines)
│   ├── main_working.py               # Leaner variant
│   ├── main_pipeline.py              # Pipecat pipeline wiring
│   ├── start_production.py           # Gunicorn launcher
│   ├── demo_runner.py                # Demo call engine
│   ├── agent_runner.py               # Production call orchestration
│   ├── ws_hub.py                     # WebSocket broadcast hub
│   ├── verify_pipeline.py            # Pipeline connectivity test
│   ├── patch_json_disconnect.py      # Utility script
│   ├── mic_test.py                   # Microphone test
│   ├── call_recording.py             # Session audio recorder
│   ├── requirements.txt              # Python dependencies
│   │
│   ├── flows/                        # Pipecat frame processors
│   │   ├── runtime.py                # Main processors (STT, LLM, TTS)
│   │   ├── runtime_working.py        # Variant of runtime
│   │   ├── conversation.py           # Legacy conversation handler
│   │   ├── mic_conversation.py       # Local mic test loop
│   │   └── v2/                       # FlowSpec v2 system
│   │       ├── spec.py               # Schema validation
│   │       ├── preview.py            # Read-only preview graphs
│   │       └── shadow_runner.py      # Shadow transition runner
│   │
│   ├── llm/                          # Language Model module
│   │   ├── llm.py                    # Groq API integration
│   │   ├── state_manager.py          # State machine (~2,250 lines)
│   │   ├── conversation_response.py  # User question handling
│   │   ├── llm_response_generator.py # Response orchestration
│   │   ├── language_utils.py         # Multilingual utilities
│   │   └── config.py                 # LLM config & constants
│   │
│   ├── stt/                          # Speech-To-Text
│   │   ├── provider.py               # Provider selection
│   │   ├── stt_groq.py               # Groq Whisper (legacy)
│   │   └── stt_deepgram.py           # Deepgram Nova-2
│   │
│   ├── tts/                          # Text-To-Speech
│   │   ├── provider.py               # Provider selection
│   │   ├── tts_edge.py               # Edge-TTS (legacy)
│   │   ├── tts_cartesia.py           # Cartesia Sonic
│   │   ├── speech_formatter.py       # Sentence splitting, pacing
│   │   └── response_formatter.py     # System response prep
│   │
│   ├── telephony/                    # Telephony providers
│   │   ├── provider_registry.py      # Registry (5 providers)
│   │   ├── twilio_handler.py         # Twilio Media Streams
│   │   └── vobiz.py                  # VoBiz SIP handler
│   │
│   ├── crm/                          # CRM Integration
│   │   └── integration.py            # HubSpot, SF, Zoho, Webhook
│   │
│   ├── intelligence/                 # Website intelligence
│   │   ├── crawler.py                # Bounded HTTP crawler
│   │   ├── extraction.py             # Knowledge extraction
│   │   ├── pipeline.py               # Orchestration pipeline
│   │   ├── script_generation.py      # FlowSpec draft generation
│   │   └── url_guard.py              # SSRF protection
│   │
│   ├── campaigns/                    # Campaign worker
│   │   └── worker_v2.py              # Execution control plane
│   │
│   ├── memory/                       # Agent memory service
│   │   └── isolated_store.py         # CRUD for memory collections
│   │
│   ├── metrics/                      # Provider latency monitoring
│   │   └── provider_metrics.py       # P50/P95 latency tracker
│   │
│   ├── platform_migration/           # Phased rollout system
│   │   ├── feature_flags.py          # ~80 feature flags
│   │   ├── auth_context.py           # Tenant/auth context (~4,600 lines)
│   │   └── repository_cleanup.py     # Cleanup audit tool
│   │
│   ├── integrations/                 # External integrations
│   │   └── whatsapp.py               # WhatsApp messaging
│   │
│   ├── audio/                        # Audio utilities
│   │   └── mic_utils.py              # Microphone recording/playback
│   │
│   ├── db/                           # Database storage
│   │   ├── db_manager.py             # Async SQLite interface (~4,700 lines)
│   │   ├── platform.db               # SQLite database
│   │   ├── agents/                   # Agent JSON schemas
│   │   └── *.json                    # Legacy data files
│   │
│   ├── test/                         # Unit tests (7 files)
│   ├── tests/                        # QA tests (26 files)
│   └── scratch/                      # Scratch files
│
├── frontend-next/                    # Next.js dashboard
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.js               # Marketing landing page
│   │   │   ├── landing.css           # Tailwind + custom animations
│   │   │   ├── globals.css           # CSS custom properties
│   │   │   ├── layout.js             # Root layout + AuthProvider
│   │   │   ├── login/                # Firebase login page
│   │   │   ├── monitor/              # Live admin dashboard
│   │   │   ├── campaigns/            # Campaign CRUD
│   │   │   ├── agents/               # Agent management
│   │   │   ├── client-dashboard/     # Client portal
│   │   │   ├── clients/              # Admin client management
│   │   │   ├── crm-readiness/        # CRM rollout gates
│   │   │   ├── demo/                 # Browser demo call
│   │   │   ├── intelligence/         # Scrape job management
│   │   │   ├── logs/                 # Call logs & QA
│   │   │   ├── numbers/              # Phone number management
│   │   │   ├── results/              # Call results & transcripts
│   │   │   └── talk-live/            # Live agent test
│   │   ├── components/
│   │   │   ├── DashboardLayout.js    # Main layout + sidebar navigation
│   │   │   └── FlowPreviewModal.js   # Conversation flow editor
│   │   ├── context/
│   │   │   └── AuthContext.js        # Firebase auth + role management
│   │   ├── hooks/
│   │   │   └── useVoiceSocket.js     # WebRTC voice client hook
│   │   └── lib/
│   │       ├── firebase.js           # Firebase init
│   │       └── providerDisplay.js    # Provider label helpers
│   ├── public/
│   │   └── audio-worklet-processor.js # AudioWorklet mic capture
│   ├── package.json                  # Next.js 16, React 19, Firebase
│   ├── next.config.mjs               # API/WS proxy rewrites
│   ├── tailwind.config.js            # Custom brand theme
│   └── eslint.config.mjs             # ESLint flat config
│
├── Dockerfile                        # Python 3.11-slim container
├── docker-compose.yml                # Single service
├── Procfile                          # Heroku/Railway process
├── railway.json                      # Railway deployment config
├── README.md                         # Project documentation
├── DEVELOPMENT_GUIDE.md              # Fine-tuning & deployment guide
├── .gitignore
│
└── docs/                             # Architectural & analysis reports
    ├── architecture_report.md
    ├── ai_pipeline_report.md
    ├── production_live_report.md
    ├── deployment_steps.md
    ├── model_performance_benchmarking_report.md
    ├── deepgram_cartesia_migration_roadmap.md
    └── graphify-out/
        ├── GRAPH_REPORT.md
        ├── graph.json
        └── cache/
```

---

## 3. Backend Structure & Modules

### 3.1 Core Server (`Backend/main.py`)

The primary entry point (~7,300 lines). A FastAPI application that:

- Manages lifespan events (DB initialization on startup)
- Registers all REST routes: agents, campaigns, leads, clients, telephony, demo, CRM, intelligence, memory, flows, phone numbers, call results, assignments, call logs
- Handles WebSocket endpoints for voice streaming (`/api/voice-demo`, `/api/voice-live`) and dashboard monitoring (`/ws/dashboard`)
- Applies API key auth middleware when `PLATFORM_API_KEY` is set
- Configures CORS for frontend origin

### 3.2 Module Overview

| Module | Path | Responsibility | Key File(s) | Size |
|--------|------|---------------|-------------|------|
| **Flows** | `flows/` | Pipecat pipeline processors | `runtime.py` | 33KB |
| **LLM** | `llm/` | Groq integration, state machine | `state_manager.py` | 102KB |
| **STT** | `stt/` | Speech-to-text providers | `stt_deepgram.py` | 6KB |
| **TTS** | `tts/` | Text-to-speech providers | `tts_cartesia.py` | 9KB |
| **Telephony** | `telephony/` | Call provider abstraction | `provider_registry.py` | 13KB |
| **Database** | `db/` | Async SQLite + JSON storage | `db_manager.py` | 209KB |
| **CRM** | `crm/` | CRM integrations (audit-only) | `integration.py` | 68KB |
| **Intelligence** | `intelligence/` | Website crawling & script gen | `pipeline.py` | 9KB |
| **Campaigns** | `campaigns/` | Campaign execution control | `worker_v2.py` | 3KB |
| **Memory** | `memory/` | Agent memory collections | `isolated_store.py` | 4KB |
| **Metrics** | `metrics/` | Provider latency tracking | `provider_metrics.py` | 2KB |
| **Migration** | `platform_migration/` | Feature flags, auth context | `auth_context.py` | 196KB |
| **Integrations** | `integrations/` | External integrations | `whatsapp.py` | 4KB |

### 3.3 Dependencies (`requirements.txt`)

- `fastapi`, `uvicorn`, `gunicorn` — Web framework & server
- `httpx` — Async HTTP client
- `python-dotenv` — Environment variable loading
- `websockets` — WebSocket support
- `pydantic` — Data validation
- `groq` — Groq cloud API
- `twilio` — Twilio telephony
- `edge-tts` — Microsoft Edge TTS
- `numpy`, `scipy` — Audio processing
- `sounddevice`, `soundfile` — Audio I/O
- `pipecat-ai` — Pipeline orchestration
- `miniaudio` — Audio decode/encode

---

## 4. Frontend Structure & Pages

### 4.1 Configuration

| File | Purpose |
|------|---------|
| `next.config.mjs` | Proxies `/api/*` and `/ws/*` to `localhost:8000` |
| `tailwind.config.js` | Custom brand colors, `tw-` prefix, disables preflight for Bootstrap compat |
| `package.json` | Next.js 16.2.4, React 19.2.4, Firebase 12.12.1, Framer Motion 12.40.0 |
| `jsconfig.json` | Path alias `@/` → `./src/` |

### 4.2 Pages & Routes

| Route | File | Access | Description |
|-------|------|--------|-------------|
| `/` | `page.js` | Public | Marketing landing page with animated orb, feature grid, pricing, FAQ |
| `/login` | `login/page.js` | Public | Firebase email/password + Google sign-in |
| `/monitor` | `monitor/page.js` | Admin | Live dashboard: call metrics, active calls, provider latency |
| `/campaigns` | `campaigns/page.js` | Admin | Campaign CRUD, lead upload, lifecycle actions |
| `/agents` | `agents/page.js` | Admin/Client | Agent CRUD, voice config, website scraping, FlowSpec editor |
| `/client-dashboard` | `client-dashboard/page.js` | Client | Campaign launch, lead upload, auto-refresh results |
| `/clients` | `clients/page.js` | Admin | Client account management |
| `/demo` | `demo/page.js` | Client | Browser-based demo call with real-time transcript |
| `/intelligence` | `intelligence/page.js` | Admin | Scrape job management, diagnostic modals |
| `/logs` | `logs/page.js` | Admin | Call logs with selectable campaigns |
| `/numbers` | `numbers/page.js` | Admin | Phone number search/buy/assign |
| `/results` | `results/page.js` | Both | Call results with filters and recordings |
| `/talk-live` | `talk-live/page.js` | Client | Live agent browser test |
| `/crm-readiness` | `crm-readiness/page.js` | Admin | CRM rollout gates (feature-flagged) |

### 4.3 Key Frontend Components

| Component | Purpose |
|-----------|---------|
| `DashboardLayout.js` | Authenticated layout with role-based sidebar navigation (admin: 8 items, client: 3 items) |
| `FlowPreviewModal.js` | Full-screen conversation flow graph editor with publish capability |
| `AuthContext.js` | Firebase auth state, role resolution from admin email list |
| `useVoiceSocket.js` | Custom hook: AudioWorklet mic capture, adaptive jitter buffer, barge-in, PCM16 streaming |
| `audio-worklet-processor.js` | Zero-stutter microphone capture via AudioWorklet API |

### 4.4 Authentication & Roles

- **Firebase Auth** with email/password and Google OAuth
- **Admin email list** hard-coded in `AuthContext.js` (navneet@jobjockey.in, vishnu@jobjockey.in, parth@jobjockey.in, maniarasan@jobjockey.in)
- **Client users** resolve their profile via `GET /api/clients/resolve?email=...`
- **Multi-tenancy**: Admin can switch clients; client data is scoped by `X-Tenant-ID` headers

---

## 5. Voice Pipeline

### 5.1 Architecture

The voice pipeline uses **Pipecat AI** — an async frame-based streaming pipeline:

```
User Audio (PCM16 @ 16kHz)
       │
       ▼
┌─────────────────────────────────────┐
│ RealEstateSTTProcessor              │
│  ┌───────────────────────────────┐  │
│  │ Adaptive VAD                  │  │
│  │ - Noise-floor calibration     │  │
│  │ - Dynamic RMS thresholds      │  │
│  │ - Barge-in detection          │  │
│  ├───────────────────────────────┤  │
│  │ STT Provider (Deepgram/Groq) │  │
│  │ - Streaming transcription     │  │
│  │ - Hallucination filtering     │  │
│  │ - Multi-language detection    │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ▼ Text transcript
┌─────────────────────────────────────┐
│ RealEstateLLMProcessor              │
│  ┌───────────────────────────────┐  │
│  │ Intent Extraction             │  │
│  │ - 40+ known intents           │  │
│  │ - Entity extraction           │  │
│  │ - Location normalization      │  │
│  ├───────────────────────────────┤  │
│  │ State Management              │  │
│  │ - Node traversal              │  │
│  │ - StateManager integration    │  │
│  │ - GenID syncing               │  │
│  ├───────────────────────────────┤  │
│  │ LLM Provider (Groq)           │  │
│  │ - llama-3.1-70B               │  │
│  │ - JSON-only structured output │  │
│  │ - Retry with backoff          │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ▼ Response text
┌─────────────────────────────────────┐
│ RealEstateTTSProcessor              │
│  ┌───────────────────────────────┐  │
│  │ TTS Provider (Cartesia/Edge) │  │
│  │ - Streaming synthesis         │  │
│  │ - GenID-tagged audio chunks   │  │
│  │ - Barge-in support            │  │
│  ├───────────────────────────────┤  │
│  │ Speech Formatting             │  │
│  │ - Sentence splitting          │  │
│  │ - Silence insertion           │  │
│  │ - Pacing adjustments          │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               ▼ PCM16 audio @ 24kHz
       │
       ▼
[Browser Playback / Twilio Stream]
```

### 5.2 Pipeline Processors

#### RealEstateSTTProcessor (`flows/runtime.py`)
- **Adaptive VAD**: Continuously calibrates noise floor from ambient audio; dynamic RMS energy thresholds
- **Chunking**: Configurable min/max chunk sizes (250ms–800ms), trailing silence detection (220ms)
- **Barge-in**: When TTS is speaking and user interrupts, sends `CancelFrame` downstream
- **Post-TTS cooldown**: 180ms window after TTS ends to avoid cutting off agent speech

#### RealEstateLLMProcessor (`flows/runtime.py`)
- Integrates with `StateManager` for conversation flow control
- Extracts intent from user text via Groq LLM
- Echo detection: Filters out repeated/filler utterances
- GenID syncing: Associates a generation ID with every turn for audio-transcript alignment

#### RealEstateTTSProcessor (`flows/runtime.py`)
- Receives text responses, sends to TTS provider
- Tags each audio chunk with its GenID
- Supports barge-in: When user interrupts, streaming TTS output is cancelled
- Output: PCM16 at 24kHz mono

### 5.3 Provider Abstraction Layer

| Component | Active Provider | Fallback/Legacy | Selection Method |
|-----------|---------------|-----------------|------------------|
| STT | Deepgram Nova-2 | Groq Whisper (legacy) | Agent config + env overrides |
| TTS | Cartesia Sonic | Edge-TTS (legacy) | Agent config + env overrides |
| Telephony | Twilio (primary) | VoBiz, Exotel, Knowlarity, Demo | Agent config via registry |

### 5.4 Latency Optimizations

| Optimization | Detail |
|-------------|--------|
| Streaming providers | Deepgram & Cartesia both use WebSocket streaming |
| Groq LPU | Custom hardware for fast LLM inference |
| Async execution | All pipeline stages are async + non-blocking |
| PCM resampling | scipy-based resampling in `call_recording.py` |
| Hard timeouts | 4s timeout for LLM, circuit breakers on failure |
| Rate-limit cooldown | Exponential backoff on Groq 429 responses |
| Hallucination filtering | Filters silence hallucinations from STT |

---

## 6. Database Layer

### 6.1 Storage Architecture

```
SQLite (platform.db) ──────── Structured data: clients, agents, campaigns,
    │                         leads, phone_numbers, call_results, etc.
    │
    ├── JSON files ─────────── Legacy compatibility / fallback
    │   ├── agents.json
    │   ├── campaigns.json
    │   ├── leads.json
    │   └── assignments.json
    │
    └── db/agents/*.json ──── Agent schemas (never in SQLite)
```

### 6.2 Database Tables (`db_manager.py`, ~4,700 lines)

| Table | Description |
|-------|-------------|
| `clients` | Client accounts with scoping |
| `agents` | Voice agent configurations |
| `campaigns` | Outbound campaign metadata |
| `leads` | Lead records with contact info |
| `phone_numbers` | Telephony number inventory |
| `call_results` | Call outcomes, recordings, transcripts |
| `live_call_state` | Real-time call state tracking |
| `assignments` | Agent-to-client assignments |
| `crm_connections` | CRM integration configs |
| `scrape_jobs` | Website scrape job records |
| `agent_memory` | RAG memory collections |

### 6.3 Key Patterns

- **Async SQLite**: All operations use async/await with connection pooling
- **JSON fallback**: Legacy files are loaded when SQLite queries fail, ensuring backward compatibility
- **Agent schemas** are always stored as individual `.json` files under `db/agents/{uuid}.json` — never in SQLite
- **File locking**: `.gitignore` excludes `platform.db` from version control

---

## 7. Telephony Integration

### 7.1 Provider Registry (`telephony/provider_registry.py`)

| Provider | Type | Cost (approx) | Support Status |
|----------|------|---------------|----------------|
| **Twilio** | Global CPaaS | ~$1.20/min | Production |
| **VoBiz** | India SIP | ~$0.40/min | Stubbed |
| **Exotel** | India CPaaS | ~$0.50/min | Stubbed |
| **Knowlarity** | India Enterprise | ~$0.60/min | Stubbed |
| **Demo** | Free simulation | $0 | Full |

All providers implement the `TelephonyProvider` base class with unified interface.

### 7.2 Twilio Integration (`telephony/twilio_handler.py`)

- Uses Twilio Media Streams over WebSocket
- Handles call lifecycle: incoming → TwiML → Media Stream → bridge to Pipecat pipeline
- Audio is PCM16 at 8kHz (Twilio) → 16kHz (Pipecat STT) → 24kHz (TTS) → 8kHz (Twilio)
- Built-in TwiML generation for outbound calls

### 7.3 Call Flow (Outbound)

```
1. Campaign Service → Trigger outbound call
2. Twilio API → `calls.create(url=TwiML endpoint, to=phone, from=number)`
3. Twilio → Calls the `voice_handler` TwiML endpoint
4. TwiML returns `<Connect><Stream url="wss://.../telephony/stream/{call_id}"></Connect>`
5. Browser/Twilio → WebSocket audio stream established
6. Audio flows through Pipecat pipeline (STT → LLM → TTS)
7. Call ends → Call result saved to DB via REST callback
```

---

## 8. State Machine & LLM

### 8.1 StateManager (`llm/state_manager.py`, ~102KB, ~2,250 lines)

The conversation brain managing:

| Capability | Description |
|-----------|-------------|
| **Node traversal** | Navigates conversation flow graph defined in agent JSON schema |
| **Intent detection** | Classifies user input into 40+ known intents |
| **Entity extraction** | Property requirements, budget, location, contact details |
| **Location normalization** | Aliases, abbreviations, area mapping |
| **Deny routing** | Handles objection handling with fallback paths |
| **Visit scheduling** | Property visit booking logic |
| **Callback scheduling** | Follow-up call scheduling |
| **Multilingual** | English, Hindi, Hinglish, Marathi |

### 8.2 LLM Integration (`llm/llm.py`)

- **Provider**: Groq Cloud (`llama-3.1-8b-instant` for intent; `llama-3.1-70B` for conversation)
- **Temperature**: 0.0 for deterministic intent extraction
- **Max tokens**: 80 (intent only)
- **Timeout**: 8s, with 2 retries
- **Rate limiting**: Exponential backoff on HTTP 429
- **Output format**: JSON-only structured payload
- **Multilingual prompts**: Support for English, Hindi, Hinglish, Marathi

### 8.3 Conversation Flow (FlowSpec v2)

A sidecar system for deterministic flow specification:

```
Agent JSON Schema
       │
       ▼
FlowSpec v2 Builder (spec.py)
  - Validates schema nodes & transitions
  - Generates deterministic flow document
       │
       ▼
FlowSpec Validator
  - Node reachability
  - Start/end node verification
  - Transition target existence
       │
       ▼
Preview Generator (preview.py) ──► Read-only graph for UI
       │
       ▼
Shadow Runner (shadow_runner.py) ──► Deterministic shadow transitions (no v1 impact)
       │
       ▼
Publish ──► Converts to v1 runtime format
```

---

## 9. Performance & Benchmarking

### 9.1 Stack Evolution

| Component | Original Stack | Enterprise Stack (Current) |
|-----------|---------------|---------------------------|
| **Orchestrator** | Pipecat | Pipecat |
| **STT** | Faster-Whisper (local) → Groq Whisper | Deepgram Nova-2 (WebSocket) |
| **LLM** | Groq Llama-3.1-8B | Groq Llama-3.1-70B |
| **TTS** | Edge-TTS → Kokoro-ONNX → ElevenLabs | Cartesia Sonic (WebSocket) |

### 9.2 Benchmark Results (May 2026)

**STT Comparison:**

| Provider | Latency | Accuracy (Indian Dialect) | Verdict |
|----------|---------|--------------------------|---------|
| Faster-Whisper | 1.8–2.5s | 72% | FAIL |
| Groq Whisper Turbo | 0.8–1.2s | 81% | FAIL |
| NVIDIA Canary | 1.1s | 88% | FAIL (VRAM) |
| Google STT | 1.5s | 84% | FAIL |
| **Deepgram Nova-2** | **<300ms** | **96%** | **PASS** |

**TTS Comparison:**

| Provider | TTFB | Indian Accent Quality | Cost | Verdict |
|----------|------|----------------------|------|---------|
| Kokoro-ONNX | 400ms | 35% | Free | FAIL |
| Edge-TTS | 1.2s | 65% | Free | FAIL |
| ElevenLabs | 600–900ms | 92% | ₹4.5/min | FAIL (cost) |
| **Cartesia Sonic** | **<150ms** | **94%** | ₹0.8/min | **PASS** |

**End-to-End Latency:** 3.8–5.2s (original) → **0.7–1.1s** (current)

### 9.3 Monitoring (`metrics/provider_metrics.py`)

- In-memory thread-safe deque with 200-sample rolling window
- Tracks: STT latency, TTS TTFB, TTS total duration
- Calculates P50 and P95 percentiles
- Configurable warning thresholds via environment variables
- Data available via `/metrics/providers` API endpoint

---

## 10. Deployment

### 10.1 Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `GROQ_API_KEY` | Groq Cloud LLM access | Yes |
| `DEEPGRAM_API_KEY` | Deepgram STT access | Migration target |
| `CARTESIA_API_KEY` | Cartesia TTS access | Migration target |
| `TWILIO_ACCOUNT_SID` | Twilio API auth | Yes (telephony) |
| `TWILIO_AUTH_TOKEN` | Twilio API auth | Yes (telephony) |
| `PLATFORM_API_KEY` | Dashboard write-action auth | Optional |
| `PLATFORM_FEATURE_PROFILE` | `live` or `shadow` feature profile | Optional |

### 10.2 Docker Deployment

```yaml
# docker-compose.yml
services:
  voice-agent-platform:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./Backend/db:/app/Backend/db
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    restart: always
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg espeak-ng build-essential
WORKDIR /app/Backend
COPY Backend/requirements.txt .
RUN pip install -r requirements.txt
COPY . /app/
EXPOSE 3000
CMD ["python", "main.py"]
```

### 10.3 Railway Deployment

```json
// railway.json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "bash -c 'cd /app/Backend && PYTHONPATH=. gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT'"
  }
}
```

```yaml
# Procfile
web: bash -c "cd /app/Backend && PYTHONPATH=. gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT"
```

### 10.4 Production Server (`start_production.py`)

```python
# Minimal launcher for local production testing
# Uses gunicorn with UvicornWorker, 4 workers
# Configurable port and log level via args
```

### 10.5 Infrastructure Requirements

| Component | Requirement |
|-----------|------------|
| Python | 3.10+ |
| FFmpeg | Required for audio processing |
| Node.js | 18+ (frontend build) |
| RAM | 4GB+ for local model caching |
| HTTPS | Required for microphone access in production |

---

## 11. Testing Infrastructure

### 11.1 Unit Tests (`test/`)

| File | Purpose |
|------|---------|
| `chat_test.py` | Chat interaction test |
| `check_voice.py` | Voice output check |
| `test_llm.py` | LLM module tests |
| `test_multilingual_support.py` | Multilingual support |
| `test_pipeline.py` | Pipeline integration |
| `test_stt.py` | STT module tests |
| `test_tts.py` | TTS module tests |

### 11.2 QA / Contract Tests (`tests/`)

| File | Purpose |
|------|---------|
| `test_smoke.py` | Basic smoke tests |
| `test_phase0_contracts.py` | Phase 0 contract validation |
| `test_phase1_contracts.py` | Phase 1 contract validation |
| `test_flow_v2.py` | FlowSpec v2 tests |
| `test_auth_context.py` | Auth context tests (228KB) |
| `test_stt_provider.py` | STT provider tests |
| `test_tts_provider.py` | TTS provider tests |
| `test_feature_flags.py` | Feature flag tests |
| `test_campaign_lifecycle.py` | Campaign lifecycle tests |
| `test_campaign_worker_v2.py` | Campaign worker v2 tests |
| `test_campaign_e2e_qa.py` | Campaign E2E QA tests |
| `test_agent_db_update.py` | Agent DB update tests |
| `test_agent_memory_isolation.py` | Memory isolation tests |
| `test_crm_sync_foundation.py` | CRM sync tests (88KB) |
| `test_crm_frontend_readiness_ui.py` | CRM UI readiness tests |
| `test_website_intelligence.py` | Website intelligence tests |
| `test_tenant_data_migration.py` | Tenant data migration |
| `test_tenant_security_audit.py` | Tenant security audit |
| `test_telephony_live_qa.py` | Telephony live QA |
| `test_telephony_tenant_numbers.py` | Tenant phone numbers |
| `test_demo_runtime_qa.py` | Demo runtime QA |
| `test_session_recorder.py` | Session recorder tests |
| `test_runtime_conversation_guards.py` | Conversation guard tests |
| `test_ws_hub_scoping.py` | WS hub scoping tests |
| `test_repository_cleanup_audit.py` | Repo cleanup audit |
| `test_final_canary_rollback.py` | Final canary rollback |

### 11.3 Utility Scripts

| Script | Purpose |
|--------|---------|
| `verify_pipeline.py` | Groq API + Edge-TTS connectivity test |
| `mic_test.py` | PyAudio/Groq local mic test |
| `patch_json_disconnect.py` | Patches agent JSON with disconnect node |

---

## 12. Security & Multi-tenancy

### 12.1 Security Measures

| Layer | Measure |
|-------|---------|
| **API** | Optional `X-API-Key` middleware for write actions |
| **WebSocket** | Firebase ID token verification (optional, controlled by `MONITOR_AUTH_PROOF_ENABLED`) |
| **SSRF** | `url_guard.py` validates scheme, credentials, ports; resolves DNS to prevent internal network attacks |
| **Rate limiting** | Exponential backoff on Groq 429 responses |
| **Secrets** | `.env` files gitignored; API keys never committed |
| **CORS** | Restricted to frontend origin |

### 12.2 Multi-tenancy

- **Tenant scoping**: Controlled by `X-Tenant-ID` headers and query parameters
- **Auth context**: `platform_migration/auth_context.py` (~4,600 lines) builds readiness manifests for tenant-scoped reads
- **Phased rollout**: Feature flags control tenant isolation features (80+ flags)
- **Client isolation**: Data scoped by `client_id` at the database level via `db_manager.py`
- **Profiles**: `live` (all features on) vs `shadow` (all features off) profiles for safe rollout

### 12.3 Phased Rollout System (`platform_migration/`)

```
1. Feature flags control each capability
2. Auth context builds readiness manifests (audit-only)
3. Repository cleanup performs non-destructive audit
4. Each phase has associated contract tests
5. Rollback = single env change: PLATFORM_FEATURE_PROFILE=shadow
```

---

## 13. Key Reports & Documents

| File | Description |
|------|-------------|
| `README.md` | Project overview and quick start |
| `DEVELOPMENT_GUIDE.md` | Fine-tuning agents, deployment, conflict avoidance |
| `architecture_report.md` | High-level architectural overview |
| `ai_pipeline_report.md` | Deep dive into the AI voice pipeline |
| `production_live_report.md` | Production feature profile documentation |
| `deployment_steps.md` | Local and Docker deployment instructions |
| `model_performance_benchmarking_report.md` | STT/TTS benchmark results and provider selection |
| `deepgram_cartesia_migration_roadmap.md` | 15-day phased migration plan from Groq/Edge to Deepgram/Cartesia |
| `graphify-out/GRAPH_REPORT.md` | Automated code dependency graph analysis |
| `graphify-out/graph.json` | Full dependency graph data (646 nodes, 1,341 edges) |
| `Agent-architecture-report (1).md` | Legacy agent architecture report |
| `AI Voice Agent Task .pdf` | Original task specification |
| `Models_testing_report.pdf` | Model testing results |
| `work_log.md` | Development work log |
| `logs.txt` | Backend server logs |

---

## Appendix: Codebase Statistics

| Metric | Value |
|--------|-------|
| Total Python files | ~70+ |
| Largest file | `db_manager.py` (~209KB, ~4,700 lines) |
| Second largest | `auth_context.py` (~196KB, ~4,600 lines) |
| Third largest | `state_manager.py` (~102KB, ~2,250 lines) |
| Largest non-code file | `main.py` (~327KB, ~7,300 lines) |
| Graph nodes | 646 |
| Graph edges | 1,341 |
| Communities detected | 77 |
| Most connected node | `StateManager` (156 edges) |
| Total tests | 33 files |
| Frontend pages | 12 routes |
| Telephony providers | 5 (2 active, 3 stubbed) |
| LLM intents | 40+ |
| Feature flags | ~80 |
