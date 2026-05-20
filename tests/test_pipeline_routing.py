import sys
from unittest.mock import MagicMock

# Mock native macOS modules before pipeline is imported
for mod in ("objc", "ScreenCaptureKit", "CoreMedia", "Foundation",
            "AVFoundation", "Cocoa", "Speech", "AppKit"):
    sys.modules.setdefault(mod, MagicMock())

import pipeline as pipeline_mod


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
