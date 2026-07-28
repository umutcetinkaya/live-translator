"""TTS oynatma seviyesi testleri.

macOS uygulama başına ses kontrolü vermiyor. Elimizdeki tek denetim sistem
sesi ve o, kaynağı da çeviriyi de AYNI katsayıyla çarpıyor — yani kısmak da
yükseltmek de aradaki oranı hiç değiştirmiyor. Ölçüldü ve doğrulandı:

  kısınca : kaynak ve TTS birlikte düşüyor ("TTS de kısılıyor")
  yükseltince: sistem zaten tavandaysa etkisiz ("yükselmiyor")

Bu yüzden sistem sesine hiç dokunulmuyor. Çevirinin duyulur olmasını
sağlayan tek gerçek kaldıraç, ses dosyasının normalize edilmesi
(bkz. test_tts_normalize.py). Kaynağı geri plana almak kullanıcının kendi
oynatıcısından yapılır.
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
    # Sistem sesi yardımcıları kaldırıldı; varsa çağrıldığını yakalamak için
    # geçici olarak enjekte ediyoruz.
    monkeypatch.setattr(tts_mod, "_set_system_volume",
                        lambda v: calls.append(v), raising=False)
    t = TextToSpeech(config={"target_lang": "tr"})
    t._enabled = True
    return t, calls


def test_playing_does_not_change_system_volume(monkeypatch):
    """Kullanıcının ses seviyesi uygulamanın işi değil.

    Hem kısmak hem yükseltmek denendi; ikisi de kaynağı ve çeviriyi eşit
    etkilediği için işe yaramadı, üstelik kullanıcının seviyesini habersiz
    değiştiriyordu. Oynatma yolunun tamamı sürülür — asıl çağrılar orada."""
    t, calls = _make(monkeypatch, volume=0.94)
    t._normalized_path = lambda p: p          # dosya dönüşümünü atla
    t._play_file = lambda p: None             # native oynatıcıyı atla
    t._synthesize_and_play("merhaba")
    t._flush()
    t.stop()
    assert calls == [], f"sistem sesi değiştirildi: {calls}"


def test_no_duck_helpers_remain(monkeypatch):
    """Ducking tamamen kaldırıldı — ölü kod bırakma."""
    assert not hasattr(TextToSpeech, "_duck")
    assert not hasattr(TextToSpeech, "_unduck")
    assert not hasattr(TextToSpeech, "_release_duck_if_idle")


def test_player_plays_at_full_scale(monkeypatch):
    """Oynatıcı kazancı 1.0 — yükseltme dosyanın kendisinde yapılıyor."""
    t, _ = _make(monkeypatch)
    assert t._player_gain() == 1.0


def test_stop_does_not_touch_volume(monkeypatch):
    t, calls = _make(monkeypatch)
    t.stop()
    assert calls == []


def test_flush_does_not_touch_volume(monkeypatch):
    t, calls = _make(monkeypatch)
    t._flush()
    assert calls == []
