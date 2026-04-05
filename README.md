# AI Voice Agent

Modular, CPU-optimised voice agent pipeline: telephony to STT to LLM to TTS.

---

## Project Structure

```
voice-agent/
├── flows/        # Conversation flow orchestration (future)
├── llm/          # LLM integration for response generation (future)
├── stt/          # Speech-to-Text — faster-whisper, implemented
│   ├── config.py # All tunable constants (model size, beam, VAD, etc.)
│   └── stt.py    # transcribe_audio(bytes) -> str
├── telephony/    # Telephony/WebSocket transport layer (future)
├── tts/          # Text-to-Speech synthesis (future)
├── requirements.txt
└── README.md
```

---

## STT Module

| Item            | Detail                                              |
|-----------------|-----------------------------------------------------|
| **Input**       | Raw audio bytes - 16 kHz, mono, PCM16 or float32    |
| **Output**      | Plain transcribed string (or `""` for silence)       |
| **Languages**   | Auto-detected - Hindi, Marathi, English supported    |
| **Engine**      | faster-whisper (CTranslate2 backend)                 |
| **Model**       | `small` with `int8` quantisation                     |
| **Latency**     | 0.3-0.8 s per 1-3 s audio chunk on CPU              |

### Public API

```python
from stt import transcribe_audio

text = transcribe_audio(audio_bytes)
```

---

## Setup

### 1. System dependencies

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

### 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The faster-whisper model weights are downloaded automatically on first import (cached in `~/.cache/huggingface`).

---

## Configuration

All constants live in `stt/config.py`. Edit that file to tune behaviour - no code changes elsewhere are needed.

| Constant         | Default   | Notes                                          |
|------------------|-----------|------------------------------------------------|
| `MODEL_SIZE`     | `"small"` | `tiny`, `base`, `small`, `medium`              |
| `COMPUTE_TYPE`   | `"int8"`  | `int8` for CPU; `float16` for GPU              |
| `BEAM_SIZE`      | `1`       | 1 = greedy (fastest); higher = more accurate   |
| `DEVICE`         | `"cpu"`   | `"cpu"` or `"cuda"`                            |
| `LANGUAGE`       | `None`    | `None` = auto-detect; or `"hi"`, `"mr"`, `"en"`|
| `VAD_FILTER`     | `True`    | Silero VAD to skip silent frames               |
| `MIN_SILENCE_MS` | `300`     | Minimum silence duration threshold (ms)        |

---

## Integration

### Connecting to the LLM module

```python
from stt import transcribe_audio

# Inside your conversation loop:
user_text = transcribe_audio(audio_chunk)
if user_text:
    llm_response = llm.generate(user_text)   # future llm module
    audio_out = tts.synthesise(llm_response)  # future tts module
```

### LiveKit / VoBiz streaming

The `transcribe_audio()` function accepts raw bytes, making it directly
compatible with frame-based streaming transports:

1. Receive audio frames from LiveKit / VoBiz WebSocket.
2. Buffer 1-3 seconds of frames (16 kHz, mono, PCM16).
3. Call `transcribe_audio(buffer)` and forward the text downstream.

No file I/O or microphone code is involved - the bytes interface is kept
clean for real-time pipeline integration.
