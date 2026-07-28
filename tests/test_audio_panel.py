"""Ses paneli backend testleri.

Chat üstünde sabit bir şerit: TTS aç/kapat, provider değiştirme, TTS ses
seviyesi ve sistem sesi — hepsi Ayarlar'a girmeden. Ayarlar penceresi
kaydetmeden uygulanmıyordu ve canlı yayın sırasında hızlı müdahale
gerektiriyor.
"""

import sys
from unittest.mock import MagicMock

_NATIVE = ("objc", "AVFoundation", "Foundation", "AppKit")
_INJECTED = [m for m in _NATIVE if m not in sys.modules]
for m in _INJECTED:
    sys.modules[m] = MagicMock()

import pytest

import tts as tts_mod
from tts import TextToSpeech, PEAK_TARGET


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    for m in _INJECTED:
        sys.modules.pop(m, None)


def _make(monkeypatch, **cfg):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda c: MagicMock())
    base = {"target_lang": "tr", "tts_provider": "piper"}
    base.update(cfg)
    return TextToSpeech(config=base)


# --- TTS ses seviyesi (normalizasyon hedefi) ---

def test_default_level_matches_peak_target(monkeypatch):
    t = _make(monkeypatch)
    assert t.speech_level == pytest.approx(PEAK_TARGET)


def test_level_can_be_set(monkeypatch):
    t = _make(monkeypatch)
    t.set_speech_level(0.5)
    assert t.speech_level == pytest.approx(0.5)


def test_level_is_clamped(monkeypatch):
    """Kaydırıcı geçersiz değer gönderse de güvenli kalmalı."""
    t = _make(monkeypatch)
    t.set_speech_level(5.0)
    assert t.speech_level <= 1.0
    t.set_speech_level(-1.0)
    assert t.speech_level >= 0.0


def test_level_changes_normalisation_output(monkeypatch):
    """Kaydırıcı gerçekten sesi değiştirmeli — sadece saklamamalı."""
    import array
    import math
    t = _make(monkeypatch)
    quiet = array.array(
        "h", [int(3000 * math.sin(2 * math.pi * i / 40)) for i in range(200)]
    ).tobytes()

    t.set_speech_level(0.9)
    loud = t.normalize(quiet)
    t.set_speech_level(0.4)
    soft = t.normalize(quiet)

    def peak(b):
        a = array.array("h"); a.frombytes(b)
        return max(abs(x) for x in a)

    assert peak(loud) > peak(soft)


def test_level_read_from_config(monkeypatch):
    t = _make(monkeypatch, speech_level=0.6)
    assert t.speech_level == pytest.approx(0.6)


# --- Provider değiştirme ---

def test_provider_can_be_switched(monkeypatch):
    seen = []
    monkeypatch.setattr(tts_mod, "get_tts_provider",
                        lambda c: seen.append(c.get("tts_provider")) or MagicMock())
    t = TextToSpeech(config={"target_lang": "tr", "tts_provider": "piper"})
    t.set_provider("openai")
    assert seen[-1] == "openai"
    assert t.provider_name == "openai"


def test_switching_provider_clears_pending_speech(monkeypatch):
    """Eski sesle sentezlenmiş kuyruk yeni provider'a taşınmamalı."""
    t = _make(monkeypatch)
    t._enabled = True
    t.speak("bir")
    t.set_provider("openai")
    assert t._queue.empty()


def test_failed_provider_switch_keeps_working_one(monkeypatch):
    """Geçersiz provider seçilirse ses tamamen kesilmemeli."""
    from providers.base import ProviderError
    good = MagicMock()
    calls = {"n": 0}

    def factory(cfg):
        calls["n"] += 1
        if calls["n"] > 1:
            raise ProviderError("nope")
        return good

    monkeypatch.setattr(tts_mod, "get_tts_provider", factory)
    t = TextToSpeech(config={"target_lang": "tr", "tts_provider": "piper"})
    t.set_provider("bogus")
    assert t._provider is good
    assert t.provider_name == "piper"
