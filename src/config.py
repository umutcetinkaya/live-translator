"""Application configuration — loaded/saved from JSON file."""

import json
import os

CONFIG_PATH = os.path.expanduser("~/.live-translator.json")

DEFAULTS = {
    "translation_provider": "openai",
    "openai_api_key": "",
    "gemini_api_key": "",
    "source_lang": "en",
    "source_locale": "en-US",
    "target_lang": "tr",
    "model": "gpt-5.4-mini",
    "tts_provider": "piper",
    "tts_voice": "nova",
    "tts_speed": 1.0,
    "realtime_mode": False,
}

# Provider başına geçerli modeller (ilk eleman = varsayılan)
MODELS = {
    "openai": ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5"],
    "gemini": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"],
}


def normalize_model(model, provider):
    """Geçersiz/eski model isimlerini provider varsayılanına düşür."""
    valid = MODELS.get(provider, [])
    if model in valid:
        return model
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


def load_config():
    config = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config.update(json.load(f))
        except Exception:
            pass
    return config


def save_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Save error: {e}")


# Audio capture defaults
SAMPLE_RATE = 16000
CHANNEL_COUNT = 1
DEFAULT_LOCALE = "en-US"
RECOGNITION_TIMEOUT = 50
SILENCE_THRESHOLD = 2.0
MIN_SEGMENT_LENGTH = 3
OVERLAY_OPACITY = 0.95
