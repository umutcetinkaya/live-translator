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


RESTART_INTERVAL = 50

# Silence is reported as an error by SFSpeechRecognizer, but it is not a
# failure — it just means this stretch of audio had no speech. Restarting on it
# spins: the new session hits the same silence and errors again immediately.
# Measured live: kAFAssistantErrorDomain 1110 during quiet system audio.
_AF_DOMAIN = "kAFAssistantErrorDomain"
_NO_SPEECH_CODES = (1110, 1107)

BASE_RESTART_DELAY = 0.3
MAX_RESTART_DELAY = 5.0

# How long a session may sit without any speech before it is rebuilt. Long
# enough to sit through natural pauses and quiet passages.
WATCHDOG_TIMEOUT = 20


def _is_fatal_error(error):
    """True when an error warrants tearing down and rebuilding the session."""
    if error is None:
        return False
    try:
        if str(error.domain()) == _AF_DOMAIN and error.code() in _NO_SPEECH_CODES:
            return False
    except Exception:
        return True   # can't classify it — assume it's real
    return True


def _restart_delay(attempt):
    """Exponential backoff so repeated failures don't burn CPU."""
    return min(BASE_RESTART_DELAY * (2 ** attempt), MAX_RESTART_DELAY)


class RealtimeSpeechRecognizer:

    def __init__(self, locale="en-US", on_partial=None, on_segment=None,
                 config=None, on_no_speech=None):
        self._locale = locale
        self._on_partial = on_partial
        self._on_segment = on_segment
        self._on_no_speech = on_no_speech
        self._recognizer = None
        self._request = None
        self._task = None
        self._running = False
        self._last_text = ""
        self._restarting = False
        self._restart_timer = None
        self._last_partial_time = time.time()
        self._pending_buffers = collections.deque(maxlen=80)
        self._restart_attempts = 0

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

    def _schedule_restart(self, fatal):
        """Queue a session rebuild, backing off when failures repeat.

        A normal end-of-utterance restart is prompt; a failing recogniser backs
        off so a persistent fault doesn't spin the CPU."""
        if not self._running or self._restarting:
            return
        self._restarting = True
        if fatal:
            delay = _restart_delay(self._restart_attempts)
            self._restart_attempts += 1
            if self._restart_attempts <= 3 or self._restart_attempts % 20 == 0:
                print(f"[STT] Restarting after error "
                      f"(attempt {self._restart_attempts}, {delay:.1f}s)")
        else:
            delay = BASE_RESTART_DELAY
            self._restart_attempts = 0
        t = threading.Timer(delay, self._new_session)
        t.daemon = True
        t.start()

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
                if not _is_fatal_error(error):
                    # Just silence. The watchdog will rebuild the session if
                    # this really is a stuck recogniser; restarting here would
                    # spin, since the next session meets the same silence.
                    return
                self._schedule_restart(fatal=True)
                return

            if result is None:
                return

            text = result.bestTranscription().formattedString()
            if text and text != self._last_text:
                self._last_text = text
                self._last_partial_time = time.time()
                self._restart_attempts = 0   # audio is flowing again
                if self._on_partial:
                    self._on_partial(text)

            if result.isFinal():
                if text and self._on_segment:
                    self._on_segment(text)
                self._schedule_restart(fatal=False)

        self._task = self._recognizer.recognitionTaskWithRequest_resultHandler_(
            self._request, on_result
        )

        while self._pending_buffers:
            buf = self._pending_buffers.popleft()
            try:
                self._request.appendAudioSampleBuffer_(buf)
            except Exception:
                pass

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
        """Rebuild the session if it goes quiet for too long.

        Silence alone is not a fault — the user may simply not be playing
        audio — so the hint fires once per quiet stretch rather than on every
        sweep, and the rebuild waits long enough to not fight normal pauses."""
        def check():
            hinted = False
            while self._running:
                time.sleep(5)
                if not self._running:
                    break
                elapsed = time.time() - self._last_partial_time
                if elapsed <= WATCHDOG_TIMEOUT:
                    hinted = False
                    continue
                if self._restarting:
                    continue
                if not hinted:
                    hinted = True
                    print(f"[STT] No speech for {WATCHDOG_TIMEOUT}s — rebuilding session")
                    if self._on_no_speech:
                        try:
                            self._on_no_speech()
                        except Exception:
                            pass
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
