"""Ayarlar ekranı için ortam bilgisi: yerel modellerin durumu ve sistem sesleri.

HTML üretimi saf kalsın diye bu bilgiler ayrı toplanır. Kritik nokta:
32 GB altındaki Mac'te büyük model için uyarı görünmeli, inmiş model
"Ready" ve boyutuyla görünmeli.
"""

import local_models
import model_store
import settings_env
from local_models import LOCAL_MODELS

GB = 1024 ** 3


def _patch(monkeypatch, ram=32 * GB, ready=(), supported=True):
    monkeypatch.setattr(local_models, "is_supported", lambda *a, **k: supported)
    monkeypatch.setattr(local_models, "total_ram_bytes", lambda: ram)
    monkeypatch.setattr(model_store, "is_ready", lambda repo: repo in ready)
    monkeypatch.setattr(model_store, "size_on_disk", lambda repo: int(2.3e9))


def _lister():
    return [{"id": "tr.x", "name": "Yelda", "quality": 1, "language": "tr-TR"},
            {"id": "en.x", "name": "Samantha", "quality": 2, "language": "en-US"}]


def test_models_listed_small_to_large(monkeypatch):
    _patch(monkeypatch)
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert [m["id"] for m in env["local_models"]] == [
        LOCAL_MODELS["small"], LOCAL_MODELS["standard"], LOCAL_MODELS["large"]]
    assert [m["label"] for m in env["local_models"]] == [
        "Small (less accurate) · 2.2 GB", "Standard · 4.2 GB", "Large (most accurate) · 6.7 GB"]
    assert env["local_supported"] is True


def test_ready_model_shows_size(monkeypatch):
    _patch(monkeypatch, ready={LOCAL_MODELS["standard"]})
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert env["local_models"][1]["status"] == "Ready · 2.3 GB"
    assert env["local_models"][0]["status"] == "Not downloaded"


def test_16_gb_warns_on_large_only(monkeypatch):
    _patch(monkeypatch, ram=16 * GB)
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert [m["warn"] for m in env["local_models"]] == [
        "", "", "Needs 32 GB of memory, may be slow on this Mac"]


def test_8_gb_warns_on_standard_and_large(monkeypatch):
    _patch(monkeypatch, ram=8 * GB)
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert [m["warn"] for m in env["local_models"]] == [
        "", "Needs 16 GB of memory, may be slow on this Mac",
        "Needs 32 GB of memory, may be slow on this Mac"]


def test_default_local_model_follows_memory(monkeypatch):
    # Ayarlarda yerel moda geçen kullanıcıya bu Mac'e uygun model önerilmeli
    _patch(monkeypatch, ram=32 * GB)
    assert settings_env.build({}, voice_lister=_lister)["default_local_model"] == LOCAL_MODELS["standard"]
    _patch(monkeypatch, ram=8 * GB)
    assert settings_env.build({}, voice_lister=_lister)["default_local_model"] == LOCAL_MODELS["small"]


def test_32_gb_no_warning(monkeypatch):
    _patch(monkeypatch, ram=32 * GB)
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert [m["warn"] for m in env["local_models"]] == ["", "", ""]


def test_system_voices_for_target_language(monkeypatch):
    _patch(monkeypatch)
    env = settings_env.build({"target_lang": "tr"}, voice_lister=_lister)
    assert [v["id"] for v in env["system_voices"]] == ["tr.x"]


def test_voice_listing_failure_is_harmless(monkeypatch):
    _patch(monkeypatch)
    def broken():
        raise RuntimeError("no AVFoundation")
    env = settings_env.build({"target_lang": "tr"}, voice_lister=broken)
    assert env["system_voices"] == []
