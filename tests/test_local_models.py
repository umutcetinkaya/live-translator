"""Yerel çeviri modeli kayıt defteri ve destek kontrolü.

Üç TranslateGemma kademesi. 4B'nin 4-bit sürümü noktalamasız konuşma
metninde günleri karıştırıyor (Thursday → Çarşamba); 8-bit sürüm
karıştırmıyor ama 4,4 GB bellek ister. Bu yüzden 16 GB ve üstünde 8-bit
varsayılan, 8 GB'lık Mac'te 4-bit. 12B en doğrusu, 7 GB ister, isteğe
bağlıdır. MLX sadece Apple Silicon'da ve MIN_MACOS ile üstünde çalışır.
"""

from local_models import (LARGE_MIN_RAM_BYTES, LOCAL_MODELS, MIN_MACOS,
                          RAM_THRESHOLD_BYTES, default_model, is_supported,
                          slow_on_this_mac)

GB = 1024 ** 3


def test_models_are_translategemma():
    assert LOCAL_MODELS == {
        "small": "mlx-community/translategemma-4b-it-4bit",
        "standard": "mlx-community/translategemma-4b-it-8bit",
        "large": "mlx-community/translategemma-12b-it-4bit",
    }


def test_default_depends_on_memory():
    assert RAM_THRESHOLD_BYTES == 16 * GB
    assert default_model(8 * GB) == LOCAL_MODELS["small"]
    assert default_model(16 * GB) == LOCAL_MODELS["standard"]
    assert default_model(48 * GB) == LOCAL_MODELS["standard"]


def test_standard_warns_on_8_gb():
    assert slow_on_this_mac(LOCAL_MODELS["standard"], 8 * GB) is True
    assert slow_on_this_mac(LOCAL_MODELS["standard"], 16 * GB) is False
    assert slow_on_this_mac(LOCAL_MODELS["small"], 8 * GB) is False


def test_setup_wizard_constants_match():
    # Sihirbaz Swift'te ayrı kopya tutar; ayrışırsa ilk açılışta yanlış model iner
    import os, re
    root = os.path.dirname(os.path.dirname(__file__))
    swift = open(os.path.join(root, "scripts", "setup_wizard.swift")).read()
    assert f'let STANDARD_MODEL = "{LOCAL_MODELS["standard"]}"' in swift
    assert f'let SMALL_MODEL = "{LOCAL_MODELS["small"]}"' in swift
    assert "let RAM_THRESHOLD: UInt64 = 16 * 1024 * 1024 * 1024" in swift
    m = re.search(r"majorVersion: (\d+), minorVersion: (\d+)", swift)
    assert (int(m.group(1)), int(m.group(2))) == MIN_MACOS


def test_large_warns_below_32_gb():
    assert LARGE_MIN_RAM_BYTES == 32 * GB
    assert slow_on_this_mac(LOCAL_MODELS["large"], 16 * GB) is True
    assert slow_on_this_mac(LOCAL_MODELS["large"], 32 * GB) is False
    assert slow_on_this_mac(LOCAL_MODELS["small"], 8 * GB) is False


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
