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
