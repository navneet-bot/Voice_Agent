# Real Estate AI Voice Agent Platform

A production-ready, modular AI voice agent platform designed for real estate sales. This project features a high-performance voice pipeline (Pipecat + Groq + Kokoro) with a premium web-based dashboard.

---

## 📂 Project Structure

The project is divided into two main components for better organization and deployment:

- **[`Frontend/`](./Frontend)**: A modern, responsive web dashboard for administrators and clients.
    - `index.html`: The main single-page application.
- **[`Backend/`](./Backend)**: The FastAPI server and AI processing modules.
    - `server.py`: Main entry point for API and WebSockets.
    - `llm/`, `stt/`, `tts/`: Core AI modules for language, speech-to-text, and text-to-speech.
    - `db/`: Local JSON-based database for agents, leads, and campaigns.
    - `flows/`: Conversation logic and state management.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg**: Required for audio processing.

### 2. Installation
1. Clone the repository and navigate to the project root.
2. Install the backend dependencies:
   ```bash
   cd Backend
   pip install -r requirements.txt
   ```

### 3. Configuration
Create a `.env` file in the `Backend/` directory:
```env
GROQ_API_KEY=your_groq_key_here
# Add optional keys if using external providers like ElevenLabs
# ELEVENLABS_API_KEY=your_11labs_key
```

### 4. Running the Platform
From the `Backend/` directory, start the server:
```bash
python server.py
```
The platform will be available at `http://localhost:3000`.

---

## 🏗 Architecture

| Component | Technology | Role |
|-----------|------------|------|
| **Frontend** | HTML5 / Vanilla JS / CSS3 | Dashboard and Live Voice Interface |
| **Backend** | FastAPI / Python | API and WebSocket Orchestration |
| **LLM** | Groq (Llama-3.1-8B) | Core logic and persona handling |
| **STT** | faster-whisper (Base) | High-speed speech-to-text |
| **TTS** | Kokoro-82M | Premium neural synthesis at 24kHz |
| **Pipeline** | Pipecat-AI | Streaming orchestration |

---

## ⚠️ Known Issues & Integration Troubleshooting

If you are experiencing issues with the AI Agent not speaking or responding on the frontend, please check the following:

### 1. Secure Context (HTTPS) Requirement
Modern browsers block microphone access (`getUserMedia`) on non-secure origins. 
- **Localhost**: Works fine over `http://localhost:3000`.
- **IP Address/Domain**: If accessing via an IP address (e.g., `http://192.168.x.x`) or a custom domain, you **MUST** use HTTPS. Otherwise, the "Connect" button will fail to access the mic.

### 2. Browser Autoplay Policy
Browsers will not play audio automatically. The dashboard requires a user gesture (clicking "Connect & Start Talking") to resume the `AudioContext`. If the agent seems silent, ensure you have clicked the connect button.

### 3. WebSocket Configuration
The frontend automatically tries to connect to the backend using `window.location.host`. 
- If your frontend is served from a different port or server than the backend, you may need to update `API_BASE_URL` and the `WebSocket` URL in `Frontend/index.html`.

### 4. First-Run Latency (Model Loading)
On the very first run, the system downloads the Whisper and Kokoro model weights (~200MB). During this time, the agent will not respond. Subsequent runs will be near-instant.

### 5. Port Availability
The platform defaults to port **3000**. Ensure this port is not being used by another service (like a local development server or another instance of the agent).

---

## 🛠 Deployment

For detailed deployment steps including Docker instructions, please refer to:
**[`deployment_steps.md`](./deployment_steps.md)**
