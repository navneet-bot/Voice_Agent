"""Passive dual-channel PCM session recorder.

This module records already-existing audio at source/sink boundaries. It does
not alter live audio frames, WebSocket payloads, STT chunks, or TTS chunks.
"""

from __future__ import annotations

import os
import re
import threading
import time
import wave
from math import gcd
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly


def recording_path_and_url(prefix: str, call_key: str, recordings_dir: str = "recordings") -> tuple[str, str]:
    safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", call_key or "call").strip("._")[:96] or "call"
    safe_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", prefix or "rec").strip("._") or "rec"
    Path(recordings_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{safe_prefix}_{safe_key}.wav"
    return os.path.join(recordings_dir, filename), f"/recordings/{filename}"


class SessionRecorder:
    """Record user and agent PCM into a timeline-aligned stereo WAV.

    Left channel is the user/customer. Right channel is the agent. Incoming
    chunks may be any PCM16 mono sample rate; they are resampled only for the
    saved WAV, never for the live runtime path.
    """

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = int(sample_rate or 24000)
        self._started_at = time.monotonic()
        self._tracks: dict[str, list[tuple[int, np.ndarray]]] = {
            "user": [],
            "agent": [],
        }
        self._lock = threading.Lock()

    def add_user_audio(self, pcm_data: bytes, sample_rate: int = 16000) -> None:
        self.add_audio("user", pcm_data, sample_rate)

    def add_agent_audio(self, pcm_data: bytes, sample_rate: int = 24000) -> None:
        self.add_audio("agent", pcm_data, sample_rate)

    def add_audio(self, speaker: str, pcm_data: bytes, sample_rate: int) -> None:
        if speaker not in self._tracks or not pcm_data:
            return

        samples = _pcm16_to_samples(pcm_data)
        if samples.size == 0:
            return

        source_rate = int(sample_rate or self.sample_rate)
        samples = _resample_samples(samples, source_rate, self.sample_rate)
        if samples.size == 0:
            return

        start_sample = max(0, int((time.monotonic() - self._started_at) * self.sample_rate))
        with self._lock:
            self._tracks[speaker].append((start_sample, samples))

    def finalize(self, filepath: str) -> float:
        with self._lock:
            tracks = {
                speaker: list(chunks)
                for speaker, chunks in self._tracks.items()
            }

        total_samples = 0
        for chunks in tracks.values():
            for start_sample, samples in chunks:
                total_samples = max(total_samples, start_sample + int(samples.size))

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        if total_samples <= 0:
            _write_stereo_wav(filepath, self.sample_rate, np.zeros((0, 2), dtype=np.int16))
            return 0.0

        user = np.zeros(total_samples, dtype=np.int16)
        agent = np.zeros(total_samples, dtype=np.int16)
        _overlay_track(user, tracks["user"])
        _overlay_track(agent, tracks["agent"])

        stereo = np.column_stack((user, agent)).astype(np.int16, copy=False)
        _write_stereo_wav(filepath, self.sample_rate, stereo)
        return total_samples / float(self.sample_rate)


def _pcm16_to_samples(pcm_data: bytes) -> np.ndarray:
    even_len = len(pcm_data) - (len(pcm_data) % 2)
    if even_len <= 0:
        return np.zeros(0, dtype=np.int16)
    return np.frombuffer(pcm_data[:even_len], dtype=np.int16).copy()


def _resample_samples(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate <= 0 or target_rate <= 0 or source_rate == target_rate:
        return samples
    rate_gcd = gcd(source_rate, target_rate)
    resampled = resample_poly(
        samples.astype(np.float32),
        target_rate // rate_gcd,
        source_rate // rate_gcd,
    )
    return np.clip(resampled, -32768, 32767).astype(np.int16)


def _overlay_track(target: np.ndarray, chunks: list[tuple[int, np.ndarray]]) -> None:
    for start_sample, samples in chunks:
        if start_sample >= target.size:
            continue
        end_sample = min(target.size, start_sample + samples.size)
        existing = target[start_sample:end_sample].astype(np.int32)
        incoming = samples[: end_sample - start_sample].astype(np.int32)
        target[start_sample:end_sample] = np.clip(existing + incoming, -32768, 32767).astype(np.int16)


def _write_stereo_wav(filepath: str, sample_rate: int, stereo: np.ndarray) -> None:
    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(stereo.tobytes())
