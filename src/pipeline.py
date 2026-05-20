"""Translation pipeline — two independent agents.

Agent 1 (Listener): SFSpeechRecognizer continuously captures speech, accumulates text.
Agent 2 (Translator): Every 3 seconds, translates the full accumulated text, updates overlay.

Listener partials are shown as original text in the overlay.
Translator replaces the entire translation — context never breaks.
"""

import threading
from audio_capture import SystemAudioCapture
from speech_recognizer import RealtimeSpeechRecognizer
from translator import AITranslator
from tts import TextToSpeech
from config import load_config
from providers import get_realtime_provider


class TranslationPipeline:

    def __init__(self, overlay, config=None):
        self._overlay = overlay
        self._config = config or load_config()
        self._locale = self._config.get("source_locale", "en-US")

        self._translator = AITranslator(
            on_translation=self._on_translation,
            config=self._config,
        )

        self._recognizer = RealtimeSpeechRecognizer(
            locale=self._locale,
            on_partial=self._on_partial,
            on_segment=self._on_segment,
            config=self._config,
        )

        self._capture = SystemAudioCapture(
            on_audio_buffer=self._on_audio
        )

        self._tts = TextToSpeech(config=self._config)
        self._tts.set_language(self._config.get("target_lang", "tr"))

        self._running = False
        self._finalized_text = ""
        self._current_partial = ""
        self._last_tts_text = ""

        self._realtime_mode = self._config.get("realtime_mode", False)
        self._realtime = None
        if self._realtime_mode:
            try:
                self._realtime = get_realtime_provider(self._config)
            except Exception as e:
                print(f"[Pipeline] Realtime kurulamadı, on-device'a düşülüyor: {e}")
                self._realtime_mode = False

    def _full_source(self):
        if self._current_partial:
            return (self._finalized_text + " " + self._current_partial).strip()
        return self._finalized_text

    @property
    def is_realtime(self):
        return self._realtime_mode

    def start(self):
        print("[Pipeline] Starting...")
        if self._realtime_mode and self._realtime:
            try:
                self._realtime.start(
                    on_translation=self._overlay.replace_all_text,
                    on_source=self._overlay.update_original_on_main_thread,
                )
            except Exception as e:
                print(f"[Pipeline] Realtime başlatılamadı, fallback: {e}")
                self._realtime = None
                self._realtime_mode = False
        if not self._realtime_mode:
            self._recognizer.start()
            self._translator.start()
        self._capture.start()
        self._running = True
        print("[Pipeline] Running")

    def stop(self):
        self._running = False
        self._capture.stop()
        if self._realtime:
            self._realtime.stop()
        else:
            self._recognizer.stop()
            self._translator.stop()
        self._tts.stop()
        print("[Pipeline] Stopped")

    def change_languages(self, source_locale, target_lang):
        was_running = self._running
        if was_running:
            self._capture.stop()
            if self._realtime:
                self._realtime.stop()
            else:
                self._recognizer.stop()
                self._translator.stop()

        self._locale = source_locale
        self._config["source_locale"] = source_locale
        self._config["target_lang"] = target_lang
        self._translator.set_target_lang(target_lang)
        self._translator.clear()
        self._tts.set_language(target_lang)
        self._finalized_text = ""
        self._current_partial = ""

        self._recognizer = RealtimeSpeechRecognizer(
            locale=self._locale,
            on_partial=self._on_partial,
            on_segment=self._on_segment,
            config=self._config,
        )

        if self._realtime_mode:
            # Realtime provider'ı yeni dil/config ile yeniden kur
            try:
                self._realtime = get_realtime_provider(self._config)
            except Exception as e:
                print(f"[Pipeline] Realtime yeniden kurulamadı, fallback: {e}")
                self._realtime_mode = False
                self._realtime = None

        if was_running:
            self._capture.start()
            if self._realtime_mode and self._realtime:
                self._realtime.start(
                    on_translation=self._overlay.replace_all_text,
                    on_source=self._overlay.update_original_on_main_thread,
                )
            else:
                self._recognizer.start()
                self._translator.start()

    def update_config(self, config):
        self._config = config
        self._translator.update_config(config)
        self._tts.update_config(config)

    def clear(self):
        self._finalized_text = ""
        self._current_partial = ""
        self._last_tts_text = ""
        self._translator.clear()

    def toggle_tts(self):
        return self._tts.toggle()

    def _on_audio(self, sample_buffer):
        if not self._running:
            return
        if self._realtime_mode and self._realtime:
            pcm = self._pcm_from_buffer(sample_buffer)
            if pcm:
                self._realtime.feed_audio(pcm)
        else:
            self._recognizer.append_audio_buffer(sample_buffer)

    def _pcm_from_buffer(self, sample_buffer):
        """CMSampleBuffer -> 16kHz mono s16 PCM (realtime API formatı).

        audio_capture 44100 Hz mono s16 üretir; burada 16000'e indiriyoruz.
        Gerçek CMSampleBuffer çıkarımı canlı doğrulanır (RT Task 5)."""
        from audio_pcm import extract_pcm_from_sample_buffer, resample_s16
        raw = extract_pcm_from_sample_buffer(sample_buffer)
        if not raw:
            return None
        return resample_s16(raw)

    def _on_partial(self, text):
        self._current_partial = text
        self._overlay.update_original_on_main_thread(text)
        self._translator.update_source(self._full_source())

    def _on_segment(self, text):
        if text and text.strip():
            if self._finalized_text:
                self._finalized_text += " " + text.strip()
            else:
                self._finalized_text = text.strip()
            self._current_partial = ""
            self._translator.update_source(self._full_source())

    def _on_translation(self, full_translation):
        self._overlay.replace_all_text(full_translation)

        if self._tts.enabled:
            old_words = self._last_tts_text.split() if self._last_tts_text else []
            new_words = full_translation.split()
            if len(new_words) > len(old_words):
                added = " ".join(new_words[len(old_words):])
                if added and len(added) > 5:
                    self._tts.speak(added)
            self._last_tts_text = full_translation

    @property
    def is_running(self):
        return self._running
