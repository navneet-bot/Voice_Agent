# Architecture

## High-Level Diagram

```
[Browser / Web App]
       │
       ├── HTTP REST ───────► [Next.js Frontend :3000]
       │                             │
       │                        Proxy /rewrites
       │                             ▼
       │                     [FastAPI Backend :8000]
       │                             │
       └── WebSocket ───────► [WebSocket Hub]
                                     │
                               ┌─────┴──────┐
                               │  Pipecat   │
                               │  Pipeline  │
                               │ STT→LLM→TTS│
                               └─────┬──────┘
                                     │
              [Twilio/Telephony] ◄───┘
                                     │
                               ┌─────┴──────┐
                               │  SQLite DB  │
                               │  + JSON     │
                               └────────────┘
```

## Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Backend** | FastAPI (Python 3.11) | ASGI async, auto-docs |
| **Frontend** | Next.js 16.2.4 (App Router) | React 19.2.4 |
| **Styling** | Bootstrap 5 + Tailwind CSS | `tw-` prefix to avoid conflicts |
| **Auth** | Firebase Auth | Email/password + Google OAuth |
| **Voice Pipeline** | Pipecat AI | Async frame-based streaming |
| **STT** | Deepgram Nova-2 | WebSocket streaming, <300ms |
| **LLM** | Groq Llama-3.1-70B | 250+ tokens/sec |
| **TTS** | Cartesia Sonic | WebSocket streaming, <150ms TTFB |
| **Database** | SQLite + JSON files | Dual storage layer |
| **Telephony** | Twilio / VoBiz / Exotel / Knowlarity | Multi-provider abstraction |
| **Deployment** | Railway (backend) | Procfile + railway.json |

## Repository Structure

```
Voice_Agent/
├── Backend/                     # FastAPI Python server
│   ├── main.py                  # ~7,300 lines — all routes + WS endpoints
│   ├── main_working.py          # Leaner variant
│   ├── main_pipeline.py         # Pipecat pipeline wiring
│   ├── start_production.py      # Gunicorn production launcher
│   ├── demo_runner.py           # Demo call engine
│   ├── agent_runner.py          # Production call orchestrator
│   ├── ws_hub.py                # WebSocket broadcast hub
│   ├── call_recording.py        # Session WAV recorder
│   ├── requirements.txt         # Python deps
│   ├── flows/                   # Pipecat frame processors
│   ├── llm/                     # Groq integration + state machine
│   ├── stt/                     # Speech-to-text providers
│   ├── tts/                     # Text-to-speech providers
│   ├── telephony/               # Telephony provider registry
│   ├── crm/                     # CRM integration (audit-only)
│   ├── intelligence/            # Website crawler + script gen
│   ├── campaigns/               # Campaign execution control
│   ├── memory/                  # Agent memory (RAG collections)
│   ├── metrics/                 # Provider latency monitoring
│   ├── platform_migration/      # Feature flags + auth context
│   ├── integrations/            # WhatsApp integration
│   ├── audio/                   # Audio utilities
│   ├── db/                      # Async SQLite + JSON storage
│   ├── test/                    # Unit tests (7 files)
│   └── tests/                   # QA tests (26 files)
│
├── frontend-next/               # Next.js dashboard
│   ├── src/app/                 # 12 routes (App Router)
│   ├── src/components/          # DashboardLayout, FlowPreviewModal
│   ├── src/context/             # AuthContext (Firebase + roles)
│   ├── src/hooks/               # useVoiceSocket (WebRTC voice)
│   └── src/lib/                 # Firebase init, provider labels
│
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── railway.json
├── README.md
├── DEVELOPMENT_GUIDE.md
└── docs/                        # This documentation
```

## Design Principles

1. **Provider Abstraction** — STT, TTS, Telephony each use a registry pattern; providers selected by agent config or env overrides; shadow/fallback for parallel comparison.
2. **Feature Flags** — ~80 flags in `platform_migration/feature_flags.py`; `live` (all on) and `shadow` (all off) profiles; individual env var overrides.
3. **Audit-First** — CRM and platform migration are audit-only by default; no data transmitted until explicitly enabled.
4. **Dual Storage** — SQLite for structured data; JSON files for agent schemas; JSON fallback for legacy compatibility.
5. **Streaming Pipeline** — Every stage (VAD, STT, LLM, TTS) streams data frame-by-frame with no blocking waits.
