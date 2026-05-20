"""Gemini provider implementasyonları (çeviri + TTS) — google-genai SDK."""

import os
import wave
import tempfile
from providers.base import TranslationProvider, TTSProvider, ProviderError

SYSTEM_PROMPT = """\
You are a live document translator. You maintain a growing translated document.
Keep your previous translation EXACTLY as is, append the translation of new
content, and fix only the last incomplete sentence. Output the FULL {target_lang}
document. Natural flowing {target_lang}. No commentary."""


class GeminiTranslationProvider(TranslationProvider):
    def __init__(self, client):
        self._client = client

    def translate_document(self, source, prev_translation, target_lang, model):
        if not self._client:
            raise ProviderError("Gemini: API key yok")
        system = SYSTEM_PROMPT.replace("{target_lang}", target_lang)
        user_msg = f"Full transcript:\n\n{source}"
        if prev_translation:
            user_msg += ("\n\n---\nYour previous translation "
                         f"(refine/continue):\n{prev_translation}")
        prompt = f"{system}\n\n{user_msg}"
        try:
            resp = self._client.models.generate_content(
                model=model, contents=prompt,
            )
            return (resp.text or "").strip()
        except Exception as e:
            raise ProviderError(f"Gemini çeviri hatası: {e}") from e


# Gemini TTS çıktısı: 24kHz, 16-bit, mono PCM
_TTS_RATE = 24000
_TTS_MODEL = "gemini-2.5-flash-preview-tts"


class GeminiTTSProvider(TTSProvider):
    def __init__(self, client, tmp_dir=None):
        self._client = client
        self._tmp_dir = tmp_dir or tempfile.gettempdir()

    def synthesize(self, text, lang, voice, speed):
        if not self._client:
            raise ProviderError("Gemini TTS: API key yok")
        try:
            from google.genai import types
            resp = self._client.models.generate_content(
                model=_TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice or "Kore",
                            )
                        )
                    ),
                ),
            )
            pcm = resp.candidates[0].content.parts[0].inline_data.data
        except ImportError as e:
            raise ProviderError(f"Gemini TTS: google-genai yüklü değil: {e}") from e
        except Exception as e:
            raise ProviderError(f"Gemini TTS hatası: {e}") from e

        path = os.path.join(self._tmp_dir, "tts_output.wav")
        with wave.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(_TTS_RATE)
            f.writeframes(pcm)
        return path
