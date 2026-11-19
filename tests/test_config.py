from config import DEFAULTS, MODELS, normalize_model


def test_new_default_keys():
    for k in ("translation_provider", "gemini_api_key", "realtime_mode"):
        assert k in DEFAULTS

def test_default_provider_is_free_when_supported(monkeypatch):
    import config, local_models
    monkeypatch.setattr(local_models, "is_supported", lambda *a, **k: True)
    assert config.fresh_defaults()["translation_provider"] == "local"
    monkeypatch.setattr(local_models, "is_supported", lambda *a, **k: False)
    assert config.fresh_defaults()["translation_provider"] == "openai"

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


def test_local_models_listed():
    from local_models import LOCAL_MODELS
    assert MODELS["local"] == [LOCAL_MODELS["small"], LOCAL_MODELS["standard"], LOCAL_MODELS["large"]]

def test_normalize_model_local_falls_back_to_ram_default(monkeypatch):
    # Geçersiz ya da eski (ör. Qwen) model bu Mac'e uygun modele düşmeli, seçili büyük model korunmalı
    import local_models
    monkeypatch.setattr(local_models, "total_ram_bytes", lambda: 8 * 1024 ** 3)
    assert normalize_model("mlx-community/Qwen3-4B-Instruct-2507-4bit", "local") == \
        local_models.LOCAL_MODELS["small"]
    assert normalize_model(local_models.LOCAL_MODELS["large"], "local") == \
        local_models.LOCAL_MODELS["large"]
