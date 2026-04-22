# Graph Report - /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent  (2026-04-20)

## Corpus Check
- 57 files · ~89,427 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 533 nodes · 1069 edges · 39 communities detected
- Extraction: 63% EXTRACTED · 37% INFERRED · 0% AMBIGUOUS · INFERRED: 398 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]

## God Nodes (most connected - your core abstractions)
1. `StateManager` - 117 edges
2. `RealEstateLLMProcessor` - 62 edges
3. `RealEstateSTTProcessor` - 62 edges
4. `RealEstateTTSProcessor` - 62 edges
5. `DemoCallEngine` - 33 edges
6. `AgentTextFrame` - 27 edges
7. `run_in_executor()` - 24 edges
8. `DatabaseManager` - 24 edges
9. `LanguageTracker` - 18 edges
10. `_log()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Campaign Runner — Production call orchestration.  Upgraded from the original age` --uses--> `StateManager`  [INFERRED]
  /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/agent_runner.py → /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/llm/state_manager.py
- `Always resolves fresh from disk — auto-reload for agent fine-tuning.` --uses--> `StateManager`  [INFERRED]
  /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/agent_runner.py → /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/llm/state_manager.py
- `Simulates a realistic human reply for non-demo production testing.     In real t` --uses--> `StateManager`  [INFERRED]
  /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/agent_runner.py → /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/llm/state_manager.py
- `Executes a full campaign for every lead.     For demo/test: simulates conversati` --uses--> `StateManager`  [INFERRED]
  /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/agent_runner.py → /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/llm/state_manager.py
- `Demo Call Engine — Zero-cost, indistinguishable from real calls.  Runs the full` --uses--> `StateManager`  [INFERRED]
  /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/demo_runner.py → /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent/Backend/llm/state_manager.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (67): BaseModel, Conversation Handler orchestrated via Pipecat.  This module bridges our custom,, Synthesizes TTS audio from LLM TextFrames using our Kokoro integration.     Expe, Wraps our custom llm.py logic (Groq API, prompt.txt, latency checks)     into a, Wraps our customized faster-whisper CPU STT logic into Pipecat.     Buffers inco, RealEstateLLMProcessor, RealEstateSTTProcessor, RealEstateTTSProcessor (+59 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (54): Returns a realistic set of demo leads for campaigns with no uploaded leads., Simulates a full outbound call through the real AI pipeline.      The same State, LLM module public interface.  Usage:     from llm import generate_response, _async_call_groq_api(), _build_phrase_constrained_system(), extract_intent(), generate_phrase_constrained_response(), _load_prompt_rules() (+46 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (47): Campaign Runner — Production call orchestration.  Upgraded from the original age, Always resolves fresh from disk — auto-reload for agent fine-tuning., Simulates a realistic human reply for non-demo production testing.     In real t, Executes a full campaign for every lead.     For demo/test: simulates conversati, _resolve_schema(), run_campaign(), simulate_human_response(), DatabaseManager (+39 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (40): analyze_user_text(), _count_markers(), detect_language_from_text(), get_language_instruction(), is_actionable_user_text(), LanguageTracker, Shared language detection and routing helpers for voice responses., Infer the user's language from a short utterance. (+32 more)

### Community 4 - "Community 4"
Cohesion: 0.06
Nodes (14): ABC, DemoProvider, ExotelProvider, KnowlarityProvider, list_providers(), Multi-Provider Telephony Registry.  Clients can choose their telephony provider, VoBiz uses SIP + WebSocket streams.         When integrated, their platform conn, Returns provider metadata for the frontend dropdown. (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (32): _normalize_sentence(), optimize_for_tts(), Utilities for turning LLM text into stable, natural TTS input., Keep TTS input short, clean, and rhythmically stable., generate_speech_stream(), TTS module powered by Microsoft Edge-TTS API.  Replaces local CPU-bound Kokoro e, Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly p, check_voice_assets() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (24): load_system_prompt(), main(), CLI Chat Simulation for the AI Voice Agent. Run from the project root:  python c, Load the base prompt from prompt.txt., generate_response(), Async compatibility wrapper for the pipeline entry point., _is_actionable(), Return False for input too weak to extract intent from.     Allow short confirma (+16 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (9): useAuth(), DashboardLayout(), CallResults(), ClientDashboard(), DemoCampaign(), Home(), MyNumbers(), TalkLive() (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.19
Nodes (7): dashboard_ws(), dashboard_ws_global(), test_ws(), WebSocket Broadcast Hub — Real-time event distribution to dashboard clients.  Re, Central hub for WebSocket connections.      Supports two broadcast scopes:     -, Send a message to all browsers connected under a specific client_id., WebSocketManager

### Community 9 - "Community 9"
Cohesion: 0.2
Nodes (8): main(), Simple script to test the Kokoro TTS engine. Usage: python check_voice.py "Text, generate_speech(), check_voice_assets(), _configure_stdout(), main(), _play_startup_greeting(), test_tts()

### Community 10 - "Community 10"
Cohesion: 0.5
Nodes (1): MicCaptureProcessor

### Community 11 - "Community 11"
Cohesion: 0.83
Nodes (3): main(), test_edge_tts(), test_groq()

### Community 12 - "Community 12"
Cohesion: 0.5
Nodes (3): optimize_for_tts(), Speech Formatter ================ This module transforms raw LLM output into spe, Format raw LLM output for TTS by handling spacing, repeated punctuation, breakin

### Community 13 - "Community 13"
Cohesion: 0.67
Nodes (2): _get_demo_leads(), Demo Call Engine — Zero-cost, indistinguishable from real calls.  Runs the full

### Community 14 - "Community 14"
Cohesion: 0.67
Nodes (1): STT configuration constants.  All tunable parameters for the faster-whisper spee

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (0): 

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (0): 

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Smoke-test for the LLM module. Run from the project root:  python test_llm.py  R

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Quick smoke-test for the STT module. Run from the project root:  python test_stt

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (0): 

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (0): 

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (0): 

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Creates a new agent JSON schema based on a generic template and admin inputs.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Provider slug used in dropdown: 'twilio', 'exotel', etc.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Human-readable name shown in UI dropdown.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Primary region: 'IN', 'US', 'Global

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Initiate an outbound call.         Returns: { "call_sid": str, "status": str }

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Returns available phone numbers to purchase.         Each: { "phone": str, "regi

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Purchase a phone number.         Returns: { "phone": str, "sid": str, "status":

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (0): 

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (0): 

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Walk through skip edges to reach terminal nodes after response delivery.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Used only by non-process_turn callers (noise, greeting, next_step).

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Enforce word and sentence limits on the final response text     to keep TTS outp

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au

## Knowledge Gaps
- **100 isolated node(s):** `WebSocket Broadcast Hub — Real-time event distribution to dashboard clients.  Re`, `Central hub for WebSocket connections.      Supports two broadcast scopes:     -`, `Send a message to all browsers connected under a specific client_id.`, `Send a message to every connected browser across all clients.`, `Structured helper — builds a typed event and broadcasts it.          event_type` (+95 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `test_flow()`, `test_backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `main()`, `start_production.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `Smoke-test for the LLM module. Run from the project root:  python test_llm.py  R`, `test_llm.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `Quick smoke-test for the STT module. Run from the project root:  python test_stt`, `test_stt.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `RootLayout()`, `layout.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `AdminMonitor()`, `page.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `tmp_explore.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Creates a new agent JSON schema based on a generic template and admin inputs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Provider slug used in dropdown: 'twilio', 'exotel', etc.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Human-readable name shown in UI dropdown.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Primary region: 'IN', 'US', 'Global`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Initiate an outbound call.         Returns: { "call_sid": str, "status": str }`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Returns available phone numbers to purchase.         Each: { "phone": str, "regi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Purchase a phone number.         Returns: { "phone": str, "sid": str, "status":`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `next.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `eslint.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Walk through skip edges to reach terminal nodes after response delivery.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Used only by non-process_turn callers (noise, greeting, next_step).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Enforce word and sentence limits on the final response text     to keep TTS outp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StateManager` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 13`?**
  _High betweenness centrality (0.356) - this node is a cross-community bridge._
- **Why does `run_campaign()` connect `Community 2` to `Community 1`, `Community 3`, `Community 4`, `Community 6`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `get_provider()` connect `Community 2` to `Community 4`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 78 inferred relationships involving `StateManager` (e.g. with `AgentCreate` and `LeadsUpload`) actually correct?**
  _`StateManager` has 78 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `RealEstateLLMProcessor` (e.g. with `AgentCreate` and `LeadsUpload`) actually correct?**
  _`RealEstateLLMProcessor` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `RealEstateSTTProcessor` (e.g. with `AgentCreate` and `LeadsUpload`) actually correct?**
  _`RealEstateSTTProcessor` has 57 INFERRED edges - model-reasoned connections that need verification._
- **Are the 57 inferred relationships involving `RealEstateTTSProcessor` (e.g. with `AgentCreate` and `LeadsUpload`) actually correct?**
  _`RealEstateTTSProcessor` has 57 INFERRED edges - model-reasoned connections that need verification._