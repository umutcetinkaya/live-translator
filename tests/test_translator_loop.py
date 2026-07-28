"""Çeviri döngüsünün ne zaman provider'a gittiğini doğrulayan testler.

20 karakterlik eşik, hızlı akan konuşmada gereksiz API çağrısını engelliyor.
Ancak konuşma durduğunda kalan kısa parça da eninde sonunda çevrilmeli —
yoksa son cümle ekranda hiç görünmez.
"""

from unittest.mock import MagicMock
import translator as translator_mod
from translator import AITranslator


def _make_translator(monkeypatch, provider=None):
    fake = provider or MagicMock()
    fake.translate_document.return_value = "çeviri"
    monkeypatch.setattr(translator_mod, "get_translation_provider",
                        lambda cfg: fake)
    t = AITranslator(config={"target_lang": "tr", "model": "gpt-5.4-mini",
                             "translation_provider": "openai"})
    return t, fake


def test_large_new_content_translates_immediately(monkeypatch):
    t, fake = _make_translator(monkeypatch)
    t.update_source("Bu yeterince uzun bir cümledir efendim.")
    assert t._should_translate(t._source_buffer) is True


def test_small_new_content_is_deferred(monkeypatch):
    t, _ = _make_translator(monkeypatch)
    t._last_sent_source = "Merhaba dünya nasılsın bugün"
    t.update_source("Merhaba dünya nasılsın bugün iyi")
    assert t._should_translate(t._source_buffer) is False


def test_unchanged_source_never_translates(monkeypatch):
    t, _ = _make_translator(monkeypatch)
    t._last_sent_source = "Merhaba dünya"
    t.update_source("Merhaba dünya")
    assert t._should_translate(t._source_buffer) is False


def test_empty_source_never_translates(monkeypatch):
    t, _ = _make_translator(monkeypatch)
    assert t._should_translate("") is False


def test_deferred_tail_translates_after_speech_stops(monkeypatch):
    """Kısa kuyruk bekletilir, ama konuşma durunca çevrilmeli."""
    t, _ = _make_translator(monkeypatch)
    t._last_sent_source = "Merhaba dünya nasılsın bugün"
    t.update_source("Merhaba dünya nasılsın bugün iyi")

    assert t._should_translate(t._source_buffer) is False  # 1. tur: beklet
    # Kaynak bir tur boyunca değişmedi → kuyruk artık çevrilmeli
    assert t._should_translate(t._source_buffer) is True


def test_growing_source_keeps_deferring_short_tail(monkeypatch):
    """Konuşma sürüyorsa kısa kuyruk için erken çeviri tetiklenmemeli."""
    t, _ = _make_translator(monkeypatch)
    t._last_sent_source = "Merhaba dünya nasılsın bugün"
    t.update_source("Merhaba dünya nasılsın bugün iyi")
    assert t._should_translate(t._source_buffer) is False
    t.update_source("Merhaba dünya nasılsın bugün iyi mi")
    assert t._should_translate(t._source_buffer) is False
