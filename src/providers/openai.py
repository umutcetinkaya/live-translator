"""OpenAI provider implementations (translation + TTS)."""

import os
import tempfile
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


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self, client):
        self._client = client

    def translate_segment(self, segment, context, target_lang, model):
        if not segment or not segment.strip():
            return ""
        if not self._client:
            raise ProviderError("OpenAI: no API key")
        modern = model.startswith("o") or model.startswith("gpt-5")
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
        modern = model.startswith("o") or model.startswith("gpt-5")
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


class OpenAITTSProvider(TTSProvider):
    def __init__(self, client, tmp_dir=None):
        self._client = client
        self._tmp_dir = tmp_dir or tempfile.gettempdir()

    def synthesize(self, text, lang, voice, speed):
        if not self._client:
            raise ProviderError("OpenAI TTS: no API key")
        try:
            resp = self._client.audio.speech.create(
                model="tts-1", voice=voice, input=text, speed=speed,
            )
            path = os.path.join(self._tmp_dir, "tts_output.mp3")
            resp.stream_to_file(path)
            return path
        except Exception as e:
            raise ProviderError(f"OpenAI TTS error: {e}") from e
