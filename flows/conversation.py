"""
Conversation Handler orchestrated via Pipecat.

This module bridges our custom, highly-optimized CPU STT and LLM implementations
into the standard Pipecat asynchronous pipeline.

Flow: Audio -> STT -> LLM -> TTS -> Audio
"""

import asyncio
import logging

try:
    from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
    from pipecat.frames.frames import Frame, TextFrame, AudioRawFrame, StartFrame
except ImportError:
    logging.error("pipecat-ai is not installed. Pipeline will fail.")
    FrameProcessor = object
    FrameDirection = None
    Frame = None
    TextFrame = None
    AudioRawFrame = None

from llm.llm import generate_response

# We attempt to import stt, if available.
try:
    from stt.stt import transcribe_audio
except ImportError:
    logging.warning("stt.stt.transcribe_audio not available yet. Using mock STT.")
    def transcribe_audio(audio_chunk: bytes) -> str:
        return "mock transcription"


class RealEstateLLMProcessor(FrameProcessor):
    """
    Wraps our custom llm.py logic (Groq API, prompt.txt, latency checks)
    into a Pipecat async FrameProcessor.
    """
    def __init__(self):
        super().__init__()
        self.history = []

    async def process_frame(self, frame: Frame, direction: FrameDirection = None): # type: ignore
        if isinstance(frame, TextFrame):
            user_text = frame.text.strip()
            if not user_text:
                return
            
            logging.info(f"LLM received text: {user_text}")

            # Offload synchronous generate_response to a background thread
            reply = await asyncio.to_thread(
                generate_response, 
                user_text, 
                self.history, 
                "en"
            )

            # Store the interaction to maintain context
            if reply:
                self.history.append({"role": "user", "content": user_text})
            # Store the interaction to maintain context
            if reply:
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": reply})
                
                # Push the LLM's text response further down the pipeline (to TTS)
                await self.push_frame(TextFrame(reply), direction)
        elif isinstance(frame, StartFrame):
            # Greeting: Neha speaks first when the pipeline starts
            greeting = "Hi! This is Neha from the real estate team. Can you hear me?"
            self.history.append({"role": "assistant", "content": greeting})
            await self.push_frame(TextFrame(greeting), direction)
            await super().process_frame(frame, direction)
        else:
            await super().process_frame(frame, direction)


class RealEstateSTTProcessor(FrameProcessor):
    """
    Wraps our customized faster-whisper CPU STT logic into Pipecat.
    Buffers incoming PCM16 audio frames until ~1 second is reached, then transcribes.
    """
    def __init__(self):
        super().__init__()
        self.audio_buffer = bytearray()
        
        # 16000 Hz * 2 bytes (PCM16) * 1.0 second = 32000 bytes
        self.buffer_threshold = 32000 

    async def process_frame(self, frame: Frame, direction: FrameDirection = None): # type: ignore
        if isinstance(frame, AudioRawFrame):
            self.audio_buffer.extend(frame.audio)
            
            # Simple chunking: if we hit 1 second of audio, run STT
            # (Note: In production pipelines, Silero VAD frames trigger the flush)
            if len(self.audio_buffer) >= self.buffer_threshold:
                chunk = bytes(self.audio_buffer)
                self.audio_buffer.clear()
                
                # Offload synchronous Whisper transcription to background thread
                text = await asyncio.to_thread(transcribe_audio, chunk)
                
                if text and text.strip():
                    # Push the transcribed word to the LLM
                    await self.push_frame(TextFrame(text), direction)
        else:
            await super().process_frame(frame, direction)


try:
    from tts import generate_speech
except ImportError:
    logging.warning("tts engine not found. Using mock TTS.")
    def generate_speech(text: str) -> bytes:
        return b"" # Mock empty wav frame

class RealEstateTTSProcessor(FrameProcessor):
    """
    Synthesizes TTS audio from LLM TextFrames using our Kokoro integration.
    """
    def __init__(self):
        super().__init__()

    async def process_frame(self, frame: Frame, direction: FrameDirection = None): # type: ignore
        if isinstance(frame, TextFrame):
            logging.info(f"TTS Synthesizing for: {frame.text}")
            audio_bytes = await asyncio.to_thread(generate_speech, frame.text)
            if audio_bytes:
                # Assuming 24000 sample rate for Kokoro, 1 channel
                await self.push_frame(AudioRawFrame(audio=audio_bytes, sample_rate=24000, num_channels=1), direction)
        else:
            await super().process_frame(frame, direction)


