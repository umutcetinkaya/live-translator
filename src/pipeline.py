"""Translation pipeline — two independent agents.

Agent 1 (Listener): SFSpeechRecognizer continuously captures speech, accumulates text.
Agent 2 (Translator): Every 3 seconds, translates the full accumulated text, updates overlay.

Listener partials are shown as original text in the overlay.
Translator replaces the entire translation — context never breaks.
"""

import subprocess
import threading
from audio_capture import SystemAudioCapture
from speech_recognizer import RealtimeSpeechRecognizer
from translator import AITranslator
from tts import TextToSpeech
from config import load_config, save_config, normalize_model
import model_store
from providers import get_realtime_provider


def _set_system_volume(level):
    """Set macOS output volume from a 0.0-1.0 value.

    Exposed through the audio bar so the user can rebalance the source
    against the translation without leaving the app — macOS offers no
    per-application volume, so this is the only lever available."""
    try:
        pct = max(0, min(100, round(level * 100)))
        subprocess.run(["osascript", "-e", f"set volume output volume {pct}"],
                       capture_output=True, timeout=2)
    except Exception as e:
        print(f"[Pipeline] Volume set failed: {e}")


class TranslationPipeline:

    def __init__(self, overlay, config=None):
        self._overlay = overlay
        self._config = config or load_config()
        self._locale = self._config.get("source_locale", "en-US")

        self._translator = AITranslator(
            on_translation=self._on_translation,
            config=self._config,
            on_error=self._on_translate_error,
        )

        self._recognizer = RealtimeSpeechRecognizer(
            locale=self._locale,
            on_partial=self._on_partial,
            on_segment=self._on_segment_final,
            config=self._config,
            on_no_speech=self._on_no_speech,
        )

        self._capture = SystemAudioCapture(
            on_audio_buffer=self._on_audio
        )

        self._tts = TextToSpeech(config=self._config, on_error=self._on_tts_error)
        self._tts.set_language(self._config.get("target_lang", "tr"))

        self._running = False
        self._finalized_text = ""
        self._current_partial = ""
        self._last_tts_text = ""

        self._download_thread = None
        self._download_lock = threading.Lock()
        self._download_pct = 0

        self._realtime_mode = self._config.get("realtime_mode", False)
        self._realtime = None
        if self._realtime_mode:
            try:
                self._realtime = get_realtime_provider(self._config)
            except Exception as e:
                print(f"[Pipeline] Realtime setup failed, falling back to on-device: {e}")
                self._realtime_mode = False

    def _full_source(self):
        if self._current_partial:
            return (self._finalized_text + " " + self._current_partial).strip()
        return self._finalized_text

    @property
    def is_realtime(self):
        return self._realtime_mode

    # --- Free on-device model ---

    def _downloading(self):
        t = self._download_thread
        return t is not None and t.is_alive()

    def ensure_local_model(self):
        """Fetch the free translation model in the background if it is missing.

        Recognition keeps running meanwhile, so the original text still shows;
        only the translation waits. Called on start and on every settings
        save, so a failed download is retried without restarting the app."""
        if self._config.get("translation_provider") != "local":
            return
        repo = normalize_model(self._config.get("model", ""), "local")
        if model_store.is_ready(repo):
            return
        with self._download_lock:
            if self._downloading():
                return
            self._download_thread = threading.Thread(
                target=self._download_local, args=(repo,), daemon=True)
            self._download_thread.start()

    def _download_local(self, repo):
        last = {"pct": -1}

        def progress(fraction):
            pct = int(fraction * 100)
            if pct != last["pct"]:
                last["pct"] = pct
                self._download_pct = pct
                self._overlay.update_original_on_main_thread(
                    f"⬇️ Downloading free translation model… {pct}%")

        try:
            model_store.download(repo, progress)
        except model_store.ModelStoreError as e:
            self._overlay.update_original_on_main_thread(f"⚠️ {e}")
            return
        self._overlay.update_original_on_main_thread(
            "✅ Translation model ready, translating now")
        self._translator.on_speech_pause()

    def start(self):
        print("[Pipeline] Starting...")
        self.ensure_local_model()
        if self._realtime_mode and self._realtime:
            try:
                self._realtime.start(
                    on_translation=self._overlay.update_text_on_main_thread,
                    on_source=self._overlay.update_original_on_main_thread,
                )
                self._overlay.update_original_on_main_thread(
                    "⏳ Realtime mode — collecting context, translation starts shortly…"
                )
            except Exception as e:
                print(f"[Pipeline] Realtime start failed, fallback: {e}")
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
            on_segment=self._on_segment_final,
            config=self._config,
            on_no_speech=self._on_no_speech,
        )

        if self._realtime_mode:
            try:
                self._realtime = get_realtime_provider(self._config)
            except Exception as e:
                print(f"[Pipeline] Realtime re-setup failed, fallback: {e}")
                self._realtime_mode = False
                self._realtime = None

        if was_running:
            self._capture.start()
            if self._realtime_mode and self._realtime:
                self._realtime.start(
                    on_translation=self._overlay.update_text_on_main_thread,
                    on_source=self._overlay.update_original_on_main_thread,
                )
                self._overlay.update_original_on_main_thread(
                    "⏳ Realtime mode — collecting context, translation starts shortly…"
                )
            else:
                self._recognizer.start()
                self._translator.start()

    def update_config(self, config):
        self._config = config
        self._translator.update_config(config)
        self._tts.update_config(config)
        self.ensure_local_model()

    def clear(self):
        self._finalized_text = ""
        self._current_partial = ""
        self._last_tts_text = ""
        self._translator.clear()

    @property
    def tts_enabled(self):
        return self._tts.enabled

    def toggle_tts(self):
        """Toggle speech and remember the choice for the next launch."""
        on = self._tts.toggle()
        self._config["tts_enabled"] = bool(on)
        save_config(self._config)
        return on

    def audio_control(self, what, value):
        """Apply a change from the audio bar, live.

        Kept off the Settings round trip: during a live stream the user needs
        to fix the sound while it is playing, not after saving a dialog."""
        if what == "provider":
            self._tts.set_provider(value)
        elif what == "level":
            self._tts.set_speech_level(float(value) / 100.0)
        elif what == "system":
            _set_system_volume(float(value) / 100.0)

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
        """CMSampleBuffer -> mono s16 PCM in realtime API format.

        audio_capture produces 44100 Hz. OpenAI Realtime GA wants 24kHz, Gemini Live wants 16kHz;
        we select the target sample rate based on the provider."""
        from audio_pcm import (extract_pcm_from_sample_buffer, resample_s16,
                               RATE_OPENAI, RATE_GEMINI)
        raw = extract_pcm_from_sample_buffer(sample_buffer)
        if not raw:
            return None
        provider = self._config.get("translation_provider", "openai")
        rate = RATE_GEMINI if provider == "gemini" else RATE_OPENAI
        return resample_s16(raw, rate_out=rate)

    def _on_translate_error(self, message):
        """Put translation failures on screen instead of only in the terminal."""
        if self._downloading() and message.startswith("Downloading the free"):
            return  # the progress line already says so, with a percentage
        self._overlay.update_original_on_main_thread(f"⚠️ {message}")

    def _on_tts_error(self, message):
        """Put TTS failures on screen — they used to only reach the terminal,
        so a bad key or a missing voice model looked like nothing happening."""
        self._overlay.update_original_on_main_thread(f"🔇 {message}")

    def _on_segment_final(self, text):
        """Recognition finalised an utterance — a pause, so flush the tail."""
        self._on_segment(text)
        self._translator.on_speech_pause()

    def _on_no_speech(self):
        if not self._finalized_text and not self._current_partial:
            self._overlay.update_original_on_main_thread(
                "🔇 No audio detected — play or focus your audio source"
            )

    def _on_partial(self, text):
        self._current_partial = text
        if self._downloading():
            # Recognised text refreshes this line constantly; keep the
            # progress visible at its end (the overlay shows the tail).
            text = f"{text} · ⬇️ model {self._download_pct}%"
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

    @staticmethod
    def _appended_part(previous, current):
        """Return the part of `current` that is genuinely new.

        The live-document model preserves earlier text but may refine its last
        sentence, so a word-count diff can start mid-sentence. Compare on word
        boundaries and re-speak from the first word that changed."""
        old_words = previous.split() if previous else []
        new_words = current.split()
        common = 0
        for old, new in zip(old_words, new_words):
            if old != new:
                break
            common += 1
        if common == len(new_words):
            return ""
        return " ".join(new_words[common:])

    def _on_translation(self, full_translation):
        self._overlay.replace_all_text(full_translation)

        if self._tts.enabled:
            added = self._appended_part(self._last_tts_text, full_translation)
            if len(added) > 5:
                self._tts.speak(added)
            self._last_tts_text = full_translation

    @property
    def is_running(self):
        return self._running
