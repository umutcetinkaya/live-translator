"""Facts about this Mac that the Settings screen needs.

Gathered outside the HTML builder so the builder stays a pure function:
which free models exist and whether they are downloaded, whether the free
mode can run here at all, and which system voices speak the target language.
"""

import local_models
import model_store

_LABELS = {"standard": "Standard (better)", "small": "Small (faster)"}
_SIZES = {"standard": "2.3 GB", "small": "1.0 GB"}


def _gb(n):
    return f"{n / 1e9:.1f} GB"


def build(config, voice_lister=None):
    low_ram = local_models.pick_tier(local_models.total_ram_bytes()) == "small"
    models = []
    for tier in ("standard", "small"):
        repo = local_models.LOCAL_MODELS[tier]
        ready = model_store.is_ready(repo)
        models.append({
            "id": repo,
            "label": f"{_LABELS[tier]} · {_SIZES[tier]}",
            "status": f"Ready · {_gb(model_store.size_on_disk(repo))}" if ready else "Not downloaded",
            "warn": "May be slow on this Mac" if (tier == "standard" and low_ram) else "",
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
        "system_voices": voices,
    }
