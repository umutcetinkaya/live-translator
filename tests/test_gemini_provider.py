import pytest
from unittest.mock import MagicMock
from providers.gemini import GeminiTranslationProvider
from providers.base import TranslationProvider, ProviderError


def _fake_client(text):
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(text=text)
    return client

def test_is_translation_provider():
    assert issubclass(GeminiTranslationProvider, TranslationProvider)

def test_translate_returns_text():
    p = GeminiTranslationProvider(client=_fake_client("Merhaba dünya"))
    out = p.translate_document("Hello world", "", "Turkish", "gemini-2.5-flash")
    assert out == "Merhaba dünya"

def test_previous_translation_in_prompt():
    client = _fake_client("Merhaba dünya nasılsın")
    p = GeminiTranslationProvider(client=client)
    p.translate_document("Hello how", "Merhaba dünya", "Turkish",
                         "gemini-2.5-flash")
    kwargs = client.models.generate_content.call_args.kwargs
    contents = kwargs.get("contents") or client.models.generate_content.call_args.args
    assert "Merhaba dünya" in str(contents)

def test_no_client_raises():
    p = GeminiTranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "gemini-2.5-flash")

def test_api_error_wrapped():
    client = MagicMock()
    client.models.generate_content.side_effect = RuntimeError("boom")
    p = GeminiTranslationProvider(client=client)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "gemini-2.5-flash")
