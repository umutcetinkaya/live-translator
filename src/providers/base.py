"""Provider arayüzleri — çeviri ve TTS için takılabilir sözleşmeler."""

from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Tüm provider hataları bu tipe sarılır."""


class TranslationProvider(ABC):
    @abstractmethod
    def translate_document(self, source: str, prev_translation: str,
                           target_lang: str, model: str) -> str:
        """Live-document çeviri: önceki çeviriyi koru, yeni içeriği ekle.
        Tam güncel çeviriyi döner. Hata olursa ProviderError fırlatır."""
        raise NotImplementedError


class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, lang: str, voice: str, speed: float) -> str:
        """Ses dosyası üretir, dosya yolunu (wav/mp3) döner.
        Üretemezse ProviderError fırlatır. Oynatma çağırana aittir."""
        raise NotImplementedError
