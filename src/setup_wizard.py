"""Setup Wizard — first-run installer UI with progress bar."""

import sys
import os
import json
import threading
import subprocess

import objc
from AppKit import (
    NSApplication,
    NSApp,
    NSWindow,
    NSView,
    NSTextField,
    NSSecureTextField,
    NSButton,
    NSProgressIndicator,
    NSColor,
    NSFont,
    NSScreen,
    NSMakeRect,
    NSObject,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSBackingStoreBuffered,
    NSTextAlignmentCenter,
    NSTextAlignmentLeft,
    NSLineBreakByWordWrapping,
    NSBezelStyleRounded,
    NSApplicationActivationPolicyRegular,
    NSProgressIndicatorStyleBar,
)

CONFIG_PATH = os.path.expanduser("~/.live-translator.json")
WIDTH = 480
HEIGHT = 360


class SetupWizard:
    """macOS native setup wizard with progress bar."""

    def __init__(self, resource_dir):
        self._dir = resource_dir
        self._window = None
        self._api_input = None
        self._progress = None
        self._status_label = None
        self._step = 0
        self._result = None  # "launch" or None

    def run(self):
        """Show wizard, return True if setup completed."""
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyRegular)

        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - WIDTH) / 2
        y = (screen.size.height - HEIGHT) / 2

        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, WIDTH, HEIGHT),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered, False,
        )
        self._window.setTitle_("Live Translator — Setup")
        self._window.setBackgroundColor_(NSColor.colorWithRed_green_blue_alpha_(0.12, 0.12, 0.14, 1.0))

        self._show_step1()
        self._window.makeKeyAndOrderFront_(None)
        app.activateIgnoringOtherApps_(True)
        app.run()

        return self._result == "launch"

    def _clear(self):
        for sub in list(self._window.contentView().subviews()):
            sub.removeFromSuperview()

    def _label(self, frame, text, size=14, weight=0.4, color=None, align=NSTextAlignmentLeft, wrap=False):
        f = NSTextField.alloc().initWithFrame_(frame)
        f.setStringValue_(text)
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setEditable_(False)
        f.setSelectable_(False)
        f.setTextColor_(color or NSColor.whiteColor())
        f.setFont_(NSFont.systemFontOfSize_weight_(size, weight))
        f.setAlignment_(align)
        if wrap:
            f.setLineBreakMode_(NSLineBreakByWordWrapping)
            f.setMaximumNumberOfLines_(0)
        return f

    # ── Step 1: Welcome + API Key ──
    def _show_step1(self):
        self._clear()
        cv = self._window.contentView()

        # Step indicator
        cv.addSubview_(self._label(
            NSMakeRect(0, HEIGHT - 40, WIDTH, 20),
            "Step 1 of 3", 11, 0.3,
            NSColor.colorWithWhite_alpha_(0.4, 1.0),
            NSTextAlignmentCenter,
        ))

        # Title
        cv.addSubview_(self._label(
            NSMakeRect(30, HEIGHT - 80, WIDTH - 60, 30),
            "Welcome to Live Translator", 22, 0.6,
            NSColor.whiteColor(), NSTextAlignmentCenter,
        ))

        # Description
        cv.addSubview_(self._label(
            NSMakeRect(40, HEIGHT - 150, WIDTH - 80, 50),
            "Translate any audio playing on your Mac in real-time.\nEnter your OpenAI API key to get started.",
            13, 0.3, NSColor.colorWithWhite_alpha_(0.6, 1.0),
            NSTextAlignmentCenter, True,
        ))

        # API Key label
        cv.addSubview_(self._label(
            NSMakeRect(40, HEIGHT - 185, 200, 20),
            "OpenAI API Key", 12, 0.5,
            NSColor.colorWithWhite_alpha_(0.7, 1.0),
        ))

        # API Key input
        self._api_input = NSSecureTextField.alloc().initWithFrame_(
            NSMakeRect(40, HEIGHT - 215, WIDTH - 80, 28)
        )
        self._api_input.setPlaceholderString_("sk-...")
        self._api_input.setFont_(NSFont.monospacedSystemFontOfSize_weight_(13, 0.3))
        self._api_input.setTextColor_(NSColor.whiteColor())
        self._api_input.setBackgroundColor_(NSColor.colorWithRed_green_blue_alpha_(0.18, 0.18, 0.20, 1.0))
        self._api_input.setBezeled_(True)
        cv.addSubview_(self._api_input)

        # Link
        cv.addSubview_(self._label(
            NSMakeRect(40, HEIGHT - 240, WIDTH - 80, 16),
            "Get your key at platform.openai.com", 11, 0.2,
            NSColor.colorWithWhite_alpha_(0.35, 1.0),
        ))

        # Next button
        btn = NSButton.alloc().initWithFrame_(NSMakeRect(WIDTH - 140, 20, 100, 36))
        btn.setTitle_("Next →")
        btn.setBezelStyle_(NSBezelStyleRounded)
        btn.setTarget_(self)
        btn.setAction_(objc.selector(self._on_next1, signature=b"v@:@"))
        cv.addSubview_(btn)

        # Quit button
        qbtn = NSButton.alloc().initWithFrame_(NSMakeRect(40, 20, 80, 36))
        qbtn.setTitle_("Quit")
        qbtn.setBezelStyle_(NSBezelStyleRounded)
        qbtn.setTarget_(self)
        qbtn.setAction_(objc.selector(self._on_quit, signature=b"v@:@"))
        cv.addSubview_(qbtn)

    def _on_next1(self, sender):
        key = self._api_input.stringValue()
        if not key or len(key) < 10:
            # Error
            self._api_input.setTextColor_(NSColor.redColor())
            return

        # Save config
        config = {
            "openai_api_key": key,
            "source_locale": "en-US",
            "target_lang": "tr",
            "model": "gpt-4o-mini",
            "tts_provider": "piper",
            "tts_voice": "nova",
            "tts_speed": 1.0,
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

        self._show_step2()

    # ── Step 2: Installing ──
    def _show_step2(self):
        self._clear()
        cv = self._window.contentView()

        cv.addSubview_(self._label(
            NSMakeRect(0, HEIGHT - 40, WIDTH, 20),
            "Step 2 of 3", 11, 0.3,
            NSColor.colorWithWhite_alpha_(0.4, 1.0),
            NSTextAlignmentCenter,
        ))

        cv.addSubview_(self._label(
            NSMakeRect(30, HEIGHT - 80, WIDTH - 60, 30),
            "Installing...", 22, 0.6,
            NSColor.whiteColor(), NSTextAlignmentCenter,
        ))

        cv.addSubview_(self._label(
            NSMakeRect(40, HEIGHT - 120, WIDTH - 80, 40),
            "Setting up Python environment and downloading packages.\nThis only happens once.",
            13, 0.3, NSColor.colorWithWhite_alpha_(0.5, 1.0),
            NSTextAlignmentCenter, True,
        ))

        # Progress bar
        self._progress = NSProgressIndicator.alloc().initWithFrame_(
            NSMakeRect(40, HEIGHT - 165, WIDTH - 80, 20)
        )
        self._progress.setStyle_(NSProgressIndicatorStyleBar)
        self._progress.setMinValue_(0)
        self._progress.setMaxValue_(100)
        self._progress.setDoubleValue_(0)
        self._progress.setIndeterminate_(False)
        cv.addSubview_(self._progress)

        # Status label
        self._status_label = self._label(
            NSMakeRect(40, HEIGHT - 195, WIDTH - 80, 20),
            "Preparing...", 12, 0.3,
            NSColor.colorWithWhite_alpha_(0.45, 1.0),
            NSTextAlignmentCenter,
        )
        cv.addSubview_(self._status_label)

        # Start install in background
        threading.Thread(target=self._do_install, daemon=True).start()

    def _update_progress(self, value, text):
        from PyObjCTools import AppHelper
        def update():
            if self._progress:
                self._progress.setDoubleValue_(value)
            if self._status_label:
                self._status_label.setStringValue_(text)
        AppHelper.callAfter(update)

    def _do_install(self):
        venv = os.path.join(self._dir, ".venv")
        log = os.path.expanduser("~/Library/Logs/LiveTranslator.log")

        try:
            # Step: venv
            self._update_progress(10, "Creating Python environment...")
            subprocess.run(
                ["python3", "-m", "venv", venv],
                capture_output=True, timeout=60,
            )

            # Step: pip install
            self._update_progress(25, "Installing packages (this may take a minute)...")
            pip = os.path.join(venv, "bin", "pip")
            req = os.path.join(self._dir, "requirements.txt")
            subprocess.run(
                [pip, "install", "-q", "-r", req],
                capture_output=True, timeout=300,
            )

            # Step: TTS models
            self._update_progress(70, "Downloading voice models...")
            dl_script = os.path.join(self._dir, "scripts", "download_models.sh")
            if os.path.exists(dl_script):
                subprocess.run(
                    ["bash", dl_script],
                    capture_output=True, timeout=600,
                    cwd=self._dir,
                )

            self._update_progress(100, "Done!")

            # Show step 3
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self._show_step3)

        except Exception as e:
            self._update_progress(0, f"Error: {e}")

    # ── Step 3: Ready ──
    def _show_step3(self):
        self._clear()
        cv = self._window.contentView()

        cv.addSubview_(self._label(
            NSMakeRect(0, HEIGHT - 40, WIDTH, 20),
            "Step 3 of 3", 11, 0.3,
            NSColor.colorWithWhite_alpha_(0.4, 1.0),
            NSTextAlignmentCenter,
        ))

        cv.addSubview_(self._label(
            NSMakeRect(30, HEIGHT - 85, WIDTH - 60, 30),
            "Ready!", 26, 0.6,
            NSColor.colorWithRed_green_blue_alpha_(0.4, 0.8, 0.5, 1.0),
            NSTextAlignmentCenter,
        ))

        cv.addSubview_(self._label(
            NSMakeRect(40, HEIGHT - 160, WIDTH - 80, 60),
            "Live Translator is ready to use.\n\nPlay any audio on your Mac and translations\nwill appear in the floating panel.",
            13, 0.3, NSColor.colorWithWhite_alpha_(0.6, 1.0),
            NSTextAlignmentCenter, True,
        ))

        # Launch button
        btn = NSButton.alloc().initWithFrame_(NSMakeRect((WIDTH - 140) / 2, 30, 140, 40))
        btn.setTitle_("Launch")
        btn.setBezelStyle_(NSBezelStyleRounded)
        btn.setFont_(NSFont.systemFontOfSize_weight_(15, 0.5))
        btn.setTarget_(self)
        btn.setAction_(objc.selector(self._on_launch, signature=b"v@:@"))
        cv.addSubview_(btn)

    def _on_launch(self, sender):
        self._result = "launch"
        NSApp.stop_(None)
        # Post dummy event to unblock run loop
        from AppKit import NSEvent, NSEventTypeApplicationDefined
        e = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            NSEventTypeApplicationDefined, (0, 0), 0, 0, 0, None, 0, 0, 0
        )
        NSApp.postEvent_atStart_(e, True)

    def _on_quit(self, sender):
        self._result = None
        NSApp.stop_(None)
        from AppKit import NSEvent, NSEventTypeApplicationDefined
        e = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
            NSEventTypeApplicationDefined, (0, 0), 0, 0, 0, None, 0, 0, 0
        )
        NSApp.postEvent_atStart_(e, True)


def needs_setup(resource_dir):
    """Check if first-run setup is needed."""
    config_exists = os.path.exists(CONFIG_PATH)
    venv_exists = os.path.exists(os.path.join(resource_dir, ".venv"))

    if not config_exists:
        return True

    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        if not config.get("openai_api_key"):
            return True
    except Exception:
        return True

    if not venv_exists:
        return True

    return False


if __name__ == "__main__":
    res_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__)
    wizard = SetupWizard(res_dir)
    if wizard.run():
        print("LAUNCH")
    else:
        print("QUIT")
