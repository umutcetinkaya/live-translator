"""OpenAI sesleri: Realtime API (gpt-realtime-2.1-mini) üzerinden metin okuma.

/v1/audio/speech (tts-1, gpt-4o-mini-tts) 6 Ocak 2027'de kapanıyor; yerine
geçen model yalnızca Realtime API'de çalışıyor. Sağlayıcı kalıcı bir
WebSocket açar, her cümle için konuşma geçmişine eklenmeyen (out-of-band)
bir yanıt ister ve gelen 24 kHz PCM parçalarını WAV olarak yazar.
"""

import base64
import json
import wave

import pytest

from providers.base import TTSProvider, ProviderError
from providers.openai import (OpenAITTSProvider, REALTIME_TTS_MODEL, REALTIME_VOICES,
                              realtime_voice)


class FakeWS:
    """Gönderilenleri kaydeder; her response.create'e senaryodaki olaylarla cevap verir."""

    def __init__(self, replies=None, fail_on_recv=False):
        self.sent = []
        self.replies = replies if replies is not None else [_audio_reply(b"\x01\x00" * 100)]
        self.queue = []
        self.closed = False
        self.fail_on_recv = fail_on_recv

    def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        if msg["type"] == "response.create":
            self.queue.extend(self.replies.pop(0) if self.replies else _audio_reply(b"\x02\x00" * 10))

    def recv(self):
        if self.fail_on_recv:
            raise ConnectionResetError("socket closed")
        return json.dumps(self.queue.pop(0))

    def close(self):
        self.closed = True

    def of_type(self, kind):
        return [m for m in self.sent if m["type"] == kind]


def _audio_reply(pcm, chunks=2):
    step = max(1, len(pcm) // chunks)
    parts = [pcm[i:i + step] for i in range(0, len(pcm), step)]
    events = [{"type": "response.created", "response": {"id": "r1"}}]
    events += [{"type": "response.output_audio.delta",
                "delta": base64.b64encode(p).decode()} for p in parts]
    events.append({"type": "response.done", "response": {"status": "completed"}})
    return events


class Factory:
    def __init__(self, *sockets):
        self.sockets = list(sockets)
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.sockets.pop(0) if self.sockets else FakeWS()


def _provider(tmp_path, factory=None, key="sk-test"):
    factory = factory or Factory(FakeWS())
    return OpenAITTSProvider(api_key=key, tmp_dir=str(tmp_path), ws_factory=factory), factory


def test_is_tts_provider():
    assert issubclass(OpenAITTSProvider, TTSProvider)


def test_connects_to_realtime_with_current_model(tmp_path):
    p, factory = _provider(tmp_path)
    p.synthesize("Merhaba", "tr", "marin", 1.0)
    url, headers = factory.calls[0]
    assert REALTIME_TTS_MODEL == "gpt-realtime-2.1-mini"
    assert url == "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1-mini"
    assert headers["Authorization"] == "Bearer sk-test"


def test_session_set_up_for_spoken_output(tmp_path):
    ws = FakeWS()
    p, _ = _provider(tmp_path, Factory(ws))
    p.synthesize("Merhaba", "tr", "cedar", 1.2)
    (update,) = ws.of_type("session.update")
    s = update["session"]
    assert s["type"] == "realtime"
    assert s["output_modalities"] == ["audio"]
    assert s["audio"]["output"] == {"format": {"type": "audio/pcm", "rate": 24000},
                                    "voice": "cedar", "speed": 1.2}
    # Model metni yanıtlamamalı, olduğu gibi okumalı
    assert "exactly as written" in s["instructions"]


def test_each_sentence_is_an_out_of_band_response(tmp_path):
    ws = FakeWS()
    p, _ = _provider(tmp_path, Factory(ws))
    p.synthesize("Toplantı perşembe.", "tr", "marin", 1.0)
    (create,) = ws.of_type("response.create")
    r = create["response"]
    assert r["conversation"] == "none"          # geçmiş birikmez, maliyet büyümez
    assert r["output_modalities"] == ["audio"]
    assert r["input"] == [{"type": "message", "role": "user",
                           "content": [{"type": "input_text", "text": "Toplantı perşembe."}]}]


def test_audio_written_as_24khz_wav(tmp_path):
    pcm = bytes(range(200))
    p, _ = _provider(tmp_path, Factory(FakeWS(replies=[_audio_reply(pcm, chunks=3)])))
    path = p.synthesize("Merhaba", "tr", "marin", 1.0)
    with wave.open(path) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (24000, 1, 2)
        assert w.readframes(w.getnframes()) == pcm


def test_connection_reused_for_next_sentence(tmp_path):
    ws = FakeWS(replies=[_audio_reply(b"\x01\x00" * 4), _audio_reply(b"\x02\x00" * 4)])
    p, factory = _provider(tmp_path, Factory(ws))
    p.synthesize("Bir.", "tr", "marin", 1.0)
    p.synthesize("İki.", "tr", "marin", 1.0)
    assert len(factory.calls) == 1
    assert len(ws.of_type("session.update")) == 1


def test_voice_change_opens_a_new_session(tmp_path):
    # Oturumda ses bir kez üretildikten sonra değiştirilemez
    first, second = FakeWS(), FakeWS()
    p, factory = _provider(tmp_path, Factory(first, second))
    p.synthesize("Bir.", "tr", "marin", 1.0)
    p.synthesize("İki.", "tr", "cedar", 1.0)
    assert len(factory.calls) == 2 and first.closed
    assert second.of_type("session.update")[0]["session"]["audio"]["output"]["voice"] == "cedar"


def test_speed_change_updates_the_session(tmp_path):
    ws = FakeWS(replies=[_audio_reply(b"\x01\x00" * 4), _audio_reply(b"\x02\x00" * 4)])
    p, factory = _provider(tmp_path, Factory(ws))
    p.synthesize("Bir.", "tr", "marin", 1.0)
    p.synthesize("İki.", "tr", "marin", 1.3)
    assert len(factory.calls) == 1
    assert ws.of_type("session.update")[-1]["session"]["audio"]["output"]["speed"] == 1.3


def test_speed_clamped_to_realtime_range(tmp_path):
    ws = FakeWS()
    p, _ = _provider(tmp_path, Factory(ws))
    p.synthesize("Hızlı.", "tr", "marin", 2.0)   # Ayarlar 2.0'a kadar izin veriyor
    assert ws.of_type("session.update")[0]["session"]["audio"]["output"]["speed"] == 1.5


def test_voices_from_speech_api_are_mapped():
    assert REALTIME_VOICES[:2] == ("marin", "cedar")
    assert realtime_voice("nova") == "marin"
    assert realtime_voice("onyx") == "cedar"
    assert realtime_voice("fable") == "verse"
    assert realtime_voice("shimmer") == "shimmer"
    assert realtime_voice("Kore") == "marin"     # Gemini adı ya da bilinmeyen
    assert realtime_voice("") == "marin"


def test_api_error_event_becomes_provider_error(tmp_path):
    err = [{"type": "error", "error": {"message": "Incorrect API key provided"}}]
    p, _ = _provider(tmp_path, Factory(FakeWS(replies=[err])))
    with pytest.raises(ProviderError, match="Incorrect API key"):
        p.synthesize("Merhaba", "tr", "marin", 1.0)


def test_failed_response_is_reported(tmp_path):
    failed = [{"type": "response.done",
               "response": {"status": "failed", "status_details": {"error": {"message": "server busy"}}}}]
    p, _ = _provider(tmp_path, Factory(FakeWS(replies=[failed])))
    with pytest.raises(ProviderError, match="server busy"):
        p.synthesize("Merhaba", "tr", "marin", 1.0)


def test_dropped_connection_is_retried_once(tmp_path):
    # Uzun sessizlikten sonra sunucu bağlantıyı kapatabilir
    p, factory = _provider(tmp_path, Factory(FakeWS(fail_on_recv=True), FakeWS()))
    path = p.synthesize("Merhaba", "tr", "marin", 1.0)
    assert path.endswith(".wav") and len(factory.calls) == 2


def test_gives_up_after_second_failure(tmp_path):
    p, _ = _provider(tmp_path, Factory(FakeWS(fail_on_recv=True), FakeWS(fail_on_recv=True)))
    with pytest.raises(ProviderError, match="OpenAI TTS"):
        p.synthesize("Merhaba", "tr", "marin", 1.0)


def test_no_api_key_raises(tmp_path):
    p, factory = _provider(tmp_path, key="")
    with pytest.raises(ProviderError, match="no API key"):
        p.synthesize("Merhaba", "tr", "marin", 1.0)
    assert factory.calls == []


def test_close_shuts_the_socket(tmp_path):
    ws = FakeWS()
    p, _ = _provider(tmp_path, Factory(ws))
    p.synthesize("Merhaba", "tr", "marin", 1.0)
    p.close()
    assert ws.closed


def test_factory_builds_realtime_provider():
    from providers import get_tts_provider
    p = get_tts_provider({"tts_provider": "openai", "openai_api_key": "sk-x"})
    assert isinstance(p, OpenAITTSProvider) and p._api_key == "sk-x"
