import sys
from unittest.mock import MagicMock

# pipeline transitively imports native macOS modules (PyObjC) that aren't
# available in the test venv. Mock them for import, tracking which keys WE
# added so a session-end fixture can remove them (no sys.modules pollution).
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
    # Sadece bizim eklediğimiz mock anahtarlarını temizle
    for mod in _INJECTED:
        sys.modules.pop(mod, None)


def _patch_components(monkeypatch):
    for name in ("SystemAudioCapture", "RealtimeSpeechRecognizer",
                 "AITranslator", "TextToSpeech"):
        monkeypatch.setattr(pipeline_mod, name, MagicMock())

def test_realtime_off_uses_recognizer(monkeypatch):
    _patch_components(monkeypatch)
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": False, "source_locale": "en-US",
                "target_lang": "tr"})
    assert p.is_realtime is False

def test_realtime_on_sets_flag(monkeypatch):
    _patch_components(monkeypatch)
    monkeypatch.setattr(pipeline_mod, "get_realtime_provider",
                        lambda cfg: MagicMock())
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": True, "source_locale": "en-US",
                "target_lang": "tr", "translation_provider": "openai",
                "openai_api_key": "k", "model": "gpt-realtime-translate"})
    assert p.is_realtime is True

def test_change_languages_restarts_realtime(monkeypatch):
    _patch_components(monkeypatch)
    rt = MagicMock()
    monkeypatch.setattr(pipeline_mod, "get_realtime_provider", lambda cfg: rt)
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": True, "source_locale": "en-US",
                "target_lang": "tr", "translation_provider": "openai",
                "openai_api_key": "k", "model": "gpt-realtime-translate"})
    p.start()
    rt.start.assert_called()
    p.change_languages("de-DE", "tr")
    # realtime modda dil değişince provider durdurulup yeniden başlatılmalı
    assert rt.stop.called
