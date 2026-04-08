"""
LLM module — Groq API integration.

Public API:
    generate_response(user_text, conversation_history, language) -> str

This module is stateless. All conversational state is managed by the
flows/conversation.py orchestrator.
"""

import time
import logging
from typing import Optional

from groq import Groq, APIError, APITimeoutError, RateLimitError

import llm.config as cfg

logger = logging.getLogger(__name__)

# ── Singleton client (loaded once at import time) ──────────────────────────────
if not cfg.GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Run: $env:GROQ_API_KEY = 'your_key_here'  (PowerShell)\n"
        "Or:  export GROQ_API_KEY='your_key_here'  (Linux/Mac)"
    )

_client = Groq(api_key=cfg.GROQ_API_KEY, timeout=cfg.REQUEST_TIMEOUT_S)


def generate_response(
    user_text: str,
    conversation_history: Optional[list[dict]] = None,
    language: str = cfg.DEFAULT_LANGUAGE,
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
    messages = _build_messages(user_text, conversation_history or [], language)

    # Call Groq API with retry logic
    for attempt in range(1, cfg.MAX_RETRIES + 1):
        try:
            t0 = time.time()
            completion = _client.chat.completions.create(
                model=cfg.MODEL_NAME,
                messages=messages,
                temperature=cfg.TEMPERATURE,
                max_tokens=cfg.MAX_TOKENS,
                top_p=cfg.TOP_P,
            )
            latency = time.time() - t0
            response_text = completion.choices[0].message.content.strip()
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
            time.sleep(2 ** attempt)   # exponential backoff

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
) -> list[dict]:
    """Construct the full message list to send to the LLM."""
    system_prompt = _get_system_prompt(language)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


def _get_system_prompt(language: str) -> str:
    """
    Returns the system prompt for the AI voice agent.
    Reads from prompt.txt and appends language-specific instructions.
    """
    import os
    
    # Check for prompt.txt in the current working directory
    base_prompt = ""
    prompt_path = "prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            base_prompt = f.read().strip()
    else:
        # Fallback if prompt.txt is missing
        base_prompt = "You are a professional, friendly AI voice agent for real-estate outbound calls."

    lang_instructions = {
        "en": "Always respond in English.",
        "hi": "Always respond in Hindi (Devanagari script).",
        "mr": "Always respond in Marathi (Devanagari script).",
    }

    return f"{base_prompt}\n\n{lang_instructions.get(language, lang_instructions['en'])}"

