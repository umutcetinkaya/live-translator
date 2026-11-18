"""Piper offline TTS provider.

Voice models ship with source checkouts (`make models`). Packaged installs
fetch the voice for the current language the first time Piper is used.
"""

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


# Path of each voice inside the rhasspy/piper-voices repository.
PIPER_REPO = "rhasspy/piper-voices"
PIPER_PATHS = {
    "tr": "tr/tr_TR/dfki/medium",
    "en": "en/en_US/amy/medium",
    "de": "de/de_DE/thorsten/medium",
    "fr": "fr/fr_FR/siwis/medium",
    "es": "es/es_ES/sharvard/medium",
    "it": "it/it_IT/riccardo/x_low",
    "zh": "zh/zh_CN/huayan/medium",
    "ru": "ru/ru_RU/denis/medium",
    "ar": "ar/ar_JO/kareem/medium",
    "pt": "pt/pt_BR/faber/medium",
}


def download_voice(lang, cache_dir):
    """Fetch one voice (.onnx + .onnx.json) into cache_dir; returns the .onnx path."""
    import shutil
    from huggingface_hub import hf_hub_download
    name = PIPER_VOICES[lang]
    staging = os.path.join(cache_dir, ".download")
    os.makedirs(staging, exist_ok=True)
    # The .json goes first: the .onnx appearing is what marks the voice usable.
    for ext in (".onnx.json", ".onnx"):
        src = hf_hub_download(PIPER_REPO, f"{PIPER_PATHS[lang]}/{name}{ext}",
                              local_dir=staging)
        os.replace(src, os.path.join(cache_dir, name + ext))
    shutil.rmtree(staging, ignore_errors=True)
    return os.path.join(cache_dir, name + ".onnx")


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
    def __init__(self, models_dir=None, tmp_dir=None, downloader=None, cache_dir=None):
        self._models_dir = models_dir or find_models_dir()
        self._tmp_dir = tmp_dir or tempfile.gettempdir()
        self._downloader = downloader or download_voice
        self._cache_override = cache_dir
        self._voice = None
        self._voice_lang = None

    def _cache_dir(self):
        if self._cache_override:
            return self._cache_override
        import model_store
        return os.path.join(model_store.MODELS_ROOT, "piper")

    def ensure_model(self, lang):
        """Path of the voice model for `lang`, downloading it if needed."""
        model_name = PIPER_VOICES.get(lang)
        if not model_name:
            raise ProviderError(f"Piper: no voice for '{lang}'")
        for folder in (self._models_dir, self._cache_dir()):
            path = os.path.join(folder, f"{model_name}.onnx")
            if os.path.exists(path):
                return path
        try:
            return self._downloader(lang, self._cache_dir())
        except Exception as e:
            raise ProviderError(f"Piper: could not download voice '{lang}': {e}") from e

    def _ensure_voice(self, lang):
        if self._voice is not None and self._voice_lang == lang:
            return
        model_path = self.ensure_model(lang)
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
