"""Live document translation — provider-agnostic orchestrator."""

import threading
import time
from config import load_config, normalize_model, CONTEXT_WINDOW_WORDS
from providers import get_translation_provider
from providers.base import ProviderError


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
    # Tuned for perceived latency: at 3.0s/20 chars a speaker could wait two
    # cycles (~6s) before seeing anything. 1.2s with a lower char floor keeps
    # subtitles close to the speech without spamming the API.
    TRANSLATE_INTERVAL = 1.2
    MIN_NEW_CHARS = 12

    def __init__(self, on_translation=None, config=None, on_error=None):
        self._on_full_update = on_translation
        self._on_error = on_error
        self._last_error = None
        self._config = config or load_config()
        self._provider = get_translation_provider(self._config)
        self._target_lang = self._config.get("target_lang", "tr")
        self._lock = threading.Lock()
        self._source_buffer = ""
        self._last_sent_source = ""
        self._last_translation = ""
        self._deferred_source = ""
        self._window_words = self._config.get("context_window_words",
                                              CONTEXT_WINDOW_WORDS)
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
        self._window_words = config.get("context_window_words",
                                        CONTEXT_WINDOW_WORDS)
        print(f"[Translator] Config updated: {config.get('model')}")

    def set_target_lang(self, lang_code):
        self._target_lang = lang_code

    def clear(self):
        with self._lock:
            self._source_buffer = ""
            self._last_sent_source = ""
            self._last_translation = ""
            self._deferred_source = ""

    def _windowed_source(self, source):
        """Keep only the last N words of the transcript.

        The transcript grows without bound, so re-sending all of it every cycle
        makes cost and latency climb linearly. The previous translation already
        carries earlier context forward, so dropping old source text preserves
        continuity."""
        words = source.split()
        if len(words) <= self._window_words:
            return source
        return " ".join(words[-self._window_words:])

    def _lang_name(self):
        names = {
            "tr": "Turkish", "en": "English", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
            "ko": "Korean", "ru": "Russian", "ar": "Arabic", "pt": "Portuguese",
        }
        return names.get(self._target_lang, self._target_lang)

    def _should_translate(self, source):
        """Decide whether `source` is worth a translation call this cycle.

        Short additions are deferred so a fast speaker doesn't trigger an API
        call per word. But once the source stops growing, the deferred tail is
        translated anyway — otherwise the final sentence never reaches the
        overlay."""
        if not source or source == self._last_sent_source:
            self._deferred_source = ""
            return False
        if len(source) - len(self._last_sent_source) >= self.MIN_NEW_CHARS:
            self._deferred_source = ""
            return True
        # Kısa kuyruk: konuşma sürüyorsa beklet, durduysa çevir.
        if source == self._deferred_source:
            self._deferred_source = ""
            return True
        self._deferred_source = source
        return False

    def _translate_loop(self):
        while self._running:
            time.sleep(self.TRANSLATE_INTERVAL)
            if not self._running:
                break
            with self._lock:
                source = self._source_buffer
            if not self._should_translate(source):
                continue
            self._last_sent_source = source
            self._do_translate(source)

    def _do_translate(self, source):
        try:
            provider = self._config.get("translation_provider", "openai")
            model = normalize_model(self._config.get("model", ""), provider)
            target = self._lang_name()
            result = self._provider.translate_document(
                self._windowed_source(source), self._last_translation,
                target, model,
            )
            if result:
                self._last_translation = result
                self._last_error = None
                print(f"[Translator] Updated ({len(result.split())} words)")
                if self._on_full_update:
                    self._on_full_update(result)
        except ProviderError as e:
            self._report_error(str(e))
        except Exception as e:
            self._report_error(f"Unexpected: {e}")

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
