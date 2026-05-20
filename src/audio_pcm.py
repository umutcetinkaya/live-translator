"""Saf-Python ses yardımcıları — realtime köprüsü için PCM dönüşümü.

ScreenCaptureKit 44100 Hz mono s16 üretir; realtime API'ler 16000 Hz mono s16
ister. Bağımlılık eklemeden (numpy yok) basit decimation tabanlı downsample.
"""

import array

RATE_IN = 44100
RATE_OUT = 16000


def resample_s16(pcm_bytes):
    """44100 Hz mono s16le -> 16000 Hz mono s16le (nearest-sample decimation).

    Basit ama bağımlılıksız: her çıkış örneği için en yakın giriş örneğini seçer.
    Kaliteli değil ama realtime STT için yeterli; gerçek kalite gerekirse
    AVAudioConverter'a geçilebilir.
    """
    if not pcm_bytes:
        return b""
    # Tam örneklere hizala (s16 = 2 byte); artık byte'ı at
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if usable <= 0:
        return b""
    samples = array.array("h")
    samples.frombytes(pcm_bytes[:usable])
    n_in = len(samples)
    n_out = int(n_in * RATE_OUT / RATE_IN)
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
        # Ham byte'ları kopyala
        out = bytearray(total)
        status, _ = CoreMedia.CMBlockBufferCopyDataBytes(block, 0, total, out)
        # Bazı PyObjC sürümlerinde imza farklı olabilir; canlı doğrulanacak
        if status != 0:
            print(f"[audio_pcm] CopyDataBytes status={status}")
            return None
        return bytes(out)
    except Exception as e:
        print(f"[audio_pcm] extract hata (canlı format incelenmeli): {e}")
        return None
