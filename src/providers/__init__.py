"""Provider factory — config'e göre uygun provider'ı döner."""

from providers.base import ProviderError
from providers.openai import OpenAITranslationProvider, OpenAITTSProvider
from providers.gemini import GeminiTranslationProvider, GeminiTTSProvider
from providers.piper import PiperTTSProvider


def _make_openai_client(config):
    key = config.get("openai_api_key", "")
    if not key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=key)


def _make_gemini_client(config):
    key = config.get("gemini_api_key", "")
    if not key:
        return None
    from google import genai
    return genai.Client(api_key=key)


def get_translation_provider(config):
    name = config.get("translation_provider", "openai")
    if name == "openai":
        return OpenAITranslationProvider(client=_make_openai_client(config))
    if name == "gemini":
        return GeminiTranslationProvider(client=_make_gemini_client(config))
    raise ProviderError(f"Bilinmeyen çeviri provider'ı: {name}")


def get_tts_provider(config):
    name = config.get("tts_provider", "piper")
    if name == "piper":
        return PiperTTSProvider()
    if name == "openai":
        return OpenAITTSProvider(client=_make_openai_client(config))
    if name == "gemini":
        return GeminiTTSProvider(client=_make_gemini_client(config))
    raise ProviderError(f"Bilinmeyen TTS provider'ı: {name}")
