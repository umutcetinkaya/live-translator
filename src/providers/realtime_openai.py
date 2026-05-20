"""OpenAI Realtime ses çeviri provider'ı (WebSocket).

NOT: Event isimleri/şeması resmi Realtime API dokümanından teyit edilmeli.
ws_factory enjekte edilebilir (test: mock, üretim: gerçek websocket).
"""

import base64
import json
import threading
from providers.base import RealtimeProvider, ProviderError

_URL = "wss://api.openai.com/v1/realtime"


def _default_ws_factory(url, headers):
    from websocket import create_connection  # websocket-client
    return create_connection(url, header=[f"{k}: {v}" for k, v in headers.items()])


class OpenAIRealtimeProvider(RealtimeProvider):
    def __init__(self, api_key, model, ws_factory=None):
        self._api_key = api_key
        self._model = model
        self._ws_factory = ws_factory or _default_ws_factory
        self._ws = None
        self._on_translation = None
        self._on_source = None
        self._reader = None
        self._running = False

    def start(self, on_translation, on_source):
        if not self._api_key:
            raise ProviderError("OpenAI Realtime: API key yok")
        self._on_translation = on_translation
        self._on_source = on_source
        headers = {"Authorization": f"Bearer {self._api_key}",
                   "OpenAI-Beta": "realtime=v1"}
        self._ws = self._ws_factory(f"{_URL}?model={self._model}", headers)
        self._running = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def feed_audio(self, pcm_chunk):
        ws = self._ws
        if not ws:
            return
        b64 = base64.b64encode(pcm_chunk).decode("ascii")
        try:
            ws.send(json.dumps({
                "type": "input_audio_buffer.append", "audio": b64,
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
            text = evt.get("text") or evt.get("transcript") or ""
            if "translation" in etype and self._on_translation and text:
                self._on_translation(text)
            elif "transcription" in etype and self._on_source and text:
                self._on_source(text)

    def stop(self):
        self._close()
