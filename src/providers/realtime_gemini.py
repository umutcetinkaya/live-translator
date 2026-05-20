"""Gemini Live API realtime ses çeviri provider'ı.

NOT: Live API session/event şeması resmi dokümandan teyit edilmeli.
Bu iskelet senkron arayüzü (feed_audio/stop) korur; Live API'nin async
session'ı ayrı bir thread içinde event loop ile sürülür.
"""

import asyncio
import threading
from providers.base import RealtimeProvider, ProviderError


class GeminiRealtimeProvider(RealtimeProvider):
    def __init__(self, api_key, model):
        self._api_key = api_key
        self._model = model
        self._on_translation = None
        self._on_source = None
        self._loop = None
        self._thread = None
        self._session = None
        self._running = False

    def start(self, on_translation, on_source):
        if not self._api_key:
            raise ProviderError("Gemini Realtime: API key yok")
        self._on_translation = on_translation
        self._on_source = on_source
        self._running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session_main())
        except Exception as e:
            print(f"[GeminiRealtime] Oturum sonlandı: {e}")
        finally:
            # Oturum öldü: feed_audio'nun ölü session'a göndermesini engelle.
            # NOT: pipeline'a tam runtime fallback canlı entegrasyon turunda eklenecek.
            self._running = False
            self._session = None

    async def _session_main(self):
        from google import genai
        client = genai.Client(api_key=self._api_key)
        config = {"response_modalities": ["TEXT"]}
        async with client.aio.live.connect(model=self._model,
                                            config=config) as session:
            self._session = session
            async for response in session.receive():
                if not self._running:
                    break
                text = getattr(response, "text", None)
                if text and self._on_translation:
                    self._on_translation(text)

    def feed_audio(self, pcm_chunk):
        if not self._session or not self._loop:
            return
        async def _send():
            await self._session.send_realtime_input(
                audio={"data": pcm_chunk, "mime_type": "audio/pcm;rate=16000"}
            )
        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._session = None
