"""PCM dönüşüm testleri.

ScreenCaptureKit'in gerçek çıktısı canlı ölçüldü (2026-07-28):
  mSampleRate=48000, mFormatID='lpcm', mFormatFlags=41,
  mBitsPerChannel=32, mBytesPerFrame=4, mChannelsPerFrame=1
Yani 48kHz, 32-bit FLOAT, mono, packed, little-endian.
Kod eskiden 44100 Hz s16 varsayıyordu — realtime moda çöp PCM gidiyordu.
"""

import array
import struct
import sys
from unittest.mock import MagicMock

from audio_pcm import (resample_s16, float32_to_s16, RATE_IN, RATE_OUT,
                       RATE_OPENAI, RATE_GEMINI)


def test_rate_in_matches_screencapturekit():
    """Canlı ölçüm 48000 Hz gösterdi; 44100 varsayımı yanlıştı."""
    assert RATE_IN == 48000


def test_output_rates_match_provider_requirements():
    assert RATE_OPENAI == 24000   # OpenAI Realtime GA
    assert RATE_GEMINI == 16000   # Gemini Live
    assert RATE_OUT == 16000


def test_resample_reduces_length_by_ratio():
    # 48000 örnek (1 saniye) -> ~16000 örnek
    src = array.array("h", [0] * 48000).tobytes()
    n_out = len(resample_s16(src)) // 2
    assert 15000 <= n_out <= 17000


def test_resample_to_openai_rate():
    src = array.array("h", [0] * 48000).tobytes()
    n_out = len(resample_s16(src, rate_out=RATE_OPENAI)) // 2
    assert 23000 <= n_out <= 25000


def test_resample_empty_returns_empty():
    assert resample_s16(b"") == b""


def test_resample_preserves_s16_byte_alignment():
    src = array.array("h", [100, 200, 300, 400, 500, 600]).tobytes()
    assert len(resample_s16(src)) % 2 == 0


def test_resample_odd_byte_input_is_handled():
    assert isinstance(resample_s16(b"\x01\x02\x03"), bytes)


# --- float32 -> s16 dönüşümü ---

def test_float32_silence_becomes_s16_silence():
    src = struct.pack("<4f", 0.0, 0.0, 0.0, 0.0)
    assert float32_to_s16(src) == b"\x00\x00" * 4


def test_float32_full_scale_maps_to_s16_range():
    """+1.0 ve -1.0 s16 sınırlarına gitmeli, taşmadan."""
    src = struct.pack("<2f", 1.0, -1.0)
    out = array.array("h")
    out.frombytes(float32_to_s16(src))
    assert out[0] == 32767
    assert out[1] == -32768


def test_float32_clips_out_of_range_input():
    """Sınır dışı örnekler sarmalanmamalı (wrap = duyulabilir bozulma)."""
    src = struct.pack("<2f", 3.5, -3.5)
    out = array.array("h")
    out.frombytes(float32_to_s16(src))
    assert out[0] == 32767
    assert out[1] == -32768


def test_float32_half_scale_is_proportional():
    src = struct.pack("<1f", 0.5)
    out = array.array("h")
    out.frombytes(float32_to_s16(src))
    assert 16000 <= out[0] <= 16600


def test_float32_output_is_byte_aligned():
    src = struct.pack("<3f", 0.1, -0.2, 0.3)
    assert len(float32_to_s16(src)) == 6  # 3 örnek x 2 bayt


def test_float32_empty_returns_empty():
    assert float32_to_s16(b"") == b""


def test_float32_partial_sample_is_dropped():
    """4 baytın katı olmayan girdi çökmemeli."""
    src = struct.pack("<1f", 0.5) + b"\x01\x02"
    out = float32_to_s16(src)
    assert len(out) == 2  # yalnızca tam örnek


# --- extract_pcm dönüşümü GERÇEKTEN uyguluyor mu ---
# float32_to_s16'yı tek başına test etmek yetmez: extract_pcm onu çağırmayı
# unutursa testler yeşil kalır ama realtime'a çöp PCM gider.

def _fake_buffer(monkeypatch, payload, is_float=True):
    """CoreMedia'yı taklit ederek extract_pcm'i başsız test edilebilir yap."""
    import audio_pcm

    flags = 41 if is_float else 12          # IsFloat|Packed|NonInterleaved / int
    bits = 32 if is_float else 16
    asbd = (48000.0, 1819304813, flags, 4, 1, 4, 1, bits, 0)

    fake_cm = MagicMock()
    fake_cm.CMSampleBufferGetDataBuffer.return_value = object()
    fake_cm.CMBlockBufferGetDataLength.return_value = len(payload)
    fake_cm.CMSampleBufferGetFormatDescription.return_value = object()
    fake_cm.CMAudioFormatDescriptionGetStreamBasicDescription.return_value = asbd

    def copy(_blk, _off, total, out):
        out[:total] = payload[:total]
        return (0, None)

    fake_cm.CMBlockBufferCopyDataBytes.side_effect = copy
    monkeypatch.setitem(sys.modules, "CoreMedia", fake_cm)
    return audio_pcm.extract_pcm_from_sample_buffer(object())


def test_extract_pcm_converts_float_buffers(monkeypatch):
    """48kHz float buffer -> s16; yarı boyut ve doğru genlik."""
    payload = struct.pack("<4f", 0.5, -0.5, 0.0, 0.25)
    out = _fake_buffer(monkeypatch, payload, is_float=True)
    assert len(out) == 8           # 4 örnek x 2 bayt (16 bayttan yarıya indi)
    a = array.array("h")
    a.frombytes(out)
    assert 16000 <= a[0] <= 16600
    assert -16600 <= a[1] <= -16000
    assert a[2] == 0


def test_extract_pcm_leaves_int_buffers_alone(monkeypatch):
    """Kaynak zaten s16 ise dönüşüm uygulanmamalı — yoksa gürültü olur."""
    payload = array.array("h", [1000, -1000, 500]).tobytes()
    out = _fake_buffer(monkeypatch, payload, is_float=False)
    assert out == payload


def test_extract_pcm_output_feeds_resample(monkeypatch):
    """Uçtan uca: float buffer -> s16 -> 24kHz, boyut yarıya inmeli."""
    payload = struct.pack("<960f", *([0.1] * 960))
    s16 = _fake_buffer(monkeypatch, payload, is_float=True)
    out = resample_s16(s16, rate_out=RATE_OPENAI)
    assert len(out) == len(s16) // 2
