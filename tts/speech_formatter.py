"""
Speech Formatter
================
This module transforms raw LLM output into speech-friendly text before Kokoro inference.
By adjusting spacing, punctuation, and sentence length, these transformations reduce robotic 
qualities, add conversational rhythm, and provide natural breathing room, significantly 
improving overall voice naturalness.
"""

import re
from tts.config import MAX_TEXT_LENGTH

def optimize_for_tts(text: str) -> str:
    """
    Format raw LLM output for TTS by handling spacing, repeated punctuation, breaking
    long comma chains and sentences, adding conversational pauses, and truncating.
    """
    if not text:
        return ""

    # 1. NORMALIZE WHITESPACE
    # Improve naturalness by ensuring clean and consistent spacing. Removes excessive gaps.
    text = text.strip()
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 2. REMOVE REPEATED PUNCTUATION
    # Prevent the TTS engine from over-emphasizing strings of punctuation
    text = re.sub(r'!{2,}', '!', text)
    text = re.sub(r'\?{2,}', '?', text)
    text = re.sub(r'\.\.\. \.\.\.', '...', text)
    text = re.sub(r',{2,}', ',', text)
    
    # 3. BREAK LONG COMMA CHAINS
    # Avoid breathless continuous lists by splitting them into short sentences.
    # Replaces commas with periods in sentences with 3 or more items to force pauses.
    def process_comma_chains(t: str) -> str:
        parts = re.split(r'([.!?]+)', t)
        processed_parts = []
        for i in range(0, len(parts), 2):
            sentence = parts[i]
            if sentence.count(',') >= 3:
                # Replace commas with periods to break up the chain
                sentence = sentence.replace(',', '.')
            processed_parts.append(sentence)
            if i + 1 < len(parts):
                processed_parts.append(parts[i+1])
        return "".join(processed_parts)
        
    text = process_comma_chains(text)
    
    # 4. SPLIT LONG SENTENCES
    # Break long compound sentences at conjunctions to keep sentences around 8-18 words,
    # improving conversational pacing.
    text = re.sub(r'(?i)(,\s*and\s+)', r'.\n', text)
    text = re.sub(r'(?i)(,\s*but\s+)', r'.\n', text)
    text = re.sub(r'(?i)(,\s*so\s+)', r'.\n', text)
    
    # Split on standard clause boundaries as well to help processing
    sentences_raw = re.split(r'([.!?]+|\n+)', text)
    sentences = []
    
    current_sentence = ""
    for i in range(0, len(sentences_raw), 2):
        chunk = sentences_raw[i].strip()
        punct = sentences_raw[i+1].strip() if i+1 < len(sentences_raw) else ""
        
        if not chunk and not punct:
            continue
            
        combined = chunk + (punct if punct else "")
        if combined.strip():
            sentences.append(combined.strip())

    # 5. ADD CONVERSATIONAL PAUSE MARKERS
    # Insert "..." to signal a natural breath after strong statements.
    # Insert "—" before contrasting clauses. Sparse usage (approx 1 per 3-4 sentences).
    # Since we broke 'but', we might not have contrasting clauses easily identifiable,
    # but we can add occasional pauses after exclamation marks or long assertions.
    for i, s in enumerate(sentences):
        if i % 3 == 0 and i > 0:
            if s.endswith('!'):
                sentences[i] = s.replace('!', '...')
            elif s.endswith('.') and len(s.split()) > 10:
                # Add a dash as a slight thought-pause inside long sentences if applicable
                word_idx = len(s.split()) // 2
                words = s.split()
                words[word_idx] = words[word_idx] + " —"
                sentences[i] = " ".join(words)
                
    # 6. PRESERVE HINGLISH AND DEVANAGARI
    # Text is purely manipulated via regex and string operations. Language scripts
    # (Latin, Devanagari) remain exactly as requested.

    # 7. TRUNCATE TO MAX LENGTH
    # Prevent extremely long text generation. Cut at word boundary.
    final_text = " ".join(sentences)
    if len(final_text) > MAX_TEXT_LENGTH:
        truncated = final_text[:MAX_TEXT_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        if not re.search(r'[.!?]$', truncated):
            truncated += "."
        final_text = truncated

    # 8. ENFORCE LINE STRUCTURE
    # Group sentences 1-2 per line and join with \n
    final_sentences = re.split(r'(?<=[.!?])\s+', final_text)
    final_lines = []
    for i in range(0, len(final_sentences), 2):
        pair = " ".join(f for f in final_sentences[i:i+2] if f)
        if pair.strip():
            final_lines.append(pair.strip())

    return "\n".join(final_lines)
