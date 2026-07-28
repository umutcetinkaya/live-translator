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
    assert calls and calls[0] < 0.8, calls


def test_duck_respects_absolute_floor(monkeypatch):
    """Sistem sesi zaten kısıkken oransal kısma TTS'i de duyulmaz yapardı."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 0.4)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.1})
    t._duck()
    assert calls[0] >= tts_mod.DUCK_FLOOR, calls


def test_duck_never_raises_volume(monkeypatch):
    """Zemin, kullanıcının seviyesinin üstüne çıkmamalı."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 0.2)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.5})
    t._duck()
    assert calls[0] <= 0.2, calls


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


def test_player_gain_compensates_for_ducking(monkeypatch):
    """TTS aynı çıkıştan çalıyor; sistem kısılınca TTS de kısılır.

    Ölçüldü: AVAudioPlayer.setVolume_ 1.0 ÜSTÜNÜ kabul ediyor (2.0, 4.0 geri
    okunuyor), yani yazılımsal kazançla telafi mümkün."""
    t, _ = _make(monkeypatch, volume=0.8)
    t._duck()
    # sistem 0.45 oranına indi -> TTS'in kaybını geri kazanması gerek
    assert t._player_gain() > 1.0


def test_player_gain_is_unity_when_not_ducking(monkeypatch):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 0.8)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: None)
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 1.0})
    assert t._player_gain() == 1.0


def test_player_gain_is_capped(monkeypatch):
    """Sınırsız kazanç kırpılma/bozulma yapar."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: 1.0)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: None)
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.05})
    t._duck()
    assert t._player_gain() <= tts_mod.MAX_PLAYER_GAIN


def test_tts_ends_up_louder_than_ducked_source(monkeypatch):
    """Asıl iddia: kısma sonrası TTS efektif seviyesi kaynaktan YÜKSEK."""
    t, calls = _make(monkeypatch, volume=0.8)
    t._duck()
    source_level = calls[0]                       # kaynak bu seviyede duyulur
    tts_level = source_level * t._player_gain()   # TTS kazançla çalar
    assert tts_level > source_level


def test_gain_resets_after_unduck(monkeypatch):
    t, _ = _make(monkeypatch, volume=0.8)
    t._duck()
    t._unduck()
    assert t._player_gain() == 1.0


# --- Konuşmalar arası ducking'i koru ---
# Her cümlede kısıp açmak sesi dalgalandırıyordu: kaynak ses TTS satırları
# arasında yükselip alçalıyor. Simültane tercüman gibi olması için kısma
# konuşma boyunca sürmeli, kuyruk boşalınca bırakılmalı.

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
    """Sistem sesi okunamazsa kısma denenmemeli — sessiz kalmaktansa üst üste bin."""
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())
    calls = []
    monkeypatch.setattr(tts_mod, "_system_volume", lambda: None)
    monkeypatch.setattr(tts_mod, "_set_system_volume", lambda v: calls.append(v))
    t = TextToSpeech(config={"target_lang": "tr", "duck_volume": 0.25})
    t._duck()
    t._unduck()
    assert calls == []
