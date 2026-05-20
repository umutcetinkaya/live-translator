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

def test_output_transcript_delta_emits_complete_sentences():
    # Çeviri delta'ları cümle sonuna gelince balon olarak emit edilmeli.
    ws = MagicMock()
    ws.recv.return_value = ""
    p = OpenAIRealtimeProvider(api_key="k", model="gpt-realtime-translate",
                               ws_factory=lambda *a, **k: ws)
    sentences = []
    p._on_translation = sentences.append
    # delta'ları elle besle (gerçek event akışını taklit)
    for d in ["Mer", "haba", " dünya.", " Nasıl", "sın", "?"]:
        p._translation += d
        p._flush_sentences()
    assert sentences == ["Merhaba dünya.", "Nasılsın?"]

def test_emit_remaining_flushes_partial():
    ws = MagicMock()
    p = OpenAIRealtimeProvider(api_key="k", model="m",
                               ws_factory=lambda *a, **k: ws)
    out = []
    p._on_translation = out.append
    p._translation = "yarım cümle"
    p._emit_remaining()
    assert out == ["yarım cümle"]
    assert p._translation == ""

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
