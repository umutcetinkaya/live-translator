"""Text-to-Speech — Piper (offline) or OpenAI (cloud).

Queue-based: translations are read in order, never skipped.
Uses AVAudioPlayer (same process) so excludesCurrentProcessAudio filters it.
"""

import os
import wave
import threading
import tempfile
import time
import queue
from config import load_config

# Find models dir — works both from source and .app bundle
def _find_models_dir():
    # Try relative to this file
    for base in [
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.dirname(os.path.dirname(__file__)) if os.path.dirname(__file__) else None,
    ]:
        if base:
            candidate = os.path.join(base, "models")
            if os.path.isdir(candidate):
                return candidate
    # Try from sys.argv[0] (main.py location)
    import sys
    if sys.argv:
        candidate = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "models")
        if os.path.isdir(candidate):
            return candidate
    # Try cwd
    if os.path.isdir("models"):
        return os.path.abspath("models")
    return os.path.join(os.path.dirname(__file__), "models")

MODELS_DIR = _find_models_dir()

PIPER_VOICES = {
    "tr": "tr_TR-dfki-medium",
    "en": "en_US-amy-medium",
    "de": "de_DE-thorsten-medium",
    "fr": "fr_FR-siwis-medium",
    "es": "es_ES-sharvard-medium",
    "it": "it_IT-riccardo-x_low",
    "zh": "zh_CN-huayan-medium",
    "ru": "ru_RU-denis-medium",
    "ar": "ar_JO-kareem-medium",
    "pt": "pt_BR-faber-medium",
}


class TextToSpeech:

    def __init__(self, config=None):
        self._config = config or load_config()
        self._enabled = False
        self._lang = self._config.get("target_lang", "tr")
        self._provider = self._config.get("tts_provider", "piper")
        self._voice_speed = self._config.get("tts_speed", 1.0)
        self._queue = queue.Queue()
        self._worker = None
        self._running = True
        self._current_process = None
        self._piper_voice = None
        self._openai_client = None

        self._load_provider()

    def _load_provider(self):
        if self._provider == "piper":
            self._load_piper()
        elif self._provider == "openai":
            self._load_openai()

    def _load_piper(self):
        model_name = PIPER_VOICES.get(self._lang)
        if not model_name:
            self._piper_voice = None
            return
        model_path = os.path.join(MODELS_DIR, f"{model_name}.onnx")
        if not os.path.exists(model_path):
            self._piper_voice = None
            return
        try:
            from piper import PiperVoice
            self._piper_voice = PiperVoice.load(model_path)
            print(f"[TTS] Piper loaded: {model_name}")
        except Exception as e:
            print(f"[TTS] Piper error: {e}")
            self._piper_voice = None

    def _load_openai(self):
        try:
            from openai import OpenAI
            key = self._config.get("openai_api_key", "")
            if key:
                self._openai_client = OpenAI(api_key=key)
                print("[TTS] OpenAI TTS ready")
        except Exception as e:
            print(f"[TTS] OpenAI error: {e}")

    @property
    def enabled(self):
        return self._enabled

    def toggle(self):
        self._enabled = not self._enabled
        if self._enabled and not self._worker:
            self._start_worker()
        if not self._enabled:
            self._flush()
        print(f"[TTS] {'ON' if self._enabled else 'OFF'} ({self._provider})")
        return self._enabled

    def set_enabled(self, val):
        self._enabled = val
        if val and not self._worker:
            self._start_worker()

    def set_language(self, lang_code):
        if lang_code == self._lang:
            return
        self._lang = lang_code
        self._load_provider()

    def update_config(self, config):
        self._config = config
        new_provider = config.get("tts_provider", "piper")
        new_speed = config.get("tts_speed", 1.0)
        changed = new_provider != self._provider or new_speed != self._voice_speed
        self._provider = new_provider
        self._voice_speed = new_speed
        if changed:
            self._load_provider()

    def speak(self, text):
        if not self._enabled or not text:
            return
        self._queue.put(text)

    def _start_worker(self):
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def _worker_loop(self):
        tmp_path = os.path.join(tempfile.gettempdir(), "tts_output.wav")
        while self._running:
            try:
                text = self._queue.get(timeout=1)
            except queue.Empty:
                continue
            if not self._enabled:
                continue
            try:
                if self._provider == "openai":
                    self._speak_openai(text, tmp_path)
                else:
                    self._speak_piper(text, tmp_path)
            except Exception as e:
                print(f"[TTS] Error: {e}")

    def _speak_piper(self, text, tmp_path):
        if not self._piper_voice:
            return
        with wave.open(tmp_path, "wb") as f:
            self._piper_voice.synthesize_wav(text, f)
        self._play_file(tmp_path)

    def _speak_openai(self, text, tmp_path):
        if not self._openai_client:
            return
        voice = self._config.get("tts_voice", "nova")
        response = self._openai_client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=self._voice_speed,
        )
        mp3_path = tmp_path.replace(".wav", ".mp3")
        response.stream_to_file(mp3_path)
        self._play_file(mp3_path)

    def _play_file(self, path):
        """Play via AVAudioPlayer (same process — excludesCurrentProcessAudio filters it)."""
        from AVFoundation import AVAudioPlayer
        from Foundation import NSURL

        url = NSURL.fileURLWithPath_(path)
        player, error = AVAudioPlayer.alloc().initWithContentsOfURL_error_(url, None)
        if player and not error:
            player.setVolume_(1.0)
            player.play()
            self._current_process = player
            while player.isPlaying() and self._enabled:
                time.sleep(0.1)
            player.stop()
            self._current_process = None

    def _flush(self):
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
        if self._current_process:
            try:
                self._current_process.stop()
            except Exception:
                pass
            self._current_process = None

    def stop(self):
        self._enabled = False
        self._running = False
        self._flush()
        print("[TTS] Stopped")
