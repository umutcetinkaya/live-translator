"""TTS kuyruğu testleri — sıralı okuma + geride kalınca atlama.

Piper offline ve yavaş; çeviri ondan hızlı üretiliyor. Kuyruk birikirse ses
görüntüden giderek geriye düşer ve simültane olmaktan çıkar. Eski kod
sınırsız kuyruk kullanıyordu.
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


@pytest.fixture(scope="module", autouse=True)
def _cleanup():
    yield
    for m in _INJECTED:
        sys.modules.pop(m, None)


def _make(monkeypatch, **cfg):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda c: MagicMock())
    base = {"target_lang": "tr"}
    base.update(cfg)
    t = TextToSpeech(config=base)
    t._enabled = True
    return t


def _drain(t):
    out = []
    while not t._queue.empty():
        out.append(t._queue.get_nowait())
    return out


def test_speech_is_queued_in_order(monkeypatch):
    t = _make(monkeypatch)
    for s in ("bir", "iki", "üç"):
        t.speak(s)
    assert _drain(t) == ["bir", "iki", "üç"]


def test_queue_is_bounded(monkeypatch):
    """Sınırsız kuyruk sesin görüntüden kopmasına yol açıyordu."""
    t = _make(monkeypatch)
    for i in range(50):
        t.speak(f"cümle {i}")
    assert t._queue.qsize() <= tts_mod.MAX_QUEUED_SPEECH


def test_oldest_is_dropped_when_behind(monkeypatch):
    """Geride kalınca EN ESKİ atılır — canlı kalmak için."""
    t = _make(monkeypatch)
    for i in range(tts_mod.MAX_QUEUED_SPEECH + 3):
        t.speak(f"c{i}")
    remaining = _drain(t)
    assert "c0" not in remaining
    assert remaining[-1] == f"c{tts_mod.MAX_QUEUED_SPEECH + 2}"


def test_newest_speech_always_survives(monkeypatch):
    """En yeni çeviri asla atılmamalı — kullanıcı onu bekliyor."""
    t = _make(monkeypatch)
    for i in range(20):
        t.speak(f"c{i}")
    assert _drain(t)[-1] == "c19"


def test_disabled_tts_queues_nothing(monkeypatch):
    t = _make(monkeypatch)
    t._enabled = False
    t.speak("bir")
    assert t._queue.empty()


def test_empty_text_is_not_queued(monkeypatch):
    t = _make(monkeypatch)
    t.speak("")
    assert t._queue.empty()
