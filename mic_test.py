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
    # We use 16kHz for input and 24kHz for output (STT/TTS engines)
    transport = LocalAudioTransport(LocalAudioTransportParams(
        audio_in_sample_rate=16000,
        audio_out_sample_rate=24000
    ))

    # 2. Initialize our Real Estate Processors
    stt = RealEstateSTTProcessor()
    llm = RealEstateLLMProcessor()
    tts = RealEstateTTSProcessor()

    # 3. Build the Pipeline
    # Mic Input -> STT -> LLM -> TTS -> Speaker Output
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
    print("🎤 Neha is listening! Start speaking now...")
    print("Press Ctrl+C to stop.")
    print("="*50 + "\n")

    try:
        await runner.run(task)
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        logger.error(f"Error in Mic Test: {e}")

if __name__ == "__main__":
    asyncio.run(main())
