# ---------------------------------------------------------------------------
# Text-to-Speech (TTS) module
# This file exposes the public interface for speech synthesis.
#
# To swap TTS engines, change the import below to point at the new
# implementation file.  The rest of the pipeline depends only on the
# generate_speech(text: str) -> bytes signature.
# ---------------------------------------------------------------------------

from tts.tts_kokoro import generate_speech

__all__ = [
    "generate_speech",
]
