# Cosmic Chameleon — Voice AI Calling SaaS Platform

A production-ready AI voice calling platform. Makes outbound calls using a real-time AI pipeline — listens (STT), thinks (LLM), speaks (TTS) in under 1 second.

**Version:** 2.1 (Production Hardened) | **Deployment:** Railway + Vercel

---

## Quick Start (5 minutes)

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (for audio processing)
- API keys: [Groq](https://console.groq.com) (+ optionally [Deepgram](https://console.deepgram.com), [Cartesia](https://cartesia.ai), [Twilio](https://twilio.com), [Firebase](https://console.firebase.google.com))

### 2. Backend

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Create .env (see below for required vars)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend-next
npm install
npm run dev
```

### 4. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"2.1","db":"connected"}
```

Open `http://localhost:3000` for the dashboard.

---

## Environment Variables

### Backend (`Backend/.env`)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | Groq LLM access |
| `DEEPGRAM_API_KEY` | For STT | Deepgram Nova-2 transcription |
| `CARTESIA_API_KEY` | For TTS | Cartesia Sonic voice synthesis |
| `TWILIO_ACCOUNT_SID` | For telephony | Twilio API auth |
| `TWILIO_AUTH_TOKEN` | For telephony | Twilio API auth |
| `TWILIO_FROM_NUMBER` | For telephony | Outbound caller ID |
| `PLATFORM_API_KEY` | Optional | Dashboard write-auth (X-API-Key header) |
| `PLATFORM_FEATURE_PROFILE` | Optional | `live` (all on) or `shadow` (all off) |

### Frontend (`frontend-next/.env.local`)

| Variable | Required | Default |
|----------|----------|---------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | For login | — |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | For login | — |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | For login | — |
| `NEXT_PUBLIC_API_URL` | Yes | `http://localhost:8000` |

Full list in `frontend-next/.env.example` (includes feature flags).

---

## Architecture

```
Browser/Phone → FastAPI → Pipecat Pipeline → Groq/Deepgram/Cartesia → SQLite
```

| Component | Technology | Role |
|-----------|------------|------|
| **Backend** | FastAPI (Python) | REST API + WebSocket orchestration |
| **Frontend** | Next.js 16 / React 19 | Dashboard, campaign management |
| **STT** | Deepgram Nova-2 | Speech-to-text (WebSocket, <300ms) |
| **LLM** | Groq Llama-3.1-70B | Intent extraction + response (250+ tok/s) |
| **TTS** | Cartesia Sonic | Voice synthesis (WebSocket, <150ms TTFB) |
| **Pipeline** | Pipecat AI | Async frame-based streaming |
| **Telephony** | Twilio (primary) | Outbound calling |
| **Database** | SQLite + JSON | Dual storage layer |

---

## API Reference

### Health

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/health` | Server + DB status |

### Agents

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/agents` | List all agents |
| POST | `/api/agents` | Create agent |
| GET | `/api/agents/{id}` | Get agent details |
| PUT | `/api/agents/{id}` | Update agent |
| DELETE | `/api/agents/{id}` | Delete agent |

### Campaigns

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/campaigns` | List campaigns |
| POST | `/api/campaigns/start` | Start campaign |
| POST | `/api/leads/upload` | Upload leads (CSV) |
| POST | `/api/campaigns/{id}/pause` | Pause campaign |
| POST | `/api/campaigns/{id}/archive` | Archive campaign |

### Clients

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/clients` | List clients |
| POST | `/api/clients` | Create client |
| GET | `/api/clients/resolve` | Resolve client by email |

### Demo / Voice

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/demo/start` | Start browser demo call |
| WS | `/api/voice-demo` | Browser demo voice stream |
| WS | `/api/voice-live` | Live call voice stream |
| WS | `/ws/dashboard` | Real-time dashboard events |

### Results & Logs

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/results` | Call results (filterable) |
| GET | `/api/logs` | Call logs |
| GET | `/api/results/{leadId}/transcript` | Transcript for lead |

### Telephony

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/phone-numbers` | List owned numbers |
| POST | `/api/phone-numbers/purchase` | Buy number |
| POST | `/api/phone-numbers/assign` | Assign number to agent |

### Website Intelligence

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/intelligence/scrape` | Start scrape job |
| GET | `/api/intelligence/jobs` | List scrape jobs |
| GET | `/api/intelligence/jobs/{id}` | Job details + draft |

### CRM

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/crm/connections` | Create CRM connection |
| POST | `/api/crm/sync/preflight` | Dry-run sync preview |
| POST | `/api/crm/sync/execute` | Execute sync |
| GET | `/api/crm/outbox` | Outbox queue |

### Memory

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/memory/collections` | Create memory collection |
| GET | `/api/memory/collections` | List collections |
| POST | `/api/memory/collections/{id}/items` | Add memory item |

---

## How to Create an Agent

### Via API

```bash
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Sales Agent",
    "voice": "ElevenLabs - Priya (Female)",
    "language": "english",
    "max_duration": 300,
    "provider": "twilio",
    "stt_provider": "deepgram",
    "tts_provider": "cartesia",
    "agent_type": "real_estate_sales",
    "script": "Hello {{name}}, this is {{agent_name}} from...",
    "data_fields": ["name", "phone", "budget", "location"]
  }'
```

### Via Frontend

Open `http://localhost:3000/agents` → **Create Agent**. Templates available for:
- Real Estate Sales
- Finance Advisory
- Insurance Renewal
- Education Counselling

From there you can configure voice, STT/TTS providers, set up website scraping to auto-generate the script, and edit the conversation flow with the FlowSpec editor.

---

## Frontend Pages

| Route | Access | Purpose |
|-------|--------|---------|
| `/` | Public | Marketing landing page |
| `/login` | Public | Firebase sign-in |
| `/monitor` | Admin | Live dashboard, call metrics |
| `/campaigns` | Admin | Campaign CRUD, lead upload |
| `/agents` | Admin/Client | Agent management, flow editor |
| `/client-dashboard` | Client | Campaign launch, live feed |
| `/clients` | Admin | Client accounts |
| `/demo` | Client | Browser-based demo call |
| `/intelligence` | Admin | Website scrape jobs |
| `/logs` | Admin | Call logs, transcripts |
| `/numbers` | Admin | Phone numbers |
| `/results` | Both | Call results, recordings |
| `/talk-live` | Client | Live agent test |

---

## Key Files to Know

| File | Why It Matters |
|------|---------------|
| `Backend/main.py` | Server entry point — all routes, WS, middleware (~7.5k lines) |
| `Backend/flows/runtime.py` | Voice pipeline — STT/LLM/TTS Pipecat processors |
| `Backend/llm/llm.py` | Groq API — intent extraction, 40+ intents |
| `Backend/llm/state_manager.py` | Conversation state machine — how the AI decides what to say (~2.2k lines) |
| `Backend/db/db_manager.py` | Database layer — async SQLite, all CRUD (~4.7k lines) |
| `Backend/ws_hub.py` | WebSocket broadcast hub — dashboard real-time updates |
| `Backend/demo_runner.py` | Demo call engine — simulates AI↔human conversation |
| `Backend/telephony/provider_registry.py` | Telephony provider abstraction (Twilio, VoBiz, etc.) |
| `Backend/platform_migration/feature_flags.py` | Feature flag system (~80 flags) |
| `frontend-next/src/hooks/useVoiceSocket.js` | WebRTC voice hook — AudioWorklet mic capture |
| `frontend-next/src/context/AuthContext.js` | Firebase auth + role management |
| `frontend-next/src/app/agents/page.js` | Agent management UI |

---

## How to Run Tests

```bash
cd Backend
python -m pytest test/           # Unit tests (7 files)
python -m pytest tests/          # QA / contract tests (26 files)
python -m pytest tests/test_flow_v2.py   # Single test
python verify_pipeline.py        # Connectivity test (Groq + Edge-TTS)
python mic_test.py               # Local microphone test
```

---

## Deployment

### Docker

```bash
docker-compose up --build
```

### Railway (primary)

Push to GitHub → Railway auto-deploys via `railway.json`. Build uses Nixpacks.

### Production Checklist

1. Set all required env vars
2. Enable HTTPS (required for browser microphone access)
3. Configure Nginx WebSocket proxy headers
4. Set `PLATFORM_FEATURE_PROFILE=live`
5. Persist `Backend/db/` as a volume
6. Verify `GET /health` returns 200

### Rollback

```bash
PLATFORM_FEATURE_PROFILE=shadow
```
Disables all new platform features while keeping the server running.

---

## Docs

Full documentation in the [`docs/`](./docs) directory:

| Document | Content |
|----------|---------|
| `docs/architecture.md` | System architecture, tech stack, design principles |
| `docs/backend-modules.md` | Every backend file with description |
| `docs/frontend-pages.md` | All routes, components, hooks |
| `docs/pipeline.md` | Voice pipeline deep dive |
| `docs/database.md` | SQLite schema, JSON fallback |
| `docs/deployment.md` | Docker, Railway, env vars |
| `docs/testing.md` | Test files & how to run them |
| `docs/index.md` | Full table of contents |

Additional reports:
- [`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md) — Agent fine-tuning & deployment
- [`architecture_report.md`](./architecture_report.md) — High-level architecture
- [`ai_pipeline_report.md`](./ai_pipeline_report.md) — Voice pipeline deep dive
- [`model_performance_benchmarking_report.md`](./model_performance_benchmarking_report.md) — STT/TTS benchmarks
- [`production_live_report.md`](./production_live_report.md) — Production feature profile
- [`deepgram_cartesia_migration_roadmap.md`](./deepgram_cartesia_migration_roadmap.md) — Provider migration plan
- [`PROJECT_DOCUMENT.md`](./PROJECT_DOCUMENT.md) — Full project analysis

---

## Known Issues

| Issue | Workaround |
|-------|-----------|
| Browser blocks mic on HTTP (non-localhost) | Use HTTPS in production |
| Browser autoplay policy blocks audio | User must click once to resume AudioContext |
| First run downloads model weights | Subsequent starts are instant |
