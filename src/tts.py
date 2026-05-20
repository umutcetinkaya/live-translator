"""Text-to-Speech orchestrator — delegates synthesis to TTSProvider.

Queue-based: translations are spoken in order. Played via AVAudioPlayer (same process);
no feedback loop thanks to excludesCurrentProcessAudio.
"""

import threading
import time
import queue
from config import load_config
from providers import get_tts_provider
from providers.base import ProviderError


class TextToSpeech:
    def __init__(self, config=None):
        self._config = config or load_config()
        self._enabled = False
        self._lang = self._config.get("target_lang", "tr")
        self._voice = self._config.get("tts_voice", "nova")
        self._speed = self._config.get("tts_speed", 1.0)
        self._queue = queue.Queue()
        self._worker = None
        self._running = True
        self._current_player = None
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

    def _synthesize_and_play(self, text):
        try:
            path = self._provider.synthesize(text, self._lang, self._voice,
                                             self._speed)
        except ProviderError as e:
            print(f"[TTS] {e}")
            return
        except Exception as e:
            print(f"[TTS] Unexpected: {e}")
            return
        if path:
            self._play_file(path)

    def _play_file(self, path):
        from AVFoundation import AVAudioPlayer
        from Foundation import NSURL
        url = NSURL.fileURLWithPath_(path)
        player, error = AVAudioPlayer.alloc().initWithContentsOfURL_error_(url, None)
        if player and not error:
            player.setVolume_(1.0)
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
