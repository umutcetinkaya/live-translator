"""TTS oynatma sırasında ses seviyesi testleri.

macOS uygulama başına ses kontrolü vermiyor: elimizdeki tek denetim sistem
sesi ve o, kaynağı da çeviriyi de aynı anda ölçekliyor. Bu yüzden KISMAK
çeviriyi de kısıyordu ("ses kısılıyor ama TTS de kısılıyor"). Sentezlenmiş
ses zaten tam ölçekte olduğundan, konuşma boyunca çıkışı YÜKSELTMEK çeviriyi
rahat duyulur seviyeye taşıyor; bitince eski seviye geri veriliyor.
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



def test_boost_can_be_disabled(monkeypatch):
    """duck_volume=1.0 -> seviye hiç değiştirilmez (kapalı)."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 0.8)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 1.0})
    t._duck()
    assert calls == []


def test_stop_restores_volume(monkeypatch):
    """Uygulama kapanırken kullanıcının seviyesi geri verilmeli."""
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


def test_tts_plays_at_full_scale(monkeypatch):
    """TTS oynatıcı tam ölçekte çalmalı.

    Ölçüldü: Piper'ın ürettiği WAV zaten tepe genlikte (32767/32767, %100
    doluluk). setVolume_ 1.0 üstünü kabul ediyormuş gibi görünse de yükselecek
    baş boşluk yok — sadece kırpma olur."""
    t, _ = _make(monkeypatch, volume=0.8)
    t._duck()
    assert t._player_gain() == 1.0




def test_ducking_raises_system_volume_to_keep_tts_audible(monkeypatch):
    """Konuşma sırasında sistem sesi kullanıcının seviyesinin ÜSTÜNE çıkmalı."""
    t, calls = _make(monkeypatch, volume=0.5)
    t._duck()
    assert calls[0] > 0.5, f"sistem sesi yükseltilmedi: {calls}"


def test_system_volume_never_exceeds_maximum(monkeypatch):
    """Telafi 1.0'ı aşamaz — macOS reddeder."""
    t, calls = _make(monkeypatch, volume=0.9)
    t._duck()
    assert calls[0] <= 1.0


def test_original_volume_is_restored_after_speaking(monkeypatch):
    """Yükseltilmiş seviye kalıcı olmamalı."""
    t, calls = _make(monkeypatch, volume=0.5)
    t._duck()
    t._unduck()
    assert calls[-1] == 0.5


def test_tts_effective_level_beats_pre_duck_source(monkeypatch):
    """Asıl iddia: çeviri en az kullanıcının kendi seviyesi kadar duyulur."""
    t, calls = _make(monkeypatch, volume=0.5)
    t._duck()
    assert calls[0] >= 0.5


# --- Seviye değişimini konuşma boyunca koru ---
# Her satırda yükseltip geri almak sesi dalgalandırıyordu. Tercüman pasajı
# bitirene kadar sözü bırakmaz: seviye kuyruk boşalana kadar korunur.

def test_volume_is_not_restored_between_lines(monkeypatch):
    """Kuyrukta iş varken ses geri yükselmemeli."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    calls.clear()
    t.speak("sonraki satır")        # kuyrukta iş var
    t._release_duck_if_idle()
    assert calls == [], "satırlar arasında ses yükseldi"


def test_volume_restored_once_queue_drains(monkeypatch):
    """Konuşacak bir şey kalmayınca ses geri gelmeli."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    calls.clear()
    t._release_duck_if_idle()       # kuyruk boş
    assert calls == [0.8]


def test_release_is_safe_without_duck(monkeypatch):
    t, calls = _make(monkeypatch, volume=0.8)
    t._release_duck_if_idle()
    assert calls == []


def test_stop_restores_even_with_queued_speech(monkeypatch):
    """Kapanışta kuyruk dolu olsa da kullanıcının sesi geri verilmeli."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    t.speak("bekleyen")
    t.stop()
    assert calls[-1] == 0.8


def test_volume_read_failure_disables_ducking(monkeypatch):
    """Sistem sesi okunamazsa dokunulmamalı."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: None)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.25})
    t._duck()
    t._unduck()
    assert calls == []
