"""
Main conversation loop for the AI Voice Agent using local microphone and speakers.
Integration Note: Orchestrates STT, LLM, and TTS modules for real-time interaction.
"""

import sys
import os
import time
import asyncio
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
POST_RESPONSE_PAUSE_S = 1.0     # silence gap after AI speaks before next listen
MIN_TRANSCRIPTION_CHARS = 3     # ignore STT output shorter than this
VERBOSE              = True


def interruptible_play(speech_gen, start_time):
    """Plays audio from a generator while listening for barge-in interruptions."""
    import sounddevice as sd
    import numpy as np
    import threading
    from stt.config import ENERGY_THRESHOLD
    
    stream = sd.OutputStream(samplerate=OUTPUT_SAMPLE_RATE, channels=1, dtype='int16')
    stream.start()
    
    interrupted = [False]
    
    def check_interruption():
        time.sleep(0.4) # Guard period
        barrage_threshold = ENERGY_THRESHOLD * 5.0
        try:
            with sd.InputStream(samplerate=INPUT_SAMPLE_RATE, channels=1, dtype='float32') as in_stream:
                while not interrupted[0]:
                    chunk, _ = in_stream.read(512)
                    rms = np.sqrt(np.mean(chunk**2))
                    if rms > barrage_threshold:
                        chunk2, _ = in_stream.read(512)
                        rms2 = np.sqrt(np.mean(chunk2**2))
                        if rms2 > barrage_threshold:
                            interrupted[0] = True
                            break
        except Exception:
            pass

    try:
        first_chunk = True
        for pcm16 in speech_gen:
            if first_chunk:
                tts_time = perf_counter() - start_time
                if VERBOSE:
                    print(f" [TTFB: {tts_time:.2f}s]")
                threading.Thread(target=check_interruption, daemon=True).start()
                first_chunk = False

            if interrupted[0]:
                sd.stop() 
                print(" (INTERRUPTED - Flushing Echo...)")
                time.sleep(0.6)
                break
            if pcm16:
                stream.write(np.frombuffer(pcm16, dtype=np.int16))
    finally:
        interrupted[0] = True 
        stream.stop()
        stream.close()


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
        from tts.tts_edge import generate_speech_stream
    except ImportError:
        print("[ERROR] Failed to import TTS module (tts/tts_edge.py)")
        sys.exit(1)

    try:
        from llm.state_manager import StateManager
        state_manager = StateManager("Updated_Real_Estate_Agent.json")
    except ImportError:
        print("[ERROR] Failed to import state_manager")
        sys.exit(1)

    # Startup Header
    print("─────────────────────────────────")
    print(" AI Voice Agent — Mic Mode")
    print(" Press Ctrl+C to end conversation")
    print("─────────────────────────────────")

    conversation_history = []
    
    # Text buffers for multi-turn thought accumulation
    accumulated_text = ""
    
    try:
        # STEP 0: Initial Greeting (AI Speaks First)
        state_manager.reset_state()
        print("[AI] Initializing greeting...")
        start_time_tts = perf_counter()
        response_text = asyncio.run(generate_response(
            "[System: The call starting. Say a charismatic 'Hello, is this Prashant?' and wait. DO NOT transition yet.]", 
            conversation_history, 
            state_manager=state_manager
        ))
        if response_text:
            print(f"[AI]   {response_text}")
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Start TTS for greeting
            speech_gen = generate_speech_stream(response_text)
            if speech_gen:
                interruptible_play(speech_gen, start_time_tts)

        while True:
            try:
                # STEP 1 — Listen
                audio = record_audio(3.0, INPUT_SAMPLE_RATE)
                
                if audio.size == 0:
                    continue

                # STEP 2 — STT
                t0 = perf_counter()
                wav_bytes = convert_to_wav_bytes(audio, INPUT_SAMPLE_RATE)
                text = transcribe_audio(wav_bytes)
                stt_time = perf_counter() - t0
                
                if not text or len(text.strip()) < 1:
                    continue
                
                current_text = (accumulated_text + " " + text).strip()
                
                # Removed 'thought incomplete' arbitrary blockers.
                # All detected speech drops to LLM to evaluate State Rules directly.
                
                # Thought is complete
                final_text = current_text
                accumulated_text = "" # Reset buffer
                
                print(f"[USER] {final_text}")
                
                # Append to history
                conversation_history.append({"role": "user", "content": final_text})

                # STEP 3 — LLM
                t1 = perf_counter()
                response_text = asyncio.run(generate_response(final_text, conversation_history, state_manager=state_manager))
                llm_time = perf_counter() - t1
                
                if not response_text:
                    continue
                    
                print(f"[AI]   {response_text}")
                conversation_history.append({"role": "assistant", "content": response_text})

                # STEP 4 — TTS
                t2 = perf_counter()
                speech_gen = generate_speech_stream(response_text)
                
                if speech_gen:
                    interruptible_play(speech_gen, t2)
                    time.sleep(POST_RESPONSE_PAUSE_S)

            except Exception as e:
                print(f"[ERROR] {e}")
                continue

    except KeyboardInterrupt:
        print("\nConversation ended.")
        sys.exit(0)

if __name__ == "__main__":
    run_conversation()
