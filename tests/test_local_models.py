"""Yerel çeviri modeli kayıt defteri: RAM'e göre model seçimi ve destek kontrolü.

8 GB'lık Mac'lerde standart model, ses tanıma ve video ile birlikte belleği
zorlar; bu yüzden 16 GB altında küçük model seçilir. MLX sadece Apple
Silicon'da ve MIN_MACOS ile üstünde çalışır.
"""

from local_models import (LOCAL_MODELS, MIN_MACOS, RAM_THRESHOLD_BYTES,
                          default_model, is_supported, pick_tier)

GB = 1024 ** 3


def test_threshold_is_16_gb():
    assert RAM_THRESHOLD_BYTES == 16 * GB


def test_pick_tier_threshold():
    assert pick_tier(8 * GB) == "small"
    assert pick_tier(16 * GB) == "standard"
    assert pick_tier(48 * GB) == "standard"


def test_default_model_maps_tier():
    assert default_model(8 * GB) == LOCAL_MODELS["small"]
    assert default_model(32 * GB) == LOCAL_MODELS["standard"]


def test_two_distinct_tiers():
    assert set(LOCAL_MODELS) == {"standard", "small"}
    assert LOCAL_MODELS["standard"] != LOCAL_MODELS["small"]


def test_is_supported():
    assert is_supported("arm64", (26, 0)) is True
    assert is_supported("x86_64", (26, 0)) is False
    assert is_supported("arm64", (MIN_MACOS[0] - 1, 0)) is False
    assert is_supported("arm64", MIN_MACOS) is True


def test_unsupported_when_mlx_not_installed(monkeypatch):
    # Eski DMG venv'i ya da Intel Python: donanım uygun olsa da mlx_lm yoksa ücretsiz mod sunulmamalı
    import importlib.util
    import local_models
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec",
                        lambda name, *a: None if name == "mlx_lm" else real(name, *a))
    assert local_models.is_supported("arm64", (26, 0)) is False


def test_requirements_guard_mlx_and_list_hub():
    # mlx sadece arm64 + macOS 14 tekerleği yayınlıyor; işaretsiz satır Intel/macOS 13 kurulumunu bozar
    import os
    req = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")).read()
    mlx_line = [l for l in req.splitlines() if l.startswith("mlx-lm")][0]
    assert 'platform_machine == "arm64"' in mlx_line
    assert "platform_release" in mlx_line
    assert any(l.startswith("huggingface_hub") for l in req.splitlines())
