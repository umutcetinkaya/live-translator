"""Model deposu: yerel çeviri modelinin indirilmesi ve hazır olma durumu.

Ağ yok: gerçek Hugging Face hub yerine dosya yazan sahte bir hub kullanılır.
Asıl risk yarım kalan indirmenin "hazır" sayılmasıdır; o zaman model
yüklenirken patlar ve kullanıcı neden çeviri gelmediğini anlamaz.
"""

import errno
import os

import pytest

import model_store


class FakeHub:
    """Verilen dosyaları local_dir'e yazar; istenirse ortada hata atar."""

    def __init__(self, files=None, fail_after=None, error=None):
        self.files = files or {"config.json": b"{}", "model.safetensors": b"x" * 4000}
        self.fail_after = fail_after
        self.error = error
        self.calls = 0

    def total_size(self, repo_id):
        return sum(len(v) for v in self.files.values())

    def fetch(self, repo_id, local_dir):
        self.calls += 1
        os.makedirs(local_dir, exist_ok=True)
        for i, (name, data) in enumerate(self.files.items()):
            if self.fail_after is not None and i >= self.fail_after:
                raise self.error or ConnectionError("connection reset")
            with open(os.path.join(local_dir, name), "wb") as f:
                f.write(data)


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(model_store, "MODELS_ROOT", str(tmp_path / "models"))
    return tmp_path


def test_model_dir_is_flat_and_safe(tmp_store):
    d = model_store.model_dir("mlx-community/translategemma-4b-it-4bit")
    assert d == os.path.join(model_store.MODELS_ROOT, "mlx-community__translategemma-4b-it-4bit")


def test_not_ready_before_download(tmp_store):
    assert not model_store.is_ready("a/b")


def test_download_marks_complete_and_reports_progress(tmp_store):
    seen = []
    path = model_store.download("a/b", seen.append, hub=FakeHub())
    assert model_store.is_ready("a/b")
    assert path == model_store.model_dir("a/b")
    assert seen[-1] == 1.0
    assert all(0.0 <= p <= 1.0 for p in seen)


def test_partial_download_is_not_ready(tmp_store):
    with pytest.raises(model_store.ModelStoreError):
        model_store.download("a/b", hub=FakeHub(fail_after=1))
    assert not model_store.is_ready("a/b")


def test_download_error_reported(tmp_store):
    full = OSError(errno.ENOSPC, "No space left on device")
    with pytest.raises(model_store.ModelStoreError, match="disk space"):
        model_store.download("a/b", hub=FakeHub(fail_after=0, error=full))


def test_network_error_message(tmp_store):
    with pytest.raises(model_store.ModelStoreError, match="Network"):
        model_store.download("a/b", hub=FakeHub(fail_after=0))


def test_resume_after_failure(tmp_store):
    """İkinci deneme aynı klasöre yazar ve tamamlanınca hazır olur."""
    with pytest.raises(model_store.ModelStoreError):
        model_store.download("a/b", hub=FakeHub(fail_after=1))
    model_store.download("a/b", hub=FakeHub())
    assert model_store.is_ready("a/b")


def test_size_on_disk(tmp_store):
    hub = FakeHub()
    model_store.download("a/b", hub=hub)
    assert model_store.size_on_disk("a/b") >= hub.total_size("a/b")


def test_delete_removes_files(tmp_store):
    model_store.download("a/b", hub=FakeHub())
    model_store.delete("a/b")
    assert not model_store.is_ready("a/b")
    assert model_store.size_on_disk("a/b") == 0
