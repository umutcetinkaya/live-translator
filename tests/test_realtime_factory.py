import pytest
from providers import get_realtime_provider
from providers.realtime_openai import OpenAIRealtimeProvider
from providers.realtime_gemini import GeminiRealtimeProvider
from providers.base import ProviderError


def test_openai_realtime():
    cfg = {"translation_provider": "openai", "openai_api_key": "k",
           "model": "gpt-realtime-translate"}
    assert isinstance(get_realtime_provider(cfg), OpenAIRealtimeProvider)

def test_gemini_realtime():
    cfg = {"translation_provider": "gemini", "gemini_api_key": "k",
           "model": "gemini-2.5-flash-live"}
    assert isinstance(get_realtime_provider(cfg), GeminiRealtimeProvider)

def test_unknown_raises():
    with pytest.raises(ProviderError):
        get_realtime_provider({"translation_provider": "nope"})
