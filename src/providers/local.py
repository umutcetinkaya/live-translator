"""On-device translation with TranslateGemma on MLX: free, no API key.

TranslateGemma is a translation model, not a chat model. Its chat template
builds the prompt itself from one message carrying the source language code,
the target language code and the text, so the shared segment prompt used by
the cloud providers does not apply here. General chat models of the same size
were tried first and kept getting weekdays, times and negations wrong in
Turkish; see README, "Free mode".

There is no slot for context: anything added to the text gets translated too,
and would be spoken twice. Segments are whole sentences, which is enough.

The model is loaded once and kept in memory; generation is serialised because
MLX models are not safe to drive from two threads at once.
"""

import re
import threading

import model_store
from config import LANGUAGE_NAMES
from providers.base import TranslationProvider, ProviderError, SEGMENT_MAX_TOKENS

# A segment is a sentence or two; a quarter of the cloud ceiling is plenty
# and keeps a runaway generation from stalling the live translation.
MAX_TOKENS = SEGMENT_MAX_TOKENS // 4

# TranslateGemma ends its turn with this token, but the tokenizer does not
# list it as an end-of-sequence token, so generation would run on to
# MAX_TOKENS without it.
END_OF_TURN = "<end_of_turn>"

_CODES = {name.lower(): code for code, name in LANGUAGE_NAMES.items()}
_LABEL = re.compile(r"^\s*(translation|translated text|turkish|output)\s*:\s*", re.I)
_QUOTES = "\"'“”«»「」"


def _clean(text):
    text = (text or "").split(END_OF_TURN)[0].strip()
    text = _LABEL.sub("", text).strip()
    if len(text) >= 2 and text[0] in _QUOTES and text[-1] in _QUOTES:
        text = text[1:-1].strip()
    return text


def _language_code(value):
    """'Turkish' or 'tr' → 'tr'; a locale such as 'zh-CN' → 'zh'."""
    value = (value or "").strip()
    return _CODES.get(value.lower(), value.split("-")[0].split("_")[0].lower())


def _mlx_load(path):
    from mlx_lm import load
    model, tokenizer = load(path)
    tokenizer.add_eos_token(END_OF_TURN)
    return model, tokenizer


def _mlx_generate(model, tokenizer, prompt):
    from mlx_lm import generate
    from mlx_lm.sample_utils import make_sampler
    # Greedy: a translation has one right answer, sampling only adds drift.
    return generate(model, tokenizer, prompt=prompt, max_tokens=MAX_TOKENS,
                    sampler=make_sampler(temp=0.0))


class LocalTranslationProvider(TranslationProvider):

    def __init__(self, config=None, loader=None, generator=None):
        # The pipeline updates this same dict when the user switches languages,
        # so the source language is read on every call rather than copied here.
        self._config = config if config is not None else {}
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

    def _prompt(self, text, source, target):
        messages = [{"role": "user", "content": [{
            "type": "text", "source_lang_code": source,
            "target_lang_code": target, "text": text,
        }]}]
        try:
            return self._tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        except Exception as e:
            raise ProviderError(
                f"Local model does not support the language pair {source} → {target}: {e}") from e

    def translate_segment(self, segment, context, target_lang, model):
        source = _language_code(self._config.get("source_locale", "en-US"))
        target = _language_code(target_lang)
        with self._lock:
            self._ensure_model(model)
            prompt = self._prompt(segment, source, target)
            try:
                raw = self._generator(self._model, self._tokenizer, prompt)
            except Exception as e:
                raise ProviderError(f"Local translation error: {e}") from e
        return _clean(raw)

    def translate_document(self, source, prev_translation, target_lang, model):
        return self.translate_segment(source, "", target_lang, model)
