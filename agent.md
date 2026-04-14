# Cosmic Chameleon: AI Voice Agent Platform

This document serves as a master guide for setting up and understanding the AI Voice Agent SaaS platform on any machine.

## 🚀 Quick Start
1. **Requirements**: Install dependencies from the root directory.
   ```bash
   pip install -r requirements.txt
   ```
2. **Environment**: Create a `.env` file in the root with your API keys.
   ```env
   GROQ_API_KEY=your_key_here
   ```
3. **Launch Server**: Start the FastAPI backend.
   ```bash
   python server.py
   ```
4. **Access Dashboard**: Open `http://localhost:3000` in your browser.

## 🛠 Tech Stack
- **Orchestration**: Pipecat-AI (Pipeline-based audio processing)
- **STT**: Faster-Whisper (Local low-latency transcription)
- **LLM**: Groq (Llama-3-70b-8192 for reasoning)
- **TTS**: Edge-TTS (Charismatic `en-IN-NeerjaNeural` voice)
- **Backend**: FastAPI (Async API and WebSocket bridge)
- **Frontend**: Vanilla JS Dashboard (Premium SaaS UI with Live Monitoring)

## 📁 Key File Structure
- `server.py`: The heart of the platform. Handles APIs, WebSockets, and Campaign launches.
- `voice_agent_platform_v2.html`: High-fidelity dashboard for Admins and Clients.
- `agent_runner.py`: Executes automated campaigns with simulated telephony features.
- `llm/state_manager.py`: Manages conversation nodes, intents, and business logic.
- `flows/runtime.py`: Pipecat processors for the live audio bridge.
- `db/`: Persistence layer (JSON databases for agents, leads, and results).

## 🌟 Demo Features
- **Live Talk**: Direct browser-to-agent voice interaction via WebSocket.
- **Live Tracker**: Real-time transcription monitor for active campaigns.
- **Virtual Numbers**: Mocked number purchase flow for client demonstrations.
- **Auto-Sync**: Background processes for lead qualification and result persistence.

## 📝 Handover Notes
- **Audio Resampling**: The dashboard now includes a 16kHz resampler and jitter buffer for stable voice quality.
- **Git Sync**: Always `git pull` before starting work to stay synced with the latest SaaS enhancements.
