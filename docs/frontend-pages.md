# Frontend Pages

## Routes

| Route | Page File | Access | Purpose |
|-------|-----------|--------|---------|
| `/` | `page.js` | Public | Marketing landing page — animated orb visualizer, feature grid, pricing, FAQ |
| `/login` | `login/page.js` | Public | Firebase email/password + Google sign-in; supports login/signup/reset modes |
| `/monitor` | `monitor/page.js` | Admin | Live dashboard — call metrics, active call table, provider latency, QA readiness panels |
| `/campaigns` | `campaigns/page.js` | Admin | Campaign CRUD — CSV lead upload, start/archive/restore/delete, E2E QA panel |
| `/agents` | `agents/page.js` | Admin/Client | Agent management — templates, voice/STT/TTS config, website script scraping, FlowSpec editor |
| `/client-dashboard` | `client-dashboard/page.js` | Client | Campaign launch, lead upload, live WS feed, credits display |
| `/clients` | `clients/page.js` | Admin | Client account management (name, email, agent assignment) |
| `/demo` | `demo/page.js` | Client | Browser-based demo call via useVoiceSocket, real-time transcript |
| `/intelligence` | `intelligence/page.js` | Admin | Scrape job management — dispatch, cancel, drafts, diagnostics modal |
| `/logs` | `logs/page.js` | Admin | Call logs with campaign selector, expandable transcripts, audio playback |
| `/numbers` | `numbers/page.js` | Admin | Phone number search/buy/assign by provider/country, Telephony Live QA panel |
| `/results` | `results/page.js` | Both | Call results with campaign selector, stats, transcripts, audio, auto-poll (5s) |
| `/talk-live` | `talk-live/page.js` | Client | Live agent browser test (non-demo) via useVoiceSocket |
| `/crm-readiness` | `crm-readiness/page.js` | Admin | CRM rollout gates — Live Readiness, Provider Sandbox, Dispatch Canary |

## Components

| Component | Description |
|-----------|-------------|
| `DashboardLayout.js` | Main authenticated layout — header with client switcher, user avatar, sign-out; role-based sidebar (admin: 8 items, client: 3 items). Redirects unauthenticated to `/login`. |
| `FlowPreviewModal.js` | Full-screen conversation flow graph viewer/editor — runtime info, path steps, fallback paths. Edit mode: add/edit nodes, transitions, responses, data collection fields. Saves Flow V2 drafts. |

## Hooks

| Hook | Description |
|------|-------------|
| `useVoiceSocket.js` | WebRTC/WebSocket voice client — AudioWorklet mic capture with ScriptProcessor fallback; adaptive jitter buffer (80–500ms); barge-in/interruption handling (gain fading, gen_id tracking); PCM16 I/O; demo vs live mode. |

## Context

| Context | Description |
|---------|-------------|
| `AuthContext.js` | Firebase auth state management — role from admin email list (navneet, vishnu, parth, maniarasan @jobjockey.in); client assignment via `/api/clients/resolve`; exposes `currentRole`, `activeClient`, `firebaseUser`. |

## Library

| File | Description |
|------|-------------|
| `firebase.js` | Firebase app initialization (anti-hot-reload). Exports `auth`. |
| `providerDisplay.js` | Label maps for STT, TTS, Telephony providers. `getProviderLabel(kind, value)`. |

## Authentication & Roles

- **Auth provider**: Firebase Auth (email/password + Google)
- **Admin emails**: Hard-coded in `AuthContext.js`
- **Client users**: Resolve profile via REST API
- **Role routes**: Admin = any page; Client = dashboard, demo, results, agents (assigned)
- **Multi-tenancy**: Admin can switch clients via dropdown; data scoped by `X-Tenant-ID`

## Feature Flags (Frontend)

All controllable via `NEXT_PUBLIC_*` env vars:
- Flow visualization
- Campaign lifecycle
- CRM readiness
- Scrape features
- Telephony QA
- Security audit
- Demo QA
- Final canary rollback

## Backend Proxy (next.config.mjs)

```
/api/:path*   →  http://localhost:8000/api/:path*
/ws/:path*    →  http://localhost:8000/ws/:path*
```

## Key Dependencies

| Package | Version |
|---------|---------|
| next | 16.2.4 |
| react | 19.2.4 |
| react-dom | 19.2.4 |
| bootstrap | ^5.3.3 |
| firebase | ^12.12.1 |
| framer-motion | ^12.40.0 |
| lucide-react | ^1.16.0 |
| tailwindcss | ^3.4.17 |
