"""Gemini provider implementasyonları (çeviri + TTS) — google-genai SDK."""

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
