# Changelog

All notable changes to Live Translator are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-11-19

Live Translator is now free: translation and speech run on the Mac, with no account and no API key. See [What's new](WHATS-NEW.md) for the overview.

### Added

- **Free on-device mode, now the default.** No account and no API key: translation runs on your Mac with [TranslateGemma](https://huggingface.co/collections/google/translategemma) through MLX, and translations are read aloud with the voices built into macOS. Nothing is sent to an AI service. Requires Apple Silicon and macOS 14 or later.
- Three on-device models, chosen by memory: Small (TranslateGemma 4B, 4-bit) on 8 GB Macs, Standard (4B, 8-bit) from 16 GB, and an opt-in Large (12B) for the best accuracy. Switch or delete them in Settings.
- The translation model downloads in the background on first launch, with progress in the panel. Download errors stay visible until resolved.
- **System voice** speech provider: free, offline and instant in every supported language. Picks the best installed voice automatically, or choose one in Settings. Enhanced and Premium voices are listed first.
- Piper voices that are not installed yet are downloaded on first use.
- The speech toggle is remembered between launches.
- Setup wizard offers the free mode first; an API key is optional.
- Anthropic Claude as a translation provider, with prompt caching.
- Live audio control panel above the chat: voice on/off, voice provider and volume without opening Settings.
- Errors are shown on screen instead of failing silently.
- `scripts/bench_local_models.py` to compare on-device models for accuracy, speed and memory.

### Changed

- The app and the DMG are signed and notarized by Apple, so macOS opens them without a security warning.
- New installs start in the free mode with speech on. Existing settings are kept: if you already use an API key, nothing changes.
- Translation is incremental: each finished sentence is translated once and kept, instead of re-translating the whole transcript. Long sessions no longer slow down or get truncated.
- A bounded context window keeps cost and latency flat on long sessions.
- Lower latency between speech and translation.
- Gemini realtime uses the dedicated live-translate model; realtime mode in Settings is limited to OpenAI.
- Spoken translations are loudness-normalised and the source audio is ducked while they play.
- Older installs pick up new dependencies on the next launch.

### Fixed

- Setup wizard text was cut off on the last step and on the error screen.
- Translation never triggered on unpunctuated speech recognition output.
- Half sentences produced meaningless translations.
- Translations only appeared once the speaker paused.
- Text-to-speech read the wrong segment or dropped the last sentence.
- OpenAI voices played too quietly; speech volume fluctuated between lines.
- An endless speech recognition restart loop and an audio format conversion error.

## [0.1.0] - 2026-05-20

### Added

- Google Gemini as a translation provider alongside OpenAI, switchable in Settings.
- Optional realtime mode that streams audio to OpenAI's Realtime Translation model for lower latency, with a privacy warning. On-device speech recognition stays the default.
- Audio sources opened after launch are captured automatically.
- "No audio detected" hint when the source is silent.

### Changed

- Model list refreshed: GPT-5.5, GPT-5.4 mini and nano; Gemini 2.5 Flash, Flash-Lite and 3.5 Flash. The model menu follows the selected provider.
- Redesigned Settings with grouped sections and provider-aware fields.
- Clear messages and graceful fallback when a provider, key or connection fails.

## [0.0.1] - 2026-03-30

### Added

- First release: live translation of any audio playing on the Mac, shown in a floating overlay.
- System audio capture with ScreenCaptureKit, on-device speech recognition.
- Translation with OpenAI models; 11 source and 12 target languages.
- Text-to-speech with Piper (offline) or OpenAI voices.
- Setup wizard and in-app settings.

[Unreleased]: https://github.com/umutcetinkaya/live-translator/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/umutcetinkaya/live-translator/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/umutcetinkaya/live-translator/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/umutcetinkaya/live-translator/releases/tag/v0.0.1
