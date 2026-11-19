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

Store the credentials once in the macOS keychain. notarytool asks for an
app-specific password (create one at account.apple.com); it is never written
to the repository or passed on the command line.

```bash
xcrun notarytool store-credentials "livetranslator-notary" \
    --apple-id your@email.com --team-id YOUR_TEAM_ID
```

Then build, sign, notarize and staple in one step:

```bash
make notarize VERSION=x.y.z
```

Build releases from a clean checkout of the release tag, so nothing from your
working copy ends up in the DMG.

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
- Add a line for user-visible changes to `CHANGELOG.md` under **Unreleased**
- Follow existing code style

## Reporting Issues

- Use [GitHub Issues](https://github.com/umutcetinkaya/live-translator/issues)
- Include macOS version, Python version, and error logs (`~/Library/Logs/LiveTranslator.log`)
