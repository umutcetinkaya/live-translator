"""Live document translation using OpenAI.

Architecture: maintains a growing translated document.
Each cycle sends the full source transcript + previous translation to GPT.
GPT preserves previous translation and appends new content.
Context never breaks, incomplete sentences get refined.
"""

import threading
import time
from openai import OpenAI
from config import load_config


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


class AITranslator:

    TRANSLATE_INTERVAL = 3.0

    def __init__(self, on_translation=None, config=None):
        self._on_full_update = on_translation
        self._config = config or load_config()
        self._client = self._create_client()
        self._target_lang = self._config.get("target_lang", "tr")
        self._lock = threading.Lock()

        self._source_buffer = ""
        self._last_sent_source = ""
        self._last_translation = ""
        self._running = False
        self._worker = None

        print(f"[Translator] {self._config.get('model', 'gpt-4o-mini')} ready")

    def _create_client(self):
        key = self._config.get("openai_api_key", "")
        if not key:
            print("[Translator] WARNING: No API key!")
            return None
        return OpenAI(api_key=key)

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
        self._client = self._create_client()
        self._target_lang = config.get("target_lang", "tr")
        print(f"[Translator] Config updated: {config.get('model')}")

    def set_target_lang(self, lang_code):
        self._target_lang = lang_code

    def clear(self):
        with self._lock:
            self._source_buffer = ""
            self._last_sent_source = ""
            self._last_translation = ""

    # Legacy API compatibility
    def translate_chunk(self, text):
        pass
    def set_source_language(self, _):
        pass

    def _lang_name(self):
        names = {
            "tr": "Turkish", "en": "English", "de": "German",
            "fr": "French", "es": "Spanish", "it": "Italian",
            "ja": "Japanese", "zh": "Chinese", "ko": "Korean",
            "ru": "Russian", "ar": "Arabic", "pt": "Portuguese",
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
        if not self._client:
            return

        try:
            model = self._config.get("model", "gpt-4o-mini")
            target = self._lang_name()
            is_reasoning = model.startswith("o")

            system = SYSTEM_PROMPT.replace("{target_lang}", target)

            user_msg = f"Full transcript:\n\n{source}"
            if self._last_translation:
                user_msg += f"\n\n---\nYour previous translation (refine/continue):\n{self._last_translation}"

            params = {
                "model": model,
                "messages": [
                    {"role": "developer" if is_reasoning else "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
            }
            if is_reasoning:
                params["max_completion_tokens"] = 2000
            else:
                params["max_tokens"] = 2000
                params["temperature"] = 0.2

            response = self._client.chat.completions.create(**params)
            result = response.choices[0].message.content.strip()

            if result:
                self._last_translation = result
                words = result.split()
                print(f"[Translator] Updated ({len(words)} words)")
                if self._on_full_update:
                    self._on_full_update(result)

        except Exception as e:
            print(f"[Translator] Error: {e}")
