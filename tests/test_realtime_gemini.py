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
