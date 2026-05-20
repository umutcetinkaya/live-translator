import array
from audio_pcm import resample_s16, RATE_IN, RATE_OUT


def test_rates():
    assert RATE_IN == 44100 and RATE_OUT == 16000

def test_resample_reduces_length_roughly_by_ratio():
    # 44100 samples of silence (1 second) -> ~16000 samples
    src = array.array("h", [0] * 44100).tobytes()
    out = resample_s16(src)
    n_out = len(out) // 2
    assert 15000 <= n_out <= 17000

def test_resample_empty_returns_empty():
    assert resample_s16(b"") == b""

def test_resample_preserves_s16_byte_alignment():
    src = array.array("h", [100, 200, 300, 400, 500, 600]).tobytes()
    out = resample_s16(src)
    assert len(out) % 2 == 0

def test_resample_odd_byte_input_is_handled():
    # 3 bytes (not a whole sample) — must not crash, drops trailing byte
    out = resample_s16(b"\x01\x02\x03")
    assert isinstance(out, bytes)
