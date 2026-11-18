"""On-device translation with a local MLX model: free, no API key.

Uses the same segment prompt as the cloud providers, so the incremental
translator behaves identically whichever provider is selected. The model is
loaded once and kept in memory; generation is serialised because MLX models
are not safe to drive from two threads at once.
"""

import re
import threading

import model_store
from providers.base import (TranslationProvider, ProviderError,
                            SEGMENT_SYSTEM_PROMPT, SEGMENT_MAX_TOKENS,
                            build_segment_prompt)

# A segment is a sentence or two; a quarter of the cloud ceiling is plenty
# and keeps a runaway generation from stalling the live translation.
MAX_TOKENS = SEGMENT_MAX_TOKENS // 4
TEMPERATURE = 0.2

_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_LABEL = re.compile(r"^\s*(translation|translated text|turkish|output)\s*:\s*", re.I)
_QUOTES = "\"'“”«»「」"


def _clean(text):
    text = _THINK.sub("", text or "").strip()
    text = _LABEL.sub("", text).strip()
    if len(text) >= 2 and text[0] in _QUOTES and text[-1] in _QUOTES:
        text = text[1:-1].strip()
    return text


def _mlx_load(path):
    from mlx_lm import load
    return load(path)


def _mlx_generate(model, tokenizer, prompt):
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=make_sampler(temp=TEMPERATURE))


class LocalTranslationProvider(TranslationProvider):

    def __init__(self, loader=None, generator=None):
        self._loader = loader or _mlx_load
        self._generator = generator or _mlx_generate
        self._lock = threading.Lock()
        self._loaded_repo = None
        self._model = None
        self._tokenizer = None

    def _ensure_model(self, repo):
        if not model_store.is_ready(repo):
            raise ProviderError("Local model not ready")
        if self._loaded_repo == repo:
            return
        try:
            self._model, self._tokenizer = self._loader(model_store.model_dir(repo))
        except Exception as e:
            raise ProviderError(f"Local model failed to load: {e}") from e
        self._loaded_repo = repo

    def _prompt(self, messages):
        try:
            return self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, enable_thinking=False)
        except TypeError:
            return self._tokenizer.apply_chat_template(
                messages, add_generation_prompt=True)

    def translate_segment(self, segment, context, target_lang, model):
        messages = [
            {"role": "system", "content": SEGMENT_SYSTEM_PROMPT},
            {"role": "user", "content": build_segment_prompt(segment, context, target_lang)},
        ]
        with self._lock:
            self._ensure_model(model)
            try:
                raw = self._generator(self._model, self._tokenizer, self._prompt(messages))
            except Exception as e:
                raise ProviderError(f"Local translation error: {e}") from e
        return _clean(raw)

    def translate_document(self, source, prev_translation, target_lang, model):
        return self.translate_segment(source, "", target_lang, model)
