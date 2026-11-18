"""Download and track the on-device translation models.

A model only counts as ready once every file has landed: a `.complete`
marker is written last, so an interrupted download is never mistaken for a
usable model and is simply resumed on the next attempt.
"""

import errno
import os
import shutil
import threading

MODELS_ROOT = os.path.expanduser("~/Library/Application Support/LiveTranslator/models")

_MARKER = ".complete"
_POLL_SECONDS = 0.5


class ModelStoreError(Exception):
    """Download failures, phrased for the user."""


class HuggingFaceHub:
    """The real source of model files."""

    def total_size(self, repo_id):
        from huggingface_hub import HfApi
        info = HfApi().model_info(repo_id, files_metadata=True)
        return sum((s.size or 0) for s in info.siblings)

    def fetch(self, repo_id, local_dir):
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id, local_dir=local_dir)


def model_dir(repo_id):
    return os.path.join(MODELS_ROOT, repo_id.replace("/", "__"))


def is_ready(repo_id):
    return os.path.exists(os.path.join(model_dir(repo_id), _MARKER))


def size_on_disk(repo_id):
    total = 0
    for root, _dirs, files in os.walk(model_dir(repo_id)):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def delete(repo_id):
    shutil.rmtree(model_dir(repo_id), ignore_errors=True)


def _friendly(exc):
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return "Not enough disk space to download the translation model"
    if isinstance(exc, (ConnectionError, TimeoutError)) or "connect" in str(exc).lower():
        return "Network problem while downloading the translation model"
    return f"Could not download the translation model: {exc}"


def download(repo_id, on_progress=None, hub=None):
    """Fetch `repo_id` into its folder, reporting progress as 0.0-1.0.

    Progress comes from watching the folder grow against the published total,
    which works for any hub implementation and needs no hooks into it."""
    hub = hub or HuggingFaceHub()
    target = model_dir(repo_id)
    os.makedirs(target, exist_ok=True)
    marker = os.path.join(target, _MARKER)
    if os.path.exists(marker):
        os.remove(marker)

    try:
        total = hub.total_size(repo_id)
    except Exception as e:
        raise ModelStoreError(_friendly(e)) from e

    done = threading.Event()

    def report():
        while not done.wait(_POLL_SECONDS):
            if on_progress and total:
                on_progress(min(0.99, size_on_disk(repo_id) / total))

    watcher = threading.Thread(target=report, daemon=True)
    watcher.start()
    try:
        hub.fetch(repo_id, target)
    except Exception as e:
        raise ModelStoreError(_friendly(e)) from e
    finally:
        done.set()
        watcher.join()

    with open(marker, "w") as f:
        f.write(repo_id)
    if on_progress:
        on_progress(1.0)
    return target
