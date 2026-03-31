"""WebKit-based translation panel with settings."""

import objc
import Quartz
import json
from AppKit import (
    NSWindow,
    NSColor,
    NSScreen,
    NSMakeRect,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSBackingStoreBuffered,
    NSWindow,
)
from Foundation import NSObject, NSURL
import WebKit
from WebKit import WKWebView, WKWebViewConfiguration
from PyObjCTools import AppHelper

from config import (
    OVERLAY_OPACITY, SOURCE_LANGUAGES, TARGET_LANGUAGES,
    load_config, save_config,
)

SCREEN_SAVER_LEVEL = 1000
WIDTH = 460
HEIGHT = 660


def _build_html(config):
    source_options = ""
    for name, locale in SOURCE_LANGUAGES.items():
        sel = "selected" if locale == config.get("source_locale", "en-US") else ""
        source_options += f'<option value="{locale}" {sel}>{name}</option>'

    target_options = ""
    for name, code in TARGET_LANGUAGES.items():
        sel = "selected" if code == config.get("target_lang", "tr") else ""
        target_options += f'<option value="{code}" {sel}>{name}</option>'

    api_key = config.get("openai_api_key", "")
    masked_key = ("•" * 20 + api_key[-8:]) if len(api_key) > 8 else api_key
    tts_provider = config.get("tts_provider", "piper")
    tts_speed = config.get("tts_speed", 1.0)

    return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%%; }
body {
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', sans-serif;
    color: #e6eadf;
    display: flex;
    flex-direction: column;
    border-radius: 12px;
    overflow: hidden;
}
body::-webkit-scrollbar { width: 4px; }
body::-webkit-scrollbar-track { background: transparent; }
body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 2px; }

/* Header */
#header {
    flex-shrink: 0;
    background: rgba(255,255,255,0.03);
    border-radius: 12px 12px 0 0;
}
#header-row1 {
    display: flex;
    align-items: center;
    padding: 8px 10px 4px;
}
#header-row1 .app-title {
    color: #5cc070;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
}
#header-row1 .spacer { flex: 1; }
#header-row1 .btn {
    background: rgba(255,255,255,0.07);
    border: none;
    color: rgba(255,255,255,0.5);
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 4px;
    cursor: pointer;
    white-space: nowrap;
    margin-left: 4px;
}
#header-row1 .btn:hover { background: rgba(255,255,255,0.15); color: #fff; }
#header-row1 .btn-close {
    color: #ff5f57;
}
#header-row1 .btn-close:hover {
    background: #ff5f57;
    color: #000;
}

#header-row2 {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 10px 7px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
#header-row2 select {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.1);
    color: #ccc;
    font-size: 11px;
    padding: 3px 6px;
    border-radius: 5px;
    outline: none;
}
#header-row2 select:focus { border-color: #5cc070; }
#header-row2 .arrow { color: rgba(255,255,255,0.3); font-size: 12px; }
#header-row2 .source-preview {
    color: rgba(255,255,255,0.18);
    font-size: 9px;
    flex: 1;
    text-align: right;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Chat area */
#chat {
    flex: 1;
    overflow-y: auto;
    padding: 10px 16px 16px;
}

.msg {
    font-size: 15px;
    line-height: 1.65;
    font-weight: 400;
    color: #e2e6da;
    margin-bottom: 10px;
    padding: 10px 14px;
    background: rgba(255,255,255,0.035);
    border-radius: 10px;
    border-left: 3px solid rgba(92, 192, 112, 0.25);
    animation: fadeIn 0.3s ease;
}
.msg.old {
    color: rgba(200, 205, 190, 0.6);
    border-left-color: rgba(92, 192, 112, 0.12);
    background: rgba(255,255,255,0.02);
}
.msg.new {
    color: #e8ecdf;
    border-left-color: #5cc070;
    background: rgba(92, 192, 112, 0.08);
    animation: fadeIn 0.4s ease;
}
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: translateY(0); }
}

.empty {
    color: rgba(255,255,255,0.25);
    font-size: 14px;
    text-align: center;
    padding: 40px 20px;
}

/* Settings modal */
#settings-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    justify-content: center;
    align-items: center;
}
#settings-overlay.show { display: flex; }
#settings-box {
    background: #1a1a22;
    border-radius: 12px;
    padding: 20px;
    width: 380px;
    border: 1px solid rgba(255,255,255,0.08);
}
#settings-box h3 { color: #5cc070; font-size: 14px; margin-bottom: 16px; }
#settings-box label { color: #999; font-size: 11px; display: block; margin-top: 12px; margin-bottom: 4px; }
#settings-box input, #settings-box select {
    width: 100%%;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    color: #ddd;
    font-size: 13px;
    padding: 8px 10px;
    border-radius: 6px;
    outline: none;
}
#settings-box input:focus, #settings-box select:focus { border-color: #5cc070; }
#settings-box .btns { display: flex; gap: 8px; margin-top: 20px; justify-content: flex-end; }
#settings-box .btns button {
    padding: 6px 16px;
    border-radius: 6px;
    border: none;
    font-size: 12px;
    cursor: pointer;
}
.btn-save { background: #5cc070; color: #000; font-weight: 600; }
.btn-cancel { background: rgba(255,255,255,0.08); color: #aaa; }
</style>
</head>
<body>

<div id="header">
    <div id="header-row1">
        <span class="app-title">Live Translator</span>
        <span class="spacer"></span>
        <button class="btn" id="ttsBtn" onclick="toggleTTS()">TTS Off</button>
        <button class="btn" onclick="openSettings()">⚙</button>
        <button class="btn" onclick="clearChat()">Clear</button>
        <button class="btn btn-close" onclick="closeApp()">✕</button>
    </div>
    <div id="header-row2">
        <select id="sourceLang" onchange="changeLang()">
            %(source_options)s
        </select>
        <span class="arrow">→</span>
        <select id="targetLang" onchange="changeLang()">
            %(target_options)s
        </select>
        <span class="source-preview" id="source"></span>
    </div>
</div>

<iframe id="dragFrame" style="display:none"></iframe>
<div id="chat">
    <div class="empty">Listening...</div>
</div>

<!-- Settings Modal -->
<div id="settings-overlay">
    <div id="settings-box">
        <h3>⚙ Settings</h3>
        <label>OpenAI API Key</label>
        <input type="password" id="apiKeyInput" value="%(api_key)s" placeholder="sk-proj-...">
        <label>Model</label>
        <select id="modelSelect">
            <option value="gpt-5" %(gpt5_sel)s>GPT-5 (latest)</option>
            <option value="gpt-5-mini" %(gpt5mini_sel)s>GPT-5 Mini</option>
            <option value="gpt-4.1" %(gpt41_sel)s>GPT-4.1</option>
            <option value="gpt-4.1-mini" %(gpt41mini_sel)s>GPT-4.1 Mini</option>
            <option value="gpt-4.1-nano" %(gpt41nano_sel)s>GPT-4.1 Nano (cheapest)</option>
            <option value="gpt-4o" %(gpt4o_sel)s>GPT-4o</option>
            <option value="gpt-4o-mini" %(gpt4omini_sel)s>GPT-4o Mini</option>
            <option value="o4-mini" %(o4mini_sel)s>o4-mini (reasoning)</option>
            <option value="o3-mini" %(o3mini_sel)s>o3-mini (reasoning)</option>
            <option value="o3" %(o3_sel)s>o3 (reasoning)</option>
            <option value="o1" %(o1_sel)s>o1 (reasoning)</option>
        </select>
        <label>TTS Provider</label>
        <select id="ttsProvider">
            <option value="piper" %(piper_sel)s>Piper (offline, free)</option>
            <option value="openai" %(openai_tts_sel)s>OpenAI TTS (cloud, natural)</option>
        </select>
        <label>OpenAI Voice</label>
        <select id="ttsVoice">
            <option value="nova" %(voice_nova)s>Nova (female, warm)</option>
            <option value="shimmer" %(voice_shimmer)s>Shimmer (female, soft)</option>
            <option value="alloy" %(voice_alloy)s>Alloy (neutral)</option>
            <option value="echo" %(voice_echo)s>Echo (male, deep)</option>
            <option value="fable" %(voice_fable)s>Fable (male, narrator)</option>
            <option value="onyx" %(voice_onyx)s>Onyx (male, strong)</option>
        </select>
        <label>TTS Speed</label>
        <input type="range" id="ttsSpeed" min="0.5" max="2.0" step="0.1" value="%(tts_speed)s"
            oninput="document.getElementById('speedVal').textContent=this.value+'x'">
        <span id="speedVal" style="color:#888;font-size:11px;">%(tts_speed)sx</span>
        <div class="btns">
            <button class="btn-cancel" onclick="closeSettings()">Cancel</button>
            <button class="btn-save" onclick="saveSettings()">Save</button>
        </div>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;color:rgba(255,255,255,0.25);font-size:10px;">
            © 2025 Umut Çetinkaya — <a href="#" style="color:rgba(92,192,112,0.6);text-decoration:none;" onclick="location.href='app://openURL?url=https://umutcetinkaya.com';return false;">umutcetinkaya.com</a>
        </div>
    </div>
</div>

<script>
let firstMsg = true;

function addMessage(text) {
    const chat = document.getElementById('chat');
    if (firstMsg) {
        chat.innerHTML = '';
        firstMsg = false;
    }
    const div = document.createElement('div');
    div.className = 'msg';
    div.textContent = text;
    chat.appendChild(div);
    // Smooth scroll to bottom
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
}

function updateSource(text) {
    document.getElementById('source').textContent = text;
}

let lastTranslation = '';

function replaceAll(text) {
    const chat = document.getElementById('chat');
    firstMsg = false;

    // Compare old and new text — find common prefix
    let commonLen = 0;
    const minLen = Math.min(lastTranslation.length, text.length);
    for (let i = 0; i < minLen; i++) {
        if (lastTranslation[i] === text[i]) commonLen = i + 1;
        else break;
    }

    const oldPart = text.substring(0, commonLen);
    const newPart = text.substring(commonLen);

    chat.innerHTML = '';

    // Old part — dimmed messages
    if (oldPart.trim()) {
        const oldParas = oldPart.split('\\n').filter(p => p.trim());
        oldParas.forEach(p => {
            const div = document.createElement('div');
            div.className = 'msg old';
            div.textContent = p.trim();
            chat.appendChild(div);
        });
    }

    // New part — highlighted
    if (newPart.trim()) {
        const newParas = newPart.split('\\n').filter(p => p.trim());
        newParas.forEach(p => {
            const div = document.createElement('div');
            div.className = 'msg new';
            div.textContent = p.trim();
            chat.appendChild(div);
        });
    }

    lastTranslation = text;
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
}

function clearChat() {
    document.getElementById('chat').innerHTML = '<div class="empty">Listening...</div>';
    firstMsg = true;
    location.href = 'app://clear';
}

function closeApp() {
    location.href = 'app://close';
}

function toggleTTS() {
    location.href = 'app://toggleTTS';
}

function setTTSState(on) {
    const btn = document.getElementById('ttsBtn');
    btn.textContent = on ? 'TTS On' : 'TTS Off';
    btn.style.color = on ? '#5cc070' : '';
}

// Drag — drag window from header area
let dragging = false;

document.getElementById('header').addEventListener('mousedown', function(e) {
    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SELECT' || e.target.tagName === 'OPTION') return;
    dragging = true;
    location.href = 'app://dragStart?x=' + e.screenX + '&y=' + e.screenY;
});

document.addEventListener('mousemove', function(e) {
    if (!dragging) return;
    // Throttle via iframe to prevent URL navigation conflicts
    const f = document.getElementById('dragFrame');
    f.src = 'app://dragMove?x=' + e.screenX + '&y=' + e.screenY;
});

document.addEventListener('mouseup', function(e) {
    if (dragging) {
        dragging = false;
        location.href = 'app://dragEnd';
    }
});

function changeLang() {
    const src = document.getElementById('sourceLang').value;
    const tgt = document.getElementById('targetLang').value;
    location.href = 'app://changeLang?source=' + encodeURIComponent(src) + '&target=' + encodeURIComponent(tgt);
}

function openSettings() {
    document.getElementById('settings-overlay').classList.add('show');
}

function closeSettings() {
    document.getElementById('settings-overlay').classList.remove('show');
}

function saveSettings() {
    const key = document.getElementById('apiKeyInput').value;
    const model = document.getElementById('modelSelect').value;
    const ttsProvider = document.getElementById('ttsProvider').value;
    const ttsSpeed = document.getElementById('ttsSpeed').value;
    const ttsVoice = document.getElementById('ttsVoice').value;
    location.href = 'app://saveSettings?apiKey=' + encodeURIComponent(key)
        + '&model=' + encodeURIComponent(model)
        + '&ttsProvider=' + encodeURIComponent(ttsProvider)
        + '&ttsSpeed=' + encodeURIComponent(ttsSpeed)
        + '&ttsVoice=' + encodeURIComponent(ttsVoice);
    closeSettings();
}
</script>
</body>
</html>""" % {
        "source_options": source_options,
        "target_options": target_options,
        "api_key": api_key,
        "gpt5_sel": "selected" if config.get("model") == "gpt-5" else "",
        "gpt5mini_sel": "selected" if config.get("model") == "gpt-5-mini" else "",
        "gpt41_sel": "selected" if config.get("model") == "gpt-4.1" else "",
        "gpt41mini_sel": "selected" if config.get("model") == "gpt-4.1-mini" else "",
        "gpt41nano_sel": "selected" if config.get("model") == "gpt-4.1-nano" else "",
        "gpt4o_sel": "selected" if config.get("model") == "gpt-4o" else "",
        "gpt4omini_sel": "selected" if config.get("model") == "gpt-4o-mini" else "",
        "o4mini_sel": "selected" if config.get("model") == "o4-mini" else "",
        "o3mini_sel": "selected" if config.get("model") == "o3-mini" else "",
        "o3_sel": "selected" if config.get("model") == "o3" else "",
        "o1_sel": "selected" if config.get("model") == "o1" else "",
        "piper_sel": "selected" if tts_provider == "piper" else "",
        "openai_tts_sel": "selected" if tts_provider == "openai" else "",
        "tts_speed": tts_speed,
        "voice_nova": "selected" if config.get("tts_voice") == "nova" else "",
        "voice_shimmer": "selected" if config.get("tts_voice") == "shimmer" else "",
        "voice_alloy": "selected" if config.get("tts_voice", "nova") == "alloy" else "",
        "voice_echo": "selected" if config.get("tts_voice") == "echo" else "",
        "voice_fable": "selected" if config.get("tts_voice") == "fable" else "",
        "voice_onyx": "selected" if config.get("tts_voice") == "onyx" else "",
    }


class _NavDelegate(NSObject):
    """WKNavigationDelegate — intercepts app:// URLs."""

    _overlay = None

    def webView_decidePolicyForNavigationAction_decisionHandler_(self, webview, action, handler):
        url = action.request().URL().absoluteString()

        if url.startswith("app://"):
            handler(0)  # cancel navigation
            # URL parse: app://action?key=val&key2=val2
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            action_name = parsed.netloc
            params = dict(urllib.parse.parse_qsl(parsed.query))
            print(f"[Bridge] {action_name} {params}")
            self.handleAction_params_(action_name, params)
        else:
            handler(1)  # allow

    def handleAction_params_(self, action, params):
        o = self._overlay
        if not o:
            return
        if action == "changeLang" and o._on_lang_change:
            o._on_lang_change(params.get("source", "en-US"), params.get("target", "tr"))
        elif action == "saveSettings":
            o._save_settings(
                params.get("apiKey", ""),
                params.get("model", "gpt-4o-mini"),
                params.get("ttsProvider", "piper"),
                params.get("ttsSpeed", "1.0"),
                params.get("ttsVoice", "nova"),
            )
        elif action == "clear" and o._on_clear:
            o._on_clear()
        elif action == "close" and o._on_close:
            o._on_close()
        elif action == "toggleTTS" and o._on_toggle_tts:
            o._on_toggle_tts()
        elif action == "dragStart":
            o._drag_start(float(params.get("x", 0)), float(params.get("y", 0)))
        elif action == "dragMove":
            o._drag_move(float(params.get("x", 0)), float(params.get("y", 0)))
        elif action == "dragEnd":
            o._drag_end()


class _Updater(NSObject):
    _overlay = None
    def appendMessage_(self, text):
        if self._overlay:
            self._overlay._js("addMessage", text)
    def updateSource_(self, text):
        if self._overlay:
            self._overlay._js("updateSource", text)
    def replaceAll_(self, text):
        if self._overlay:
            self._overlay._js("replaceAll", text)


class TranslationOverlay:

    def __init__(self, on_lang_change=None, on_settings_change=None, on_clear=None, on_close=None, on_toggle_tts=None):
        self._window = None
        self._webview = None
        self._on_lang_change = on_lang_change
        self._on_settings_change = on_settings_change
        self._on_clear = on_clear
        self._on_close = on_close
        self._on_toggle_tts = on_toggle_tts
        self._config = load_config()
        self._updater = _Updater.alloc().init()
        self._updater._overlay = self

    def setup(self):
        screen = NSScreen.mainScreen()
        sf = screen.visibleFrame()

        x = sf.origin.x + sf.size.width - WIDTH - 16
        y = sf.origin.y + sf.size.height - HEIGHT - 16

        frame = NSMakeRect(x, y, WIDTH, HEIGHT)

        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame, style, NSBackingStoreBuffered, False
        )
        self._window.setLevel_(SCREEN_SAVER_LEVEL)
        self._window.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorStationary
        )
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(
            NSColor.colorWithRed_green_blue_alpha_(0.07, 0.07, 0.09, 0.96)
        )
        self._window.setHasShadow_(True)
        self._window.setAlphaValue_(OVERLAY_OPACITY)
        self._window.setTitlebarAppearsTransparent_(True)
        self._window.setTitleVisibility_(1)  # hidden
        self._window.setMovable_(True)
        # Hide window buttons
        self._window.standardWindowButton_(0).setHidden_(True)  # close
        self._window.standardWindowButton_(1).setHidden_(True)  # minimize
        self._window.standardWindowButton_(2).setHidden_(True)  # zoom
        # fullSizeContentView — HTML extends into titlebar area
        from AppKit import NSWindowStyleMaskFullSizeContentView
        self._window.setStyleMask_(
            self._window.styleMask() | NSWindowStyleMaskFullSizeContentView
        )

        # WKWebView
        config = WKWebViewConfiguration.alloc().init()
        self._webview = WKWebView.alloc().initWithFrame_configuration_(
            NSMakeRect(0, 0, WIDTH, HEIGHT), config
        )

        # Navigation delegate — app:// URL'leri yakalar
        self._nav_delegate = _NavDelegate.alloc().init()
        self._nav_delegate._overlay = self
        self._webview.setNavigationDelegate_(self._nav_delegate)
        self._webview.setValue_forKey_(False, "drawsBackground")
        self._window.setContentView_(self._webview)
        self._window.setMovableByWindowBackground_(False)  # Drag handled via JS bridge

        # Load HTML
        html = _build_html(self._config)
        self._webview.loadHTMLString_baseURL_(html, None)

    def _js(self, func, arg):
        escaped = json.dumps(arg)
        js = f"{func}({escaped})"
        self._webview.evaluateJavaScript_completionHandler_(js, None)

    def _save_settings(self, api_key, model, tts_provider="piper", tts_speed="1.0", tts_voice="nova"):
        self._config["openai_api_key"] = api_key
        self._config["model"] = model
        self._config["tts_provider"] = tts_provider
        self._config["tts_speed"] = float(tts_speed)
        self._config["tts_voice"] = tts_voice
        save_config(self._config)
        print(f"[Overlay] Settings saved (model: {model}, tts: {tts_provider}, voice: {tts_voice})")
        if self._on_settings_change:
            self._on_settings_change(self._config)

    # ── Public ──

    def show(self):
        if self._window:
            self._window.orderFrontRegardless()

    def hide(self):
        if self._window:
            self._window.orderOut_(None)

    def is_visible(self):
        return self._window.isVisible() if self._window else False

    def get_config(self):
        return self._config

    def update_original_on_main_thread(self, text):
        display = text if len(text) <= 100 else "..." + text[-97:]
        self._updater.performSelectorOnMainThread_withObject_waitUntilDone_(
            "updateSource:", display, False
        )

    def update_text_on_main_thread(self, text):
        self._updater.performSelectorOnMainThread_withObject_waitUntilDone_(
            "appendMessage:", text, False
        )

    # ── Drag ──
    _drag_start_x = 0
    _drag_start_y = 0
    _drag_origin_x = 0
    _drag_origin_y = 0

    def _drag_start(self, x, y):
        self._drag_start_x = x
        self._drag_start_y = y
        origin = self._window.frame().origin
        self._drag_origin_x = origin.x
        self._drag_origin_y = origin.y

    def _drag_move(self, x, y):
        from AppKit import NSPoint
        dx = x - self._drag_start_x
        dy = self._drag_start_y - y  # macOS y-axis is inverted
        new_origin = NSPoint(self._drag_origin_x + dx, self._drag_origin_y + dy)
        self._window.setFrameOrigin_(new_origin)

    def _drag_end(self):
        pass

    def set_tts_state(self, on):
        js = f"setTTSState({'true' if on else 'false'})"
        self._webview.evaluateJavaScript_completionHandler_(js, None)

    def replace_all_text(self, text):
        """Replace all chat content with updated translation."""
        self._updater.performSelectorOnMainThread_withObject_waitUntilDone_(
            "replaceAll:", text, False
        )

    def update_status_on_main_thread(self, status):
        pass
