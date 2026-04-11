"""
LLM module — Groq API integration.

Public API:
    generate_response(user_text, conversation_history, language) -> str

This module is stateless. All conversational state is managed by the
flows/conversation.py orchestrator.
"""

import asyncio
import logging
import os
import re
import time
from typing import Optional, Any

from groq import AsyncGroq, APIError, APITimeoutError, RateLimitError

import llm.config as cfg
from llm.language_utils import get_language_instruction

logger = logging.getLogger(__name__)

# ── Singleton client (loaded once at import time) ──────────────────────────────
if not cfg.GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Run: $env:GROQ_API_KEY = 'your_key_here'  (PowerShell)\n"
        "Or:  export GROQ_API_KEY='your_key_here'  (Linux/Mac)"
    )

_client = AsyncGroq(api_key=cfg.GROQ_API_KEY, timeout=cfg.REQUEST_TIMEOUT_S)
_prompt_cache: Optional[str] = None


async def generate_response(
    user_text: str,
    conversation_history: Optional[list[dict]] = None,
    language: str = cfg.DEFAULT_LANGUAGE,
    state_manager: Optional[Any] = None,
    allow_transition: bool = True,
) -> str:
    """
    Generate a conversational response from the LLM.

    Args:
        user_text:             The transcribed text from the STT module.
        conversation_history:  List of prior {"role": ..., "content": ...} dicts.
                               Pass None or [] to start a fresh conversation.
        language:              Language code — "en", "hi", or "mr".

    Returns:
        The assistant's response as a plain string.
        Returns "" on unrecoverable error (caller should handle gracefully).
    """
    if not user_text or not user_text.strip():
        logger.debug("generate_response called with empty text — skipping.")
        return ""

    if language not in cfg.SUPPORTED_LANGUAGES:
        logger.warning("Unsupported language '%s', falling back to 'en'.", language)
        language = cfg.DEFAULT_LANGUAGE

    # Build the message list: system prompt + history + new user message
    messages = _build_messages(
        user_text,
        conversation_history or [],
        language,
        state_manager,
        allow_transition=allow_transition,
    )

    # Call Groq API with retry logic
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            t0 = time.time()
            completion = await _client.chat.completions.create(
                model=cfg.MODEL_NAME,
                messages=messages,
                temperature=cfg.TEMPERATURE,
                max_tokens=cfg.MAX_TOKENS,
                top_p=cfg.TOP_P,
                response_format={"type": "json_object"}
            )
            latency = time.time() - t0
            raw_content = completion.choices[0].message.content or "{}"
            
            # Parse state transitions from JSON
            clean_content = ""
            try:
                import json
                data = json.loads(raw_content)
                edge_id = data.get("transition_edge_id")
                
                if allow_transition and state_manager and edge_id and str(edge_id).lower() != "null":
                    state_manager.transition_to(edge_id)
                    
                clean_content = data.get("response_text", "")
            except Exception as e:
                logger.error("JSON parsing failed, falling back to raw output. Error: %s", e)
                clean_content = raw_content
            
            response_text = _postprocess_response(
                clean_content,
                history=conversation_history or [],
            )
            logger.info(
                "LLM response generated in %.3fs (attempt %d/%d)",
                latency, attempt, cfg.MAX_RETRIES,
            )
            if latency > 1.0:
                logger.warning(
                    "⚠️  LLM latency %.3fs exceeded 1.0s target.", latency
                )
            return response_text

        except RateLimitError:
            logger.error("Groq rate limit hit on attempt %d.", attempt)
            await asyncio.sleep(2 ** attempt)   # exponential backoff

        except APITimeoutError:
            logger.error("Groq request timed out on attempt %d.", attempt)
            if attempt == cfg.MAX_RETRIES:
                return ""

        except APIError as e:
            logger.error("Groq API error on attempt %d: %s", attempt, e)
            return ""

    return ""


def _build_messages(
    user_text: str,
    history: list[dict],
    language: str,
    state_manager: Optional[Any] = None,
    allow_transition: bool = True,
) -> list[dict]:
    """Construct the full message list to send to the LLM."""
    if state_manager:
        system_prompt = state_manager.get_system_prompt(
            language=language,
            allow_transition=allow_transition,
        )
    else:
        system_prompt = _get_system_prompt(language)
        
    messages = [{"role": "system", "content": system_prompt}]
    if cfg.MAX_HISTORY_MESSAGES > 0:
        history = history[-cfg.MAX_HISTORY_MESSAGES:]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def _get_system_prompt(language: str) -> str:
    """
    Returns the system prompt for the AI voice agent.
    Reads from prompt.txt and appends language-specific instructions.
    """
    global _prompt_cache

    if _prompt_cache is None:
        prompt_path = "prompt.txt"
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                _prompt_cache = f.read().strip()
        else:
            _prompt_cache = "You are a professional, friendly AI voice agent for real-estate outbound calls."

    call_style = (
        "Keep every reply crisp for a live phone call: 1 or 2 short sentences, one question at a time, "
        "no bullet points, no repetition, and no restating the same sentence in different words. "
        "Keep a warm, steady, confident pace."
    )

    return f"{_prompt_cache}\n\n{get_language_instruction(language)}\n{call_style}"


def _postprocess_response(raw_text: str, history: list[dict]) -> str:
    """Normalize LLM output for short, non-repetitive voice responses."""
    text = re.sub(r"\s+", " ", raw_text or "").strip()
    if not text:
        return ""

    text = re.sub(r"[*_#`]+", "", text)
    text = re.sub(r"\b(um+|uh+)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()

    sentences = _split_sentences(text)
    deduped_sentences: list[str] = []
    seen_normalized: set[str] = set()
    for sentence in sentences:
        normalized = _normalize_text(sentence)
        if not normalized or normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        deduped_sentences.append(sentence.strip())
        if len(deduped_sentences) >= cfg.MAX_RESPONSE_SENTENCES:
            break

    if not deduped_sentences:
        deduped_sentences = [text]

    response = " ".join(deduped_sentences).strip()
    words = response.split()
    if len(words) > cfg.MAX_RESPONSE_WORDS:
        response = " ".join(words[:cfg.MAX_RESPONSE_WORDS]).rstrip(",;:- ")
        if response and response[-1] not in ".!?":
            response += "."

    previous_assistant = next(
        (msg.get("content", "") for msg in reversed(history) if msg.get("role") == "assistant"),
        "",
    )
    if previous_assistant and _normalize_text(response) == _normalize_text(previous_assistant):
        logger.warning("LLM repeated the previous assistant turn; suppressing duplicate reply.")
        return ""

    return response


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if part and part.strip()]


def _normalize_text(text: str) -> str:
    lowered = text.casefold()
    lowered = re.sub(r"[^\w\s]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered
