import sys
from unittest.mock import MagicMock

# pipeline transitively imports native macOS modules (PyObjC) that aren't
# available in the test venv. Mock them for import, tracking which keys WE
# added so a session-end fixture can remove them (no sys.modules pollution).
_NATIVE_MODS = ("objc", "ScreenCaptureKit", "CoreMedia", "Foundation",
                "AVFoundation", "Cocoa", "Speech", "AppKit")
_INJECTED = [m for m in _NATIVE_MODS if m not in sys.modules]
for mod in _INJECTED:
    sys.modules[mod] = MagicMock()

import pipeline as pipeline_mod

import pytest


@pytest.fixture(scope="module", autouse=True)
def _cleanup_native_mocks():
    yield
    # Sadece bizim eklediğimiz mock anahtarlarını temizle
    for mod in _INJECTED:
        sys.modules.pop(mod, None)


def _patch_components(monkeypatch):
    for name in ("SystemAudioCapture", "RealtimeSpeechRecognizer",
                 "AITranslator", "TextToSpeech"):
        monkeypatch.setattr(pipeline_mod, name, MagicMock())

def test_realtime_off_uses_recognizer(monkeypatch):
    _patch_components(monkeypatch)
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": False, "source_locale": "en-US",
                "target_lang": "tr"})
    assert p.is_realtime is False

def test_no_speech_shows_english_hint(monkeypatch):
    _patch_components(monkeypatch)
    overlay = MagicMock()
    p = pipeline_mod.TranslationPipeline(overlay,
        config={"realtime_mode": False, "source_locale": "en-US",
                "target_lang": "tr"})
    p._on_no_speech()  # henüz hiç konuşma yok → ipucu göster
    overlay.update_original_on_main_thread.assert_called_once()
    msg = overlay.update_original_on_main_thread.call_args.args[0]
    assert "No audio detected" in msg

def test_no_speech_silent_when_already_transcribing(monkeypatch):
    _patch_components(monkeypatch)
    overlay = MagicMock()
    p = pipeline_mod.TranslationPipeline(overlay,
        config={"realtime_mode": False, "source_locale": "en-US",
                "target_lang": "tr"})
    p._finalized_text = "hello world"  # zaten konuşma var
    p._on_no_speech()
    overlay.update_original_on_main_thread.assert_not_called()

def test_realtime_on_sets_flag(monkeypatch):
    _patch_components(monkeypatch)
    monkeypatch.setattr(pipeline_mod, "get_realtime_provider",
                        lambda cfg: MagicMock())
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": True, "source_locale": "en-US",
                "target_lang": "tr", "translation_provider": "openai",
                "openai_api_key": "k", "model": "gpt-realtime-translate"})
    assert p.is_realtime is True

def test_change_languages_restarts_realtime(monkeypatch):
    _patch_components(monkeypatch)
    rt = MagicMock()
    monkeypatch.setattr(pipeline_mod, "get_realtime_provider", lambda cfg: rt)
    p = pipeline_mod.TranslationPipeline(MagicMock(),
        config={"realtime_mode": True, "source_locale": "en-US",
                "target_lang": "tr", "translation_provider": "openai",
                "openai_api_key": "k", "model": "gpt-realtime-translate"})
    p.start()
    rt.start.assert_called()
    p.change_languages("de-DE", "tr")
    # realtime modda dil değişince provider durdurulup yeniden başlatılmalı
    assert rt.stop.called


# --- Ücretsiz modelin arka planda indirilmesi ---
# Model hazır değilken uygulama sessiz kalmamalı: indirme tek sefer başlar,
# ilerleme ekranda görünür, bitince bekleyen metin çevrilir.

import threading

import model_store
from local_models import LOCAL_MODELS

LOCAL_CFG = {"realtime_mode": False, "source_locale": "en-US", "target_lang": "tr",
             "translation_provider": "local", "model": LOCAL_MODELS["standard"]}


class GatedDownload:
    """download() çağrılarını sayar; gate açılana kadar bekler."""

    def __init__(self, fail=None):
        self.calls = []
        self.gate = threading.Event()
        self.fail = fail

    def __call__(self, repo, on_progress=None, hub=None):
        self.calls.append(repo)
        if on_progress:
            on_progress(0.5)
        self.gate.wait(5)
        if self.fail:
            raise self.fail
        if on_progress:
            on_progress(1.0)
        return "/models/x"


def _local_pipeline(monkeypatch, download, ready=False, cfg=None):
    _patch_components(monkeypatch)
    monkeypatch.setattr(model_store, "is_ready", lambda repo: ready)
    monkeypatch.setattr(model_store, "download", download)
    overlay = MagicMock()
    p = pipeline_mod.TranslationPipeline(overlay, config=dict(cfg or LOCAL_CFG))
    return p, overlay


def _messages(overlay):
    return [c.args[0] for c in overlay.update_original_on_main_thread.call_args_list]


def test_download_started_when_local_not_ready(monkeypatch):
    dl = GatedDownload()
    p, overlay = _local_pipeline(monkeypatch, dl)
    p.ensure_local_model()
    dl.gate.set()
    p._download_thread.join(5)
    assert dl.calls == [LOCAL_MODELS["standard"]]
    msgs = _messages(overlay)
    assert any("Downloading free translation model" in m and "50%" in m for m in msgs)


def test_download_started_once(monkeypatch):
    dl = GatedDownload()
    p, _ = _local_pipeline(monkeypatch, dl)
    p.start()
    p.update_config(dict(LOCAL_CFG))
    p.change_languages("en-US", "de")
    dl.gate.set()
    p._download_thread.join(5)
    assert len(dl.calls) == 1


def test_no_download_when_ready(monkeypatch):
    dl = GatedDownload()
    p, _ = _local_pipeline(monkeypatch, dl, ready=True)
    p.ensure_local_model()
    assert dl.calls == []


def test_no_download_for_cloud_provider(monkeypatch):
    dl = GatedDownload()
    cfg = dict(LOCAL_CFG, translation_provider="openai", model="gpt-5.4-mini")
    p, _ = _local_pipeline(monkeypatch, dl, cfg=cfg)
    p.ensure_local_model()
    assert dl.calls == []


def test_download_failure_shown_on_overlay(monkeypatch):
    dl = GatedDownload(fail=model_store.ModelStoreError("Not enough disk space to download the translation model"))
    p, overlay = _local_pipeline(monkeypatch, dl)
    p.ensure_local_model()
    dl.gate.set()
    p._download_thread.join(5)
    assert any(m.startswith("⚠️") and "disk space" in m for m in _messages(overlay))


def test_retry_after_failure(monkeypatch):
    # Hata sonrası ayar kaydı ya da yeniden başlatma indirmeyi tekrar denemeli
    dl = GatedDownload(fail=model_store.ModelStoreError("Network problem"))
    p, _ = _local_pipeline(monkeypatch, dl)
    dl.gate.set()
    p.ensure_local_model()
    p._download_thread.join(5)
    p.ensure_local_model()
    p._download_thread.join(5)
    assert len(dl.calls) == 2


def test_translation_resumes_after_download(monkeypatch):
    dl = GatedDownload()
    p, overlay = _local_pipeline(monkeypatch, dl)
    p.ensure_local_model()
    dl.gate.set()
    p._download_thread.join(5)
    p._translator.on_speech_pause.assert_called()
    assert any("ready" in m.lower() for m in _messages(overlay))


def test_not_ready_error_hidden_while_downloading(monkeypatch):
    # İndirme sürerken translator'ın "Downloading…" hatası ilerleme satırını ezmemeli
    dl = GatedDownload()
    p, overlay = _local_pipeline(monkeypatch, dl)
    p.ensure_local_model()
    before = len(_messages(overlay))
    p._on_translate_error("Downloading the free translation model…")
    assert len(_messages(overlay)) == before
    dl.gate.set()
    p._download_thread.join(5)


def test_progress_survives_incoming_speech(monkeypatch):
    # Video oynarken her yeni kısmi metin satırı yeniler; ilerleme kaybolmamalı
    dl = GatedDownload()
    p, overlay = _local_pipeline(monkeypatch, dl)
    p.ensure_local_model()
    p._on_partial("hello everyone and welcome back")
    last = _messages(overlay)[-1]
    assert "welcome back" in last and "50%" in last
    assert last.endswith("%")  # overlay keeps the END of long text
    dl.gate.set()
    p._download_thread.join(5)
    p._on_partial("next sentence")
    assert _messages(overlay)[-1] == "next sentence"
