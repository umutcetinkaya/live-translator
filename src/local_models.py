"""Registry of the on-device translation models.

Two tiers: the standard model for Macs with enough memory, and a small one
for 8 GB machines, where the standard model plus speech recognition plus the
video being watched would push the system into swap.
"""

import importlib.util
import os
import platform

# Chosen by scripts/bench_local_models.py (see README, "Free mode").
LOCAL_MODELS = {
    "standard": "mlx-community/Qwen3-4B-Instruct-2507-4bit",
    "small": "mlx-community/Qwen3-1.7B-4bit",
}

# Oldest macOS the published MLX wheels support (macosx_14_0_arm64).
# scripts/setup_wizard.swift carries a copy of this value.
MIN_MACOS = (14, 0)

RAM_THRESHOLD_BYTES = 16 * 1024 ** 3


def total_ram_bytes():
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")


def pick_tier(ram_bytes):
    return "standard" if ram_bytes >= RAM_THRESHOLD_BYTES else "small"


def default_model(ram_bytes=None):
    if ram_bytes is None:
        ram_bytes = total_ram_bytes()
    return LOCAL_MODELS[pick_tier(ram_bytes)]


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
