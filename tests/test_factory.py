import pytest
from unittest.mock import patch, MagicMock
from providers import get_translation_provider, get_tts_provider
from providers.openai import OpenAITranslationProvider, OpenAITTSProvider
from providers.gemini import GeminiTranslationProvider
from providers.piper import PiperTTSProvider
from providers.base import ProviderError


@patch("providers._make_openai_client", return_value=MagicMock())
def test_openai_translation(_):
    cfg = {"translation_provider": "openai", "openai_api_key": "k"}
    assert isinstance(get_translation_provider(cfg), OpenAITranslationProvider)

@patch("providers._make_gemini_client", return_value=MagicMock())
def test_gemini_translation(_):
    cfg = {"translation_provider": "gemini", "gemini_api_key": "k"}
    assert isinstance(get_translation_provider(cfg), GeminiTranslationProvider)

def test_unknown_translation_provider_raises():
    with pytest.raises(ProviderError):
        get_translation_provider({"translation_provider": "nope"})

def test_piper_tts():
    assert isinstance(get_tts_provider({"tts_provider": "piper"}), PiperTTSProvider)

@patch("providers._make_openai_client", return_value=MagicMock())
def test_openai_tts(_):
    cfg = {"tts_provider": "openai", "openai_api_key": "k"}
    assert isinstance(get_tts_provider(cfg), OpenAITTSProvider)
