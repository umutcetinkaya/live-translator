# Live Translator

Real-time system audio translation for macOS. Captures any audio playing on your computer, transcribes it, and translates it live — like having a simultaneous interpreter on your screen.

![macOS](https://img.shields.io/badge/macOS-13%2B-blue) ![Python](https://img.shields.io/badge/Python-3.11%2B-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## How It Works

```
System Audio → Speech Recognition → AI Translation → Live Overlay
(ScreenCaptureKit)  (SFSpeechRecognizer)  (OpenAI GPT)     (WebKit Panel)
```

**Two independent agents work in parallel:**
- **Listener** — continuously captures and transcribes system audio using Apple's on-device speech recognition
- **Translator** — every few seconds, takes the full transcript and produces a coherent, context-aware translation

The translation is displayed in a floating overlay panel. New content is highlighted so you always know what was just added.

## Features

- **Real-time translation** of any audio playing on your Mac
- **11 source languages** — English, German, French, Spanish, Italian, Japanese, Chinese, Korean, Russian, Arabic, Portuguese
- **12 target languages** — translate into any supported language
- **Context-aware** — maintains full conversation context, never loses track
- **Live overlay** — floating dark-themed panel, draggable, always on top
- **Text-to-Speech** — hear translations read aloud (Piper offline or OpenAI cloud voices)
- **Multiple AI models** — GPT-5, GPT-4.1, GPT-4o, o4-mini, o3, and more
- **In-app settings** — configure everything from the UI
- **No audio drivers needed** — uses ScreenCaptureKit (macOS 13+)
- **On-device STT** — speech recognition works offline

## Requirements

- **macOS 13 (Ventura)** or later
- **Python 3.11+**
- **OpenAI API key** — [platform.openai.com](https://platform.openai.com)

## Install

### Option 1: DMG Installer (Recommended)

1. Download the latest `.dmg` from [Releases](https://github.com/umutcetinkaya/live-translator/releases)
2. Open the DMG, drag **Live Translator** to **Applications**
3. Launch — it will ask for your **OpenAI API key** on first run
4. Dependencies are installed automatically on first launch

### Option 2: From Source

```bash
git clone https://github.com/umutcetinkaya/live-translator.git
cd live-translator
make install
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Optional: Download TTS voice models (~580MB)

```bash
make models
```

### Optional: Build macOS .app bundle

```bash
make build
# Output: dist/Live Translator.app
```

## Usage

```bash
make run
```

Or:

```bash
source .venv/bin/activate
python main.py
```

### First Run

macOS will ask for permissions:
1. **Screen Recording** — System Settings → Privacy & Security → Screen Recording → add Terminal/Python
2. **Speech Recognition** — auto-prompted

### Quick Start

1. Launch → floating panel appears + 🌐 in menu bar
2. Click **⚙ Settings** → enter your **OpenAI API key**
3. Select **source language** (spoken) and **target language** (output)
4. Play any audio → translations appear in real-time

### Controls

| Control | Action |
|---------|--------|
| Source / Target dropdowns | Change languages |
| ⚙ Settings | API key, model, TTS config |
| Clear | Reset translation history |
| ✕ | Quit |
| TTS Off / On | Toggle text-to-speech |
| Menu bar 🌐 | Pause, Show/Hide, Quit |

## Text-to-Speech

| Provider | Pros | Cons |
|----------|------|------|
| **Piper** (default) | Free, offline | Robotic voice |
| **OpenAI TTS** | Natural voices (Nova, Shimmer, Alloy, Echo, Fable, Onyx) | Costs money |

Configure in Settings → TTS Provider + Voice + Speed.

## Supported Models

| Model | Speed | Cost |
|-------|-------|------|
| GPT-5 | Fast | $$ |
| GPT-5 Mini | Fastest | $ |
| GPT-4.1 | Fast | $$ |
| GPT-4.1 Mini | Fast | $ |
| GPT-4.1 Nano | Fastest | ¢ |
| GPT-4o | Fast | $$ |
| GPT-4o Mini | Fastest | ¢ |
| o4-mini | Slow | $$ |
| o3-mini | Slow | $$ |
| o3 | Slowest | $$$ |
| o1 | Slowest | $$$ |

**Recommended:** GPT-4o Mini or GPT-4.1 Nano (fast + cheap).

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
│   └── config.py                # JSON settings (~/.live-translator.json)
├── models/                      # Piper voice models (downloaded separately)
├── scripts/
│   └── download_models.sh       # TTS model downloader
├── setup_app.py                 # py2app config for .app bundle
├── Makefile                     # install, run, build, models, clean
├── requirements.txt
├── setup.sh
└── LICENSE
```

## How Translation Works

Unlike chunk-by-chunk translation, Live Translator uses a **live document model**:

1. Speech is continuously transcribed and accumulated
2. Every ~3 seconds, the **full transcript** + **previous translation** are sent to GPT
3. GPT **preserves previous translation** and appends/refines new content
4. The overlay shows the growing translation with **new parts highlighted**

This ensures context is never lost, incomplete sentences get refined, and the output reads as a coherent document.

## Configuration

Stored in `~/.live-translator.json`:

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
| No audio detected | Grant Screen Recording permission in System Settings |
| STT stops working | Built-in watchdog auto-recovers within 10 seconds |
| Translation not appearing | Check OpenAI API key in Settings |
| TTS not working | Check TTS provider in Settings, try OpenAI TTS |

## License

MIT — see [LICENSE](LICENSE).

## Credits

- [ScreenCaptureKit](https://developer.apple.com/documentation/screencapturekit) — macOS audio capture
- [SFSpeechRecognizer](https://developer.apple.com/documentation/speech) — on-device STT
- [OpenAI API](https://platform.openai.com) — translation
- [Piper TTS](https://github.com/rhasspy/piper) — offline text-to-speech
- [PyObjC](https://pyobjc.readthedocs.io) — Python ↔ macOS bridge
