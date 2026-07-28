"""Gemini Live API realtime audio translation provider.

Uses Gemini's dedicated live-translation model with a first-class
translationConfig, rather than prompting a general Live model to translate.
Translated text arrives on serverContent.outputTranscription; the source
transcript on inputTranscription.

The async Live session runs in its own event loop on a dedicated thread.
feed_audio (called from another thread) puts audio chunks into an asyncio.Queue;
the sender task inside the loop forwards them, and the receiver task collects
the translation. Input: 16kHz PCM.
"""

import asyncio
import threading
import re
from providers.base import RealtimeProvider, ProviderError

# Dedicated live-translation model — preview tier, so pin it and watch for
# deprecation notices (Google gives >=2 weeks for preview models).
LIVE_TRANSLATE_MODEL = "gemini-3.5-live-translate-preview"


class GeminiRealtimeProvider(RealtimeProvider):
    def __init__(self, api_key, model=None, target_language="tr"):
        # `model` is accepted for a uniform factory signature but ignored:
        # realtime translation always runs on LIVE_TRANSLATE_MODEL, not on the
        # text model picked in Settings.
        self._api_key = api_key
        self._target_language = target_language
        self._on_translation = None
        self._on_source = None
        self._loop = None
        self._thread = None
        self._audio_q = None
        self._running = False
        self._translation = ""

    def start(self, on_translation, on_source):
        if not self._api_key:
            raise ProviderError("Gemini Realtime: no API key")
        self._on_translation = on_translation
        self._on_source = on_source
        self._running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[GeminiRealtime] Started (model={LIVE_TRANSLATE_MODEL}, "
              f"target={self._target_language})")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._session_main())
        except Exception as e:
            print(f"[GeminiRealtime] Session ended: {e}")
        finally:
            self._running = False

    def _build_config(self):
        """Live session config.

        translationConfig is a first-class field on the live-translate model —
        no system instruction needed, and the model won't answer questions it
        hears instead of translating them."""
        return {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": {},
            "output_audio_transcription": {},
            "translation_config": {
                "target_language_code": self._target_language,
            },
            "realtime_input_config": {
                "automatic_activity_detection": {
                    "silence_duration_ms": 500,
                }
            },
        }

    async def _session_main(self):
        from google import genai
        client = genai.Client(api_key=self._api_key)
        self._audio_q = asyncio.Queue()
        async with client.aio.live.connect(
            model=LIVE_TRANSLATE_MODEL, config=self._build_config()
        ) as session:
            print("[GeminiRealtime] Live session opened")
            sender = asyncio.create_task(self._sender(session))
            try:
                await self._receiver(session)
            finally:
                sender.cancel()

    async def _sender(self, session):
        from google.genai import types
        while self._running:
            try:
                chunk = await asyncio.wait_for(self._audio_q.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            try:
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                )
            except Exception as e:
                print(f"[GeminiRealtime] send error: {e}")
                break

    async def _receiver(self, session):
        async for response in session.receive():
            if not self._running:
                break
            text = self._extract_text(response)
            if text:
                self._translation += text
                self._flush_sentences()

    @staticmethod
    def _extract_text(response):
        sc = getattr(response, "server_content", None)
        if sc is not None:
            ot = getattr(sc, "output_transcription", None)
            if ot is not None and getattr(ot, "text", None):
                return ot.text
        return getattr(response, "text", None)

    def _flush_sentences(self):
        while True:
            m = re.search(r"[.!?…]+[\s]*", self._translation)
            if not m:
                break
            end = m.end()
            sentence = self._translation[:end].strip()
            self._translation = self._translation[end:]
            if sentence and self._on_translation:
                self._on_translation(sentence)

    def feed_audio(self, pcm_chunk):
        if not self._running or not self._loop or self._audio_q is None:
            return
        try:
            self._loop.call_soon_threadsafe(self._audio_q.put_nowait, pcm_chunk)
        except Exception:
            pass

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
