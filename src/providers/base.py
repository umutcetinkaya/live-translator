"""Provider interfaces — pluggable contracts for translation and TTS."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """All provider errors are wrapped in this type."""


SEGMENT_SYSTEM_PROMPT = """\
You are a simultaneous interpreter producing live subtitles.

You receive:
1. CONTEXT — earlier speech, for reference only
2. NEW — the text to translate

Translate ONLY the NEW text. Never translate or repeat the CONTEXT.

Rules:
- Output only the translation of NEW, nothing else
- Natural, spoken-register prose in the target language
- Keep it tight — this is a live subtitle, not an essay
- Use CONTEXT to resolve pronouns, terminology and tone
- If NEW ends mid-sentence, translate what is there
- No commentary, no quotes, no labels"""

# A segment is one or a few sentences, so the reply is short. Bounding it is
# what stops the truncation the full-document model suffered from.
SEGMENT_MAX_TOKENS = 1000


def build_segment_prompt(segment, context, target_lang):
    """User message shared by every provider, so they stay consistent."""
    msg = f"Target language: {target_lang}\n\n"
    if context:
        msg += f"CONTEXT (do not translate):\n{context}\n\n"
    return msg + f"NEW (translate only this):\n{segment}"


class TranslationProvider(ABC):
    @abstractmethod
    def translate_document(self, source: str, prev_translation: str,
                           target_lang: str, model: str) -> str:
        """Live-document translation: preserve previous translation, append new content.
        Returns the full up-to-date translation. Raises ProviderError on failure."""
        raise NotImplementedError

    def translate_segment(self, segment: str, context: str,
                          target_lang: str, model: str) -> str:
        """Translate one new segment, using `context` only as background.

        Incremental counterpart to translate_document: the caller commits each
        result and never asks for it again, so the output stays short and can't
        be truncated. Returns the translation of `segment` alone."""
        raise NotImplementedError


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, lang: str, voice: str, speed: float) -> str:
        """Produces an audio file and returns its path (wav/mp3).
        Raises ProviderError on failure. Playback is the caller's responsibility."""
        raise NotImplementedError


class RealtimeProvider(ABC):
    @abstractmethod
    def start(self, on_translation, on_source) -> None:
        """Starts a realtime session. on_translation(text) and on_source(text)
        callbacks are called with partial/complete results."""
        raise NotImplementedError

    @abstractmethod
    def feed_audio(self, pcm_chunk: bytes) -> None:
        """Sends a 16kHz/16-bit/mono PCM chunk to the session."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError
