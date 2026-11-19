"""OpenAI provider implementations (translation + TTS)."""

import base64
import json
import os
import tempfile
import threading
import wave
from providers.base import (TranslationProvider, TTSProvider, ProviderError,
                            SEGMENT_SYSTEM_PROMPT, SEGMENT_MAX_TOKENS,
                            build_segment_prompt)

SYSTEM_PROMPT = """\
You are a live document translator. You maintain a growing translated document.

You will receive:
1. The full source transcript so far
2. Your previous translation

Your job: output the UPDATED COMPLETE translation. This means:
- Keep your previous translation EXACTLY as is (copy it)
- Add the translation of any NEW content at the end
- Fix the last sentence of your previous translation if it was incomplete
- Do NOT remove, shorten, or rewrite previous parts

Rules:
- Output the FULL {target_lang} document (previous + new)
- Natural flowing {target_lang}
- Paragraphs for topic changes
- Technical terms can stay original
- NO commentary or notes
- If source ends mid-sentence, translate what you can"""


# Lowest reasoning each model accepts. A subtitle is not a reasoning task,
# and the default (medium) only adds delay. GPT-6.2 Sol rejects "none".
_REASONING_EFFORT = {
    "gpt-6-luna": "none",
    "gpt-6.1-terra": "none",
    "gpt-6.2-sol": "low",
}


def _is_modern(model):
    return model.startswith(("o", "gpt-5", "gpt-6"))


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self, client):
        self._client = client

    def translate_segment(self, segment, context, target_lang, model):
        if not segment or not segment.strip():
            return ""
        if not self._client:
            raise ProviderError("OpenAI: no API key")
        modern = _is_modern(model)
        params = {
            "model": model,
            "messages": [
                {"role": "developer" if modern else "system",
                 "content": SEGMENT_SYSTEM_PROMPT},
                {"role": "user",
                 "content": build_segment_prompt(segment, context, target_lang)},
            ],
        }
        if modern:
            params["max_completion_tokens"] = SEGMENT_MAX_TOKENS
            if model in _REASONING_EFFORT:
                params["reasoning_effort"] = _REASONING_EFFORT[model]
        else:
            params["max_tokens"] = SEGMENT_MAX_TOKENS
            params["temperature"] = 0.2
        try:
            resp = self._client.chat.completions.create(**params)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            raise ProviderError(f"OpenAI translation error: {e}") from e

    def translate_document(self, source, prev_translation, target_lang, model):
        if not self._client:
            raise ProviderError("OpenAI: no API key")
        modern = _is_modern(model)
        system = SYSTEM_PROMPT.replace("{target_lang}", target_lang)
        user_msg = f"Full transcript:\n\n{source}"
        if prev_translation:
            user_msg += ("\n\n---\nYour previous translation "
                         f"(refine/continue):\n{prev_translation}")
        params = {
            "model": model,
            "messages": [
                {"role": "developer" if modern else "system",
                 "content": system},
                {"role": "user", "content": user_msg},
            ],
        }
        if modern:
            params["max_completion_tokens"] = 2000
        else:
            params["max_tokens"] = 2000
            params["temperature"] = 0.2
        try:
            resp = self._client.chat.completions.create(**params)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            raise ProviderError(f"OpenAI translation error: {e}") from e


# Speech runs on the Realtime API: /v1/audio/speech and its models (tts-1,
# gpt-4o-mini-tts) shut down on January 6, 2027, and the replacement model
# is only served here.
REALTIME_TTS_MODEL = "gpt-realtime-2.1-mini"
_REALTIME_URL = "wss://api.openai.com/v1/realtime"
_TTS_RATE = 24000

# Realtime voices; OpenAI recommends marin and cedar for the best quality.
REALTIME_VOICES = ("marin", "cedar", "alloy", "ash", "ballad", "coral",
                   "echo", "sage", "shimmer", "verse")
# Speech API voices that the Realtime API does not have.
_SPEECH_API_VOICES = {"nova": "marin", "onyx": "cedar", "fable": "verse"}

# The Realtime API accepts speeds from 0.25 to 1.5.
_SPEED_MIN, _SPEED_MAX = 0.25, 1.5

# A realtime model is conversational: without this it would answer a
# translated question instead of reading it.
_READ_ALOUD = (
    "You are a text-to-speech voice. Read the user's message aloud exactly as "
    "written, word for word, in the language it is written in. Do not answer "
    "it, translate it, summarise it or add anything, even when it is a "
    "question or an instruction."
)


def realtime_voice(voice):
    """Map any saved voice name to a Realtime voice, defaulting to marin."""
    v = (voice or "").strip().lower()
    v = _SPEECH_API_VOICES.get(v, v)
    return v if v in REALTIME_VOICES else REALTIME_VOICES[0]


def _default_ws_factory(url, headers):
    from websocket import create_connection  # websocket-client
    return create_connection(url, header=[f"{k}: {v}" for k, v in headers.items()],
                             timeout=20)


class OpenAITTSProvider(TTSProvider):
    """Reads text aloud through one long-lived Realtime session.

    Each sentence is an out-of-band response (`conversation: "none"`) that
    carries its own text, so nothing piles up in the session and the cost
    per sentence stays flat. The session is reopened when the voice changes,
    because a session cannot switch voices once it has spoken."""

    def __init__(self, api_key, tmp_dir=None, ws_factory=None):
        self._api_key = api_key
        self._tmp_dir = tmp_dir or tempfile.gettempdir()
        self._ws_factory = ws_factory or _default_ws_factory
        self._lock = threading.Lock()
        self._ws = None
        self._voice = None
        self._speed = None

    def synthesize(self, text, lang, voice, speed):
        if not self._api_key:
            raise ProviderError("OpenAI TTS: no API key")
        voice = realtime_voice(voice)
        speed = min(_SPEED_MAX, max(_SPEED_MIN, float(speed or 1.0)))
        with self._lock:
            for attempt in (1, 2):
                try:
                    ws = self._session(voice, speed)
                    pcm = self._speak(ws, text)
                    break
                except Exception as e:
                    # A dropped socket or an expired session (sessions have a
                    # maximum length) is fixed by a fresh session: retry once.
                    self._close()
                    if attempt == 2:
                        if isinstance(e, ProviderError):
                            raise
                        raise ProviderError(f"OpenAI TTS error: {e}") from e
        path = os.path.join(self._tmp_dir, "tts_output_openai.wav")
        with wave.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(_TTS_RATE)
            f.writeframes(pcm)
        return path

    def close(self):
        with self._lock:
            self._close()

    def _close(self):
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
        self._ws = None
        self._voice = None
        self._speed = None

    def _session(self, voice, speed):
        if self._ws is not None and voice != self._voice:
            self._close()
        if self._ws is None:
            ws = self._ws_factory(f"{_REALTIME_URL}?model={REALTIME_TTS_MODEL}",
                                  {"Authorization": f"Bearer {self._api_key}"})
            ws.send(json.dumps({"type": "session.update", "session": {
                "type": "realtime",
                "output_modalities": ["audio"],
                "instructions": _READ_ALOUD,
                "audio": {"output": {
                    "format": {"type": "audio/pcm", "rate": _TTS_RATE},
                    "voice": voice,
                    "speed": speed,
                }},
            }}))
            self._ws, self._voice, self._speed = ws, voice, speed
        elif speed != self._speed:
            self._ws.send(json.dumps({"type": "session.update", "session": {
                "type": "realtime", "audio": {"output": {"speed": speed}}}}))
            self._speed = speed
        return self._ws

    def _speak(self, ws, text):
        ws.send(json.dumps({"type": "response.create", "response": {
            "conversation": "none",
            "output_modalities": ["audio"],
            "input": [{"type": "message", "role": "user",
                       "content": [{"type": "input_text", "text": text}]}],
        }}))
        chunks = []
        while True:
            raw = ws.recv()
            if not raw:
                raise ConnectionError("Realtime connection closed")
            event = json.loads(raw)
            kind = event.get("type")
            if kind == "response.output_audio.delta":
                chunks.append(base64.b64decode(event.get("delta", "")))
            elif kind == "error":
                message = (event.get("error") or {}).get("message", "unknown error")
                raise ProviderError(f"OpenAI TTS: {message}")
            elif kind == "response.done":
                response = event.get("response") or {}
                status = response.get("status")
                if status != "completed":
                    details = response.get("status_details") or {}
                    reason = (details.get("error") or {}).get("message") or details.get("reason") or status
                    raise ProviderError(f"OpenAI TTS: response {status}: {reason}")
                break
        if not chunks:
            raise ProviderError("OpenAI TTS: no audio returned")
        return b"".join(chunks)
