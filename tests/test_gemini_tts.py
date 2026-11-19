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


def _voice_sent(tmp_path, voice):
    client = MagicMock()
    part = MagicMock()
    part.inline_data.data = b"\x00\x01" * 10
    cand = MagicMock()
    cand.content.parts = [part]
    client.models.generate_content.return_value = MagicMock(candidates=[cand])
    GeminiTTSProvider(client=client, tmp_dir=str(tmp_path)).synthesize("Merhaba", "tr", voice, 1.0)
    cfg = client.models.generate_content.call_args.kwargs["config"]
    return cfg.speech_config.voice_config.prebuilt_voice_config.voice_name


def test_openai_voice_name_is_not_sent_to_gemini(tmp_path):
    # tts_voice alanı OpenAI ile ortak; "marin" ya da "nova" Gemini'de yok
    assert _voice_sent(tmp_path, "marin") == "Kore"
    assert _voice_sent(tmp_path, "nova") == "Kore"


def test_gemini_voices_pass_through(tmp_path):
    assert _voice_sent(tmp_path, "Puck") == "Puck"
    assert _voice_sent(tmp_path, "voice_abc123") == "voice_abc123"   # özel ses
