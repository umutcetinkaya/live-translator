from providers.realtime_gemini import GeminiRealtimeProvider
from providers.base import RealtimeProvider


def test_is_realtime_provider():
    assert issubclass(GeminiRealtimeProvider, RealtimeProvider)

def test_feed_audio_buffers_when_not_started():
    p = GeminiRealtimeProvider(api_key="k", model="gemini-2.5-flash-live")
    # start çağrılmadan feed_audio sessizce yutulmalı (crash yok)
    p.feed_audio(b"\x00\x01")

def test_stop_is_idempotent():
    p = GeminiRealtimeProvider(api_key="k", model="gemini-2.5-flash-live")
    p.stop(); p.stop()  # crash yok

def test_uses_dedicated_translate_model():
    """Genel Live modeli + system instruction yerine özel translate modeli."""
    from providers.realtime_gemini import LIVE_TRANSLATE_MODEL
    assert LIVE_TRANSLATE_MODEL == "gemini-3.5-live-translate-preview"

def test_config_uses_translation_config():
    """translationConfig first-class alan — system instruction ile çeviri istemez."""
    p = GeminiRealtimeProvider(api_key="k", model="", target_language="tr")
    cfg = p._build_config()
    assert cfg["translation_config"]["target_language_code"] == "tr"
    assert "system_instruction" not in cfg

def test_config_requests_transcriptions():
    """Çeviri metni output_transcription'dan gelir; kaynak input'tan."""
    p = GeminiRealtimeProvider(api_key="k", model="", target_language="de")
    cfg = p._build_config()
    assert "input_audio_transcription" in cfg
    assert "output_audio_transcription" in cfg
