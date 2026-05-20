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

def test_missing_model_file_raises(tmp_path):
    p = PiperTTSProvider(models_dir=str(tmp_path))
    with pytest.raises(ProviderError):
        p.synthesize("merhaba", "tr", "", 1.0)
