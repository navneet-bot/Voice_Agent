"""Utilities for turning LLM text into stable, natural TTS input."""

import re

from tts.config import MAX_SENTENCES, MAX_TEXT_LENGTH


def optimize_for_tts(text: str) -> str:
    """Keep TTS input short, clean, and rhythmically stable."""
    if not text:
        return ""

    cleaned = text.strip()
    cleaned = cleaned.replace("\r", " ")
    cleaned = re.sub(r"[*_#`]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"([!?.,;:])\1+", r"\1", cleaned)
    cleaned = re.sub(r"\b(uh+|um+)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if not sentences:
        sentences = [cleaned]

    deduped_sentences: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        normalized = _normalize_sentence(sentence)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_sentences.append(sentence)
        if len(deduped_sentences) >= MAX_SENTENCES:
            break

    final_text = " ".join(deduped_sentences).strip()
    if len(final_text) > MAX_TEXT_LENGTH:
        truncated = final_text[:MAX_TEXT_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        final_text = truncated.rstrip()

    if final_text and final_text[-1] not in ".!?":
        final_text += "."

    return final_text


def _normalize_sentence(text: str) -> str:
    normalized = text.casefold()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
