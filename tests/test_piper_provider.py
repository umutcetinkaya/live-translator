import os
import pytest
from providers.piper import PiperTTSProvider, PIPER_VOICES
from providers.base import TTSProvider, ProviderError


def test_is_tts_provider():
    assert issubclass(PiperTTSProvider, TTSProvider)

def test_known_languages_present():
    assert "tr" in PIPER_VOICES and "en" in PIPER_VOICES

def test_unknown_language_raises(tmp_path):
    p = PiperTTSProvider(models_dir=str(tmp_path))
    with pytest.raises(ProviderError):
        p.synthesize("hi", "xx", "", 1.0)

def _failing_downloader(lang, cache_dir):
    raise ConnectionError("offline")


def test_missing_model_file_raises(tmp_path):
    p = PiperTTSProvider(models_dir=str(tmp_path), cache_dir=str(tmp_path / "c"),
                         downloader=_failing_downloader)
    with pytest.raises(ProviderError):
        p.synthesize("merhaba", "tr", "", 1.0)


# --- İsteğe bağlı indirme ---
# DMG kullanıcısı `make models` çalıştıramaz. Piper seçilince ses modeli
# uygulama içinde indirilmeli, bir kez.

def _recording_downloader(calls):
    def dl(lang, cache_dir):
        calls.append(lang)
        path = os.path.join(cache_dir, PIPER_VOICES[lang] + ".onnx")
        os.makedirs(cache_dir, exist_ok=True)
        open(path, "wb").write(b"onnx")
        open(path + ".json", "w").write("{}")
        return path
    return dl


def test_downloads_missing_voice_once(tmp_path):
    calls = []
    p = PiperTTSProvider(models_dir=str(tmp_path / "bundled"), cache_dir=str(tmp_path / "c"),
                         downloader=_recording_downloader(calls))
    first = p.ensure_model("tr")
    second = p.ensure_model("tr")
    assert calls == ["tr"]
    assert first == second and os.path.exists(first)


def test_bundled_model_preferred(tmp_path):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / (PIPER_VOICES["tr"] + ".onnx")).write_bytes(b"onnx")
    calls = []
    p = PiperTTSProvider(models_dir=str(bundled), cache_dir=str(tmp_path / "c"),
                         downloader=_recording_downloader(calls))
    assert p.ensure_model("tr") == str(bundled / (PIPER_VOICES["tr"] + ".onnx"))
    assert calls == []


def test_download_failure_is_provider_error(tmp_path):
    p = PiperTTSProvider(models_dir=str(tmp_path), cache_dir=str(tmp_path / "c"),
                         downloader=_failing_downloader)
    with pytest.raises(ProviderError, match="could not download voice"):
        p.ensure_model("tr")


def test_default_cache_under_model_store(monkeypatch, tmp_path):
    import model_store
    monkeypatch.setattr(model_store, "MODELS_ROOT", str(tmp_path / "root"))
    p = PiperTTSProvider(models_dir=str(tmp_path))
    assert p._cache_dir() == os.path.join(str(tmp_path / "root"), "piper")
