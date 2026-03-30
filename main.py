"""Live Translator — Real-time system audio translation for macOS."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import objc
from AppKit import (
    NSApplication,
    NSApp,
    NSStatusBar,
    NSMenu,
    NSMenuItem,
    NSVariableStatusItemLength,
    NSObject,
    NSApplicationActivationPolicyAccessory,
)
import threading

from overlay import TranslationOverlay
from pipeline import TranslationPipeline
from config import load_config, save_config


class AppDelegate(NSObject):

    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self._overlay = None
        self._pipeline = None
        self._config = load_config()
        return self

    def applicationDidFinishLaunching_(self, notification):
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self._overlay = TranslationOverlay(
            on_lang_change=self._on_lang_change,
            on_settings_change=self._on_settings_change,
            on_clear=self._on_clear,
            on_close=self._on_close,
            on_toggle_tts=self._on_toggle_tts,
        )
        self._overlay.setup()
        self._overlay.show()

        self._setup_status_bar()
        threading.Thread(target=self._start_pipeline, daemon=True).start()

    def _start_pipeline(self):
        try:
            self._pipeline = TranslationPipeline(
                self._overlay, config=self._config
            )
            self._pipeline.start()
        except Exception as e:
            print(f"[Main] Pipeline error: {e}")

    def _setup_status_bar(self):
        self._status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        self._status_item.setTitle_("🌐")

        menu = NSMenu.alloc().init()

        toggle = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Pause", "toggleCapture:", "t"
        )
        toggle.setTarget_(self)
        menu.addItem_(toggle)

        show_hide = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show/Hide Window", "toggleOverlay:", "o"
        )
        show_hide.setTarget_(self)
        menu.addItem_(show_hide)

        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        menu.addItem_(quit_item)

        self._status_item.setMenu_(menu)

    def _on_lang_change(self, source_locale, target_lang):
        self._config["source_locale"] = source_locale
        self._config["target_lang"] = target_lang
        save_config(self._config)
        if self._pipeline:
            threading.Thread(
                target=self._pipeline.change_languages,
                args=(source_locale, target_lang),
                daemon=True,
            ).start()

    def _on_settings_change(self, config):
        self._config = config
        if self._pipeline:
            self._pipeline.update_config(config)

    def _on_clear(self):
        if self._pipeline:
            self._pipeline.clear()

    def _on_close(self):
        if self._pipeline:
            self._pipeline.stop()
        NSApp.terminate_(None)

    def _on_toggle_tts(self):
        if self._pipeline:
            on = self._pipeline.toggle_tts()
            self._overlay.set_tts_state(on)

    @objc.IBAction
    def toggleCapture_(self, sender):
        if self._pipeline and self._pipeline.is_running:
            self._pipeline.stop()
            sender.setTitle_("Resume")
            self._status_item.setTitle_("⏸")
        else:
            if self._pipeline:
                threading.Thread(target=self._pipeline.start, daemon=True).start()
                sender.setTitle_("Pause")
                self._status_item.setTitle_("🌐")

    @objc.IBAction
    def toggleOverlay_(self, sender):
        if self._overlay.is_visible():
            self._overlay.hide()
        else:
            self._overlay.show()

    @objc.IBAction
    def quitApp_(self, sender):
        if self._pipeline:
            self._pipeline.stop()
        NSApp.terminate_(None)


def main():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    print("=" * 50)
    print("  Live Translator")
    print("  Menu bar: 🌐")
    print("=" * 50)
    app.run()


if __name__ == "__main__":
    main()
