import asyncio
import os
import sys
import unittest
from pathlib import Path


os.environ.setdefault("GROQ_API_KEY", "phase-zero-smoke-test-key")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from pipecat.frames.frames import StartFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from flows import runtime
from flows.runtime import (
    AgentTextFrame,
    RealEstateLLMProcessor,
    RealEstateSTTProcessor,
    RealEstateTTSProcessor,
    VoiceTurnState,
)
from llm.pipeline_logger import pipeline_logger


pipeline_logger.log_path = os.devnull


class PhaseZeroSmokeTest(unittest.TestCase):
    def test_pipeline_processors_initialize_without_error(self):
        turn_state = VoiceTurnState()
        pipeline = Pipeline(
            [
                RealEstateSTTProcessor(turn_state),
                RealEstateLLMProcessor(),
                RealEstateTTSProcessor(turn_state),
            ]
        )
        task = PipelineTask(pipeline)
        self.assertIsNotNone(task)

    def test_start_frame_triggers_agent_greeting_without_network(self):
        async def fake_generate_response(*args, **kwargs):
            return "Hello from smoke test."

        async def run_processor():
            original_generate_response = runtime.generate_response
            original_process_frame = FrameProcessor.process_frame
            runtime.generate_response = fake_generate_response
            pushed_frames = []

            try:
                async def noop_process_frame(self, frame, direction=None):
                    return None

                FrameProcessor.process_frame = noop_process_frame
                llm = RealEstateLLMProcessor()

                async def capture_frame(frame, direction=None):
                    pushed_frames.append(frame)

                llm.push_frame = capture_frame
                await llm.process_frame(StartFrame(), FrameDirection.DOWNSTREAM)
                return pushed_frames
            finally:
                FrameProcessor.process_frame = original_process_frame
                runtime.generate_response = original_generate_response

        pushed_frames = asyncio.run(run_processor())
        self.assertTrue(
            any(
                isinstance(frame, AgentTextFrame)
                and frame.text == "Hello from smoke test."
                for frame in pushed_frames
            )
        )


if __name__ == "__main__":
    unittest.main()
