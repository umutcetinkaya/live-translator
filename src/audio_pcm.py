"""Pure-Python audio helpers — PCM conversion for the realtime bridge.

ScreenCaptureKit hands us 48000 Hz mono **32-bit float** (measured live: format
'lpcm', mFormatFlags=41 → IsFloat|IsPacked|IsNonInterleaved, mBitsPerChannel=32).
Both realtime providers want 16-bit int, so float32_to_s16 runs before any
resample. OpenAI Realtime GA wants 24000 Hz, Gemini Live wants 16000 Hz.
Decimation-based resample, no extra dependencies (no numpy).
"""

import array
import struct

RATE_IN = 48000
RATE_OUT = 16000
RATE_OPENAI = 24000
RATE_GEMINI = 16000

_S16_MAX = 32767
_S16_MIN = -32768


def float32_to_s16(pcm_bytes):
    """32-bit float PCM (-1.0..1.0) -> signed 16-bit PCM.

    Out-of-range samples are clipped rather than allowed to wrap: wrapping
    turns a loud passage into audible noise, which upstream speech models
    then fail to transcribe."""
    if not pcm_bytes:
        return b""
    n = len(pcm_bytes) // 4
    if n == 0:
        return b""
    floats = struct.unpack_from(f"<{n}f", pcm_bytes)
    out = array.array("h", bytes(2 * n))
    for i, f in enumerate(floats):
        v = int(f * 32768.0)
        if v > _S16_MAX:
            v = _S16_MAX
        elif v < _S16_MIN:
            v = _S16_MIN
        out[i] = v
    return out.tobytes()


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


def _is_float_format(sample_buffer):
    """True when the buffer carries 32-bit float samples.

    ScreenCaptureKit delivers float on every macOS version we've measured, but
    the format is read per buffer rather than assumed — an int-PCM buffer run
    through the float path would be pure noise."""
    try:
        import CoreMedia
        fd = CoreMedia.CMSampleBufferGetFormatDescription(sample_buffer)
        if fd is None:
            return True
        asbd = CoreMedia.CMAudioFormatDescriptionGetStreamBasicDescription(fd)
        if not asbd:
            return True
        # ASBD tuple order: rate, id, flags, bytesPerPacket, framesPerPacket,
        # bytesPerFrame, channels, bitsPerChannel, reserved
        flags, bits = asbd[2], asbd[7]
        return bool(flags & 1) or bits == 32   # kAudioFormatFlagIsFloat
    except Exception:
        return True


def extract_pcm_from_sample_buffer(sample_buffer):
    """CMSampleBuffer -> mono s16 PCM bytes at the source sample rate.

    ScreenCaptureKit gives 32-bit float; callers want s16, so the conversion
    happens here and the rest of the pipeline only ever sees s16.
    Returns None on failure — callers can safely swallow this.
    """
    try:
        import CoreMedia
        block = CoreMedia.CMSampleBufferGetDataBuffer(sample_buffer)
        if block is None:
            return None
        total = CoreMedia.CMBlockBufferGetDataLength(block)
        if not total:
            return None
        out = bytearray(total)
        status, _ = CoreMedia.CMBlockBufferCopyDataBytes(block, 0, total, out)
        if status != 0:
            print(f"[audio_pcm] CopyDataBytes status={status}")
            return None
        raw = bytes(out)
        if _is_float_format(sample_buffer):
            return float32_to_s16(raw)
        return raw
    except Exception as e:
        print(f"[audio_pcm] extract error: {e}")
        return None
