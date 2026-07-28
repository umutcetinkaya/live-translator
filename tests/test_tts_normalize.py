"""TTS ses normalizasyonu testleri.

Ölçüldü: OpenAI TTS çıktısı tepe genliğin yalnızca %23'ünde (7409/32767),
yani 4.4x baş boşluk var — kullanıcı "OpenAI'nin sesi yükselmiyor" diye
bildirdi. Piper ise zaten tavanda (32767) ve yükseltilemez. Normalizasyon
sağlanan baş boşluğu kullanır, olmayanı zorlamaz.
"""

import array
import math
import struct

from tts import normalize_pcm_s16, PEAK_TARGET


def _pcm(peak, n=200):
    """Verilen tepe genlikte basit bir sinüs üret."""
    vals = [int(peak * math.sin(2 * math.pi * i / 40)) for i in range(n)]
    return array.array("h", vals).tobytes()


def _peak(pcm):
    a = array.array("h")
    a.frombytes(pcm)
    return max(abs(x) for x in a)


def test_quiet_audio_is_amplified():
    """%23 dolulukta gelen ses hedefe yükseltilmeli."""
    out = normalize_pcm_s16(_pcm(7409))
    assert _peak(out) > 25000


def test_loud_audio_is_brought_down_to_target():
    """Hedefin üstündeki ses hedefe İNDİRİLİR.

    Kaydırıcı eklendiğinde bu davranış değişti: kullanıcı sesi kısmak da
    isteyebiliyor. Yükseltmek kırpardı, indirmek güvenli."""
    out = normalize_pcm_s16(_pcm(32000), target=0.5)
    assert _peak(out) <= int(32767 * 0.5) + 1


def test_audio_already_at_target_is_untouched():
    src = _pcm(int(32767 * PEAK_TARGET))
    assert normalize_pcm_s16(src) == src


def test_normalized_peak_stays_below_clipping():
    """Hedef tam tavan olmamalı — kırpma payı bırakılır."""
    out = normalize_pcm_s16(_pcm(5000))
    assert _peak(out) <= int(32767 * PEAK_TARGET) + 1


def test_silence_is_untouched():
    """Sessizlikte bölme hatası olmamalı."""
    src = array.array("h", [0] * 100).tobytes()
    assert normalize_pcm_s16(src) == src


def test_empty_input_is_safe():
    assert normalize_pcm_s16(b"") == b""


def test_odd_byte_input_is_safe():
    out = normalize_pcm_s16(b"\x01\x02\x03")
    assert isinstance(out, bytes)


def test_waveform_shape_is_preserved():
    """Normalizasyon oranı korumalı — bozulma olmamalı."""
    src = _pcm(4000)
    out = normalize_pcm_s16(src)
    a = array.array("h"); a.frombytes(src)
    b = array.array("h"); b.frombytes(out)
    gain = _peak(out) / _peak(src)
    for x, y in zip(a[:50], b[:50]):
        assert abs(y - x * gain) <= 2, (x, y, gain)


def test_gain_is_capped():
    """Çok sessiz kayıtta sınırsız kazanç gürültüyü de yükseltir."""
    out = normalize_pcm_s16(_pcm(50))
    assert _peak(out) / 50 <= 12
