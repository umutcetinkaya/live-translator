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
DUCK_VOLUME = 0.25


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

    def _duck(self):
        """Lower system volume so the spoken translation stands out."""
        if self._duck_ratio >= 1.0 or self._pre_duck_volume is not None:
            return
        current = _system_volume()
        if current is None:
            return
        self._pre_duck_volume = current
        _set_system_volume(current * self._duck_ratio)

    def _unduck(self):
        """Restore the volume captured by the matching _duck()."""
        if self._pre_duck_volume is None:
            return
        level, self._pre_duck_volume = self._pre_duck_volume, None
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
            player.setVolume_(1.0)
            self._duck()
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
