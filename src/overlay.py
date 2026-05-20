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
    OVERLAY_OPACITY, SOURCE_LANGUAGES, TARGET_LANGUAGES, MODELS,
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

    openai_key = config.get("openai_api_key", "")
    gemini_key = config.get("gemini_api_key", "")
    provider = config.get("translation_provider", "openai")
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
    background: rgba(0,0,0,0.72);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 100;
    justify-content: center;
    align-items: center;
    animation: ovFade 0.18s ease;
}
@keyframes ovFade { from { opacity: 0; } to { opacity: 1; } }
#settings-overlay.show { display: flex; }
#settings-box {
    background: linear-gradient(180deg, #1e1e27 0%%, #16161d 100%%);
    border-radius: 16px;
    padding: 22px 22px 18px;
    width: 400px;
    max-height: 86vh;
    overflow-y: auto;
    border: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 24px 60px rgba(0,0,0,0.55);
    animation: boxRise 0.22s cubic-bezier(.2,.8,.2,1);
}
@keyframes boxRise { from { transform: translateY(12px) scale(.98); opacity: 0; } to { transform: none; opacity: 1; } }
#settings-box::-webkit-scrollbar { width: 6px; }
#settings-box::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.14); border-radius: 3px; }
#settings-box h3 {
    color: #fff; font-size: 16px; font-weight: 600; margin-bottom: 4px;
    display: flex; align-items: center; gap: 7px;
}
#settings-box .subtitle { color: rgba(255,255,255,0.4); font-size: 11px; margin-bottom: 16px; }
/* Section cards */
.section {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 12px 14px 14px;
    margin-bottom: 12px;
}
.section-title {
    color: #5cc070; font-size: 10px; font-weight: 700;
    letter-spacing: 0.7px; text-transform: uppercase;
    margin-bottom: 8px;
}
#settings-box label { color: rgba(255,255,255,0.55); font-size: 11px; display: block; margin-top: 11px; margin-bottom: 5px; }
.section > label:first-of-type, .section .section-title + label { margin-top: 0; }
#settings-box input, #settings-box select {
    width: 100%%;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    color: #eee;
    font-size: 13px;
    padding: 9px 11px;
    border-radius: 8px;
    outline: none;
    transition: border-color 0.15s, background 0.15s;
}
#settings-box input:hover, #settings-box select:hover { background: rgba(255,255,255,0.09); }
#settings-box input:focus, #settings-box select:focus {
    border-color: #5cc070; background: rgba(92,192,112,0.06);
}
#settings-box input[type=range] { padding: 0; }
.hidden { display: none !important; }
/* Toggle row */
.toggle-row {
    display: flex; align-items: center; justify-content: space-between;
    margin-top: 4px;
}
.toggle-row .tl { color: rgba(255,255,255,0.8); font-size: 12px; }
.toggle-row .tl small { display: block; color: rgba(255,255,255,0.35); font-size: 10px; margin-top: 1px; }
.switch { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
.switch input { display: none; }
.slider {
    position: absolute; inset: 0; cursor: pointer;
    background: rgba(255,255,255,0.15); border-radius: 22px; transition: 0.2s;
}
.slider:before {
    content: ""; position: absolute; height: 16px; width: 16px;
    left: 3px; top: 3px; background: #fff; border-radius: 50%%; transition: 0.2s;
}
.switch input:checked + .slider { background: #5cc070; }
.switch input:checked + .slider:before { transform: translateX(18px); }
.switch input:disabled + .slider { opacity: 0.35; cursor: not-allowed; }
#settings-box .btns { display: flex; gap: 10px; margin-top: 18px; }
#settings-box .btns button {
    flex: 1; padding: 10px; border-radius: 9px; border: none;
    font-size: 13px; font-weight: 600; cursor: pointer; transition: 0.15s;
}
.btn-save { background: #5cc070; color: #0a0a0a; }
.btn-save:hover { background: #6cd47f; }
.btn-cancel { background: rgba(255,255,255,0.08); color: #bbb; }
.btn-cancel:hover { background: rgba(255,255,255,0.14); }
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
        <div class="subtitle">Translation provider, models and voice</div>

        <div class="section">
            <div class="section-title">Translation</div>
            <label>Provider</label>
            <select id="providerSelect" onchange="onProviderChange()">
                <option value="openai" %(openai_prov_sel)s>OpenAI</option>
                <option value="gemini" %(gemini_prov_sel)s>Google Gemini</option>
            </select>
            <div id="openaiKeyRow">
                <label>OpenAI API Key</label>
                <input type="password" id="openaiKeyInput" value="%(openai_key)s" placeholder="sk-proj-…">
            </div>
            <div id="geminiKeyRow">
                <label>Gemini API Key</label>
                <input type="password" id="geminiKeyInput" value="%(gemini_key)s" placeholder="AIza…">
            </div>
            <label>Model</label>
            <select id="modelSelect"></select>
        </div>

        <div class="section">
            <div class="section-title">Text-to-Speech</div>
            <label>Voice provider</label>
            <select id="ttsProvider" onchange="onTtsProviderChange()">
                <option value="piper" %(piper_sel)s>Piper — offline, free</option>
                <option value="openai" %(openai_tts_sel)s>OpenAI — natural</option>
                <option value="gemini" %(gemini_tts_sel)s>Gemini — natural</option>
            </select>
            <div id="openaiVoiceRow">
                <label>OpenAI voice</label>
                <select id="ttsVoice">
                    <option value="nova" %(voice_nova)s>Nova — female, warm</option>
                    <option value="shimmer" %(voice_shimmer)s>Shimmer — female, soft</option>
                    <option value="alloy" %(voice_alloy)s>Alloy — neutral</option>
                    <option value="echo" %(voice_echo)s>Echo — male, deep</option>
                    <option value="fable" %(voice_fable)s>Fable — male, narrator</option>
                    <option value="onyx" %(voice_onyx)s>Onyx — male, strong</option>
                </select>
            </div>
            <label>Speed — <span id="speedVal">%(tts_speed)sx</span></label>
            <input type="range" id="ttsSpeed" min="0.5" max="2.0" step="0.1" value="%(tts_speed)s"
                oninput="document.getElementById('speedVal').textContent=this.value+'x'">
        </div>

        <div class="section">
            <div class="section-title">Realtime</div>
            <div class="toggle-row">
                <span class="tl">Realtime audio mode
                    <small id="realtimeHint">Lower latency — streams audio to the cloud</small>
                </span>
                <label class="switch">
                    <input type="checkbox" id="realtimeToggle" %(realtime_checked)s onchange="onRealtimeChange()">
                    <span class="slider"></span>
                </label>
            </div>
            <div id="realtimeWarn" style="display:%(realtime_warn_display)s;color:#e0a000;font-size:11px;margin-top:8px;line-height:1.4;">
                ⚠️ Audio is sent to the cloud. On-device STT is disabled. Takes effect after restart.
            </div>
        </div>

        <div class="btns">
            <button class="btn-cancel" onclick="closeSettings()">Cancel</button>
            <button class="btn-save" onclick="saveSettings()">Save</button>
        </div>
        <div style="margin-top:14px;text-align:center;color:rgba(255,255,255,0.25);font-size:10px;">
            © 2025 Umut Çetinkaya — <a href="#" style="color:rgba(92,192,112,0.6);text-decoration:none;" onclick="location.href='app://openURL?url=https://umutcetinkaya.com';return false;">umutcetinkaya.com</a>
        </div>
    </div>
</div>

<script>
let firstMsg = true;

const MODELS = %(models_json)s;
const CURRENT_MODEL = %(current_model_json)s;
function populateModels() {
    const provider = document.getElementById('providerSelect').value;
    const sel = document.getElementById('modelSelect');
    sel.innerHTML = '';
    (MODELS[provider] || []).forEach(function(m) {
        const o = document.createElement('option');
        o.value = m; o.textContent = m;
        if (m === CURRENT_MODEL) o.selected = true;
        sel.appendChild(o);
    });
}
function onProviderChange() {
    const provider = document.getElementById('providerSelect').value;
    // İlgili API key alanını göster, diğerini gizle
    document.getElementById('openaiKeyRow').classList.toggle('hidden', provider !== 'openai');
    document.getElementById('geminiKeyRow').classList.toggle('hidden', provider !== 'gemini');
    // Realtime sadece OpenAI'da kullanılabilir; Gemini'de kapat + devre dışı bırak
    const rt = document.getElementById('realtimeToggle');
    const hint = document.getElementById('realtimeHint');
    if (provider === 'gemini') {
        rt.checked = false;
        rt.disabled = true;
        hint.textContent = 'Available with OpenAI provider';
        document.getElementById('realtimeWarn').style.display = 'none';
    } else {
        rt.disabled = false;
        hint.textContent = 'Lower latency — streams audio to the cloud';
    }
    populateModels();
}

function onRealtimeChange() {
    const on = document.getElementById('realtimeToggle').checked;
    document.getElementById('realtimeWarn').style.display = on ? 'block' : 'none';
}

function onTtsProviderChange() {
    // OpenAI voice seçimi yalnızca OpenAI TTS'te anlamlı
    const tts = document.getElementById('ttsProvider').value;
    document.getElementById('openaiVoiceRow').classList.toggle('hidden', tts !== 'openai');
}

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
    const provider = document.getElementById('providerSelect').value;
    const openaiKey = document.getElementById('openaiKeyInput').value;
    const geminiKey = document.getElementById('geminiKeyInput').value;
    const model = document.getElementById('modelSelect').value;
    const ttsProvider = document.getElementById('ttsProvider').value;
    const ttsSpeed = document.getElementById('ttsSpeed').value;
    const ttsVoice = document.getElementById('ttsVoice').value;
    location.href = 'app://saveSettings?provider=' + encodeURIComponent(provider)
        + '&openaiKey=' + encodeURIComponent(openaiKey)
        + '&geminiKey=' + encodeURIComponent(geminiKey)
        + '&model=' + encodeURIComponent(model)
        + '&ttsProvider=' + encodeURIComponent(ttsProvider)
        + '&ttsSpeed=' + encodeURIComponent(ttsSpeed)
        + '&ttsVoice=' + encodeURIComponent(ttsVoice)
        + '&realtime=' + (document.getElementById('realtimeToggle').checked ? '1' : '0');
    closeSettings();
}

function initSettings() {
    onProviderChange();      // key satırları + realtime durumu + modeller
    onTtsProviderChange();   // OpenAI voice görünürlüğü
}
document.addEventListener('DOMContentLoaded', initSettings);
initSettings();
</script>
</body>
</html>""" % {
        "source_options": source_options,
        "target_options": target_options,
        "openai_prov_sel": "selected" if provider == "openai" else "",
        "gemini_prov_sel": "selected" if provider == "gemini" else "",
        "openai_key": openai_key,
        "gemini_key": gemini_key,
        "piper_sel": "selected" if tts_provider == "piper" else "",
        "openai_tts_sel": "selected" if tts_provider == "openai" else "",
        "gemini_tts_sel": "selected" if tts_provider == "gemini" else "",
        "tts_speed": tts_speed,
        "voice_nova": "selected" if config.get("tts_voice") == "nova" else "",
        "voice_shimmer": "selected" if config.get("tts_voice") == "shimmer" else "",
        "voice_alloy": "selected" if config.get("tts_voice", "nova") == "alloy" else "",
        "voice_echo": "selected" if config.get("tts_voice") == "echo" else "",
        "voice_fable": "selected" if config.get("tts_voice") == "fable" else "",
        "voice_onyx": "selected" if config.get("tts_voice") == "onyx" else "",
        "models_json": json.dumps(MODELS),
        "current_model_json": json.dumps(config.get("model", "")),
        "realtime_checked": "checked" if config.get("realtime_mode") else "",
        "realtime_warn_display": "block" if config.get("realtime_mode") else "none",
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
            # API key'leri loglara sızdırma
            safe = {k: ("***" if "key" in k.lower() else v) for k, v in params.items()}
            print(f"[Bridge] {action_name} {safe}")
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
                params.get("provider", "openai"),
                params.get("openaiKey", ""),
                params.get("geminiKey", ""),
                params.get("model", "gpt-5.4-mini"),
                params.get("ttsProvider", "piper"),
                params.get("ttsSpeed", "1.0"),
                params.get("ttsVoice", "nova"),
                params.get("realtime", "0"),
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

    def _save_settings(self, provider, openai_key, gemini_key, model,
                       tts_provider="piper", tts_speed="1.0", tts_voice="nova",
                       realtime="0"):
        self._config["translation_provider"] = provider
        self._config["openai_api_key"] = openai_key
        self._config["gemini_api_key"] = gemini_key
        self._config["model"] = model
        self._config["tts_provider"] = tts_provider
        self._config["tts_speed"] = float(tts_speed)
        self._config["tts_voice"] = tts_voice
        # Realtime yalnızca OpenAI'da desteklenir; Gemini'de her zaman kapalı.
        self._config["realtime_mode"] = (realtime == "1") and (provider == "openai")
        save_config(self._config)
        print(f"[Overlay] Settings saved (provider: {provider}, model: {model})")
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
