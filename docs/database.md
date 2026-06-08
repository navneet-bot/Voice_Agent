# Database

## Storage Architecture

```
┌─────────────────────────────────────────────┐
│           SQLite (platform.db)              │
│   Structured data: clients, campaigns,       │
│   leads, phone_numbers, call_results, etc.   │
│   Async interface via db_manager.py          │
│   (~4,700 lines)                             │
└──────────────────┬──────────────────────────┘
                   │
     ┌─────────────┴─────────────┐
     │                           │
     ▼                           ▼
┌──────────────┐      ┌──────────────────────┐
│  JSON Files  │      │  db/agents/*.json     │
│  (legacy)    │      │  Agent schemas        │
│  · agents    │      │  (never in SQLite)    │
│  · campaigns │      └──────────────────────┘
│  · leads     │
│  · assignmts │
└──────────────┘
```

## Database Tables (platform.db)

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `clients` | Client accounts | id, name, email, created_at |
| `agents` | Voice agent configurations | id, name, client_id, provider, voice, stt_provider, tts_provider, schema_path |
| `campaigns` | Outbound campaigns | id, name, agent_id, client_id, status, created_at |
| `leads` | Lead records | id, name, phone, email, campaign_id, status |
| `phone_numbers` | Telephony numbers | id, number, provider, country, assigned_agent_id |
| `call_results` | Call outcomes | id, call_id, lead_id, agent_id, duration, status, transcript_path, recording_path |
| `live_call_state` | Real-time call state | id, call_id, state, started_at |
| `assignments` | Agent-to-client | id, agent_id, client_id |
| `crm_connections` | CRM integration configs | id, client_id, provider, credentials_ref |
| `scrape_jobs` | Website scrape jobs | id, url, client_id, status, draft_flow_id |
| `agent_memory` | RAG memory collections | id, client_id, agent_id, content, metadata |

## Key Patterns

### Async SQLite (`db_manager.py`)
- All database operations use `async/await` with a connection pool
- Single-file implementation (~4,700 lines) covering all CRUD operations
- Query results are returned as Python dicts/lists

### JSON Fallback
- Legacy `.json` files (`agents.json`, `campaigns.json`, `leads.json`, `assignments.json`) are loaded when SQLite queries fail
- Ensures backward compatibility during migration
- New data is always written to SQLite first

### Agent Schema Storage
- Agent conversation flows are stored as individual `.json` files under `db/agents/{uuid}.json`
- Never stored in SQLite
- Schema defines nodes, transitions, scripts, voice settings
- Loaded at start of every call by `StateManager`

### File Locking & Git
- `platform.db` is excluded from version control (in `.gitignore`)
- JSON files in `db/agents/` are version-controlled
- `.env` files (containing API keys) are gitignored

## Data Flow

```
Call Incoming
     │
     ▼
Create live_call_state record
     │
     ▼
Process audio through Pipecat pipeline
     │
     ▼
Call ends
     │
     ▼
Save call_result (transcript, recording, duration, status)
     │
     ▼
Update campaign stats
     │
     ▼
Broadcast via WebSocket hub to dashboard
```
