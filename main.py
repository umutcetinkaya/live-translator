"""Live Translator — Real-time system audio translation for macOS."""

import sys
import os

# Add src to path (use realpath to resolve symlinks and relative paths)
_BASE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(_BASE, "src"))

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
        # Hide from dock, show only in menu bar
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        self._overlay = TranslationOverlay(
            on_lang_change=self._on_lang_change,
            on_settings_change=self._on_settings_change,
            on_clear=self._on_clear,
            on_close=self._on_close,
            on_toggle_tts=self._on_toggle_tts,
        )
        self._setup_status_bar()
        self._overlay.setup()
        self._overlay.show()
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
    import os, ctypes, ctypes.util

    # 1. Set process name BEFORE anything else
    try:
        libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
        libc.setprogname(b"Live Translator")
    except Exception:
        pass

    # 2. Point NSBundle to our .app so macOS reads its Info.plist
    from Foundation import NSBundle
    res_dir = os.path.dirname(os.path.realpath(__file__))
    if "/Contents/Resources" in res_dir:
        bundle_path = res_dir.split("/Contents/Resources")[0]
        our_bundle = NSBundle.bundleWithPath_(bundle_path)
        if our_bundle:
            our_bundle.load()
            # Patch mainBundle's infoDictionary
            our_info = our_bundle.infoDictionary()
            main_info = NSBundle.mainBundle().infoDictionary()
            if our_info and main_info:
                main_info["CFBundleName"] = our_info.get("CFBundleName", "Live Translator")
                main_info["CFBundleDisplayName"] = our_info.get("CFBundleDisplayName", "Live Translator")
                main_info["CFBundleIdentifier"] = our_info.get("CFBundleIdentifier", "com.livetranslator.app")
                main_info["CFBundleIconFile"] = our_info.get("CFBundleIconFile", "AppIcon")

    # 3. Create NSApplication
    app = NSApplication.sharedApplication()

    # 4. Set dock icon
    from AppKit import NSImage
    icon_path = os.path.join(res_dir, "AppIcon.icns")
    if os.path.exists(icon_path):
        app.setApplicationIconImage_(NSImage.alloc().initWithContentsOfFile_(icon_path))

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    print("=" * 50)
    print("  Live Translator")
    print("  Menu bar: 🌐")
    print("=" * 50)
    app.run()


if __name__ == "__main__":
    main()
