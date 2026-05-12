"""TTS provider selection.

The runtime contract stays stable:
    generate_speech_stream(text: str, preferred_language: str | None) -> Iterator[bytes]

Providers must yield raw PCM16 mono chunks at 24kHz.
"""

from __future__ import annotations

import logging
import os
import json
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "edge"
SUPPORTED_PROVIDERS = {"edge", "cartesia"}
_AGENT_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "db" / "agents"
_AGENT_CONFIG_CACHE: dict[str, tuple[float, str | None]] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_provider(provider: str | None) -> str:
    normalized = (provider or DEFAULT_PROVIDER).strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        logger.warning("Unknown TTS_PROVIDER=%s; falling back to %s", provider, DEFAULT_PROVIDER)
        return DEFAULT_PROVIDER
    return normalized


def _configured_provider(agent_id: str = "default") -> str:
    global_provider = _normalize_provider(os.getenv("TTS_PROVIDER", DEFAULT_PROVIDER))
    if _env_bool("TTS_DISABLE_AGENT_OVERRIDES", False):
        return global_provider

    schema_provider = _provider_from_agent_schema(agent_id)
    if schema_provider:
        return schema_provider

    cartesia_agent_ids = {
        item.strip()
        for item in os.getenv("CARTESIA_AGENT_IDS", "").split(",")
        if item.strip()
    }
    if agent_id and agent_id in cartesia_agent_ids:
        return "cartesia"
    return global_provider


def _provider_from_agent_schema(agent_id: str) -> str | None:
    if not agent_id or agent_id == "default":
        return None
    path = _AGENT_SCHEMA_DIR / f"{agent_id}.json"
    try:
        stat = path.stat()
    except OSError:
        return None

    cached = _AGENT_CONFIG_CACHE.get(agent_id)
    if cached and cached[0] == stat.st_mtime:
        return cached[1]

    provider = None
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        provider_config = schema.get("provider_config") or {}
        provider = provider_config.get("tts_provider") or schema.get("tts_provider")
        if provider:
            provider = _normalize_provider(provider)
    except Exception as exc:
        logger.warning("Could not read TTS provider config for agent_id=%s: %s", agent_id, exc)
        provider = None

    _AGENT_CONFIG_CACHE[agent_id] = (stat.st_mtime, provider)
    return provider


def _shadow_provider(primary_provider: str) -> str:
    configured = os.getenv("TTS_SHADOW_PROVIDER")
    if configured:
        return _normalize_provider(configured)
    return "cartesia" if primary_provider == "edge" else "edge"


def _load_provider(provider: str):
    if provider == "cartesia":
        from .tts_cartesia import generate_speech_stream as _cartesia

        return _cartesia
    from .tts_edge import generate_speech_stream as _edge

    return _edge


def _consume_shadow(provider: str, text: str, preferred_language: str | None) -> None:
    started_at = time.perf_counter()
    first_chunk_at = None
    chunks = 0
    bytes_out = 0
    try:
        for chunk in _load_provider(provider)(text, preferred_language):
            if not chunk:
                continue
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()
            chunks += 1
            bytes_out += len(chunk)
        total_s = time.perf_counter() - started_at
        ttfb_s = (first_chunk_at - started_at) if first_chunk_at is not None else total_s
        logger.info(
            "[TTS SHADOW] shadow_provider=%s ttfb_ms=%.1f total_ms=%.1f chunks=%d bytes=%d",
            provider,
            ttfb_s * 1000.0,
            total_s * 1000.0,
            chunks,
            bytes_out,
        )
    except Exception as exc:
        logger.warning("[TTS SHADOW] shadow_provider=%s failed without affecting live audio: %s", provider, exc)


def _stream_provider(provider: str, text: str, preferred_language: str | None):
    return _load_provider(provider)(text, preferred_language)


def generate_speech_stream(
    text: str,
    preferred_language: str | None = None,
    agent_id: str = "default",
):
    """Yield live TTS audio from the selected provider."""
    primary_provider = _configured_provider(agent_id)

    if _env_bool("TTS_SHADOW_MODE", False):
        shadow = _shadow_provider(primary_provider)
        if shadow != primary_provider:
            threading.Thread(
                target=_consume_shadow,
                args=(shadow, text, preferred_language),
                daemon=True,
            ).start()

    nonempty_yielded = False
    try:
        for chunk in _stream_provider(primary_provider, text, preferred_language):
            if chunk:
                nonempty_yielded = True
            yield chunk
    except Exception as exc:
        logger.exception("[TTS PROVIDER] primary=%s failed: %s", primary_provider, exc)

    if (
        not nonempty_yielded
        and primary_provider != DEFAULT_PROVIDER
        and _env_bool("TTS_FALLBACK_ENABLED", True)
        and text
        and text.strip()
    ):
        logger.warning(
            "[TTS PROVIDER] primary=%s produced no audio; falling back to %s",
            primary_provider,
            DEFAULT_PROVIDER,
        )
        try:
            for chunk in _stream_provider(DEFAULT_PROVIDER, text, preferred_language):
                yield chunk
        except Exception as fallback_exc:
            logger.exception("[TTS PROVIDER] fallback=%s failed: %s", DEFAULT_PROVIDER, fallback_exc)
            yield b""
