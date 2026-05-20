import pytest
from unittest.mock import MagicMock, patch
from providers.gemini import GeminiTTSProvider
from providers.base import TTSProvider, ProviderError


def test_is_tts_provider():
    assert issubclass(GeminiTTSProvider, TTSProvider)

def test_no_client_raises(tmp_path):
    p = GeminiTTSProvider(client=None, tmp_dir=str(tmp_path))
    with pytest.raises(ProviderError):
        p.synthesize("Merhaba", "tr", "Kore", 1.0)

def test_synthesize_writes_wav(tmp_path):
    # Gemini TTS PCM döner; provider wav'a sarar
    client = MagicMock()
    part = MagicMock()
    part.inline_data.data = b"\x00\x01" * 100
    cand = MagicMock()
    cand.content.parts = [part]
    client.models.generate_content.return_value = MagicMock(candidates=[cand])
    p = GeminiTTSProvider(client=client, tmp_dir=str(tmp_path))
    out = p.synthesize("Merhaba", "tr", "Kore", 1.0)
    assert out.endswith(".wav")
    import os
    assert os.path.exists(out)
