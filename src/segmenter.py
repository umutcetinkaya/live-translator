"""Sentence segmentation for incremental translation.

Time-based chunking cut mid-phrase; simultaneous-translation systems segment
on sentence boundaries instead. The trailing incomplete sentence is kept
separate from the settled ones because speech recognition may still revise it,
and anything already translated must never change.
"""

import re

_SENTENCE_PUNCT = ".!?…"

# A boundary is punctuation followed by whitespace or end of text.
_SENTENCE_END = re.compile(r"(?<=[.!?…])(?=\s|$)")

# Trailing dots here are sentence-internal, not sentence ends.
_ABBREVIATIONS = {
    "dr", "mr", "mrs", "ms", "prof", "sr", "jr", "st", "vs", "etc",
    "inc", "ltd", "co", "no", "fig", "approx",
}


def _is_real_boundary(text, pos):
    """False for decimals (3.14) and known abbreviations (Dr.)."""
    before = text[:pos + 1].rstrip()
    if not before:
        return False

    if before.endswith("."):
        # 3.14 — digits on both sides of the dot
        if len(before) >= 2 and before[-2].isdigit():
            after = text[pos + 1:].lstrip()
            if after and after[0].isdigit():
                return False
        word = re.split(r"\s", before)[-1].rstrip(_SENTENCE_PUNCT).lower()
        if word in _ABBREVIATIONS:
            return False
    return True


def split_sentences(text):
    """Split into sentences, keeping any trailing incomplete one as the last."""
    if not text or not text.strip():
        return []
    out, start = [], 0
    for m in _SENTENCE_END.finditer(text):
        pos = m.start() - 1          # index of the punctuation itself
        if pos < start or not _is_real_boundary(text, pos):
            continue
        piece = text[start:m.start()].strip()
        if piece:
            out.append(piece)
        start = m.start()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def stable_prefix(text):
    """Split into (settled sentences, unstable tail).

    The tail is whatever follows the last sentence-ending punctuation. Speech
    recognition can still rewrite it, so it must not be committed."""
    sentences = split_sentences(text)
    if not sentences:
        return "", ""
    if sentences[-1].endswith(tuple(_SENTENCE_PUNCT)):
        return " ".join(sentences), ""
    return " ".join(sentences[:-1]), sentences[-1]
