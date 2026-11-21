"""Settings changed outside the Settings dialog must survive a restart.

The speech level slider in the audio bar applied the level live but never
saved it, so every launch went back to the default. And the Settings dialog
saved its own copy of the config loaded at startup, so pressing Save wrote
back stale values for anything changed elsewhere (speech on/off, level).
"""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

_NATIVE_MODS = ("objc", "ScreenCaptureKit", "CoreMedia", "Foundation", "AVFoundation",
                "Cocoa", "Speech", "AppKit")
_INJECTED = [m for m in _NATIVE_MODS if m not in sys.modules]
for mod in _INJECTED:
    sys.modules[mod] = MagicMock()

import ast  # noqa: E402
import os  # noqa: E402

import pytest  # noqa: E402

import pipeline as pipeline_mod  # noqa: E402

_OVERLAY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "overlay.py")


def _overlay_save_settings(load_config, save_config):
    """TranslationOverlay._save_settings, isolated (overlay.py needs AppKit/WebKit)."""
    tree = ast.parse(open(_OVERLAY_PATH, encoding="utf-8").read())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TranslationOverlay")
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_save_settings")
    ns = {"load_config": load_config, "save_config": save_config}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), _OVERLAY_PATH, "exec"), ns)
    return ns["_save_settings"]


@pytest.fixture(scope="module", autouse=True)
def _cleanup_native_mocks():
    yield
    for mod in _INJECTED:
        sys.modules.pop(mod, None)


def _make_pipeline(monkeypatch, saved):
    for name in ("SystemAudioCapture", "RealtimeSpeechRecognizer", "AITranslator", "TextToSpeech"):
        monkeypatch.setattr(pipeline_mod, name, MagicMock())
    monkeypatch.setattr(pipeline_mod, "save_config", lambda c: saved.append(dict(c)))
    return pipeline_mod.TranslationPipeline(
        MagicMock(), config={"realtime_mode": False, "source_locale": "en-US", "target_lang": "tr"})


def test_speech_level_is_saved(monkeypatch):
    saved = []
    p = _make_pipeline(monkeypatch, saved)
    p.audio_control("level", "60")
    p._tts.set_speech_level.assert_called_once_with(0.6)
    assert saved[-1]["speech_level"] == pytest.approx(0.6)


def test_other_audio_controls_do_not_write_the_level(monkeypatch):
    saved = []
    p = _make_pipeline(monkeypatch, saved)
    monkeypatch.setattr(pipeline_mod, "_set_system_volume", lambda v: None)
    p.audio_control("system", "40")
    assert all("speech_level" not in c for c in saved)


def test_settings_dialog_keeps_values_saved_elsewhere(monkeypatch):
    on_disk = {"tts_enabled": True, "speech_level": 0.5, "target_lang": "de",
               "translation_provider": "local"}
    written = []
    save_settings = _overlay_save_settings(lambda: dict(on_disk), lambda c: written.append(dict(c)))
    stale = {"tts_enabled": False, "speech_level": 0.92, "target_lang": "tr",
             "translation_provider": "local"}
    fake = SimpleNamespace(_config=stale, _on_settings_change=None)

    save_settings(
        fake, "openai", "sk-x", "", "", "gpt-6-luna", tts_provider="system")

    saved = written[-1]
    assert saved["translation_provider"] == "openai"     # the dialog's own fields win
    assert saved["tts_provider"] == "system"
    assert saved["tts_enabled"] is True                  # changed elsewhere, kept
    assert saved["speech_level"] == 0.5
    assert saved["target_lang"] == "de"
    assert fake._config is not stale and fake._config == saved
