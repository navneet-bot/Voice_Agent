# AI Voice Agent - Developer & Agent Context

This document provides essential context for AI agents and contributors working on the **Modular AI Voice Agent** project. Use this as a reference for architecture, design principles, and coding standards.

## 🚀 Project Overview

A high-performance, CPU-optimized modular voice agent pipeline designed for real-time conversation over telephony (VoIP/SIP) and WebSockets (LiveKit).

**The Pipeline Flow:**
`Audio Stream (Telephony)` → `Speech-to-Text (STT)` → `Large Language Model (LLM)` → `Text-to-Speech (TTS)` → `Audio Stream`

## 🏗️ Architecture & Modules

The project is strictly modular. Each component is isolated and communicates via clean, byte-oriented interfaces.

| Module | Technology | Status | Role |
| :--- | :--- | :--- | :--- |
| **`stt/`** | `faster-whisper` | ✅ Implemented | Transcribes raw audio bytes. Optimized for CPU (`int8`). |
| **`tts/`** | `Kokoro-82M` | ✅ Implemented | Synthesizes text to audio bytes (24kHz Mono). |
| **`llm/`** | Groq (`llama-3.1-8b`) | ✅ Implemented | Conversational logic (Neha Persona) in `llm/llm.py`. |
| **`telephony/`** | FastAPI WebSockets | ✅ Implemented | Scalable VoBiz bridge in `telephony/vobiz.py`. |
| **`flows/`** | `pipecat-ai` | ✅ Implemented | Orchestration in `flows/conversation.py`. |

## 🛠️ Tech Stack

- **Language**: Python 3.12+ (managed via `.venv`)
- **STT Engine**: `faster-whisper` (CTranslate2 backend)
- **TTS Engine**: `Kokoro-82M` (HuggingFace CPU-optimized)
- **Audio Format**: 16kHz STT input, 24kHz TTS output, Mono, PCM/WAV
- **Orchestration**: Pipecat + FastAPI

## 📌 Coding Standards & Principles

### 1. Configuration-Driven Development
All constants must live in their respective module's `config.py`. 
- Global AI Key: `.env` (GROQ_API_KEY)

### 2. Pipecat Orchestration
The system uses the `FrameProcessor` pattern. To add new logic, subclass `FrameProcessor` in `flows/conversation.py`.

### 3. Scalability (20+ Calls)
The FastAPI server spawns isolated Pipecat `PipelineTask` runners in separate `asyncio` loops. Ensure all I/O stays non-blocking. Use `asyncio.to_thread` for STT/TTS inference.

## 🤖 Instructions for next Agent/Teammate

1. **Local Test**: Run `python chat_test.py` to verify LLM charisma.
2. **Tunneling**: Run `ngrok http 8000`. If `ngrok` fails with a version error, use the absolute path or `localtunnel`.
3. **Server Start**: `python -m uvicorn telephony.vobiz:app --host 0.0.0.0 --port 8000`.
4. **Handoff**: Read `handoff_report.md` for full project status.
