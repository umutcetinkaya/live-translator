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
    "source_locale": "en-US",
    "target_lang": "tr",
    "model": "gpt-6-luna",
    "tts_provider": "piper",
    "tts_voice": "marin",
    "tts_speed": 1.0,
    "tts_enabled": False,
    "realtime_mode": False,
    # Ask GitHub once per launch whether a newer release exists.
    "check_for_updates": True,
}

MODELS = {
    "local": [LOCAL_MODELS["small"], LOCAL_MODELS["standard"], LOCAL_MODELS["large"]],
    # First entry is the default: fast and cheap, which suits live subtitles.
    "openai": ["gpt-6-luna", "gpt-6.1-terra", "gpt-6.2-sol"],
    "gemini": ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"],
    "claude": ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"],
}


# Models dropped from the lists, mapped to the successor each provider
# recommends, so an update keeps the tier the user picked instead of
# dropping them to the cheapest model.
MODEL_SUCCESSORS = {
    "claude-haiku-4-5": "claude-haiku-5-5",
    "claude-sonnet-5": "claude-sonnet-5-5",
    "claude-opus-5": "claude-opus-5-5",
    "gpt-5.4-nano": "gpt-6-luna",
    "gpt-5.4-mini": "gpt-6.1-terra",
    "gpt-5.5": "gpt-6.2-sol",
    "gemini-2.5-flash": "gemini-3.5-flash-lite",
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-3.5-flash": "gemini-3.6-flash",
}


def normalize_model(model, provider):
    """Normalize invalid/outdated model names to the provider default."""
    valid = MODELS.get(provider, [])
    if model in valid:
        return model
    if MODEL_SUCCESSORS.get(model) in valid:
        return MODEL_SUCCESSORS[model]
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
    "Turkish": "tr-TR",
    "Dutch": "nl-NL",
    "Polish": "pl-PL",
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
    "Nederlands": "nl",
    "Polski": "pl",
}

# English names the translation prompts use for each target language code.
LANGUAGE_NAMES = {
    "tr": "Turkish", "en": "English", "de": "German", "fr": "French",
    "es": "Spanish", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
    "ko": "Korean", "ru": "Russian", "ar": "Arabic", "pt": "Portuguese",
    "nl": "Dutch", "pl": "Polish",
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

