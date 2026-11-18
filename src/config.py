"""Application configuration — loaded/saved from JSON file."""

import json
import os

import local_models
from local_models import LOCAL_MODELS

CONFIG_PATH = os.path.expanduser("~/.live-translator.json")

DEFAULTS = {
    "translation_provider": "openai",
    "openai_api_key": "",
    "gemini_api_key": "",
    "anthropic_api_key": "",
    "source_lang": "en",
    "source_locale": "en-US",
    "target_lang": "tr",
    "model": "gpt-5.4-mini",
    "tts_provider": "piper",
    "tts_voice": "nova",
    "tts_speed": 1.0,
    "tts_enabled": False,
    "realtime_mode": False,
}

MODELS = {
    "local": [LOCAL_MODELS["standard"], LOCAL_MODELS["small"]],
    "openai": ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"],
    "claude": ["claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5"],
}


def normalize_model(model, provider):
    """Normalize invalid/outdated model names to the provider default."""
    valid = MODELS.get(provider, [])
    if model in valid:
        return model
    if provider == "local":
        # The default local model depends on this Mac's memory.
        return local_models.default_model()
    return valid[0] if valid else model

SOURCE_LANGUAGES = {
    "English": "en-US",
    "German": "de-DE",
    "French": "fr-FR",
    "Spanish": "es-ES",
    "Italian": "it-IT",
    "Japanese": "ja-JP",
    "Chinese": "zh-CN",
    "Korean": "ko-KR",
    "Russian": "ru-RU",
    "Arabic": "ar-SA",
    "Portuguese": "pt-BR",
}

TARGET_LANGUAGES = {
    "Türkçe": "tr",
    "English": "en",
    "Deutsch": "de",
    "Français": "fr",
    "Español": "es",
    "Italiano": "it",
    "日本語": "ja",
    "中文": "zh",
    "한국어": "ko",
    "Русский": "ru",
    "العربية": "ar",
    "Português": "pt",
}


def fresh_defaults():
    """Defaults for a brand-new install: free and on-device where possible."""
    config = dict(DEFAULTS)
    if local_models.is_supported():
        config.update({
            "translation_provider": "local",
            "model": local_models.default_model(),
            "tts_provider": "system",
        })
    config["tts_enabled"] = True
    return config


def _legacy_defaults(saved):
    """Defaults for a config written before the free mode existed.

    Those files never stored `translation_provider` (the setup wizard did not
    write it), so the provider is inferred from whichever API key is present.
    Speech stays off: turning it on unasked could mean paid TTS calls."""
    config = dict(DEFAULTS)
    for key, provider in (("openai_api_key", "openai"),
                          ("gemini_api_key", "gemini"),
                          ("anthropic_api_key", "claude")):
        if saved.get(key):
            config["translation_provider"] = provider
            break
    config["tts_enabled"] = False
    return config


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return fresh_defaults()
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            saved = {}
    except Exception:
        saved = {}
    config = _legacy_defaults(saved)
    config.update(saved)
    return config


def save_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Save error: {e}")


SAMPLE_RATE = 16000
CHANNEL_COUNT = 1
DEFAULT_LOCALE = "en-US"
RECOGNITION_TIMEOUT = 50
SILENCE_THRESHOLD = 2.0
MIN_SEGMENT_LENGTH = 3
OVERLAY_OPACITY = 0.95

