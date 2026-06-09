"""STT provider selection.

The runtime processor contract stays stable:
    transcribe_audio(audio_chunk: bytes) -> str

Providers are selected by feature flag and remain reversible by environment.
"""

from __future__ import annotations

import logging
import os
import json
import time
from difflib import SequenceMatcher
from pathlib import Path
import urllib.request

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "groq"
SUPPORTED_PROVIDERS = {"groq", "deepgram"}
_AGENT_CONFIG_CACHE: dict[str, tuple[float, str | None]] = {}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_provider(provider: str | None) -> str:
    normalized = (provider or DEFAULT_PROVIDER).strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        logger.warning("Unknown STT_PROVIDER=%s; falling back to %s", provider, DEFAULT_PROVIDER)
        return DEFAULT_PROVIDER
    return normalized


def _configured_provider(agent_id: str = "default") -> str:
    global_provider = _normalize_provider(os.getenv("STT_PROVIDER", DEFAULT_PROVIDER))
    if _env_bool("STT_DISABLE_AGENT_OVERRIDES", False):
        return global_provider

    schema_provider = _provider_from_agent_schema(agent_id)
    if schema_provider:
        return schema_provider

    deepgram_agent_ids = {
        item.strip()
        for item in os.getenv("DEEPGRAM_AGENT_IDS", "").split(",")
        if item.strip()
    }
    if agent_id and agent_id in deepgram_agent_ids:
        return "deepgram"
    return global_provider


def _provider_from_agent_schema(agent_id: str) -> str | None:
    if not agent_id or agent_id == "default":
        return None

    # Check cache (expire after 30s)
    cached = _AGENT_CONFIG_CACHE.get(agent_id)
    if cached and (time.time() - cached[0]) < 30.0:
        return cached[1]

    provider = None
    try:
        url = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000") + f"/api/agents/{agent_id}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2.0) as response:
            if response.status == 200:
                schema = json.loads(response.read().decode())
                provider_config = schema.get("provider_config") or {}
                provider_raw = provider_config.get("stt_provider") or schema.get("stt_provider")
                if provider_raw:
                    provider = _normalize_provider(provider_raw)
            else:
                raise RuntimeError(f"Backend API returned status {response.status}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logger.info("Agent %s not found in API, falling back to default STT provider.", agent_id)
            provider = None
        else:
            logger.error("API error for STT provider config agent_id=%s: %s", agent_id, exc)
            raise RuntimeError(f"Backend API error ({exc.code}) while fetching STT configuration.") from exc
    except urllib.error.URLError as exc:
        logger.error("Could not read STT provider config for agent_id=%s from API: %s", agent_id, exc)
        raise RuntimeError("Backend API must be running to fetch STT configuration.") from exc
    except Exception as exc:
        logger.error("Unexpected error fetching STT config: %s", exc)
        raise RuntimeError("Unexpected error fetching STT configuration from API.") from exc

    _AGENT_CONFIG_CACHE[agent_id] = (time.time(), provider)
    return provider


def _shadow_provider(primary_provider: str) -> str:
    configured = os.getenv("STT_SHADOW_PROVIDER")
    if configured:
        return _normalize_provider(configured)
    return "deepgram" if primary_provider == "groq" else "groq"


def _fallback_provider(primary_provider: str) -> str:
    configured = os.getenv("STT_FALLBACK_PROVIDER")
    if configured:
        return _normalize_provider(configured)
    return "deepgram" if primary_provider == "groq" else "groq"


def _provider_has_credentials(provider: str) -> bool:
    if provider == "deepgram":
        return bool(os.getenv("DEEPGRAM_API_KEY", "").strip())
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY", "").strip())
    return False


def _load_provider(provider: str):
    if provider == "deepgram":
        from .stt_deepgram import transcribe_audio as _deepgram

        return _deepgram
    from .stt_groq import transcribe_audio as _groq

    return _groq


def _similarity(primary_text: str, shadow_text: str) -> float:
    return SequenceMatcher(None, primary_text or "", shadow_text or "").ratio()


def _run_provider(provider: str, audio_chunk: bytes, language: str | None = None) -> tuple[str, float]:
    started_at = time.perf_counter()
    func = _load_provider(provider)
    try:
        text = func(audio_chunk, language=language)
    except TypeError:
        text = func(audio_chunk)
    return text, time.perf_counter() - started_at


def _run_fallback(primary_provider: str, audio_chunk: bytes, reason: str, language: str | None = None) -> str | None:
    if not _env_bool("STT_FALLBACK_ENABLED", True):
        return None

    fallback_provider = _fallback_provider(primary_provider)
    if fallback_provider == primary_provider:
        return None

    if not _provider_has_credentials(fallback_provider):
        logger.warning(
            "[STT PROVIDER] primary=%s %s; fallback=%s skipped because credentials are not configured",
            primary_provider,
            reason,
            fallback_provider,
        )
        return None

    try:
        try:
            fallback_text, fallback_latency = _run_provider(fallback_provider, audio_chunk, language=language)
        except TypeError:
            fallback_text, fallback_latency = _run_provider(fallback_provider, audio_chunk)
    except Exception as fallback_exc:
        logger.exception("[STT PROVIDER] fallback=%s failed after primary=%s %s: %s", fallback_provider, primary_provider, reason, fallback_exc)
        return None

    if fallback_text:
        logger.warning(
            "[STT PROVIDER] primary=%s %s; fallback=%s produced transcript in %.1fms",
            primary_provider,
            reason,
            fallback_provider,
            fallback_latency * 1000.0,
        )
    else:
        logger.warning(
            "[STT PROVIDER] primary=%s %s; fallback=%s also returned empty in %.1fms",
            primary_provider,
            reason,
            fallback_provider,
            fallback_latency * 1000.0,
        )
    return fallback_text


def transcribe_audio(audio_chunk: bytes, agent_id: str = "default", language: str | None = None) -> str:
    """Transcribe PCM16 mono 16kHz bytes with the selected provider."""
    primary_provider = _configured_provider(agent_id)

    try:
        try:
            primary_text, primary_latency = _run_provider(primary_provider, audio_chunk, language=language)
        except TypeError:
            primary_text, primary_latency = _run_provider(primary_provider, audio_chunk)
    except Exception as exc:
        logger.exception("[STT PROVIDER] primary=%s failed: %s", primary_provider, exc)
        fallback_text = _run_fallback(primary_provider, audio_chunk, "failed", language=language)
        return fallback_text or ""

    if not primary_text and _env_bool("STT_FALLBACK_ON_EMPTY", True):
        fallback_text = _run_fallback(primary_provider, audio_chunk, "returned empty", language=language)
        if fallback_text:
            return fallback_text

    if _env_bool("STT_SHADOW_MODE", False):
        shadow = _shadow_provider(primary_provider)
        if shadow != primary_provider:
            try:
                try:
                    shadow_text, shadow_latency = _run_provider(shadow, audio_chunk, language=language)
                except TypeError:
                    shadow_text, shadow_latency = _run_provider(shadow, audio_chunk)
                logger.info(
                    "[STT SHADOW] primary_provider=%s shadow_provider=%s "
                    "primary_ms=%.1f shadow_ms=%.1f similarity=%.3f primary=%r shadow=%r",
                    primary_provider,
                    shadow,
                    primary_latency * 1000.0,
                    shadow_latency * 1000.0,
                    _similarity(primary_text, shadow_text),
                    primary_text,
                    shadow_text,
                )
            except Exception as exc:
                logger.warning("[STT SHADOW] shadow_provider=%s failed without affecting live flow: %s", shadow, exc)

    return primary_text
