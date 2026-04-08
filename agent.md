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
| **`stt/`** | `faster-whisper` | ✅ Implemented | Transcribes raw audio bytes to text. Optimized for CPU (`int8`). |
| **`tts/`** | `Kokoro-82M` | ✅ Implemented | Synthesizes text to audio bytes (24kHz Mono). Optimized for naturalness. |
| **`llm/`** | TBD | 🛠️ In Progress | Processes transcribed text and generates conversational responses. |
| **`telephony/`** | LiveKit / VoIP | 🛠️ In Progress | Handles the real-time audio transport layer (WebSockets/SIP). |
| **`flows/`** | Orchestration | 🛠️ In Progress | Manages the conversation state and logic flow. |

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **STT Engine**: `faster-whisper` (CTranslate2 backend)
- **TTS Engine**: `Kokoro-82M` (HuggingFace CPU-optimized)
- **Audio Format**: 16kHz STT input, 24kHz TTS output, Mono, PCM/WAV

## 📌 Coding Standards & Principles

### 1. Configuration-Driven Development
**NEVER** hardcode constants (model names, timeouts, sample rates, etc.) in the logic files.
- All STT-related constants must live in `stt/config.py`.

### 2. Byte-Stream Interfaces
Modules should accept and return raw audio bytes where possible. This ensures compatibility with streaming transports like LiveKit without requiring temporary file I/O.
- `stt.transcribe_audio(audio_bytes: bytes) -> str`

### 3. Performance First (CPU Optimization)
The agent is designed to run efficiently on CPUs without requiring high-end GPUs.
- Use `int8` quantization for Whisper.
- Keep inference time under **1 second** per chunk to maintain conversational flow.

### 4. Multilingual Support
The agent primarily targets **Hindi (hi)**, **Marathi (mr)**, and **English (en)**.
- Ensure all modules handle these language codes correctly.

## 🧪 Testing & Verification

Always use the provided test scripts to verify changes before integration:
- `test_tts.py`: Verify speech generation, multilingual handling, and naturalness.
- `test_stt.py`: Verify transcription accuracy and speed.
- `check_voice.py`: General audio utility check.

## 🤖 Instructions for AI Agents

- **Modifying STT**: If you add a feature, update the corresponding `config.py` with any new parameters.
- **Adding Modules**: Follow the established pattern: a directory containing `config.py` (constants) and one or more logic files (stateless functions).
- **Latency**: If a change increases latency significantly, flag it immediately. Real-time nature is non-negotiable.
- **Dependencies**: Add new requirements to `requirements.txt` immediately.
