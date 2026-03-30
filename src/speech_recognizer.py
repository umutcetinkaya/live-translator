"""Speech recognition using macOS SFSpeechRecognizer with watchdog.

Features:
- On-device recognition (no network required for STT)
- Auto-restart every 50s (Apple's 60s limit)
- Ring buffer prevents audio loss during restarts
- Watchdog auto-recovers from stuck states
"""

import objc
import Speech
from Speech import (
    SFSpeechRecognizer,
    SFSpeechAudioBufferRecognitionRequest,
)
from Foundation import NSLocale
import time
import threading
import collections


RESTART_INTERVAL = 50  # seconds (Apple limit ~60s)


class RealtimeSpeechRecognizer:

    def __init__(self, locale="en-US", on_partial=None, on_segment=None, config=None):
        self._locale = locale
        self._on_partial = on_partial
        self._on_segment = on_segment
        self._recognizer = None
        self._request = None
        self._task = None
        self._running = False
        self._last_text = ""
        self._restarting = False
        self._restart_timer = None
        self._last_partial_time = time.time()
        # Ring buffer — saves audio during restart gap
        self._pending_buffers = collections.deque(maxlen=80)  # ~4 seconds

    def _request_authorization(self):
        event = threading.Event()
        status_ref = [None]
        def handler(status):
            status_ref[0] = status
            event.set()
        SFSpeechRecognizer.requestAuthorization_(handler)
        event.wait(timeout=10)
        if status_ref[0] != 3:
            raise RuntimeError("Speech recognition permission denied")

    def start(self):
        self._request_authorization()
        self._running = True
        self._new_session()
        self._start_watchdog()
        print(f"[STT] Started ({self._locale})")

    def _new_session(self):
        if not self._running:
            return

        self._restarting = False

        ns_locale = NSLocale.alloc().initWithLocaleIdentifier_(self._locale)
        self._recognizer = SFSpeechRecognizer.alloc().initWithLocale_(ns_locale)
        if not self._recognizer or not self._recognizer.isAvailable():
            print("[STT] Recognizer unavailable, retrying in 2s...")
            threading.Timer(2.0, self._new_session).start()
            return

        self._request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
        self._request.setShouldReportPartialResults_(True)
        if self._recognizer.supportsOnDeviceRecognition():
            self._request.setRequiresOnDeviceRecognition_(True)

        self._last_text = ""
        self._last_partial_time = time.time()

        def on_result(result, error):
            if error:
                if self._running and not self._restarting:
                    self._restarting = True
                    threading.Timer(0.3, self._new_session).start()
                return

            if result is None:
                return

            text = result.bestTranscription().formattedString()
            if text and text != self._last_text:
                self._last_text = text
                self._last_partial_time = time.time()
                if self._on_partial:
                    self._on_partial(text)

            if result.isFinal():
                if text and self._on_segment:
                    self._on_segment(text)
                if self._running and not self._restarting:
                    self._restarting = True
                    threading.Timer(0.3, self._new_session).start()

        self._task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
            self._request, on_result
        )

        # Flush pending buffers from ring buffer
        while self._pending_buffers:
            buf = self._pending_buffers.popleft()
            try:
                self._request.appendAudioSampleBuffer_(buf)
            except Exception:
                pass

        # Schedule forced restart before Apple's limit
        if self._restart_timer:
            self._restart_timer.cancel()
        self._restart_timer = threading.Timer(RESTART_INTERVAL, self._force_restart)
        self._restart_timer.daemon = True
        self._restart_timer.start()

        print("[STT] New session started")

    def _force_restart(self):
        if not self._running or self._restarting:
            return
        self._restarting = True

        if self._last_text and self._on_segment:
            self._on_segment(self._last_text)

        try:
            if self._task:
                self._task.cancel()
            if self._request:
                self._request.endAudio()
        except Exception:
            pass

        threading.Timer(0.3, self._new_session).start()

    def _start_watchdog(self):
        """Auto-recover if no speech detected for 10 seconds."""
        def check():
            while self._running:
                time.sleep(5)
                if not self._running:
                    break
                elapsed = time.time() - self._last_partial_time
                if elapsed > 10 and not self._restarting:
                    print("[STT] WATCHDOG: No speech for 10s, forcing restart")
                    self._restarting = True
                    try:
                        if self._task:
                            self._task.cancel()
                        if self._request:
                            self._request.endAudio()
                    except Exception:
                        pass
                    threading.Timer(0.5, self._new_session).start()

        threading.Thread(target=check, daemon=True).start()

    def append_audio_buffer(self, sample_buffer):
        if not self._running:
            return
        if self._restarting:
            self._pending_buffers.append(sample_buffer)
            return
        if not self._request:
            return
        try:
            self._request.appendAudioSampleBuffer_(sample_buffer)
        except Exception:
            pass

    def stop(self):
        self._running = False
        self._restarting = True
        if self._restart_timer:
            self._restart_timer.cancel()
        try:
            if self._task:
                self._task.cancel()
            if self._request:
                self._request.endAudio()
        except Exception:
            pass
        print("[STT] Stopped")
