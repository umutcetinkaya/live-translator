"""Piper offline TTS provider."""

import os
import wave
import tempfile
from providers.base import TTSProvider, ProviderError

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


def find_models_dir():
    here = os.path.dirname(os.path.realpath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    candidate = os.path.join(root, "models")
    if os.path.isdir(candidate):
        return candidate
    if os.path.isdir("models"):
        return os.path.abspath("models")
    return candidate


class PiperTTSProvider(TTSProvider):
    def __init__(self, models_dir=None, tmp_dir=None):
        self._models_dir = models_dir or find_models_dir()
        self._tmp_dir = tmp_dir or tempfile.gettempdir()
        self._voice = None
        self._voice_lang = None

    def _ensure_voice(self, lang):
        if self._voice is not None and self._voice_lang == lang:
            return
        model_name = PIPER_VOICES.get(lang)
        if not model_name:
            raise ProviderError(f"Piper: no voice for '{lang}'")
        model_path = os.path.join(self._models_dir, f"{model_name}.onnx")
        if not os.path.exists(model_path):
            raise ProviderError(f"Piper: model file not found: {model_path}")
        try:
            from piper import PiperVoice
            self._voice = PiperVoice.load(model_path)
            self._voice_lang = lang
        except Exception as e:
            raise ProviderError(f"Piper load error: {e}") from e

    def synthesize(self, text, lang, voice, speed):
        self._ensure_voice(lang)
        path = os.path.join(self._tmp_dir, "tts_output.wav")
        try:
            with wave.open(path, "wb") as f:
                self._voice.synthesize_wav(text, f)
            return path
        except Exception as e:
            raise ProviderError(f"Piper synthesis error: {e}") from e
