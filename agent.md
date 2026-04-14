# AI Voice Agent: Phase 9 & 10 Handover Document

**To the AI Assistant taking over on the new laptop:**

This project is a high-performance, production-ready AI Voice SaaS platform. The user is moving to a new machine because the current one has hardware/environmental issues. Your goal is to resume work starting from **Phase 9 (Audio Reliability)** and **Phase 10 (High-Fidelity Telephony Demo)**.

## 🛠 Project Context
- **Tech Stack**: Pipecat-AI, Edge-TTS (`en-IN-NeerjaNeural`), Groq (`Llama-3-70b/8b`), Faster-Whisper.
- **Current State**: 
  - Backend (FastAPI) and Frontend Dashboard (SaaS UI) are built and synchronized.
  - Basic WebSocket audio bridge exists in `server.py` and `voice_agent_platform_v2.html`.
  - Campaign runner exists in `agent_runner.py`.
- **The Problem**: The "Live Talk" feature is currently unreliable (the agent doesn't "listen" or "speak" correctly in the browser). This is likely due to sample rate mismatches and jitter.

## 🎯 Your Immediate Tasks (The "Very Serious" Phase)

### Phase 9: Audio Reliability & Resampling
1. **Frontend Fix**: The browser `MediaRecorder` or `ScriptProcessor` needs to send **raw 16kHz PCM16 mono** bytes to the server. Implement a robust linear resampler in the dashboard (see `voice_agent_platform_v2.html`).
2. **Jitter Buffer**: Implement a scheduling queue for incoming TTS chunks (`audioCtx.currentTime` based) to ensure smooth playback without gaps.
3. **Verification**: Confirm Neha (the agent) responds with her charismatic voice when spoken to via the browser.

### Phase 10: High-Fidelity Telephony Demo
1. **Virtual Telephony**: Create a mocked "Purchase Number" flow in the Admin dashboard to show how clients would buy Indian phone numbers.
2. **Live Campaign Monitor**: When a campaign starts, the dashboard should show a **Live Tracker** with real-time transcript bubbles.
3. **Enhanced Runner**: Update `agent_runner.py` to use the real AI state machine (`StateManager`) to simulate human-agent interactions and update the `db/live_state.json` for the dashboard to poll.

## 🤖 Persona Definition (prompt.txt)
The agent is **Neha**, a warm and charismatic Real Estate Lead Qualifier. 
- Use contractions ("I'm", "You're").
- Never sound like a chatbot (avoid "Wonderful!", "I understand").
- One sentence per idea.

## 🚀 Setup on New Machine
1. `pip install -r requirements.txt`
2. Ensure `.env` has `GROQ_API_KEY`.
3. **Run Diagnostics**: Run `python verify_pipeline.py`. If it says "ALL SYSTEMS GO", we are ready.
4. Run `python server.py` and open `localhost:3000`.

**Note**: I have already implemented the robust audio bridge and monitoring logic. If the local machine has performance issues, the next AI should use `verify_pipeline.py` to check for network/CPU bottlenecks.
