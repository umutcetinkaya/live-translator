from unittest.mock import MagicMock
from providers.realtime_openai import OpenAIRealtimeProvider
from providers.base import RealtimeProvider


def test_is_realtime_provider():
    assert issubclass(OpenAIRealtimeProvider, RealtimeProvider)

def test_feed_audio_sends_to_ws():
    ws = MagicMock()
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    p.feed_audio(b"\x00\x01" * 160)
    assert ws.send.called

def test_stop_closes_ws():
    ws = MagicMock()
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    p.stop()
    assert ws.close.called
