"""TTS hatalarının kullanıcıya ULAŞTIĞINI doğrulayan testler.

Gerçek olay (2026-07-28): Gemini TTS anahtarı geçersizdi, sonra Piper'a
geçildi ama ses modeli indirilmemişti. Her iki durumda da uygulama sessizce
hiçbir ses üretmedi — hata yalnızca terminale yazıldı, kullanıcı ekranda
hiçbir şey görmedi ve neyin bozuk olduğunu anlayamadı.
"""

import queue
import sys
from unittest.mock import MagicMock

_NATIVE = ("objc", "AVFoundation", "Foundation", "AppKit")
_INJECTED = [m for m in _NATIVE if m not in sys.modules]
for m in _INJECTED:
    sys.modules[m] = MagicMock()

import pytest

import tts as tts_mod
from tts import TextToSpeech
from providers.base import ProviderError


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    for m in _INJECTED:
        sys.modules.pop(m, None)


def _make(monkeypatch, provider):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: provider)
    errors = []
    t = TextToSpeech(config={"target_lang": "tr", "tts_provider": "piper"},
                     on_error=errors.append)
    t._enabled = True
    return t, errors


def test_provider_error_reaches_the_user(monkeypatch):
    """Anahtar geçersiz / model yok -> kullanıcı bilgilendirilmeli."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError("Piper: model file not found")
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("Merhaba")
    assert errors, "hata kullanıcıya iletilmedi"
    # Ham yol değil, ne yapılacağını söyleyen mesaj gitmeli
    assert "make models" in errors[0].lower()


def test_unexpected_error_also_reaches_the_user(monkeypatch):
    prov = MagicMock()
    prov.synthesize.side_effect = RuntimeError("boom")
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("Merhaba")
    assert errors


def test_same_error_reported_once(monkeypatch):
    """Her çeviri turunda tekrar etmemeli — ekranı doldurur."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError("API key not valid")
    t, errors = _make(monkeypatch, prov)
    for _ in range(5):
        t._synthesize_and_play("Merhaba")
    assert len(errors) == 1, errors


def test_new_error_is_reported_again(monkeypatch):
    """Farklı bir hata çıkarsa yine bildirilmeli."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError("API key not valid")
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("bir")
    prov.synthesize.side_effect = ProviderError("model file not found")
    t._synthesize_and_play("iki")
    assert len(errors) == 2


def test_recovery_allows_reporting_again(monkeypatch):
    """Hata düzelip tekrar bozulursa yeniden bildirilmeli."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError("API key not valid")
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("bir")
    prov.synthesize.side_effect = None
    prov.synthesize.return_value = None      # başarılı ama çalacak dosya yok
    t._synthesize_and_play("iki")
    prov.synthesize.side_effect = ProviderError("API key not valid")
    t._synthesize_and_play("uc")
    assert len(errors) == 2


def test_success_reports_nothing(monkeypatch):
    prov = MagicMock()
    prov.synthesize.return_value = None
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("Merhaba")
    assert errors == []


def test_works_without_callback(monkeypatch):
    """on_error verilmezse çökmemeli (geriye dönük uyumluluk)."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError("x")
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: prov)
    t = TextToSpeech(config={"target_lang": "tr"})
    t._enabled = True
    t._synthesize_and_play("Merhaba")   # patlamamalı


def test_missing_model_message_is_actionable(monkeypatch):
    """Kullanıcı ne yapacağını anlamalı — ham yol yeterli değil."""
    prov = MagicMock()
    prov.synthesize.side_effect = ProviderError(
        "Piper: model file not found: /x/models/tr_TR-dfki-medium.onnx")
    t, errors = _make(monkeypatch, prov)
    t._synthesize_and_play("Merhaba")
    assert "make models" in errors[0].lower()
