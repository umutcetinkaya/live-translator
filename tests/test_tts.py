from unittest.mock import MagicMock
import tts as tts_mod
from tts import TextToSpeech


def test_synthesize_delegates_to_provider(monkeypatch, tmp_path):
    fake = MagicMock()
    wav = str(tmp_path / "out.wav"); open(wav, "wb").close()
    fake.synthesize.return_value = wav
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: fake)
    played = []
    t = TextToSpeech(config={"tts_provider": "piper", "target_lang": "tr",
                             "tts_voice": "nova", "tts_speed": 1.0})
    monkeypatch.setattr(t, "_play_file", lambda p: played.append(p))
    t._synthesize_and_play("Merhaba")
    fake.synthesize.assert_called_once_with("Merhaba", "tr", "nova", 1.0)
    assert played == [wav]

def test_provider_error_does_not_crash(monkeypatch):
    from providers.base import ProviderError
    fake = MagicMock()
    fake.synthesize.side_effect = ProviderError("x")
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: fake)
    t = TextToSpeech(config={"tts_provider": "piper", "target_lang": "tr",
                             "tts_voice": "nova", "tts_speed": 1.0})
    monkeypatch.setattr(t, "_play_file", lambda p: None)
    t._synthesize_and_play("Merhaba")  # sızdırmamalı


def _quiet(monkeypatch):
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: MagicMock())


def test_starts_enabled_when_config_says_so(monkeypatch):
    # Yeni kurulumda çeviri hemen sesli okunmalı: worker da çalışıyor olmalı
    _quiet(monkeypatch)
    t = TextToSpeech(config={"tts_provider": "system", "tts_enabled": True})
    assert t.enabled is True
    assert t._worker is not None and t._worker.is_alive()
    t.stop()


def test_starts_disabled_by_default_for_old_configs(monkeypatch):
    _quiet(monkeypatch)
    t = TextToSpeech(config={"tts_provider": "openai"})
    assert t.enabled is False
    assert t._worker is None


def test_system_provider_uses_its_own_voice_setting(monkeypatch, tmp_path):
    # OpenAI ses adı ("nova") sistem sesine gönderilmemeli; sistem sesi kendi alanından gelir
    fake = MagicMock()
    wav = str(tmp_path / "o.wav"); open(wav, "wb").close()
    fake.synthesize.return_value = wav
    monkeypatch.setattr(tts_mod, "get_tts_provider", lambda cfg: fake)
    t = TextToSpeech(config={"tts_provider": "system", "target_lang": "tr",
                             "tts_voice": "nova", "tts_voice_system": "tr.enhanced",
                             "tts_speed": 1.0})
    monkeypatch.setattr(t, "_play_file", lambda p: None)
    t._synthesize_and_play("Merhaba")
    fake.synthesize.assert_called_once_with("Merhaba", "tr", "tr.enhanced", 1.0)


# --- Sağlayıcı değişince eski bağlantı kapanmalı (OpenAI Realtime kalıcı WebSocket tutar) ---

def _closable(monkeypatch):
    made = []

    def make(cfg):
        p = MagicMock()
        made.append(p)
        return p
    monkeypatch.setattr(tts_mod, "get_tts_provider", make)
    return made


def _wait_closed(provider):
    import time
    for _ in range(50):
        if provider.close.called:
            return True
        time.sleep(0.01)
    return False


def test_update_config_closes_previous_provider(monkeypatch):
    made = _closable(monkeypatch)
    t = TextToSpeech(config={"tts_provider": "openai"})
    t.update_config({"tts_provider": "system"})
    assert _wait_closed(made[0])
    assert not made[1].close.called


def test_set_provider_closes_previous_provider(monkeypatch):
    made = _closable(monkeypatch)
    t = TextToSpeech(config={"tts_provider": "openai"})
    t.set_provider("system")
    assert _wait_closed(made[0])


def test_stop_closes_provider(monkeypatch):
    made = _closable(monkeypatch)
    t = TextToSpeech(config={"tts_provider": "openai"})
    t.stop()
    assert _wait_closed(made[0])


def test_closing_does_not_block_the_caller(monkeypatch):
    # Kapatma, süren bir seslendirmeyi bekleyebilir; Ayarlar'ı kaydeden ana iş parçacığı beklememeli
    import threading, time
    made = _closable(monkeypatch)
    gate = threading.Event()
    t = TextToSpeech(config={"tts_provider": "openai"})
    made[0].close.side_effect = lambda: gate.wait(2)
    start = time.time()
    t.update_config({"tts_provider": "system"})
    assert time.time() - start < 0.5
    gate.set()
