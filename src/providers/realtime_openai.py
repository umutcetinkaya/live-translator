"""OpenAI Realtime ses çeviri provider'ı (GA Realtime Translation, WebSocket).

Özel çeviri endpoint'i /v1/realtime/translations kullanır. Kaynak dili otomatik
algılanır; sadece hedef dil verilir. Çeviri, output_transcript.delta event'leriyle
parça parça gelir. ws_factory enjekte edilebilir (test: mock, üretim: gerçek socket).
"""

import base64
import json
import threading
from providers.base import RealtimeProvider, ProviderError

# GA Realtime Translation: özel çeviri endpoint'i (normal /v1/realtime DEĞİL).
_URL = "wss://api.openai.com/v1/realtime/translations"


def _default_ws_factory(url, headers):
    from websocket import create_connection  # websocket-client
    return create_connection(url, header=[f"{k}: {v}" for k, v in headers.items()])


class OpenAIRealtimeProvider(RealtimeProvider):
    def __init__(self, api_key, model, ws_factory=None, target_language="tr",
                 source_language="en"):
        self._api_key = api_key
        self._model = model
        self._ws_factory = ws_factory or _default_ws_factory
        self._target_language = target_language
        self._source_language = source_language
        self._ws = None
        self._on_translation = None
        self._on_source = None
        self._reader = None
        self._running = False
        self._translation = ""

    def start(self, on_translation, on_source):
        if not self._api_key:
            raise ProviderError("OpenAI Realtime: API key yok")
        self._on_translation = on_translation
        self._on_source = on_source
        # GA Realtime: OpenAI-Beta header KULLANILMAZ. Model query'de verilir.
        headers = {"Authorization": f"Bearer {self._api_key}"}
        url = f"{_URL}?model={self._model}"
        self._ws = self._ws_factory(url, headers)
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._configure_session()
        print(f"[OpenAIRealtime] Bağlandı (hedef dil={self._target_language})")

    def _configure_session(self):
        ws = self._ws
        if not ws:
            return
        # Çeviri oturumu: kaynak otomatik algılanır, sadece hedef dil verilir.
        cfg = {
            "type": "session.update",
            "session": {
                "audio": {
                    "input": {
                        "transcription": {"model": "gpt-realtime-whisper"},
                        "noise_reduction": {"type": "near_field"},
                    },
                    "output": {"language": self._target_language},
                },
            },
        }
        try:
            ws.send(json.dumps(cfg))
        except Exception as e:
            print(f"[OpenAIRealtime] session.update hatası: {e}")

    def feed_audio(self, pcm_chunk):
        ws = self._ws
        if not ws:
            return
        b64 = base64.b64encode(pcm_chunk).decode("ascii")
        try:
            ws.send(json.dumps({
                "type": "session.input_audio_buffer.append", "audio": b64,
            }))
        except Exception as e:
            # Kopuk/kapalı socket'e yazma uygulamayı çökertmemeli.
            # feed_audio native dispatch thread'inden çağrılır; hatayı burada yut.
            print(f"[OpenAIRealtime] Bağlantı koptu, ses gönderilemedi: {e}")
            self._close()

    def _close(self):
        """Bağlantıyı güvenle kapat ve durumu temizle (tekrar çağrılabilir)."""
        self._running = False
        ws, self._ws = self._ws, None
        if ws:
            try:
                ws.close()
            except Exception:
                pass

    def _read_loop(self):
        while self._running and self._ws:
            try:
                raw = self._ws.recv()
            except Exception:
                # Bağlantı koptu — döngüden çık (stop/feed_audio temizler).
                break
            if not raw:
                continue
            try:
                evt = json.loads(raw)
            except Exception:
                continue
            etype = evt.get("type", "")
            # Çeviri delta (parça) olarak gelir. Cümle sonu (.?!…) görünce tam cümleyi
            # bir balon olarak gönderip biriktiriciyi sıfırlarız (akışkan değil, balon).
            if etype == "session.output_transcript.delta":
                delta = evt.get("delta", "")
                if delta:
                    self._translation += delta
                    self._flush_sentences()
            elif etype in ("session.output_transcript.done",
                           "session.output_transcript.completed"):
                # Segment bitti: kalan metni balon olarak gönder.
                self._emit_remaining()
            elif etype == "session.input_audio_transcription.delta":
                delta = evt.get("delta", "")
                if delta and self._on_source:
                    self._on_source(delta)
            elif etype == "error":
                print(f"[OpenAIRealtime] API error: {evt.get('error')}")

    def _flush_sentences(self):
        """Biriken metinde tamamlanmış cümleleri (.?!… ile biten) balon olarak gönder."""
        import re
        while True:
            m = re.search(r"[.!?…]+[\s]*", self._translation)
            if not m:
                break
            end = m.end()
            sentence = self._translation[:end].strip()
            self._translation = self._translation[end:]
            if sentence and self._on_translation:
                self._on_translation(sentence)

    def _emit_remaining(self):
        rest = self._translation.strip()
        self._translation = ""
        if rest and self._on_translation:
            self._on_translation(rest)

    def stop(self):
        self._close()
