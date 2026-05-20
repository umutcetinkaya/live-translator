"""Provider interfaces — pluggable contracts for translation and TTS."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """All provider errors are wrapped in this type."""


class TranslationProvider(ABC):
    @abstractmethod
    def translate_document(self, source: str, prev_translation: str,
                           target_lang: str, model: str) -> str:
        """Live-document translation: preserve previous translation, append new content.
        Returns the full up-to-date translation. Raises ProviderError on failure."""
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
