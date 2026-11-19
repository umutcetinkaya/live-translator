"""macOS system voices (AVSpeechSynthesizer): free, offline, every language.

Speech is rendered to a file rather than spoken directly, so the existing
pipeline (loudness normalisation, the speech-level slider, the player) treats
it exactly like every other voice. Rendering is several times faster than
real time, so this adds no noticeable delay.
"""

import os
import tempfile
import threading
import time

from providers.base import TTSProvider, ProviderError

# AVSpeechUtterance rate constants (documented values), kept here so the
# mapping can be tested without loading AVFoundation.
DEFAULT_RATE = 0.5
MIN_RATE = 0.0
MAX_RATE = 1.0

RENDER_TIMEOUT = 30.0


def _avfoundation_voices():
    from AVFoundation import AVSpeechSynthesisVoice
    return [{"id": str(v.identifier()), "name": str(v.name()),
             "quality": int(v.quality()), "language": str(v.language())}
            for v in AVSpeechSynthesisVoice.speechVoices()]


def _matches(language, lang):
    language = language.lower()
    lang = lang.lower()
    return language == lang or language.startswith(lang + "-")


def list_voices(lang, lister=None):
    """Installed voices for `lang`, best quality first (3 premium, 2 enhanced, 1 default)."""
    voices = (lister or _avfoundation_voices)()
    found = [v for v in voices if _matches(v["language"], lang)]
    return sorted(found, key=lambda v: -v["quality"])


def best_voice(lang, lister=None):
    voices = list_voices(lang, lister)
    return voices[0] if voices else None


def _avfoundation_render(text, voice_id, rate, path):
    """Render `text` to an audio file at `path` (CAF, float PCM)."""
    from AVFoundation import (AVSpeechSynthesizer, AVSpeechUtterance,
                              AVSpeechSynthesisVoice, AVAudioFile)
    from Foundation import NSURL, NSRunLoop, NSDate, NSThread

    synth = AVSpeechSynthesizer.alloc().init()
    utterance = AVSpeechUtterance.speechUtteranceWithString_(text)
    utterance.setVoice_(AVSpeechSynthesisVoice.voiceWithIdentifier_(voice_id))
    utterance.setRate_(rate)
    state = {"file": None, "done": False, "error": None}
    finished = threading.Event()

    def on_buffer(buf):
        if buf.frameLength() == 0:
            state["done"] = True
            finished.set()
            return
        try:
            if state["file"] is None:
                fmt = buf.format()
                f, err = AVAudioFile.alloc().initForWriting_settings_commonFormat_interleaved_error_(
                    NSURL.fileURLWithPath_(path), fmt.settings(), fmt.commonFormat(),
                    fmt.isInterleaved(), None)
                if f is None:
                    raise RuntimeError(f"cannot open output file: {err}")
                state["file"] = f
            ok, err = state["file"].writeFromBuffer_error_(buf, None)
            if not ok:
                raise RuntimeError(f"write failed: {err}")
        except Exception as e:
            state["error"] = e
            state["done"] = True
            finished.set()

    synth.writeUtterance_toBufferCallback_(utterance, on_buffer)
    # AVFoundation delivers the buffers on the main thread. In the app the
    # main run loop is always turning, so a worker thread only has to wait;
    # called on the main thread itself, we must turn the loop ourselves.
    if NSThread.isMainThread():
        deadline = time.time() + RENDER_TIMEOUT
        while not finished.is_set() and time.time() < deadline:
            NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))
    else:
        finished.wait(RENDER_TIMEOUT)
    state["file"] = None  # closes the file
    if state["error"]:
        raise state["error"]
    if not state["done"]:
        raise RuntimeError("speech synthesis timed out")


class SystemVoiceTTSProvider(TTSProvider):

    def __init__(self, tmp_dir=None, voice_lister=None, renderer=None):
        self._tmp_dir = tmp_dir or tempfile.gettempdir()
        self._lister = voice_lister or _avfoundation_voices
        self._render = renderer or _avfoundation_render
        self._lock = threading.Lock()

    def _pick(self, lang, voice):
        voices = list_voices(lang, self._lister)
        if not voices:
            raise ProviderError(f"System voice: no voice for '{lang}'")
        for v in voices:
            if v["id"] == voice:
                return v["id"]
        return voices[0]["id"]

    def synthesize(self, text, lang, voice, speed):
        voice_id = self._pick(lang, voice)
        rate = max(MIN_RATE, min(MAX_RATE, DEFAULT_RATE * float(speed or 1.0)))
        path = os.path.join(self._tmp_dir, "tts_output_system.caf")
        with self._lock:
            try:
                if os.path.exists(path):
                    os.remove(path)
                self._render(text, voice_id, rate, path)
            except Exception as e:
                raise ProviderError(f"System voice error: {e}") from e
        return path
