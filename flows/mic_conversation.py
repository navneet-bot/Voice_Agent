"""
Main conversation loop for the AI Voice Agent using local microphone and speakers.
Integration Note: Orchestrates STT, LLM, and TTS modules for real-time interaction.
"""

import sys
import os
import time
from time import perf_counter

# Ensure project root is in sys.path for module imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import local audio utilities
from audio.mic_utils import record_audio, play_audio, convert_to_wav_bytes

# CONFIGURATION BLOCK
INPUT_SAMPLE_RATE    = 16000    # Hz — microphone recording
OUTPUT_SAMPLE_RATE   = 24000    # Hz — Kokoro TTS output
RECORD_DURATION_S    = 4        # seconds per recording window
POST_RESPONSE_PAUSE_S = 0.2     # silence gap after AI speaks before next listen
MIN_TRANSCRIPTION_CHARS = 3     # ignore STT output shorter than this
VERBOSE              = True

def run_conversation():
    """
    Implements the core conversation loop: Listen -> STT -> LLM -> TTS -> Playback.
    Handles individual module imports and provides clean exit on Ctrl+C.
    """
    
    # STEP 1: Startup - Individual module imports with error handling
    try:
        from stt.stt import transcribe_audio
    except ImportError:
        print("[ERROR] Failed to import STT module (stt/stt.py)")
        sys.exit(1)

    try:
        from llm.llm import generate_response
    except ImportError:
        print("[ERROR] Failed to import LLM module (llm/llm.py)")
        sys.exit(1)

    try:
        from tts.tts_kokoro import generate_speech
    except ImportError:
        print("[ERROR] Failed to import TTS module (tts/tts_kokoro.py)")
        sys.exit(1)

    # Startup Header
    print("─────────────────────────────────")
    print(" AI Voice Agent — Mic Mode")
    print(" Press Ctrl+C to end conversation")
    print("─────────────────────────────────")

    conversation_history = []
    
    try:
        while True:
            try:
                # STEP 1 — Listen (Reduced to 3 seconds for lower latency)
                print("\nListening...")
                audio = record_audio(3.0, INPUT_SAMPLE_RATE)
                
                if audio.size == 0:
                    print("[WARN] Microphone returned no audio — retrying...")
                    continue

                # STEP 2 — STT
                t0 = perf_counter()
                wav_bytes = convert_to_wav_bytes(audio, INPUT_SAMPLE_RATE)
                text = transcribe_audio(wav_bytes)
                stt_time = perf_counter() - t0
                
                if not text or len(text.strip()) < 2:  # Reduced from 3 to 2
                    print("[WARN] No speech detected — listening again")
                    continue
                
                print(f"[USER] {text}")
                
                # Append user message to history
                conversation_history.append({"role": "user", "content": text})

                # STEP 3 — LLM (Now with history)
                t1 = perf_counter()
                response_text = generate_response(text, conversation_history)
                llm_time = perf_counter() - t1
                
                if not response_text:
                    print("[WARN] LLM returned empty response, continuing...")
                    continue
                    
                print(f"[AI]   {response_text}")
                
                # Append AI message to history
                conversation_history.append({"role": "assistant", "content": response_text})

                # STEP 4 — TTS
                t2 = perf_counter()
                audio_bytes = generate_speech(response_text)
                tts_time = perf_counter() - t2
                
                if not audio_bytes:
                    print("[ERROR] TTS failed — skipping playback")
                    continue
                
                if VERBOSE:
                    print(f"[TIME] STT: {stt_time:.2f}s  LLM: {llm_time:.2f}s  TTS: {tts_time:.2f}s")
                
                total_latency = stt_time + llm_time + tts_time
                print(f"[LATENCY] Total: {total_latency:.2f}s")

                # STEP 5 — Playback
                play_audio(audio_bytes, OUTPUT_SAMPLE_RATE)
                time.sleep(POST_RESPONSE_PAUSE_S)

            except Exception as e:
                print(f"[ERROR] {e}")
                continue

    except KeyboardInterrupt:
        print("\nConversation ended.")
        sys.exit(0)

if __name__ == "__main__":
    run_conversation()
