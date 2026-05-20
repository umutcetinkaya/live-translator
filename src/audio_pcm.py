"""Pure-Python audio helpers — PCM conversion for the realtime bridge.

ScreenCaptureKit produces 44100 Hz mono s16. OpenAI Realtime GA wants 24000 Hz,
Gemini Live wants 16000 Hz. Decimation-based resample with no extra dependencies (no numpy).
"""

import array

RATE_IN = 44100
RATE_OUT = 16000
RATE_OPENAI = 24000
RATE_GEMINI = 16000


def resample_s16(pcm_bytes, rate_out=RATE_OUT, rate_in=RATE_IN):
    """mono s16le -> mono s16le (nearest-sample resample, default 44100->16000).

    Simple but dependency-free: selects the nearest input sample for each output sample.
    Not high quality, but sufficient for realtime; use AVAudioConverter if quality matters.
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
    """CMSampleBuffer -> raw s16 PCM bytes (at source sample rate).

    NOTE: This function requires live audio; cannot be tested headless.
    The actual CMSampleBuffer format is logged at runtime (prints below).
    Returns None on failure — callers can safely swallow this.
    """
    try:
        import CoreMedia
        block = CoreMedia.CMSampleBufferGetDataBuffer(sample_buffer)
        if block is None:
            print("[audio_pcm] DataBuffer None — format should be inspected")
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
