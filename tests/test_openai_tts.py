import pytest
from unittest.mock import MagicMock
from providers.openai import OpenAITTSProvider
from providers.base import TTSProvider, ProviderError


def test_is_tts_provider():
    assert issubclass(OpenAITTSProvider, TTSProvider)

def test_synthesize_writes_file_and_returns_path(tmp_path):
    client = MagicMock()
    resp = MagicMock()
    client.audio.speech.create.return_value = resp
    p = OpenAITTSProvider(client=client, tmp_dir=str(tmp_path))
    out = p.synthesize("Merhaba", "tr", "nova", 1.0)
    assert out.endswith(".mp3")
    resp.stream_to_file.assert_called_once()

def test_no_client_raises(tmp_path):
    p = OpenAITTSProvider(client=None, tmp_dir=str(tmp_path))
    with pytest.raises(ProviderError):
        p.synthesize("Merhaba", "tr", "nova", 1.0)
