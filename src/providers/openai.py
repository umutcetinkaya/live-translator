"""OpenAI provider implementasyonları (çeviri + TTS)."""

from providers.base import TranslationProvider, TTSProvider, ProviderError

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

    def translate_document(self, source, prev_translation, target_lang, model):
        if not self._client:
            raise ProviderError("OpenAI: API key yok")
        is_reasoning = model.startswith("o")
        system = SYSTEM_PROMPT.replace("{target_lang}", target_lang)
        user_msg = f"Full transcript:\n\n{source}"
        if prev_translation:
            user_msg += ("\n\n---\nYour previous translation "
                         f"(refine/continue):\n{prev_translation}")
        params = {
            "model": model,
            "messages": [
                {"role": "developer" if is_reasoning else "system",
                 "content": system},
                {"role": "user", "content": user_msg},
            ],
        }
        if is_reasoning:
            params["max_completion_tokens"] = 2000
        else:
            params["max_tokens"] = 2000
            params["temperature"] = 0.2
        try:
            resp = self._client.chat.completions.create(**params)
            return resp.choices[0].message.content.strip()
        except Exception as e:
            raise ProviderError(f"OpenAI çeviri hatası: {e}") from e
