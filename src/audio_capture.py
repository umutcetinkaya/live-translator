"""System audio capture using ScreenCaptureKit (macOS 13+)."""

import objc
import ScreenCaptureKit
from ScreenCaptureKit import (
    SCContentFilter,
    SCShareableContent,
    SCStream,
    SCStreamConfiguration,
)
import CoreMedia
from Foundation import NSObject
import threading


class AudioCaptureDelegate(NSObject):
    """SCStream output delegate — captures audio buffers."""

    _buffer_count = 0

    def init(self):
        self = objc.super(AudioCaptureDelegate, self).init()
        if self is None:
            return None
        self._callback = None
        return self

    def setCallback_(self, callback):
        self._callback = callback

    def stream_didOutputSampleBuffer_ofType_(self, stream, sample_buffer, output_type):
        if output_type != 1:  # 1 = audio
            return
        AudioCaptureDelegate._buffer_count += 1
        if AudioCaptureDelegate._buffer_count <= 5 or AudioCaptureDelegate._buffer_count % 100 == 0:
            print(f"[AudioCapture] Buffer #{AudioCaptureDelegate._buffer_count}")
        if self._callback:
            self._callback(sample_buffer)


class SystemAudioCapture:
    """Captures system audio via ScreenCaptureKit. No third-party software needed."""

    def __init__(self, on_audio_buffer=None):
        self._on_audio_buffer = on_audio_buffer
        self._stream = None
        self._delegate = None
        self._running = False

    def start(self):
        event = threading.Event()
        error_ref = [None]

        def on_content(content, error):
            if error:
                print(f"[AudioCapture] Content error: {error}")
                error_ref[0] = error
                event.set()
                return

            displays = content.displays()
            if not displays or len(displays) == 0:
                print("[AudioCapture] No display found")
                event.set()
                return

            content_filter = SCContentFilter.alloc().initWithDisplay_excludingWindows_(
                displays[0], []
            )

            config = SCStreamConfiguration.alloc().init()
            config.setCapturesAudio_(True)
            config.setSampleRate_(16000)
            config.setChannelCount_(1)
            config.setWidth_(2)
            config.setHeight_(2)
            config.setMinimumFrameInterval_(CoreMedia.CMTimeMake(1, 1))
            config.setExcludesCurrentProcessAudio_(True)

            self._delegate = AudioCaptureDelegate.alloc().init()
            self._delegate.setCallback_(self._on_audio_buffer)

            self._stream = SCStream.alloc().initWithFilter_configuration_delegate_(
                content_filter, config, None
            )

            self._stream.addStreamOutput_type_sampleHandlerQueue_error_(
                self._delegate, 1, None, None
            )

            def on_start(error):
                if error:
                    print(f"[AudioCapture] Start error: {error}")
                    error_ref[0] = error
                else:
                    self._running = True
                    print("[AudioCapture] Capturing system audio")
                event.set()

            self._stream.startCaptureWithCompletionHandler_(on_start)

        SCShareableContent.getShareableContentWithCompletionHandler_(on_content)
        event.wait(timeout=10)

        if error_ref[0]:
            raise RuntimeError(f"Audio capture failed: {error_ref[0]}")

    def stop(self):
        if self._stream and self._running:
            event = threading.Event()

            def on_stop(error):
                if error:
                    print(f"[AudioCapture] Stop error: {error}")
                self._running = False
                event.set()

            self._stream.stopCaptureWithCompletionHandler_(on_stop)
            event.wait(timeout=5)
            print("[AudioCapture] Stopped")

    @property
    def is_running(self):
        return self._running
