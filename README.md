# Real Estate AI Voice Agent Platform

A production-ready, modular AI voice agent platform designed for real estate sales. This project features a high-performance voice pipeline (Pipecat + Groq + Kokoro) with a premium web-based dashboard.

---

## 📂 Project Structure

The project is divided into two main components for better organization and deployment:

- **[`Frontend/`](./Frontend)**: A modern, responsive web dashboard for administrators and clients.
- **[`Backend/`](./Backend)**: The FastAPI server and AI processing modules.
- **[`DEVELOPMENT_GUIDE.md`](./DEVELOPMENT_GUIDE.md)**: **CRITICAL** guide for fine-tuning agents, deployment, and conflict avoidance.

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
ELEVENLABS_API_KEY=your_11labs_key # Optional for premium voice
PLATFORM_API_KEY=your_secure_password # For platform security
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
| **TTS** | Kokoro / ElevenLabs | Premium neural synthesis |
| **Pipeline** | Pipecat-AI | Streaming orchestration |

---

## 🔧 Maintenance & Fine-Tuning
For detailed instructions on how to improve the agent, update prompts, and push changes to production without conflicts, please refer to the:
👉 **[Development & Fine-Tuning Guide](./DEVELOPMENT_GUIDE.md)**

---

## ⚠️ Known Issues & Integration Troubleshooting

### 1. Secure Context (HTTPS) Requirement
Modern browsers block microphone access (`getUserMedia`) on non-secure origins. 
- **Localhost**: Works fine over `http://localhost:3000`.
- **Remote Prod**: You **MUST** use HTTPS.

### 2. Browser Autoplay Policy
Browsers will not play audio automatically. The dashboard requires a user gesture (clicking "Start Demo Call") to resume the `AudioContext`.

### 3. First-Run Latency
On the first run, the system downloads weights (~200MB). Subsequent runs are instant.

---

## 🛠 Deployment
For production deployment steps:
**[`deployment_steps.md`](./deployment_steps.md)**
