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
