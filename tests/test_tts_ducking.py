"""Audio ducking testleri — simültane tercüman davranışı.

TTS konuşurken arkadaki orijinal ses kısılmalı, çeviri sesi öne çıkmalı;
konuşma bitince eski seviye geri gelmeli. Aksi halde iki ses üst üste biner
ve hiçbiri anlaşılmaz.
"""

import sys
from unittest.mock import MagicMock

_NATIVE = ("objc", "AVFoundation", "Foundation", "AppKit")
_INJECTED = [m for m in _NATIVE if m not in sys.modules]
for m in _INJECTED:
    sys.modules[m] = MagicMock()

import pytest

import tts as tts_mod
from tts import TextToSpeech


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    for m in _INJECTED:
        sys.modules.pop(m, None)


def _make(monkeypatch, volume=0.8):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: volume)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.25})
    t._enabled = True
    return t, calls


def test_duck_lowers_system_volume(monkeypatch):
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    assert calls == [0.25 * 0.8], calls


def test_unduck_restores_original_volume(monkeypatch):
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    t._unduck()
    assert calls[-1] == 0.8


def test_duck_is_idempotent(monkeypatch):
    """Üst üste duck çağrısı orijinal seviyeyi kaybetmemeli."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    t._duck()
    t._unduck()
    assert calls[-1] == 0.8, calls


def test_unduck_without_duck_is_noop(monkeypatch):
    t, calls = _make(monkeypatch, volume=0.8)
    t._unduck()
    assert calls == []


def test_duck_ratio_is_configurable(monkeypatch):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 1.0)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.5})
    t._duck()
    assert calls == [0.5]


def test_ducking_can_be_disabled(monkeypatch):
    """duck_volume=1.0 -> kısma yok (kapalı)."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 0.8)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 1.0})
    t._duck()
    assert calls == []


def test_stop_restores_volume(monkeypatch):
    """Uygulama kapanırken sistem sesi kısık kalmamalı."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    t.stop()
    assert calls[-1] == 0.8


def test_flush_restores_volume(monkeypatch):
    """TTS kapatılınca (toggle) ses geri gelmeli."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    t._flush()
    assert calls[-1] == 0.8


def test_volume_read_failure_disables_ducking(monkeypatch):
    """Sistem sesi okunamazsa kısma denenmemeli — sessiz kalmaktansa üst üste bin."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: None)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.25})
    t._duck()
    t._unduck()
    assert calls == []
