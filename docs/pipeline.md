# Voice Pipeline

## Pipeline Flow

```
User Audio (PCM16 @ 16kHz)
       │
       ▼
┌─────────────────────────────────────┐
│ RealEstateSTTProcessor              │
│  ├─ Adaptive VAD                    │
│  │  • Noise-floor calibration       │
│  │  • Dynamic RMS thresholds        │
│  │  • Barge-in detection             │
│  ├─ STT Provider (Deepgram/Groq)    │
│  │  • Streaming transcription        │
│  │  • Hallucination filtering        │
│  └─ Multi-language detection         │
└──────────────┬──────────────────────┘
               ▼ Text transcript
┌─────────────────────────────────────┐
│ RealEstateLLMProcessor              │
│  ├─ Intent Extraction (40+ intents) │
│  ├─ State Management                │
│  │  • Node traversal                │
│  │  • StateManager integration      │
│  │  • GenID syncing                 │
│  └─ Groq LLM (llama-3.1-70B)       │
│     • JSON-only structured output   │
│     • Retry with exponential backoff│
└──────────────┬──────────────────────┘
               ▼ Response text
┌─────────────────────────────────────┐
│ RealEstateTTSProcessor              │
│  ├─ TTS Provider (Cartesia/Edge)    │
│  │  • Streaming synthesis           │
│  │  • GenID-tagged audio chunks     │
│  ├─ Speech Formatting               │
│  │  • Sentence splitting            │
│  │  • Pacing adjustments            │
│  └─ Barge-in support                │
└──────────────┬──────────────────────┘
               ▼ PCM16 audio @ 24kHz
       │
       ▼
[Browser Playback / Twilio Stream]
```

## Processors (flows/runtime.py)

### RealEstateSTTProcessor
- **Adaptive VAD**: Continuously calibrates noise floor from ambient audio during silence periods
- **Dynamic thresholds**: Energy-based with `SILENCE_RMS_THRESHOLD = 0.015` (configurable)
- **Chunking**: `MIN_CHUNK_MS = 250ms`, `MAX_CHUNK_MS = 800ms`, trailing silence `220ms`
- **Barge-in**: Detects user speech during TTS playback → sends `CancelFrame` to interrupt TTS
- **Post-TTS cooldown**: `180ms` window after TTS ends to avoid cutting off agent speech
- **Multi-language**: Routes detected language to STT provider

### RealEstateLLMProcessor
- Integrates with `StateManager` for conversation flow graph
- Extracts intent from user text via Groq LLM
- **Echo detection**: Filters repeated or filler utterances (e.g., "uh", "um", repeated phrases)
- **GenID syncing**: Associates a unique generation ID with every LLM turn
- Outputs structured JSON with intent, entities, and next node

### RealEstateTTSProcessor
- Receives text responses from LLM processor
- Sends to TTS provider (Cartesia or Edge)
- Tags each audio chunk with its GenID for transcript alignment
- **Barge-in**: When user interrupts, streaming TTS output is cancelled mid-stream
- Output: PCM16 at 24kHz mono

## Provider Abstraction

| Component | Active | Fallback/Legacy | Selection |
|-----------|--------|----------------|-----------|
| **STT** | Deepgram Nova-2 (WebSocket) | Groq Whisper Turbo | Agent config + env overrides |
| **TTS** | Cartesia Sonic (WebSocket) | Edge-TTS | Agent config + env overrides |
| **Telephony** | Twilio (global) | VoBiz, Exotel, Knowlarity, Demo | Per-agent via registry |

Each provider layer supports:
- **Shadow mode**: Run both old and new providers in parallel for comparison
- **Per-agent selection**: Each agent can choose its STT/TTS provider
- **Feature flag gating**: Controlled by `FEATURE_*` env vars

## Latency

### Optimization Techniques

| Technique | Detail |
|-----------|--------|
| Streaming providers | Deepgram & Cartesia use WebSocket streaming (no polling) |
| Groq LPU | Custom hardware for fast LLM inference |
| Async execution | All pipeline stages are non-blocking async |
| Hard timeouts | 4s LLM timeout, circuit breakers on failure |
| Rate-limit cooldown | Exponential backoff on Groq 429 responses |
| Hallucination filtering | Filters silence-only transcriptions from STT |

### Benchmarks (May 2026)

**End-to-End Latency:** 3.8–5.2s (original stack) → **0.7–1.1s** (current stack)

| Provider | Role | Latency | Accuracy | Result |
|----------|------|---------|----------|--------|
| Deepgram Nova-2 | STT | <300ms | 96% | PASS |
| Groq Llama-3.1-70B | LLM | streamed | 250+ tok/s | PASS |
| Cartesia Sonic | TTS | <150ms TTFB | 94% quality | PASS |

## Audio Specifications

| Stage | Sample Rate | Format | Channels |
|-------|-------------|--------|----------|
| Mic input | 16kHz | PCM16 | Mono |
| STT input | 16kHz | PCM16 → WAV | Mono |
| TTS output | 24kHz | PCM16 | Mono |
| Browser playback | 24kHz | PCM16 | Mono |
| Twilio stream | 8kHz | PCMU | Mono |
| Recording | 16kHz | WAV | Stereo (L=user, R=agent) |

## Configuration

| Module | Config File | Key Params |
|--------|-------------|------------|
| STT | `stt/config.py` | `SAMPLE_RATE=16000`, `MIN_CHUNK_MS=250`, `MAX_CHUNK_MS=800`, `TRAILING_SILENCE_MS=220` |
| TTS | `tts/config.py` | `SAMPLE_RATE=24000`, `MAX_TEXT_LENGTH=500`, `SPEED=1.1` |
| Pipeline | `.env` | `GROQ_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY` |
