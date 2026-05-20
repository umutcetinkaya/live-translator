import pytest
from unittest.mock import MagicMock
from providers.openai import OpenAITranslationProvider
from providers.base import ProviderError, TranslationProvider


def _fake_client(content):
    client = MagicMock()
    msg = MagicMock()
    msg.message.content = content
    client.chat.completions.create.return_value = MagicMock(choices=[msg])
    return client

def test_is_translation_provider():
    assert issubclass(OpenAITranslationProvider, TranslationProvider)

def test_translate_document_returns_text():
    p = OpenAITranslationProvider(client=_fake_client("Merhaba dünya"))
    out = p.translate_document("Hello world", "", "Turkish", "gpt-5.4-mini")
    assert out == "Merhaba dünya"

def test_translate_document_includes_previous_in_prompt():
    client = _fake_client("Merhaba dünya nasılsın")
    p = OpenAITranslationProvider(client=client)
    p.translate_document("Hello world how are you", "Merhaba dünya",
                         "Turkish", "gpt-5.4-mini")
    sent = client.chat.completions.create.call_args.kwargs
    user_msg = sent["messages"][1]["content"]
    assert "Merhaba dünya" in user_msg

def test_no_client_raises_provider_error():
    p = OpenAITranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "gpt-5.4-mini")

def test_api_error_wrapped_as_provider_error():
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("boom")
    p = OpenAITranslationProvider(client=client)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "gpt-5.4-mini")
