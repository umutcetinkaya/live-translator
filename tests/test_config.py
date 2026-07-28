from config import DEFAULTS, MODELS, normalize_model


def test_new_default_keys():
    for k in ("translation_provider", "gemini_api_key", "realtime_mode"):
        assert k in DEFAULTS

def test_default_provider_openai():
    assert DEFAULTS["translation_provider"] == "openai"

def test_models_per_provider():
    assert "openai" in MODELS and "gemini" in MODELS
    assert "gpt-5.4-mini" in MODELS["openai"]
    assert "gemini-2.5-flash" in MODELS["gemini"]

def test_legacy_model_normalized():
    assert normalize_model("o1", "openai") == "gpt-5.4-mini"
    assert normalize_model("gpt-5.4-mini", "openai") == "gpt-5.4-mini"
    assert normalize_model("gemini-2.5-flash", "gemini") == "gemini-2.5-flash"

def test_claude_models_listed():
    assert MODELS["claude"] == [
        "claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5",
    ]

def test_claude_default_key_present():
    assert DEFAULTS["anthropic_api_key"] == ""

def test_normalize_model_claude_fallback():
    # Geçersiz model claude varsayılanına düşmeli
    assert normalize_model("gpt-5.5", "claude") == "claude-haiku-4-5"
    assert normalize_model("claude-sonnet-5", "claude") == "claude-sonnet-5"

