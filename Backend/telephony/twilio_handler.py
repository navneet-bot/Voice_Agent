"""
Twilio Telephony Handler — Production Outbound Call Integration.

Handles:
  - Twilio Media Streams (bidirectional audio WebSocket)
  - TwiML webhook endpoint
  - Inbound μ-law 8kHz audio → Pipecat pipeline → 8kHz PCM back to Twilio
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from scipy.signal import resample_poly

from pipecat.frames.frames import AudioRawFrame, EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger("telephony.twilio")


class TwilioSource(FrameProcessor):
    """Queues audio frames from the Twilio WebSocket into the Pipecat pipeline."""

    def __init__(self):
        super().__init__()
        self._queue: asyncio.Queue = asyncio.Queue()

    async def process_frame(self, frame, direction):
        await self.push_frame(frame, direction)

    def queue_audio(self, pcm16_bytes: bytes, sample_rate: int = 8000) -> None:
        frame = AudioRawFrame(audio=pcm16_bytes, sample_rate=sample_rate, num_channels=1)
        self._queue.put_nowait(frame)

    async def run_queue_loop(self):
        """Must be run as a task alongside the Pipecat runner."""
        while True:
            frame = await self._queue.get()
            await self.push_frame(frame, FrameDirection.DOWNSTREAM)
            self._queue.task_done()


class TwilioSink(FrameProcessor):
    """Encodes Pipecat TTS audio as base64 μ-law and sends it back to Twilio."""

    def __init__(self, websocket: WebSocket, call_id: str = "", ws_manager=None):
        super().__init__()
        self.ws = websocket
        self.call_id = call_id
        self.ws_manager = ws_manager

    async def process_frame(self, frame, direction):
        if isinstance(frame, AudioRawFrame):
            # Resample to 8kHz μ-law for Twilio
            pcm8 = _resample_pcm16(frame.audio, frame.sample_rate, 8000)
            ulaw = _pcm16_to_ulaw(pcm8)
            payload = base64.b64encode(ulaw).decode("utf-8")
            msg = json.dumps({
                "event": "media",
                "streamSid": self.call_id,
                "media": {"payload": payload},
            })
            try:
                await self.ws.send_text(msg)
            except Exception as e:
                logger.error("[TWILIO SINK] Send error: %s", e)
        await self.push_frame(frame, direction)


async def handle_twilio_stream(
    websocket: WebSocket,
    call_id: str,
    agent_schema_path: str,
    ws_manager=None,
    campaign_id: str = "",
    lead_id: str = "",
):
    """
    Main Twilio Media Streams WebSocket handler.
    Called for each active call — creates an isolated Pipecat pipeline.
    """
    await websocket.accept()
    logger.info("[TWILIO] Stream connected — call_id=%s", call_id)

    from flows.runtime import RealEstateSTTProcessor, RealEstateLLMProcessor, RealEstateTTSProcessor
    from llm.state_manager import StateManager

    source = TwilioSource()
    stt = RealEstateSTTProcessor()
    llm = RealEstateLLMProcessor()

    # Load agent schema FRESH from disk on every call (auto-reload)
    if os.path.exists(agent_schema_path):
        llm.state_manager = StateManager(agent_schema_path)
    
    tts = RealEstateTTSProcessor()
    sink = TwilioSink(websocket, call_id=call_id, ws_manager=ws_manager)

    pipeline = Pipeline([source, stt, llm, tts, sink])
    runner = PipelineRunner()
    task = PipelineTask(pipeline)
    runner_task = asyncio.create_task(runner.run(task))
    queue_task = asyncio.create_task(source.run_queue_loop())

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "connected":
                logger.info("[TWILIO] Media stream connected")

            elif event == "start":
                stream_sid = msg.get("start", {}).get("streamSid", "")
                logger.info("[TWILIO] Stream started: %s", stream_sid)

            elif event == "media":
                payload = msg["media"]["payload"]
                ulaw_bytes = base64.b64decode(payload)
                # Convert μ-law to PCM16
                pcm16 = _ulaw_to_pcm16(ulaw_bytes)
                source.queue_audio(pcm16, sample_rate=8000)

            elif event == "stop":
                logger.info("[TWILIO] Stream stop received")
                break

    except WebSocketDisconnect:
        logger.info("[TWILIO] WebSocket disconnected — call_id=%s", call_id)
    except Exception as e:
        logger.error("[TWILIO] Stream error: %s", e)
    finally:
        queue_task.cancel()
        try:
            await source.push_frame(EndFrame(), FrameDirection.DOWNSTREAM)
            await asyncio.sleep(0.3)
            runner_task.cancel()
            await runner_task
        except (asyncio.CancelledError, Exception):
            pass
        logger.info("[TWILIO] Pipeline cleanup complete — call_id=%s", call_id)


def build_twiml(stream_url: str) -> str:
    """
    Returns TwiML XML that connects Twilio to our Media Stream WebSocket.
    Called by the /telephony/twiml/{call_id} webhook.
    """
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{stream_url}">
      <Parameter name="encoding" value="audio/x-mulaw"/>
    </Stream>
  </Connect>
</Response>"""


# ── Audio Codec Helpers ───────────────────────────────────────────────────────

def _resample_pcm16(audio: bytes, source_rate: int, target_rate: int) -> bytes:
    if not audio:
        return audio
    samples = np.frombuffer(audio, dtype=np.int16)
    if source_rate == target_rate or samples.size == 0:
        return audio
    gcd = np.gcd(source_rate, target_rate)
    resampled = resample_poly(samples.astype(np.float32), target_rate // gcd, source_rate // gcd)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


# μ-law lookup tables (standard G.711)
_ULAW_BIAS = 0x84
_ULAW_CLIP = 32635

_ENCODE_TABLE = bytes([
    0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
])


def _pcm16_to_ulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit PCM to 8-bit μ-law."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    out = bytearray(len(samples))
    for i, sample in enumerate(samples):
        sign = 0 if sample >= 0 else 0x80
        if sign:
            sample = -sample
        sample = min(sample, _ULAW_CLIP)
        sample += _ULAW_BIAS
        exp = _ENCODE_TABLE[sample >> 7]
        mantissa = (sample >> (exp + 3)) & 0x0F
        out[i] = ~(sign | (exp << 4) | mantissa) & 0xFF
    return bytes(out)


def _ulaw_to_pcm16(ulaw_bytes: bytes) -> bytes:
    """Convert 8-bit μ-law to 16-bit PCM."""
    out = bytearray(len(ulaw_bytes) * 2)
    for i, byte in enumerate(ulaw_bytes):
        byte = ~byte & 0xFF
        sign   = byte & 0x80
        exp    = (byte >> 4) & 0x07
        mant   = byte & 0x0F
        sample = (mant << (exp + 3)) + (0x21 << exp) - 33
        if sign:
            sample = -sample
        packed = max(-32768, min(32767, sample))
        out[i * 2]     = packed & 0xFF
        out[i * 2 + 1] = (packed >> 8) & 0xFF
    return bytes(out)
