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


# SFSpeechRecognizer emits no punctuation, so sentence boundaries alone would
# never fire and nothing would ever be translated. Past this many unsettled
# words the text is chunked anyway.
#
# Sized to carry a complete thought, not just a fixed span. Half a sentence
# translates badly into any language whose word order differs from English —
# Turkish, Japanese, Korean and German all put the verb last, so a fragment
# cut before the English verb leaves the model nothing to build on. Measured:
# a 14-word cut produced "Bugün bakıyoruz nasıl büyük" (word salad); the full
# thought produced "Bugün büyük dil modellerinin ... inceliyoruz."
#
# 28 read well but only ever fired at a pause — the translation arrived after
# the speaker stopped. 18 is long enough to carry a clause and short enough to
# keep firing while speech flows.
UNPUNCTUATED_SEGMENT_WORDS = 18

# Words held back as unstable. Recognition keeps revising the most recent
# words, and committing them would freeze text that is about to change.
UNSTABLE_TAIL_WORDS = 6


def stable_prefix(text):
    """Split into (settled text, unstable tail).

    With punctuation, the boundary is the last sentence end. Without it — the
    normal case for on-device recognition — fall back to a word count, keeping
    the most recent words unstable because they are the ones still being
    revised."""
    sentences = split_sentences(text)
    if not sentences:
        return "", ""

    if sentences[-1].endswith(tuple(_SENTENCE_PUNCT)):
        return " ".join(sentences), ""

    settled = " ".join(sentences[:-1])
    tail = sentences[-1]

    # No sentence end in the tail: chunk it by word count instead. The cut is
    # snapped to a multiple of the segment size so the boundary only advances
    # once per full segment — cutting at "whatever is over the threshold"
    # produces one segment per new word, and so one API call per word.
    words = tail.split()
    if len(words) >= UNPUNCTUATED_SEGMENT_WORDS + UNSTABLE_TAIL_WORDS:
        cut = (len(words) - UNSTABLE_TAIL_WORDS) // UNPUNCTUATED_SEGMENT_WORDS
        cut *= UNPUNCTUATED_SEGMENT_WORDS
        if cut > 0:
            settled = (settled + " " + " ".join(words[:cut])).strip()
            tail = " ".join(words[cut:])
    return settled, tail


def flush_prefix(text):
    """Treat everything as settled — for when the speaker has stopped.

    Waiting for a full segment keeps quality up while speech is flowing, but
    at a pause the remaining words would hang untranslated. A silence means
    the thought is finished, so it is safe to commit."""
    if not text or not text.strip():
        return "", ""
    return text.strip(), ""
