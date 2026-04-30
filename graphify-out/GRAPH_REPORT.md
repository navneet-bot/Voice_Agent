# Graph Report - /Users/mani/Documents/Projects/Voice Agent Pro/Voice_Agent  (2026-04-29)

## Corpus Check
- 65 files · ~95,201 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 646 nodes · 1341 edges · 77 communities detected
- Extraction: 55% EXTRACTED · 45% INFERRED · 0% AMBIGUOUS · INFERRED: 603 edges (avg confidence: 0.57)
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
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]

## God Nodes (most connected - your core abstractions)
1. `StateManager` - 156 edges
2. `RealEstateTTSProcessor` - 85 edges
3. `RealEstateLLMProcessor` - 84 edges
4. `RealEstateSTTProcessor` - 84 edges
5. `DemoCallEngine` - 55 edges
6. `AgentTextFrame` - 49 edges
7. `VoiceTurnState` - 49 edges
8. `LanguageTracker` - 30 edges
9. `run_in_executor()` - 28 edges
10. `DatabaseManager` - 27 edges

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
Cohesion: 0.03
Nodes (69): load_system_prompt(), main(), CLI Chat Simulation for the AI Voice Agent. Run from the project root:  python c, Load the base prompt from prompt.txt., Returns a realistic set of demo leads for campaigns with no uploaded leads., Simulates a full outbound call through the real AI pipeline.      The same State, LLM module public interface.  Usage:     from llm import generate_response, _async_call_groq_api() (+61 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (80): BaseModel, Conversation Handler orchestrated via Pipecat.  This module bridges our custom,, Synthesizes TTS audio from LLM TextFrames using our Kokoro integration.     Expe, Wraps our custom llm.py logic (Groq API, prompt.txt, latency checks)     into a, Wraps our customized faster-whisper CPU STT logic into Pipecat.     Buffers inco, RealEstateLLMProcessor, RealEstateSTTProcessor, RealEstateTTSProcessor (+72 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (46): Campaign Runner — Production call orchestration.  Upgraded from the original age, Always resolves fresh from disk — auto-reload for agent fine-tuning., Simulates a realistic human reply for non-demo production testing.     In real t, Executes a full campaign for every lead.     For demo/test: simulates conversati, _resolve_schema(), run_campaign(), simulate_human_response(), DatabaseManager (+38 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (53): analyze_user_text(), _count_markers(), detect_language_from_text(), get_language_instruction(), is_actionable_user_text(), LanguageTracker, Shared language detection and routing helpers for voice responses., Infer the user's language from a short utterance. (+45 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (18): ABC, get_providers(), purchase_number(), search_numbers(), DemoProvider, ExotelProvider, get_provider(), KnowlarityProvider (+10 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (32): _normalize_sentence(), optimize_for_tts(), Utilities for turning LLM text into stable, natural TTS input., Keep TTS input short, clean, and rhythmically stable., generate_speech_stream(), TTS module powered by Microsoft Edge-TTS API.  Replaces local CPU-bound Kokoro e, Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly p, check_voice_assets() (+24 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (25): main(), Simple script to test the Kokoro TTS engine. Usage: python check_voice.py "Text, generate_speech(), check_voice_assets(), _configure_stdout(), main(), _play_startup_greeting(), _bytes_to_pcm16() (+17 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (14): AuthProvider(), getInitials(), useAuth(), DashboardLayout(), AgentsPage(), CallResults(), CampaignsPage(), ClientDashboard() (+6 more)

### Community 8 - "Community 8"
Cohesion: 0.16
Nodes (9): dashboard_ws(), dashboard_ws_global(), test_ws(), WebSocket Broadcast Hub — Real-time event distribution to dashboard clients.  Re, Structured helper — builds a typed event and broadcasts it.          event_type, Central hub for WebSocket connections.      Supports two broadcast scopes:     -, Send a message to all browsers connected under a specific client_id., Send a message to every connected browser across all clients. (+1 more)

### Community 9 - "Community 9"
Cohesion: 0.19
Nodes (9): twilio_stream(), twilio_twiml(), build_twiml(), handle_twilio_stream(), _pcm16_to_ulaw(), _resample_pcm16(), TwilioSink, TwilioSource (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.83
Nodes (3): main(), test_edge_tts(), test_groq()

### Community 11 - "Community 11"
Cohesion: 0.5
Nodes (3): optimize_for_tts(), Speech Formatter ================ This module transforms raw LLM output into spe, Format raw LLM output for TTS by handling spacing, repeated punctuation, breakin

### Community 12 - "Community 12"
Cohesion: 0.67
Nodes (1): TextFrame

### Community 13 - "Community 13"
Cohesion: 0.5
Nodes (1): MicCaptureProcessor

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
Nodes (0): 

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (0): 

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Creates a new agent JSON schema based on a generic template and admin inputs.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (0): 

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (0): 

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Provider slug used in dropdown: 'twilio', 'exotel', etc.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Human-readable name shown in UI dropdown.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Primary region: 'IN', 'US', 'Global

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Initiate an outbound call.         Returns: { "call_sid": str, "status": str }

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Returns available phone numbers to purchase.         Each: { "phone": str, "regi

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Purchase a phone number.         Returns: { "phone": str, "sid": str, "status":

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (0): 

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (0): 

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (0): 

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (0): 

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (0): 

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Clean common STT artefacts before intent extraction.     Operates on words only

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Return True if user gave a vague non-answer for a specific field.     Used to of

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Return a static guidance response for a vague slot answer.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): Return a short bridge phrase for unclear/fallback intents only. Empty string oth

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Detect clearly hostile or dismissive input.     Lightweight keyword check — no M

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): Map intent_trigger -> node_id for all nodes.     If two nodes share a trigger, l

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): Extract all approved phrases from the JSON conversation file and     hardcoded c

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): Return the list of approved phrases from the JSON conversation file.

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): Return which phrase bank entries appear (fully or partially) in the response.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Return the node mapped to the given intent, if any.

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): Return False for input too weak to extract intent from.     Allow short confirma

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): Return node["response"] with {{placeholders}} filled from data.     Never return

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): Return True only if the user is asking an informational question     that is not

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): Conversation state tracker backed by Updated_Real_Estate_Agent.json.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Creates a new agent JSON schema based on a generic template and admin inputs.

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Asynchronously triggers WhatsApp property details based on intent or node.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Returns (next_node, bypass_forward_guard).

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): Route deny intent based on conversation context (current node).         Returns

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): Walk through skip edges to reach terminal nodes after response delivery.

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): Used only by non-process_turn callers (noise, greeting, next_step).

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): Enforce word and sentence limits on the final response text     to keep TTS outp

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly p

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Run a synchronous DB function in the default thread pool.

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Async interface to the SQLite platform database.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Initialize DB schema. Call once at server startup.

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Returns (next_node, bypass_forward_guard).

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Route deny intent based on conversation context (current node).         Returns

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Walk through skip edges to reach terminal nodes after response delivery.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Used only by non-process_turn callers (noise, greeting, next_step).

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Enforce word and sentence limits on the final response text     to keep TTS outp

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Walk through skip edges to reach terminal nodes after response delivery.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Used only by non-process_turn callers (noise, greeting, next_step).

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Enforce word and sentence limits on the final response text     to keep TTS outp

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au

## Knowledge Gaps
- **139 isolated node(s):** `WebSocket Broadcast Hub — Real-time event distribution to dashboard clients.  Re`, `Central hub for WebSocket connections.      Supports two broadcast scopes:     -`, `Send a message to all browsers connected under a specific client_id.`, `Send a message to every connected browser across all clients.`, `Structured helper — builds a typed event and broadcasts it.          event_type` (+134 more)
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
- **Thin community `Community 21`** (2 nodes): `LogsPage()`, `page.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `tmp_explore.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `patch_json_disconnect.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Creates a new agent JSON schema based on a generic template and admin inputs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Provider slug used in dropdown: 'twilio', 'exotel', etc.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Human-readable name shown in UI dropdown.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Primary region: 'IN', 'US', 'Global`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Initiate an outbound call.         Returns: { "call_sid": str, "status": str }`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Returns available phone numbers to purchase.         Each: { "phone": str, "regi`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Purchase a phone number.         Returns: { "phone": str, "sid": str, "status":`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `next.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `eslint.config.mjs`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `firebase.js`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Clean common STT artefacts before intent extraction.     Operates on words only`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Return True if user gave a vague non-answer for a specific field.     Used to of`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Return a static guidance response for a vague slot answer.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `Return a short bridge phrase for unclear/fallback intents only. Empty string oth`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Detect clearly hostile or dismissive input.     Lightweight keyword check — no M`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `Map intent_trigger -> node_id for all nodes.     If two nodes share a trigger, l`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `Extract all approved phrases from the JSON conversation file and     hardcoded c`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `Return the list of approved phrases from the JSON conversation file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `Return which phrase bank entries appear (fully or partially) in the response.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Return the node mapped to the given intent, if any.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `Return False for input too weak to extract intent from.     Allow short confirma`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `Return node["response"] with {{placeholders}} filled from data.     Never return`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `Return True only if the user is asking an informational question     that is not`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `Conversation state tracker backed by Updated_Real_Estate_Agent.json.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `Creates a new agent JSON schema based on a generic template and admin inputs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `Asynchronously triggers WhatsApp property details based on intent or node.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Returns (next_node, bypass_forward_guard).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 55`** (1 nodes): `Route deny intent based on conversation context (current node).         Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 56`** (1 nodes): `Walk through skip edges to reach terminal nodes after response delivery.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 57`** (1 nodes): `Used only by non-process_turn callers (noise, greeting, next_step).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 58`** (1 nodes): `Enforce word and sentence limits on the final response text     to keep TTS outp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 59`** (1 nodes): `Synchronous wrapper that yields PCM16 bytes chunks sequentially so it directly p`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 60`** (1 nodes): `Run a synchronous DB function in the default thread pool.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (1 nodes): `Async interface to the SQLite platform database.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (1 nodes): `Initialize DB schema. Call once at server startup.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Returns (next_node, bypass_forward_guard).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Route deny intent based on conversation context (current node).         Returns`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Walk through skip edges to reach terminal nodes after response delivery.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Used only by non-process_turn callers (noise, greeting, next_step).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Enforce word and sentence limits on the final response text     to keep TTS outp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Walk through skip edges to reach terminal nodes after response delivery.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Used only by non-process_turn callers (noise, greeting, next_step).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Enforce word and sentence limits on the final response text     to keep TTS outp`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Convert raw audio bytes to a 16-bit PCM NumPy array.     Supports WAV container,`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Transcribe a short audio chunk to text using Groq Cloud STT.      Accepts raw au`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `StateManager` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 9`?**
  _High betweenness centrality (0.333) - this node is a cross-community bridge._
- **Why does `run_campaign()` connect `Community 2` to `Community 8`, `Community 0`, `Community 4`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `get_provider()` connect `Community 4` to `Community 2`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 112 inferred relationships involving `StateManager` (e.g. with `Campaign Runner — Production call orchestration.  Upgraded from the original age` and `Always resolves fresh from disk — auto-reload for agent fine-tuning.`) actually correct?**
  _`StateManager` has 112 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `RealEstateTTSProcessor` (e.g. with `Live Microphone Test for Agent Neha (Pipecat 0.0.108). Speak into your computer'` and `Avoid Windows console encoding crashes during local diagnostics.`) actually correct?**
  _`RealEstateTTSProcessor` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `RealEstateLLMProcessor` (e.g. with `Live Microphone Test for Agent Neha (Pipecat 0.0.108). Speak into your computer'` and `Avoid Windows console encoding crashes during local diagnostics.`) actually correct?**
  _`RealEstateLLMProcessor` has 79 INFERRED edges - model-reasoned connections that need verification._
- **Are the 79 inferred relationships involving `RealEstateSTTProcessor` (e.g. with `Live Microphone Test for Agent Neha (Pipecat 0.0.108). Speak into your computer'` and `Avoid Windows console encoding crashes during local diagnostics.`) actually correct?**
  _`RealEstateSTTProcessor` has 79 INFERRED edges - model-reasoned connections that need verification._