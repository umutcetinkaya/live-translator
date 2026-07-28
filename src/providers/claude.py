"""Anthropic Claude provider (translation only).

Anthropic has no audio or TTS API — the Messages API accepts text, images and
PDFs only, and streaming is SSE (one-way). So Claude plugs into the on-device
STT path as a text translator; there is no realtime or TTS provider here.

The system prompt is a single cached block: the same prefix is re-sent every
~3 seconds, so caching drops it to ~0.1x input cost. Everything volatile
(target language, transcript, previous translation) goes in the user message —
a byte change in the prefix would invalidate the cache.
"""

from providers.base import TranslationProvider, ProviderError

# Frozen — must stay byte-identical across calls for the prompt cache to hit.
SYSTEM_PROMPT = """\
You are a live document translator. You maintain a growing translated document.

You will receive:
1. The target language
2. The full source transcript so far
3. Your previous translation

Your job: output the UPDATED COMPLETE translation. This means:
- Keep your previous translation EXACTLY as is (copy it)
- Add the translation of any NEW content at the end
- Fix the last sentence of your previous translation if it was incomplete
- Do NOT remove, shorten, or rewrite previous parts

Rules:
- Output the FULL translated document (previous + new)
- Natural flowing prose in the target language
- Paragraphs for topic changes
- Technical terms can stay original
- NO commentary or notes
- If source ends mid-sentence, translate what you can"""

# The live document is resent in full every cycle, so the output grows with the
# session. 4096 truncated long translations mid-sentence.
MAX_TOKENS = 16000

# Per-model tuning. Adaptive thinking is on by default on Sonnet 5 and Opus 5
# and costs latency in a sub-second subtitle loop, so it is disabled; Haiku 4.5
# has no thinking to disable and rejects the parameter. Effort is only accepted
# by the models that reason, and `low` is the right setting here — translation
# is not a reasoning task, and lower effort means fewer tokens and less delay.
_MODEL_TUNING = {
    "claude-haiku-4-5": {},
    "claude-sonnet-5": {"thinking": {"type": "disabled"}},
    "claude-opus-5": {"thinking": {"type": "disabled"}},
}


class ClaudeTranslationProvider(TranslationProvider):
    def __init__(self, client):
        self._client = client

    def translate_document(self, source, prev_translation, target_lang, model):
        if not self._client:
            raise ProviderError("Claude: no API key")

        user_msg = f"Target language: {target_lang}\n\nFull transcript:\n\n{source}"
        if prev_translation:
            user_msg += ("\n\n---\nYour previous translation "
                         f"(refine/continue):\n{prev_translation}")

        params = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": [{
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            "messages": [{"role": "user", "content": user_msg}],
        }
        params.update(_MODEL_TUNING.get(model, {}))

        try:
            resp = self._client.messages.create(**params)
            parts = [b.text for b in resp.content
                     if getattr(b, "type", None) == "text"]
            return "".join(parts).strip()
        except Exception as e:
            raise ProviderError(f"Claude translation error: {e}") from e
