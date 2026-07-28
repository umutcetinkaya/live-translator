"""Kayan pencere testleri.

Transkript sonsuz büyüyor; her 3 saniyede tüm geçmişi göndermek token
maliyetini ve gecikmeyi lineer artırır. Pencere son N kelimeyi tutar —
önceki çeviri zaten bağlam taşıdığı için süreklilik korunur.
"""

from unittest.mock import MagicMock
import translator as translator_mod
from translator import AITranslator


def _make(monkeypatch, window=10):
    fake = MagicMock()
    fake.translate_document.return_value = "çeviri"
    monkeypatch.setattr(translator_mod, "get_translation_provider", lambda cfg: fake)
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"})
    t._window_words = window
    return t, fake


def test_short_source_passes_through_unchanged(monkeypatch):
    t, _ = _make(monkeypatch, window=10)
    assert t._windowed_source("bir iki üç") == "bir iki üç"


def test_long_source_keeps_last_n_words(monkeypatch):
    t, _ = _make(monkeypatch, window=3)
    assert t._windowed_source("a b c d e") == "c d e"


def test_window_boundary_exact(monkeypatch):
    """Tam sınırdaki metin kırpılmamalı."""
    t, _ = _make(monkeypatch, window=3)
    assert t._windowed_source("a b c") == "a b c"


def test_empty_source_safe(monkeypatch):
    t, _ = _make(monkeypatch, window=3)
    assert t._windowed_source("") == ""


def test_provider_receives_windowed_text(monkeypatch):
    """_do_translate provider'a ham değil, pencerelenmiş metni vermeli."""
    t, fake = _make(monkeypatch, window=3)
    t._do_translate("a b c d e")
    sent = fake.translate_document.call_args.args[0]
    assert sent == "c d e"


def test_window_size_read_from_config(monkeypatch):
    """Pencere boyutu config'ten okunabilmeli."""
    fake = MagicMock()
    monkeypatch.setattr(translator_mod, "get_translation_provider", lambda cfg: fake)
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude",
                             "context_window_words": 42})
    assert t._window_words == 42


def test_update_config_refreshes_window(monkeypatch):
    """Ayarlardan pencere değişince yeni değer geçerli olmalı."""
    t, _ = _make(monkeypatch, window=10)
    t.update_config({"target_lang": "tr", "model": "claude-haiku-4-5",
                     "translation_provider": "claude",
                     "context_window_words": 5})
    assert t._window_words == 5
