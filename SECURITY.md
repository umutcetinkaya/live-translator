# Security Policy

## What leaves your Mac

- **Free mode (default):** translation runs on your Mac with TranslateGemma, and the voice is a macOS system voice. Nothing is sent to an AI service.
- **Speech recognition:** Apple's speech recognition runs on-device for languages whose dictation model is installed (English usually is). For other spoken languages, Apple's speech service recognises the audio over the internet.
- **Cloud translation (optional):** if you choose OpenAI, Gemini or Claude with your own key, the recognised text is sent to that provider, under its privacy policy.
- **Cloud voices (optional):** OpenAI and Gemini voices send the translated text to that provider.
- **Realtime mode (optional):** your system audio is streamed to OpenAI.
- **Downloads:** the translation model and Piper voices come from Hugging Face on first use.
- **Update check:** once per launch the app asks `api.github.com` for the latest release. The request carries only the app version in its User-Agent. Turn it off with `"check_for_updates": false` in `~/.live-translator.json`.
- **No analytics, telemetry or tracking** of any kind.

## API keys

- Keys for OpenAI, Gemini and Anthropic are stored locally in `~/.live-translator.json`.
- A key is only sent to its own provider's API.
- The config file lives in your home folder, outside the repository, so it is never committed.
- Key fields in Settings and in the setup wizard are masked.

## If a key leaks

1. Revoke it at the provider: [OpenAI](https://platform.openai.com/api-keys), [Google AI Studio](https://aistudio.google.com/apikey) or [Anthropic Console](https://console.anthropic.com/settings/keys).
2. Create a new key.
3. Paste it into Live Translator, Settings.

## Reporting vulnerabilities

If you discover a security vulnerability, please email [cetinkayaposta@gmail.com](mailto:cetinkayaposta@gmail.com) instead of opening a public issue.
