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
