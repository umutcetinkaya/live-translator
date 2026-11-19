"""Registry of the on-device translation models.

All three are TranslateGemma, Google's translation model built on Gemma 3.

- standard (4B, 8-bit): the default from 16 GB of memory. About 4.4 GB in use.
- small (4B, 4-bit): the default on 8 GB Macs, where the 8-bit model next to
  speech recognition and a video would push the system into swap. It mixes up
  weekdays noticeably more often, mostly on unpunctuated recognised speech.
- large (12B, 4-bit): the most accurate, about 7 GB in use. Opt-in, and
  flagged as slow below 32 GB.
"""

import importlib.util
import os
import platform

# Chosen by scripts/bench_local_models.py (see README, "Free mode").
LOCAL_MODELS = {
    "small": "mlx-community/translategemma-4b-it-4bit",
    "standard": "mlx-community/translategemma-4b-it-8bit",
    "large": "mlx-community/translategemma-12b-it-4bit",
}

# Oldest macOS the published MLX wheels support (macosx_14_0_arm64).
# scripts/setup_wizard.swift carries a copy of this value.
MIN_MACOS = (14, 0)

# scripts/setup_wizard.swift carries a copy of this value.
RAM_THRESHOLD_BYTES = 16 * 1024 ** 3
LARGE_MIN_RAM_BYTES = 32 * 1024 ** 3


def total_ram_bytes():
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")


def default_model(ram_bytes=None):
    if ram_bytes is None:
        ram_bytes = total_ram_bytes()
    return LOCAL_MODELS["standard" if ram_bytes >= RAM_THRESHOLD_BYTES else "small"]


def slow_on_this_mac(repo, ram_bytes=None):
    """True when `repo` would crowd this Mac's memory during live use."""
    needs = {LOCAL_MODELS["standard"]: RAM_THRESHOLD_BYTES,
             LOCAL_MODELS["large"]: LARGE_MIN_RAM_BYTES}.get(repo)
    if needs is None:
        return False
    if ram_bytes is None:
        ram_bytes = total_ram_bytes()
    return ram_bytes < needs


def _macos_version():
    ver = platform.mac_ver()[0]
    if not ver:
        return (0, 0)
    parts = [int(p) for p in ver.split(".")[:2] if p.isdigit()]
    return tuple(parts + [0] * (2 - len(parts)))


def is_supported(machine=None, macos=None):
    """True when the free mode can run here: Apple Silicon on MIN_MACOS or
    later, with mlx-lm installed. The install check catches venvs created
    before the free mode existed and x86_64 Pythons running under Rosetta,
    where pip skips mlx-lm."""
    machine = machine if machine is not None else platform.machine()
    macos = tuple(macos) if macos is not None else _macos_version()
    if machine != "arm64" or macos < MIN_MACOS:
        return False
    return importlib.util.find_spec("mlx_lm") is not None
