import pytest
from providers.base import (
    ProviderError, TranslationProvider, TTSProvider,
)

def test_translation_provider_is_abstract():
    with pytest.raises(TypeError):
        TranslationProvider()

def test_tts_provider_is_abstract():
    with pytest.raises(TypeError):
        TTSProvider()

def test_provider_error_is_exception():
    assert issubclass(ProviderError, Exception)

def test_concrete_translation_provider_must_implement_translate_document():
    class Incomplete(TranslationProvider):
        pass
    with pytest.raises(TypeError):
        Incomplete()

def test_concrete_tts_provider_must_implement_synthesize():
    class Incomplete(TTSProvider):
        pass
    with pytest.raises(TypeError):
        Incomplete()
