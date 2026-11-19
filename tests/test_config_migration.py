"""Ücretsiz modu varsayılan yaparken mevcut kullanıcıların ayarlarını koruma.

Swift kurulum sihirbazı config'e `translation_provider` yazmıyordu. "Eksik alan
yeni varsayılanı alır" kuralı bu kullanıcıları sessizce yerel modele geçirip
2,5 GB indirme başlatırdı; `tts_enabled` için de sormadan ücretli ses çağrısı
yapılırdı. Yeni varsayılanlar sadece config dosyası hiç yokken uygulanır.
"""

import json

import pytest

import config
import local_models


@pytest.fixture
def cfg_file(tmp_path, monkeypatch):
    path = tmp_path / "live-translator.json"
    monkeypatch.setattr(config, "CONFIG_PATH", str(path))
    monkeypatch.setattr(local_models, "is_supported", lambda *a, **k: True)
    monkeypatch.setattr(local_models, "total_ram_bytes", lambda: 32 * 1024 ** 3)

    def write(data):
        path.write_text(json.dumps(data))
    return write


def test_fresh_install_gets_free_defaults(cfg_file, monkeypatch):
    monkeypatch.setattr(local_models, "total_ram_bytes", lambda: 16 * 1024 ** 3)
    c = config.load_config()
    assert c["translation_provider"] == "local"
    assert c["model"] == local_models.LOCAL_MODELS["standard"]
    assert c["tts_provider"] == "system"
    assert c["tts_enabled"] is True


def test_fresh_install_low_ram_gets_small_model(cfg_file, monkeypatch):
    # 8 GB'lık Mac'te 8-bit model video ve ses tanımayla birlikte belleği zorlar
    monkeypatch.setattr(local_models, "total_ram_bytes", lambda: 8 * 1024 ** 3)
    assert config.load_config()["model"] == local_models.LOCAL_MODELS["small"]


def test_unsupported_mac_fresh_install_falls_back(cfg_file, monkeypatch):
    monkeypatch.setattr(local_models, "is_supported", lambda *a, **k: False)
    c = config.load_config()
    assert c["translation_provider"] == "openai"
    assert c["model"] == "gpt-5.4-mini"
    assert c["tts_provider"] == "piper"


def test_existing_key_without_provider_stays_openai(cfg_file):
    # Swift sihirbazının yazdığı tipik dosya
    cfg_file({"openai_api_key": "sk-x", "model": "gpt-4o-mini", "tts_provider": "piper"})
    c = config.load_config()
    assert c["translation_provider"] == "openai"
    assert c["model"] == "gpt-4o-mini"


def test_gemini_only_key_maps_to_gemini(cfg_file):
    cfg_file({"gemini_api_key": "AIza"})
    assert config.load_config()["translation_provider"] == "gemini"


def test_claude_only_key_maps_to_claude(cfg_file):
    cfg_file({"anthropic_api_key": "sk-ant"})
    assert config.load_config()["translation_provider"] == "claude"


def test_existing_file_without_tts_enabled_is_off(cfg_file):
    cfg_file({"openai_api_key": "sk-x"})
    assert config.load_config()["tts_enabled"] is False


def test_existing_file_without_tts_provider_is_piper(cfg_file):
    cfg_file({"openai_api_key": "sk-x"})
    assert config.load_config()["tts_provider"] == "piper"


def test_saved_values_untouched(cfg_file):
    cfg_file({"translation_provider": "claude", "tts_provider": "openai",
              "tts_enabled": True, "model": "claude-sonnet-5"})
    c = config.load_config()
    assert (c["translation_provider"], c["tts_provider"], c["tts_enabled"], c["model"]) == \
        ("claude", "openai", True, "claude-sonnet-5")


def test_corrupt_file_treated_as_existing_user(cfg_file, tmp_path):
    # Bozuk dosya: kullanıcı vardı ama okunamıyor. Sessizce 2,5 GB indirme başlatma.
    (tmp_path / "live-translator.json").write_text("{not json")
    assert config.load_config()["translation_provider"] == "openai"
