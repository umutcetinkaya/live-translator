from unittest.mock import MagicMock
from providers.realtime_openai import OpenAIRealtimeProvider
from providers.base import RealtimeProvider


def test_is_realtime_provider():
    assert issubclass(OpenAIRealtimeProvider, RealtimeProvider)

def test_feed_audio_sends_to_ws():
    ws = MagicMock()
    ws.recv.return_value = ""  # reader thread'in hot-spin yapmasını önle
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    p.feed_audio(b"\x00\x01" * 160)
    assert ws.send.called
    p.stop()

def test_stop_closes_ws():
    ws = MagicMock()
    ws.recv.return_value = ""
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    p.stop()
    assert ws.close.called

def test_feed_audio_swallows_send_error_and_closes():
    # Kapalı/kopuk socket'e yazınca uygulama ÇÖKMEMELİ (send hata fırlatır).
    ws = MagicMock()
    ws.recv.return_value = ""
    ws.send.side_effect = RuntimeError("socket is already closed")
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    p.start(on_translation=lambda t: None, on_source=lambda t: None)
    # exception sızdırmamalı
    p.feed_audio(b"\x00\x01" * 160)
    # kopuk bağlantı temizlenmeli; sonraki feed_audio sessiz no-op
    assert p._ws is None
    p.feed_audio(b"\x00\x01" * 160)  # ikinci çağrı da güvenli
