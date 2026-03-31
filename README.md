<p align="center">
  <img src="assets/icon.iconset/icon_256x256.png" width="128" height="128" alt="Live Translator">
</p>

<h1 align="center">Live Translator</h1>

<p align="center">
  <strong>Real-time system audio translation for macOS</strong><br>
  Translate any audio playing on your Mac — YouTube, podcasts, meetings, movies — live on screen.
</p>

<p align="center">
  <a href="https://github.com/umutcetinkaya/live-translator/releases/latest"><img src="https://img.shields.io/github/v/release/umutcetinkaya/live-translator?style=flat-square&color=brightgreen" alt="Release"></a>
  <a href="https://github.com/umutcetinkaya/live-translator/stargazers"><img src="https://img.shields.io/github/stars/umutcetinkaya/live-translator?style=flat-square" alt="Stars"></a>
  <img src="https://img.shields.io/badge/macOS-13%2B-blue?style=flat-square" alt="macOS">
  <img src="https://img.shields.io/badge/Python-3.11%2B-yellow?style=flat-square" alt="Python">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/umutcetinkaya/live-translator/releases/latest/download/LiveTranslator-v0.0.1-macOS.dmg">
    <img src="https://img.shields.io/badge/⬇_Download_DMG-brightgreen?style=for-the-badge&logo=apple&logoColor=white" alt="Download" height="36">
  </a>
  &nbsp;&nbsp;
  <a href="https://buymeacoffee.com/umutcetinkaya">
    <img src="https://img.shields.io/badge/Buy_Me_a_Coffee-☕-orange?style=for-the-badge" alt="Buy Me a Coffee" height="36">
  </a>
</p>

---

## Why?

You're watching a YouTube video in Japanese. A podcast in Arabic. A meeting in German. You don't speak these languages — but you want to understand **everything**, **right now**.

Live Translator sits quietly in your menu bar, captures whatever audio your Mac is playing, and shows you a live, flowing translation on screen. No copy-pasting, no tab switching, no waiting. Just play audio and read.

It's not a word-by-word subtitler. It uses a **live document model** — the AI sees the full conversation, maintains context, and produces natural translations that read like a human wrote them.

```
System Audio → Speech Recognition → AI Translation → Live Overlay
(ScreenCaptureKit)  (SFSpeechRecognizer)  (OpenAI GPT)     (WebKit Panel)
```

## Demo

### 🇬🇧 English → 🇹🇷 Turkish
<img src="assets/videos/en-to-tr-demo.gif" width="100%" alt="English to Turkish demo">

### 🇯🇵 Japanese → 🇹🇷 Turkish
<img src="assets/videos/jp-to-tr-demo.gif" width="100%" alt="Japanese to Turkish demo">

### 🇸🇦 Arabic → 🇹🇷 Turkish
<img src="assets/videos/ar-to-tr-demo.gif" width="100%" alt="Arabic to Turkish demo">

### 🇸🇦 Arabic → Multi Language
<img src="assets/videos/ar-to-multi-lang-demo.gif" width="100%" alt="Arabic to Multi Language demo">

## Features

- **Real-time translation** of any audio on your Mac
- **11 source languages** — English, German, French, Spanish, Italian, Japanese, Chinese, Korean, Russian, Arabic, Portuguese
- **12 target languages** — translate into any supported language
- **Context-aware AI** — maintains full conversation context, never loses track
- **Live document model** — translation grows like a live document, new parts highlighted
- **Text-to-Speech** — hear translations read aloud (Piper offline or OpenAI voices)
- **Multiple AI models** — GPT-5, GPT-4.1, GPT-4o, o4-mini, o3, and more
- **Floating overlay** — dark-themed panel, draggable, always on top
- **In-app settings** — API key, model, TTS, languages — all configurable from the UI
- **No audio drivers needed** — uses ScreenCaptureKit (macOS 13+)
- **On-device STT** — speech recognition works without internet
- **Auto-recovery** — watchdog detects and recovers from stuck states
- **Menu bar app** — runs quietly with 🌐 icon in menu bar

## Install

### Option 1: DMG (Recommended)

<a href="https://github.com/umutcetinkaya/live-translator/releases/latest/download/LiveTranslator-v0.0.1-macOS.dmg">
  <img src="https://img.shields.io/badge/⬇_Download_DMG-brightgreen?style=for-the-badge&logo=apple&logoColor=white" alt="Download DMG">
</a>

1. Download → Open DMG → Drag to **Applications**
2. Launch → Setup wizard guides you through everything
3. Enter your **OpenAI API key** ([get one here](https://platform.openai.com))
4. Grant **Screen & System Audio Recording** permission when prompted
5. Play any audio → translations appear live

> **First launch:** If macOS blocks the app, right-click → Open, or run `xattr -cr /Applications/Live\ Translator.app`

### Option 2: Homebrew

```bash
brew tap umutcetinkaya/tap
brew install --cask live-translator
```

### Option 3: From Source

```bash
git clone https://github.com/umutcetinkaya/live-translator.git
cd live-translator
make install    # Create venv + install deps
make models     # Download TTS voice models (~580MB)
make run        # Launch
```

## Quick Start

1. Launch → floating panel appears + 🌐 in menu bar
2. Click **⚙ Settings** → enter your OpenAI API key
3. Select **source language** (what's being spoken) and **target language** (what you want to read)
4. Play any audio → translations appear in real-time
5. New translations are **highlighted** so you always know what just changed

### Controls

| Control | Action |
|---------|--------|
| Source / Target dropdowns | Change languages |
| ⚙ Settings | API key, model, TTS provider, voice, speed |
| TTS Off / On | Toggle text-to-speech |
| Clear | Reset translation history |
| ✕ | Quit |
| Menu bar 🌐 | Pause, Show/Hide, Quit |

## Text-to-Speech

| Provider | Pros | Cons |
|----------|------|------|
| **Piper** (default) | Free, offline, fast | Robotic voice |
| **OpenAI TTS** | Natural voices (Nova, Shimmer, Alloy, Echo, Fable, Onyx) | Costs money |

TTS plays through the same process — the app's own voice is automatically filtered from capture. No feedback loops.

## Supported Models

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| GPT-4o Mini | ⚡ Fastest | ¢ | Daily use |
| GPT-4.1 Nano | ⚡ Fastest | ¢ | Budget |
| GPT-4.1 Mini | 🚀 Fast | $ | Balanced |
| GPT-5 Mini | 🚀 Fast | $ | Latest |
| GPT-4o | 🚀 Fast | $$ | Quality |
| GPT-4.1 | 🚀 Fast | $$ | Quality |
| GPT-5 | 🚀 Fast | $$ | Latest + Quality |
| o4-mini | 🐢 Slow | $$ | Reasoning |
| o3-mini | 🐢 Slow | $$ | Reasoning |
| o3 | 🐢 Slowest | $$$ | Deep reasoning |
| o1 | 🐢 Slowest | $$$ | Deep reasoning |

> **Recommendation:** GPT-4o Mini or GPT-4.1 Nano for real-time translation (fast + cheap).

## How It Works

Live Translator runs two independent agents in parallel:

1. **Listener** — continuously captures system audio via ScreenCaptureKit and transcribes it on-device using SFSpeechRecognizer
2. **Translator** — every ~3 seconds, takes the full accumulated transcript and sends it to OpenAI GPT

The AI is instructed to **preserve its previous translation** and only **append or refine new content**. The overlay highlights what changed, so you can always follow along.

This means:
- Context is never lost
- Incomplete sentences get refined next cycle
- The translation reads as a coherent, flowing document
- No disconnected fragments

## Architecture

```
live-translator/
├── main.py                      # Entry point + menu bar
├── src/
│   ├── audio_capture.py         # ScreenCaptureKit system audio
│   ├── speech_recognizer.py     # SFSpeechRecognizer + watchdog + ring buffer
│   ├── translator.py            # OpenAI live document translation
│   ├── pipeline.py              # Listener + Translator orchestrator
│   ├── overlay.py               # WebKit floating panel (HTML/CSS/JS)
│   ├── tts.py                   # Piper (offline) / OpenAI TTS
│   └── config.py                # JSON settings
├── models/                      # Piper voice models (downloaded separately)
├── scripts/
│   ├── build_app.sh             # Build .app bundle
│   ├── build_dmg.sh             # Create DMG installer
│   ├── download_models.sh       # Download TTS models
│   ├── notarize.sh              # Apple notarization
│   ├── setup_wizard.swift       # Native macOS setup wizard
│   └── launcher.c               # Native .app launcher
├── assets/                      # App icon + demo media
├── Makefile
├── requirements.txt
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

## Configuration

Settings are stored in `~/.live-translator.json` and can be changed from the in-app Settings panel:

```json
{
  "openai_api_key": "sk-...",
  "source_locale": "en-US",
  "target_lang": "tr",
  "model": "gpt-4o-mini",
  "tts_provider": "piper",
  "tts_voice": "nova",
  "tts_speed": 1.0
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Damaged and can't be opened" | Run `xattr -cr /Applications/Live\ Translator.app` |
| No audio detected | Grant Screen & System Audio Recording permission, restart app |
| STT stops working | Built-in watchdog auto-recovers within 10 seconds |
| Translation not appearing | Check OpenAI API key in Settings |
| TTS not working | Check TTS provider in Settings |
| App not in dock | By design — it's a menu bar app (🌐) |

## Requirements

- **macOS 13 (Ventura)** or later
- **Python 3.11+** (auto-installed via setup wizard if missing)
- **OpenAI API key** ([get one here](https://platform.openai.com))

---

<p align="center">
  <strong>If Live Translator helps you, give it a ⭐ on GitHub — it helps others find it!</strong>
</p>

<p align="center">
  <a href="https://github.com/umutcetinkaya/live-translator">
    <img src="https://img.shields.io/github/stars/umutcetinkaya/live-translator?style=social" alt="Star on GitHub">
  </a>
</p>

---

## Support the Project

<a href="https://buymeacoffee.com/umutcetinkaya">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="48" alt="Buy Me a Coffee">
</a>

## License

MIT — see [LICENSE](LICENSE).

Copyright © 2025 [Umut Çetinkaya](https://umutcetinkaya.com)

## Credits

- [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit) — macOS audio capture
- [SFSpeechRecognizer](https://developer.apple.com/documentation/speech) — on-device speech recognition
- [OpenAI API](https://platform.openai.com) — AI translation
- [Piper TTS](https://github.com/rhasspy/piper) — offline text-to-speech
- [PyObjC](https://pyobjc.readthedocs.io) — Python ↔ macOS bridge
