# Real Estate AI Voice Agent (Neha)

A production-ready, modular AI voice agent designed for outbound real estate sales. Neha is charismatic, warm, and highly efficient, running locally with low-latency modules.

---

## 🚀 Quick Start

To start a real-time conversation using your computer's microphone and speakers:

```powershell
# 1. Ensure you have your GROQ_API_KEY set in .env
# 2. Run the mic loop
python flows/mic_conversation.py
```

---

## ✨ Features

- **⚡ Real-Time Responsiveness**: Optimized pipeline (Early-stop STT + Groq + Kokoro) with a target latency of < 2 seconds.
- **🧠 Persistent Memory**: Remembers conversation history across turns to provide natural continuity.
- **🎭 JSON-Aligned Persona**: Neha follows the exact conversation flow and objection handling scripts defined in `Updated_Real_Estate_Agent.json`.
- **🎙️ Smart Activation**: Energy-based silence detection automatically stops recording once you finish speaking.
- **🇮🇳 Multilingual Support**: Seamlessly handles English, Hindi, and Hinglish.

---

## 🏗 Architecture

| Component | Technology | Role |
|-----------|------------|------|
| **LLM**   | Groq (Llama-3.1-8B) | Core logic and persona. |
| **STT**   | faster-whisper (Base) | High-speed, int8 quantized speech-to-text. |
| **TTS**   | Kokoro-82M | Premium neural text-to-speech at 24kHz. |
| **Orchestration** | Python / SoundDevice | Real-time audio I/O and state management. |

---

## ⚙️ Configuration

Tunable parameters are centralized in `config.py` files within each module:

- **LLM (`llm/config.py`)**: Tone, max tokens, history length.
- **STT (`stt/config.py`)**: Model size (`tiny`->`small`), energy threshold, VAD filters.
- **TTS (`tts/config.py`)**: Speech speed (e.g., 1.15), inter-sentence pause.

---

## 📂 Project Structure

```text
voice-agent/
├── flows/           # High-level conversation loops (Mic, WebSocket)
├── audio/           # SoundDevice and buffer management utilities
├── llm/             # Groq integration and prompt management
├── stt/             # faster-whisper configuration and wrapper
├── tts/             # Kokoro synthesis engine and text formatting
├── prompt.txt       # Neha's primary system instruction
└── README.md        # You are here
```

---

## 🛠 Setup

### 1. Requirements
- Python 3.11+
- FFmpeg (for audio processing)
- `pip install -r requirements.txt`

### 2. Environment
Create a `.env` file in the root:
```env
GROQ_API_KEY=your_key_here
```

### 3. Audio Assets
Model weights and voice packs are automatically downloaded on first run. To use pre-downloaded Kokoro voices, set `KOKORO_VOICE_DIR` in your environment.
