"""Text-to-Speech orchestrator — delegates synthesis to TTSProvider.

Queue-based: translations are spoken in order. Played via AVAudioPlayer (same process);
no feedback loop thanks to excludesCurrentProcessAudio.
"""

import threading
import time
import queue
import subprocess
import array
from config import load_config
from providers import get_tts_provider
from providers.base import ProviderError


# Lines allowed to wait for the voice. Small on purpose: a backlog means the
# spoken translation is trailing the picture, which defeats the point.
MAX_QUEUED_SPEECH = 3


# Normalisation target, just under full scale so rounding can't clip.
PEAK_TARGET = 0.92

# Ceiling on normalisation gain — a near-silent take is mostly noise, and
# lifting it all the way just makes the noise loud.
MAX_NORMALISE_GAIN = 12.0


def normalize_pcm_s16(pcm_bytes):
    """Raise quiet synthesised speech toward full scale.

    Voices differ enormously in level: measured, OpenAI's output peaks at 23%
    of full scale while Piper's is already at the ceiling. Without this the
    OpenAI voice is simply too quiet to hear over the source audio, and no
    amount of system-volume juggling fixes it — the file itself is quiet.
    Audio already near the ceiling is returned untouched, since amplifying it
    would only clip."""
    if not pcm_bytes:
        return pcm_bytes
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if usable <= 0:
        return pcm_bytes
    samples = array.array("h")
    samples.frombytes(pcm_bytes[:usable])
    peak = max((abs(s) for s in samples), default=0)
    if peak == 0:
        return pcm_bytes

    target = int(32767 * PEAK_TARGET)
    if peak >= target:
        return pcm_bytes
    gain = min(target / peak, MAX_NORMALISE_GAIN)

    out = array.array("h", bytes(2 * len(samples)))
    for i, s in enumerate(samples):
        v = int(s * gain)
        out[i] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
    return out.tobytes()


def _friendly(message):
    """Turn a provider error into something the user can act on.

    The raw text is accurate but not actionable — 'model file not found:
    /long/path.onnx' doesn't tell anyone to run `make models`."""
    low = message.lower()
    if "model file not found" in low:
        return "Voice model missing — run `make models` to download it"
    if "api key not valid" in low or "api_key_invalid" in low:
        return "TTS API key is not valid — check it in Settings"
    if "no api key" in low:
        return "No TTS API key — add one in Settings"
    if "no voice for" in low:
        return "No offline voice for this language — pick OpenAI or Gemini TTS"
    return message


class TextToSpeech:
    def __init__(self, config=None, on_error=None):
        self._config = config or load_config()
        self._enabled = False
        self._lang = self._config.get("target_lang", "tr")
        self._voice = self._config.get("tts_voice", "nova")
        self._speed = self._config.get("tts_speed", 1.0)
        self._queue = queue.Queue()
        self._worker = None
        self._running = True
        self._current_player = None
        self._on_error = on_error
        self._last_error = None
        self._provider = get_tts_provider(self._config)

    @property
    def enabled(self):
        return self._enabled

    def toggle(self):
        self._enabled = not self._enabled
        if self._enabled and not self._worker:
            self._start_worker()
        if not self._enabled:
            self._flush()
        print(f"[TTS] {'ON' if self._enabled else 'OFF'}")
        return self._enabled

    def set_enabled(self, val):
        self._enabled = val
        if val and not self._worker:
            self._start_worker()

    def set_language(self, lang_code):
        self._lang = lang_code

    def update_config(self, config):
        self._config = config
        self._lang = config.get("target_lang", self._lang)
        self._voice = config.get("tts_voice", self._voice)
        self._speed = config.get("tts_speed", self._speed)
        self._provider = get_tts_provider(config)

    def speak(self, text):
        """Queue a translation to be spoken, oldest first.

        Synthesis is slower than translation (markedly so with the offline
        voice), so an unbounded queue drifts further behind the video the
        longer it runs. Past the cap the oldest pending line is dropped: being
        a few lines behind is worse than missing one."""
        if not self._enabled or not text:
            return
        while self._queue.qsize() >= MAX_QUEUED_SPEECH:
            try:
                dropped = self._queue.get_nowait()
                print(f"[TTS] Behind — skipping: {dropped[:40]}")
            except queue.Empty:
                break
        self._queue.put(text)

    def _start_worker(self):
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self):
        while self._running:
            try:
                text = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            if not self._enabled:
                continue
            self._synthesize_and_play(text)

    def _player_gain(self):
        """Playback gain for the spoken translation — always full scale.

        Loudness is handled by normalising the audio file itself, not by
        player gain: setVolume_ accepts values above 1.0 and reads them back,
        but they only clip."""
        return 1.0


    def _normalized_path(self, path):
        """Return a playable path whose audio sits near full scale.

        Voice levels vary wildly between providers — OpenAI's output was
        measured at 23% of full scale, Piper's at 100% — so without this the
        OpenAI voice is inaudible over the source no matter how the system
        volume is set. Falls back to the original file if anything goes
        wrong; a quiet translation beats none."""
        import os
        import wave
        try:
            src = path
            if not path.lower().endswith(".wav"):
                src = os.path.join(os.path.dirname(path), "_tts_norm_in.wav")
                r = subprocess.run(
                    ["afconvert", "-f", "WAVE", "-d", "LEI16", path, src],
                    capture_output=True, timeout=15,
                )
                if r.returncode != 0 or not os.path.exists(src):
                    return path

            with wave.open(src, "rb") as w:
                params = w.getparams()
                if params.sampwidth != 2:
                    return path
                frames = w.readframes(params.nframes)

            loud = normalize_pcm_s16(frames)
            if loud is frames or loud == frames:
                return src

            out = os.path.join(os.path.dirname(path), "_tts_norm_out.wav")
            with wave.open(out, "wb") as w:
                w.setnchannels(params.nchannels)
                w.setsampwidth(2)
                w.setframerate(params.framerate)
                w.writeframes(loud)
            return out
        except Exception as e:
            print(f"[TTS] Normalise skipped: {e}")
            return path

    def _report_error(self, message):
        """Surface a failure to the user, once per distinct problem.

        Synthesis runs per translation cycle, so an unresolved fault (bad key,
        missing model) would otherwise repeat every few seconds."""
        print(f"[TTS] {message}")
        if message == self._last_error:
            return
        self._last_error = message
        if self._on_error:
            try:
                self._on_error(_friendly(message))
            except Exception:
                pass

    def _synthesize_and_play(self, text):
        try:
            path = self._provider.synthesize(text, self._lang, self._voice,
                                             self._speed)
        except ProviderError as e:
            self._report_error(str(e))
            return
        except Exception as e:
            self._report_error(f"Unexpected: {e}")
            return
        self._last_error = None
        if path:
            self._play_file(self._normalized_path(path))

    def _play_file(self, path):
        from AVFoundation import AVAudioPlayer
        from Foundation import NSURL
        url = NSURL.fileURLWithPath_(path)
        player, error = AVAudioPlayer.alloc().initWithContentsOfURL_error_(url, None)
        if player and not error:
            player.setVolume_(self._player_gain())
            player.play()
            self._current_player = player
            while player.isPlaying() and self._enabled:
                time.sleep(0.1)
            player.stop()
            self._current_player = None

    def _flush(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        if self._current_player:
            try:
                self._current_player.stop()
            except Exception:
                pass
            self._current_player = None

    def stop(self):
        self._enabled = False
        self._running = False
        self._flush()
        print("[TTS] Stopped")
