"""Saf-Python ses yardımcıları — realtime köprüsü için PCM dönüşümü.

ScreenCaptureKit 44100 Hz mono s16 üretir. OpenAI Realtime GA 24000 Hz, Gemini
Live 16000 Hz ister. Bağımlılık eklemeden (numpy yok) decimation tabanlı resample.
"""

import array

RATE_IN = 44100
RATE_OUT = 16000
RATE_OPENAI = 24000
RATE_GEMINI = 16000


def resample_s16(pcm_bytes, rate_out=RATE_OUT, rate_in=RATE_IN):
    """mono s16le -> mono s16le (nearest-sample resample, varsayılan 44100->16000).

    Basit ama bağımlılıksız: her çıkış örneği için en yakın giriş örneğini seçer.
    Kaliteli değil ama realtime için yeterli; kalite gerekirse AVAudioConverter.
    """
    if not pcm_bytes:
        return b""
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if usable <= 0:
        return b""
    samples = array.array("h")
    samples.frombytes(pcm_bytes[:usable])
    n_in = len(samples)
    n_out = int(n_in * rate_out / rate_in)
    if n_out <= 0:
        return b""
    out = array.array("h", bytes(2 * n_out))
    step = n_in / n_out
    for i in range(n_out):
        out[i] = samples[int(i * step)]
    return out.tobytes()


def extract_pcm_from_sample_buffer(sample_buffer):
    """CMSampleBuffer -> ham s16 PCM bytes (kaynak örnekleme hızında).

    NOT: Bu fonksiyon canlı ses gerektirir; headless test edilemez.
    Gerçek CMSampleBuffer formatı çalışma anında loglanır (aşağıdaki print'ler).
    Başarısız olursa None döner — çağıran bunu güvenle yutar.
    """
    try:
        import CoreMedia
        block = CoreMedia.CMSampleBufferGetDataBuffer(sample_buffer)
        if block is None:
            print("[audio_pcm] DataBuffer None — format incelenmeli")
            return None
        total = CoreMedia.CMBlockBufferGetDataLength(block)
        if not total:
            return None
        out = bytearray(total)
        status, _ = CoreMedia.CMBlockBufferCopyDataBytes(block, 0, total, out)
        if status != 0:
            print(f"[audio_pcm] CopyDataBytes status={status}")
            return None
        return bytes(out)
    except Exception as e:
        print(f"[audio_pcm] extract error: {e}")
        return None
