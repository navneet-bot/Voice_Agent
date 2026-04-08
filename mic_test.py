"""
Live Microphone Test for Agent Neha (Pipecat 0.0.108).
Speak into your computer's microphone and listen to Neha through your speakers.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

from flows.conversation import RealEstateSTTProcessor, RealEstateLLMProcessor, RealEstateTTSProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MIC-TEST")
load_dotenv()

async def main():
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY not found in .env file.")
        sys.exit(1)

    # 1. Initialize Local Audio Transport (PyAudio wrapper)
    # Print device info before starting
    import pyaudio
    pa = pyaudio.PyAudio()
    default_in = pa.get_default_input_device_info()
    default_out = pa.get_default_output_device_info()
    print(f"🎤 Using Input: {default_in['name']}")
    print(f"🔊 Using Output: {default_out['name']}")
    pa.terminate()

    # 1. Initialize Local Audio Transport (PyAudio wrapper)
    # Using explicit indices found from list_audio.py:
    # Index 5: Microphone Array (Realtek)
    # Index 3: Speakers (Realtek)
    print("🎤 Selecting Microphone (Index 5)...")
    print("🔊 Selecting Speakers (Index 3)...")
    
    transport = LocalAudioTransport(LocalAudioTransportParams(
        audio_in_sample_rate=16000,
        audio_out_sample_rate=24000,
        input_device_index=5,
        output_device_index=3
    ))

    # 2. Initialize our Real Estate Processors
    print("⏳ Loading AI Engines (Whisper + Kokoro)...")
    print("   - Initializing STT (Whisper)...")
    stt = RealEstateSTTProcessor()
    print("   - Initializing LLM (Groq)...")
    llm = RealEstateLLMProcessor()
    print("   - Initializing TTS (Kokoro)...")
    tts = RealEstateTTSProcessor()
    print("✅ AI Engines Ready.")


    # 3. Build the Pipeline
    pipeline = Pipeline([
        transport.input(), # Mic Input
        stt,
        llm,
        tts,
        transport.output()  # Speaker Output
    ])

    runner = PipelineRunner()
    task = PipelineTask(pipeline)

    print("\n" + "="*50)
    print("🚀 Pipeline starting...")
    print("Press Ctrl+C to stop.")
    print("="*50 + "\n")

    try:
        print("🟢 Running... (Neha should speak now)")
        await runner.run(task)



    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        logger.error(f"Error in Mic Test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
