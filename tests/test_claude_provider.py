"""Claude (Anthropic) çeviri provider testleri.

Anthropic'in ses API'si yok; bu provider yalnızca metin çevirisi yapar.
Prompt caching için system prompt SABİT tutulmalı — değişken içerik
mesaj gövdesine gider, yoksa cache öneki her istekte geçersiz olur.
"""

import pytest
from unittest.mock import MagicMock
from providers.claude import ClaudeTranslationProvider, SYSTEM_PROMPT, MAX_TOKENS
from providers.base import ProviderError


def _fake_client(text="Merhaba dünya"):
    client = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    client.messages.create.return_value = MagicMock(content=[block])
    return client


def test_no_client_raises_provider_error():
    p = ClaudeTranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")


def test_returns_translated_text():
    client = _fake_client("Merhaba dünya")
    p = ClaudeTranslationProvider(client=client)
    out = p.translate_document("Hello world", "", "Turkish", "claude-haiku-4-5")
    assert out == "Merhaba dünya"


def test_sends_required_params():
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5"
    assert kwargs["max_tokens"] == MAX_TOKENS
    assert kwargs["messages"][0]["role"] == "user"


def test_system_prompt_is_cacheable_block():
    """System prompt cache_control taşımalı — 3 sn'de bir aynı önek gidiyor."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    system = client.messages.create.call_args.kwargs["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_system_prompt_identical_across_calls():
    """Cache prefix eşleşmesi: system bloğu bayt bayt aynı kalmalı."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    first = client.messages.create.call_args.kwargs["system"][0]["text"]
    p.translate_document("Hello again, much more text", "Merhaba", "Turkish",
                         "claude-haiku-4-5")
    second = client.messages.create.call_args.kwargs["system"][0]["text"]
    assert first == second == SYSTEM_PROMPT


def test_target_language_goes_in_message_not_system():
    """Hedef dil değişkendir; system'e girerse cache her dil için ayrışır."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    system_text = client.messages.create.call_args.kwargs["system"][0]["text"]
    user_text = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Turkish" not in system_text
    assert "Turkish" in user_text


def test_sonnet_disables_thinking():
    """Sonnet 5'te adaptive thinking varsayılan AÇIK — gecikme ekler, kapatılmalı."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-sonnet-5")
    kwargs = client.messages.create.call_args.kwargs
    assert kwargs["thinking"] == {"type": "disabled"}


def test_haiku_omits_thinking():
    """Haiku 4.5 thinking desteklemez; parametre gönderilmemeli."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    assert "thinking" not in client.messages.create.call_args.kwargs


def test_haiku_omits_effort():
    """Haiku effort de kabul etmez."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")
    assert "output_config" not in client.messages.create.call_args.kwargs


def test_reasoning_models_disable_thinking_without_effort():
    """Thinking kapatılır; effort GÖNDERİLMEZ.

    Ölçüldü: Sonnet 5'te effort=low gecikmeyi 2.19s -> 3.49s'e ÇIKARIYOR.
    Sezgiye aykırı, o yüzden test ediyoruz — biri 'hızlansın diye' effort
    eklemeye kalkarsa burada yakalanır."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    for model in ("claude-sonnet-5", "claude-opus-5"):
        p.translate_document("Hello", "", "Turkish", model)
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["thinking"] == {"type": "disabled"}, model
        assert "output_config" not in kwargs, model


def test_max_tokens_leaves_room_for_long_documents():
    """Canlı doküman her turda tam gönderilir; 4096 uzun çeviriyi kesiyordu."""
    assert MAX_TOKENS >= 16000


def test_unknown_model_sends_no_tuning():
    """Tanınmayan model için ekstra parametre gönderilmemeli (400 riski)."""
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello", "", "Turkish", "claude-future-9")
    kwargs = client.messages.create.call_args.kwargs
    assert "thinking" not in kwargs and "output_config" not in kwargs


def test_prev_translation_included_when_present():
    client = _fake_client()
    p = ClaudeTranslationProvider(client=client)
    p.translate_document("Hello world", "Merhaba", "Turkish", "claude-haiku-4-5")
    user_text = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Merhaba" in user_text


def test_api_error_wrapped_in_provider_error():
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("boom")
    p = ClaudeTranslationProvider(client=client)
    with pytest.raises(ProviderError):
        p.translate_document("Hello", "", "Turkish", "claude-haiku-4-5")


def test_non_text_blocks_ignored():
    """Yanıt metin dışı blok içerirse yalnızca metin toplanmalı."""
    client = MagicMock()
    thinking = MagicMock()
    thinking.type = "thinking"
    text = MagicMock()
    text.type = "text"
    text.text = "Merhaba"
    client.messages.create.return_value = MagicMock(content=[thinking, text])
    p = ClaudeTranslationProvider(client=client)
    assert p.translate_document("Hi", "", "Turkish", "claude-haiku-4-5") == "Merhaba"
