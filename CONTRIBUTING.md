# Contributing to Live Translator

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/umutcetinkaya/live-translator.git
cd live-translator
make install
make models    # Download TTS voice models
make run       # Launch from source
```

## Building

### .app Bundle
```bash
make build
```

### DMG Installer
```bash
make dmg
```

### Code Signing (maintainers only)
Requires an Apple Developer ID certificate. Set environment variables:
```bash
export SIGN_ID="Developer ID Application: Your Name (TEAM_ID)"
make build
```

### Notarization (maintainers only)
```bash
export APPLE_ID=your@email.com
export APP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # App-specific password from appleid.apple.com
export TEAM_ID=YOUR_TEAM_ID
bash scripts/notarize.sh dist/LiveTranslator-v0.0.1-macOS.dmg
```

## Project Structure

```
src/
├── audio_capture.py       # ScreenCaptureKit system audio
├── speech_recognizer.py   # SFSpeechRecognizer + watchdog
├── translator.py          # OpenAI translation engine
├── pipeline.py            # Orchestrator (listener + translator)
├── overlay.py             # WebKit UI panel
├── tts.py                 # Text-to-speech (Piper/OpenAI)
└── config.py              # Settings management
```

## Guidelines

- Keep code in English (comments, variables, docs)
- Test on macOS 13+ before submitting PRs
- Don't commit API keys, credentials, or personal config files
- Follow existing code style

## Reporting Issues

- Use [GitHub Issues](https://github.com/umutcetinkaya/live-translator/issues)
- Include macOS version, Python version, and error logs (`~/Library/Logs/LiveTranslator.log`)
