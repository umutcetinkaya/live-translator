"""Text-to-Speech orchestrator — delegates synthesis to TTSProvider.

Queue-based: translations are spoken in order. Played via AVAudioPlayer (same process);
no feedback loop thanks to excludesCurrentProcessAudio.
"""

import threading
import time
import queue
import subprocess
from config import load_config
from providers import get_tts_provider
from providers.base import ProviderError


# Fraction of the original volume the source audio drops to while the
# translation is being spoken. 1.0 turns ducking off.
#
# The translation shares this output, so ducking too hard makes the
# translation quiet as well — 0.25 was low enough that users reported the
# spoken translation getting quiet along with the source. 0.45 keeps the
# source clearly in the background while leaving the translation audible.
DUCK_VOLUME = 0.45

# Never duck below this absolute level: at a low system setting, a purely
# relative duck would take the translation down with the source.
DUCK_FLOOR = 0.30

# Extra headroom on top of pure compensation, so the translation sits clearly
# above the ducked source rather than merely matching its pre-duck level.
TTS_BOOST = 1.3

# Ceiling on software gain — past this, quiet recordings clip instead of
# getting louder.
MAX_PLAYER_GAIN = 4.0


def _system_volume():
    """Current output volume as 0.0–1.0, or None if it can't be read."""
    try:
        out = subprocess.run(
            ["osascript", "-e", "output volume of (get volume settings)"],
            capture_output=True, text=True, timeout=2,
        )
        return int(out.stdout.strip()) / 100.0
    except Exception:
        return None


def _set_system_volume(level):
    """Set output volume from a 0.0–1.0 value."""
    try:
        pct = max(0, min(100, round(level * 100)))
        subprocess.run(["osascript", "-e", f"set volume output volume {pct}"],
                       capture_output=True, timeout=2)
    except Exception:
        pass


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
        # Simultaneous-interpreter behaviour: drop the source audio while the
        # translation is spoken, so the two don't talk over each other.
        # 1.0 disables ducking entirely.
        self._duck_ratio = float(self._config.get("duck_volume", DUCK_VOLUME))
        self._pre_duck_volume = None
        self._ducked_level = None
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
        if not self._enabled or not text:
            return
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
        """Playback gain for the spoken translation.

        The translation shares the output we just turned down, so ducking
        quiets it along with the source. AVAudioPlayer accepts volumes above
        1.0 (verified: 2.0 and 4.0 read back), so the loss is compensated in
        software — the source drops, the translation does not."""
        if self._pre_duck_volume is None:
            return 1.0
        ducked = self._ducked_level or self._pre_duck_volume
        if ducked <= 0:
            return 1.0
        gain = self._pre_duck_volume / ducked
        return min(gain * TTS_BOOST, MAX_PLAYER_GAIN)

    def _duck(self):
        """Lower system volume so the spoken translation stands out.

        The source drops to `duck_ratio`, while the translation plays at full
        player gain — that difference is what makes the translation audible
        over the original, interpreter-style."""
        if self._duck_ratio >= 1.0 or self._pre_duck_volume is not None:
            return
        current = _system_volume()
        if current is None:
            return
        self._pre_duck_volume = current
        # Duck relative to the user's own level, but never below a floor —
        # a very quiet system setting would otherwise make the translation
        # inaudible too, since both share this output.
        ducked = min(max(current * self._duck_ratio, DUCK_FLOOR), current)
        self._ducked_level = ducked
        _set_system_volume(ducked)

    def _unduck(self):
        """Restore the volume captured by the matching _duck()."""
        if self._pre_duck_volume is None:
            return
        level, self._pre_duck_volume = self._pre_duck_volume, None
        self._ducked_level = None
        _set_system_volume(level)

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
            self._play_file(path)

    def _play_file(self, path):
        from AVFoundation import AVAudioPlayer
        from Foundation import NSURL
        url = NSURL.fileURLWithPath_(path)
        player, error = AVAudioPlayer.alloc().initWithContentsOfURL_error_(url, None)
        if player and not error:
            # Duck first: the gain is computed from how far the output dropped.
            self._duck()
            player.setVolume_(self._player_gain())
            try:
                player.play()
                self._current_player = player
                while player.isPlaying() and self._enabled:
                    time.sleep(0.1)
                player.stop()
                self._current_player = None
            finally:
                self._unduck()

    def _flush(self):
        self._unduck()   # never leave the user's volume turned down
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
