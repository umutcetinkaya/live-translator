"""Bulut sağlayıcılarının güncel model listeleri ve modele özgü istek ayarları.

Kasım 2026: gemini-2.5-flash 1 Aralık'ta kapanıyor, gemini-3.5-flash 3.6'ya
yönleniyor, gpt-5 ailesi Aralık'ta kapanıyor, gemini-2.5-flash-preview-tts
18 Aralık'ta kapanıyor. Canlı altyazı için her modelde düşünme en aza
indirilir; yanlış parametre 400 döndürür, o yüzden model başına test edilir.
"""

import os
import re
from unittest.mock import MagicMock

from config import MODELS, DEFAULTS, normalize_model
from providers.claude import ClaudeTranslationProvider
from providers.openai import OpenAITranslationProvider
from providers.gemini import GeminiTranslationProvider
import providers.gemini as gemini_mod
from providers.realtime_openai import OpenAIRealtimeProvider


def test_model_lists_are_current():
    assert MODELS["openai"] == ["gpt-6-luna", "gpt-6.1-terra", "gpt-6.2-sol"]
    assert MODELS["gemini"] == ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.8-flash"]
    assert MODELS["claude"] == ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]


def test_previous_models_move_to_their_successor():
    # Kullanıcının seçtiği seviye korunmalı: Sonnet kullanan Haiku'ya düşmemeli.
    # Eşleşmeler sağlayıcıların kendi önerdiği halefler.
    expected = {
        ("claude-haiku-4-5", "claude"): "claude-haiku-5-5",
        ("claude-sonnet-5", "claude"): "claude-sonnet-5-5",
        ("claude-opus-5", "claude"): "claude-opus-5-5",
        ("gpt-5.4-nano", "openai"): "gpt-6-luna",
        ("gpt-5.4-mini", "openai"): "gpt-6.1-terra",
        ("gpt-5.5", "openai"): "gpt-6.2-sol",
        ("gemini-2.5-flash", "gemini"): "gemini-3.5-flash-lite",
        ("gemini-2.5-flash-lite", "gemini"): "gemini-3.5-flash-lite",
        ("gemini-3.5-flash", "gemini"): "gemini-3.6-flash",
    }
    for (old, provider), new in expected.items():
        assert normalize_model(old, provider) == new, old


def test_unknown_models_fall_back_to_default():
    assert normalize_model("gpt-4o-mini", "openai") == "gpt-6-luna"
    assert normalize_model("something", "gemini") == "gemini-3.5-flash-lite"
    assert DEFAULTS["model"] == "gpt-6-luna"


# --- OpenAI ---

def _openai_client():
    c = MagicMock()
    c.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Merhaba"))])
    return c


def _openai_kwargs(model):
    c = _openai_client()
    OpenAITranslationProvider(client=c).translate_segment("Hello", "", "Turkish", model)
    return c.chat.completions.create.call_args.kwargs


def test_gpt6_luna_and_terra_skip_reasoning():
    for model in ("gpt-6-luna", "gpt-6.1-terra"):
        kw = _openai_kwargs(model)
        assert kw["reasoning_effort"] == "none", model
        assert kw["messages"][0]["role"] == "developer"
        assert "max_completion_tokens" in kw and "temperature" not in kw


def test_gpt62_sol_uses_lowest_allowed_effort():
    # GPT-6.2 Sol, reasoning_effort "none" isteğini reddediyor
    assert _openai_kwargs("gpt-6.2-sol")["reasoning_effort"] == "low"


def test_unknown_openai_model_gets_no_reasoning_param():
    assert "reasoning_effort" not in _openai_kwargs("gpt-4o-mini")


# --- Gemini ---

def _gemini_config(model):
    c = MagicMock()
    c.models.generate_content.return_value = MagicMock(text="Merhaba")
    GeminiTranslationProvider(client=c).translate_segment("Hello", "", "Turkish", model)
    return c.models.generate_content.call_args.kwargs.get("config")


def test_gemini_thinking_kept_minimal():
    assert str(_gemini_config("gemini-3.5-flash-lite").thinking_config.thinking_level).endswith("MINIMAL")
    assert str(_gemini_config("gemini-3.6-flash").thinking_config.thinking_level).endswith("MINIMAL")
    # 3.8 Flash'ta en düşük seviye "low"
    assert str(_gemini_config("gemini-3.8-flash").thinking_config.thinking_level).endswith("LOW")


def test_unknown_gemini_model_gets_no_thinking_config():
    assert _gemini_config("gemini-x") is None


def test_gemini_tts_model_is_current():
    assert gemini_mod._TTS_MODEL == "gemini-3.8-flash-lite-tts"


# --- Claude ---

def _claude_kwargs(model):
    c = MagicMock()
    b = MagicMock(type="text", text="Merhaba")
    c.messages.create.return_value = MagicMock(content=[b])
    ClaudeTranslationProvider(client=c).translate_segment("Hello", "", "Turkish", model)
    return c.messages.create.call_args.kwargs


def test_claude_haiku_55_thinking_off():
    kw = _claude_kwargs("claude-haiku-5-5")
    assert kw["thinking"] == {"type": "disabled"}
    assert "output_config" not in kw


def test_claude_sonnet_55_uses_between_tools():
    # Sonnet 5.5'te {"type": "disabled"} 400 döner; düşünmeyi kapatmanın yolu between_tools
    kw = _claude_kwargs("claude-sonnet-5-5")
    assert kw["thinking"] == {"type": "between_tools"}
    assert "output_config" not in kw


def test_claude_opus_55_lowest_effort():
    # Opus 5.5'te düşünme kapatılamaz; tek kontrol effort
    kw = _claude_kwargs("claude-opus-5-5")
    assert "thinking" not in kw
    assert kw["output_config"] == {"effort": "low"}


def test_settings_preselect_the_successor_of_a_saved_model():
    # Ayarlar listede olmayan eski modeli görünce ilkini (Haiku) seçerdi; Kaydet'e
    # basan kullanıcı sessizce daha zayıf modele geçerdi.
    from tests.test_overlay_html import _load_build_html, _config
    html = _load_build_html()(_config(translation_provider="claude", model="claude-sonnet-5"))
    assert 'const CURRENT_MODEL = "claude-sonnet-5-5";' in html


# --- OpenAI realtime ---

def test_openai_realtime_always_uses_translate_model():
    # Metin modeli (ör. gpt-6-luna) çeviri uç noktasına gönderilmemeli
    seen = {}
    ws = MagicMock()
    ws.recv.return_value = ""

    def factory(url, headers):
        seen["url"] = url
        return ws
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-6-luna", ws_factory=factory)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    p.stop()
    assert seen["url"].endswith("?model=gpt-realtime-translate")


# --- Sihirbaz ---

def test_setup_wizard_key_path_uses_current_openai_default():
    root = os.path.dirname(os.path.dirname(__file__))
    swift = open(os.path.join(root, "scripts", "setup_wizard.swift")).read()
    written = re.findall(r'"model": "(gpt-[^"]+)"', swift)
    assert written == [MODELS["openai"][0]]
