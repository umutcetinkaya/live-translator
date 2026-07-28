"""TTS'e hangi metnin gönderildiğini doğrulayan testler.

Çeviri "canlı doküman" modeli kullanıyor: model önceki çeviriyi koruyup
sonuna ekleme yapıyor, ancak son cümleyi düzeltebiliyor (prompt bunu
açıkça istiyor). TTS sadece gerçekten YENİ olan kısmı okumalı.
"""

import sys
from unittest.mock import MagicMock

_NATIVE_MODS = ("objc", "ScreenCaptureKit", "CoreMedia", "Foundation",
                "AVFoundation", "Cocoa", "Speech", "AppKit")
_INJECTED = [m for m in _NATIVE_MODS if m not in sys.modules]
for mod in _INJECTED:
    sys.modules[mod] = MagicMock()

import pipeline as pipeline_mod

import pytest


@pytest.fixture(scope="module", autouse=True)
def _cleanup_native_mocks():
    yield
    for mod in _INJECTED:
        sys.modules.pop(mod, None)


def _make_pipeline(monkeypatch):
    for name in ("SystemAudioCapture", "RealtimeSpeechRecognizer",
                 "AITranslator", "TextToSpeech"):
        monkeypatch.setattr(pipeline_mod, name, MagicMock())
    p = pipeline_mod.TranslationPipeline(
        MagicMock(),
        config={"realtime_mode": False, "source_locale": "en-US",
                "target_lang": "tr"})
    p._tts.enabled = True
    return p


def _spoken(pipeline):
    return [c.args[0] for c in pipeline._tts.speak.call_args_list]


def test_speaks_only_appended_text(monkeypatch):
    p = _make_pipeline(monkeypatch)
    p._on_translation("Merhaba dünya.")
    p._on_translation("Merhaba dünya. Bugün hava çok güzel.")
    assert _spoken(p) == ["Merhaba dünya.", "Bugün hava çok güzel."]


def test_refined_word_is_respoken_not_skipped(monkeypatch):
    """Model önceki bir kelimeyi düzeltirse TTS o kelimeden itibaren okumalı.

    Kelime-sayısı diff'i hizayı kaydırdığı için eski kod cümle ortasından
    kesik bir parça okuyordu."""
    p = _make_pipeline(monkeypatch)
    p._on_translation("Bugün hava kötü")
    # Model "kötü" -> "çok güzeldi" olarak düzeltip yeni cümle ekliyor
    p._on_translation("Bugün hava çok güzeldi. Yarın yağmur var.")
    # Kelime sayısı farkı 3 → eski kod "güzeldi. Yarın yağmur var." derdi
    # ("çok" yutulur, cümle ortasından başlar). Düzeltilen kelimeden başlamalı.
    assert _spoken(p)[-1] == "çok güzeldi. Yarın yağmur var."


def test_appended_part_starts_at_first_changed_word():
    diff = pipeline_mod.TranslationPipeline._appended_part(
        "Bugün hava kötü", "Bugün hava çok güzeldi.")
    assert diff == "çok güzeldi."


def test_shorter_translation_does_not_speak(monkeypatch):
    """Çeviri kısalırsa (clear/yeniden yazım) hiçbir şey okunmamalı."""
    p = _make_pipeline(monkeypatch)
    p._on_translation("Merhaba dünya. Bugün hava çok güzel.")
    p._tts.speak.reset_mock()
    p._on_translation("Merhaba dünya.")
    assert _spoken(p) == []


def test_disabled_tts_never_speaks(monkeypatch):
    p = _make_pipeline(monkeypatch)
    p._tts.enabled = False
    p._on_translation("Merhaba dünya.")
    assert _spoken(p) == []
