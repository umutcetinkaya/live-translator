"""Facts about this Mac that the Settings screen needs.

Gathered outside the HTML builder so the builder stays a pure function:
which free models exist and whether they are downloaded, whether the free
mode can run here at all, and which system voices speak the target language.
"""

import local_models
import model_store

_TIERS = ("small", "standard", "large")
_LABELS = {"small": "Small (less accurate)", "standard": "Standard",
           "large": "Large (most accurate)"}
_SIZES = {"small": "2.2 GB", "standard": "4.2 GB", "large": "6.7 GB"}
_NEEDS = {"standard": "16 GB", "large": "32 GB"}


def _gb(n):
    return f"{n / 1e9:.1f} GB"


def build(config, voice_lister=None):
    ram = local_models.total_ram_bytes()
    models = []
    for tier in _TIERS:
        repo = local_models.LOCAL_MODELS[tier]
        ready = model_store.is_ready(repo)
        slow = local_models.slow_on_this_mac(repo, ram)
        models.append({
            "id": repo,
            "label": f"{_LABELS[tier]} · {_SIZES[tier]}",
            "status": f"Ready · {_gb(model_store.size_on_disk(repo))}" if ready else "Not downloaded",
            "warn": f"Needs {_NEEDS[tier]} of memory, may be slow on this Mac" if slow else "",
        })

    try:
        from providers.system_voice import list_voices
        voices = list_voices(config.get("target_lang", "tr"), voice_lister)
    except Exception as e:
        print(f"[Settings] System voices unavailable: {e}")
        voices = []

    return {
        "local_supported": local_models.is_supported(),
        "local_models": models,
        "default_local_model": local_models.default_model(ram),
        "system_voices": voices,
    }
