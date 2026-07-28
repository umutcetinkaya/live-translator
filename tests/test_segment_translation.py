"""Segment çevirisi testleri — provider yalnızca YENİ metni çevirmeli.

Doküman modelinde her turda tüm metin yeniden yazılıyordu: çıktı token
sınırına çarpıp kesiliyor, uzun bağlamda model önceki cümleleri tekrar
etmeye başlıyordu. Artık bağlam salt-okunur veriliyor, çeviri kısa kalıyor.
"""

from unittest.mock import MagicMock
import pytest

from providers.claude import ClaudeTranslationProvider
from providers.openai import OpenAITranslationProvider
from providers.gemini import GeminiTranslationProvider
from providers.base import ProviderError


def _claude_client(text="Merhaba"):
    c = MagicMock()
    b = MagicMock()
    b.type = "text"
    b.text = text
    c.messages.create.return_value = MagicMock(content=[b])
    return c


def _openai_client(text="Merhaba"):
    c = MagicMock()
    msg = MagicMock()
    msg.content = text
    c.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=msg)])
    return c


def _gemini_client(text="Merhaba"):
    c = MagicMock()
    c.models.generate_content.return_value = MagicMock(text=text)
    return c


# --- Claude ---

def test_claude_translates_only_the_segment():
    c = _claude_client("İkinci cümle.")
    p = ClaudeTranslationProvider(client=c)
    out = p.translate_segment("Second sentence.", "First sentence.",
                              "Turkish", "claude-haiku-4-5")
    assert out == "İkinci cümle."


def test_claude_marks_context_read_only():
    """Bağlam çevrilmeyecek diye prompt'ta açıkça işaretlenmeli."""
    c = _claude_client()
    p = ClaudeTranslationProvider(client=c)
    p.translate_segment("New text.", "Old context.", "Turkish",
                        "claude-haiku-4-5")
    msg = c.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Old context." in msg and "New text." in msg
    low = msg.lower()
    assert "do not translate" in low or "only this" in low


def test_claude_segment_output_is_bounded():
    """Segment kısa; büyük max_tokens gerekmez ve kesilme riski kalkar."""
    c = _claude_client()
    p = ClaudeTranslationProvider(client=c)
    p.translate_segment("Short.", "", "Turkish", "claude-haiku-4-5")
    assert c.messages.create.call_args.kwargs["max_tokens"] <= 2000


def test_claude_works_without_context():
    c = _claude_client()
    p = ClaudeTranslationProvider(client=c)
    p.translate_segment("First.", "", "Turkish", "claude-haiku-4-5")
    assert c.messages.create.called


def test_claude_no_client_raises():
    p = ClaudeTranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_segment("x", "", "Turkish", "claude-haiku-4-5")


def test_claude_empty_segment_skips_api_call():
    c = _claude_client()
    p = ClaudeTranslationProvider(client=c)
    assert p.translate_segment("   ", "ctx", "Turkish", "claude-haiku-4-5") == ""
    assert not c.messages.create.called


def test_claude_segment_keeps_prompt_cacheable():
    """Sistem prompt'u sabit kalmalı — her turda aynı önek gidiyor."""
    c = _claude_client()
    p = ClaudeTranslationProvider(client=c)
    p.translate_segment("A.", "x", "Turkish", "claude-haiku-4-5")
    first = c.messages.create.call_args.kwargs["system"][0]
    p.translate_segment("B.", "y", "German", "claude-haiku-4-5")
    second = c.messages.create.call_args.kwargs["system"][0]
    assert first["text"] == second["text"]
    assert second["cache_control"] == {"type": "ephemeral"}


# --- OpenAI ---

def test_openai_translates_only_the_segment():
    c = _openai_client("İkinci.")
    p = OpenAITranslationProvider(client=c)
    assert p.translate_segment("Second.", "First.", "Turkish",
                               "gpt-5.4-mini") == "İkinci."


def test_openai_empty_segment_skips_api_call():
    c = _openai_client()
    p = OpenAITranslationProvider(client=c)
    assert p.translate_segment("", "ctx", "Turkish", "gpt-5.4-mini") == ""
    assert not c.chat.completions.create.called


def test_openai_no_client_raises():
    p = OpenAITranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_segment("x", "", "Turkish", "gpt-5.4-mini")


# --- Gemini ---

def test_gemini_translates_only_the_segment():
    c = _gemini_client("İkinci.")
    p = GeminiTranslationProvider(client=c)
    assert p.translate_segment("Second.", "First.", "Turkish",
                               "gemini-2.5-flash") == "İkinci."


def test_gemini_empty_segment_skips_api_call():
    c = _gemini_client()
    p = GeminiTranslationProvider(client=c)
    assert p.translate_segment("  ", "ctx", "Turkish", "gemini-2.5-flash") == ""
    assert not c.models.generate_content.called


def test_gemini_no_client_raises():
    p = GeminiTranslationProvider(client=None)
    with pytest.raises(ProviderError):
        p.translate_segment("x", "", "Turkish", "gemini-2.5-flash")


def test_all_providers_share_the_segment_contract():
    """Üç provider da aynı imzayla çağrılabilmeli."""
    for prov, client, model in (
        (ClaudeTranslationProvider, _claude_client(), "claude-haiku-4-5"),
        (OpenAITranslationProvider, _openai_client(), "gpt-5.4-mini"),
        (GeminiTranslationProvider, _gemini_client(), "gemini-2.5-flash"),
    ):
        assert prov(client=client).translate_segment(
            "Hello.", "ctx", "Turkish", model) == "Merhaba"
