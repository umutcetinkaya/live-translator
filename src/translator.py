"""Live document translation — provider-agnostic orkestratör."""

import threading
import time
from config import load_config, normalize_model
from providers import get_translation_provider
from providers.base import ProviderError


class AITranslator:
    TRANSLATE_INTERVAL = 3.0

    def __init__(self, on_translation=None, config=None):
        self._on_full_update = on_translation
        self._config = config or load_config()
        self._provider = get_translation_provider(self._config)
        self._target_lang = self._config.get("target_lang", "tr")
        self._lock = threading.Lock()
        self._source_buffer = ""
        self._last_sent_source = ""
        self._last_translation = ""
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
            self._last_sent_source = ""
            self._last_translation = ""

    def translate_chunk(self, text):
        pass

    def set_source_language(self, _):
        pass

    def _lang_name(self):
        names = {
            "tr": "Turkish", "en": "English", "de": "German", "fr": "French",
            "es": "Spanish", "it": "Italian", "ja": "Japanese", "zh": "Chinese",
            "ko": "Korean", "ru": "Russian", "ar": "Arabic", "pt": "Portuguese",
        }
        return names.get(self._target_lang, self._target_lang)

    def _translate_loop(self):
        while self._running:
            time.sleep(self.TRANSLATE_INTERVAL)
            if not self._running:
                break
            with self._lock:
                source = self._source_buffer
            if not source or source == self._last_sent_source:
                continue
            if len(source) - len(self._last_sent_source) < 20:
                continue
            self._last_sent_source = source
            self._do_translate(source)

    def _do_translate(self, source):
        try:
            provider = self._config.get("translation_provider", "openai")
            model = normalize_model(self._config.get("model", ""), provider)
            target = self._lang_name()
            result = self._provider.translate_document(
                source, self._last_translation, target, model,
            )
            if result:
                self._last_translation = result
                print(f"[Translator] Updated ({len(result.split())} words)")
                if self._on_full_update:
                    self._on_full_update(result)
        except ProviderError as e:
            print(f"[Translator] Error: {e}")
        except Exception as e:
            print(f"[Translator] Unexpected: {e}")
