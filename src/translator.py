"""Incremental translation — provider-agnostic orchestrator.

Each settled sentence is translated once and then frozen: committed text is
never re-sent or rewritten. The earlier design re-translated the whole
transcript every cycle, which grew to 600+ words per call — output hit the
token ceiling and got truncated, and quality fell as the context grew.

The translator sees only the new sentences plus a couple of earlier ones as
read-only context.
"""

import threading
import time
from config import load_config, normalize_model
from providers import get_translation_provider
from providers.base import ProviderError
from segmenter import split_sentences, stable_prefix, flush_prefix

# Prior source sentences handed to the translator as background. Deliberately
# small: with a few hundred tokens of context, models start repeating earlier
# sentences instead of translating the new one.
CONTEXT_SENTENCES = 2


def _friendly(message):
    """Turn a provider error into something the user can act on."""
    low = message.lower()
    if "no api key" in low or "authentication" in low or "401" in low:
        return "Translation API key missing or invalid — check Settings"
    if "rate_limit" in low or "429" in low:
        return "Rate limit reached — the provider is throttling requests"
    if "credit" in low or "quota" in low or "billing" in low:
        return "Provider quota or billing issue — check your account"
    if "connection" in low or "timeout" in low:
        return "Network problem reaching the translation provider"
    return f"Translation failed: {message}"


class AITranslator:
    # How often to look for newly-settled sentences. Sentence boundaries decide
    # *what* gets translated; this only decides how often we check.
    TRANSLATE_INTERVAL = 0.6

    def __init__(self, on_translation=None, config=None, on_error=None):
        self._on_full_update = on_translation
        self._on_error = on_error
        self._last_error = None
        self._config = config or load_config()
        self._provider = get_translation_provider(self._config)
        self._target_lang = self._config.get("target_lang", "tr")
        self._lock = threading.Lock()
        self._source_buffer = ""
        self._committed = ""          # frozen translation — never rewritten
        self._committed_source = ""   # source already translated
        self._running = False
        self._worker = None
        print(f"[Translator] {self._config.get('model')} ready")

    def start(self):
        self._running = True
        self._worker = threading.Thread(target=self._translate_loop, daemon=True)
        self._worker.start()

    def stop(self):
        self._running = False
        print("[Translator] Stopped")

    def update_source(self, full_text):
        with self._lock:
            self._source_buffer = full_text

    def update_config(self, config):
        self._config = config
        self._provider = get_translation_provider(config)
        self._target_lang = config.get("target_lang", "tr")
        print(f"[Translator] Config updated: {config.get('model')}")

    def set_target_lang(self, lang_code):
        self._target_lang = lang_code

    def clear(self):
        with self._lock:
            self._source_buffer = ""
            self._committed = ""
            self._committed_source = ""

    def _lang_name(self):
        names = {
            "tr": "Turkish", "en": "English", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
            "ko": "Korean", "ru": "Russian", "ar": "Arabic", "pt": "Portuguese",
        }
        return names.get(self._target_lang, self._target_lang)

    def _context_sentences(self, n=CONTEXT_SENTENCES):
        """Last n committed source sentences, as read-only background.

        Bounded on purpose: given a few hundred tokens of history, models drift
        into repeating earlier sentences instead of translating the new one."""
        return " ".join(split_sentences(self._committed_source)[-n:])

    def _translate_loop(self):
        while self._running:
            time.sleep(self.TRANSLATE_INTERVAL)
            if not self._running:
                break
            self._translate_pending()

    def on_speech_pause(self):
        """Speaker stopped — translate whatever is still waiting.

        Segments are held until they carry a full thought, which would leave
        the last words of an utterance stranded. A pause means the thought is
        over, so it is safe to commit."""
        self._translate_pending(flush=True)

    def _translate_pending(self, flush=False):
        """Translate whatever settled source hasn't been translated yet.

        Only complete thoughts are translated; the trailing partial is left
        alone because recognition may still rewrite it. `flush` overrides that
        and commits everything, for when speech has stopped."""
        with self._lock:
            source = self._source_buffer
        settled, _tail = flush_prefix(source) if flush else stable_prefix(source)
        if not settled:
            return

        if not settled.startswith(self._committed_source):
            # Recognition rewrote history — what we committed no longer
            # corresponds to what was said, so start over.
            self._committed_source = ""
            self._committed = ""

        new = settled[len(self._committed_source):].strip()
        if not new:
            return

        try:
            provider = self._config.get("translation_provider", "openai")
            model = normalize_model(self._config.get("model", ""), provider)
            piece = self._provider.translate_segment(
                new, self._context_sentences(), self._lang_name(), model,
            )
        except ProviderError as e:
            self._report_error(str(e))
            return
        except Exception as e:
            self._report_error(f"Unexpected: {e}")
            return

        if not piece:
            return
        self._last_error = None
        self._committed = (self._committed + " " + piece).strip()
        self._committed_source = settled
        print(f"[Translator] +{len(piece.split())}w "
              f"(total {len(self._committed.split())}w)")
        if self._on_full_update:
            self._on_full_update(self._committed)

    def _report_error(self, message):
        """Surface a failure on screen, once per distinct problem.

        Translation runs every cycle, so an unresolved fault would otherwise
        repeat every couple of seconds."""
        print(f"[Translator] Error: {message}")
        if message == self._last_error:
            return
        self._last_error = message
        if self._on_error:
            try:
                self._on_error(_friendly(message))
            except Exception:
                pass
