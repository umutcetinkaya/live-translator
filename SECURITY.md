# Security Policy

## API Key Handling

- Your OpenAI API key is stored locally in `~/.live-translator.json`
- The key is **never** transmitted anywhere except to OpenAI's API
- The key is **never** committed to git (`.gitignore` excludes the config file)
- The setup wizard input field masks the key

## If Your API Key Is Leaked

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Revoke the compromised key
3. Generate a new key
4. Update it in Live Translator → Settings → OpenAI API Key

## Data Privacy

- **Speech recognition** runs on-device (SFSpeechRecognizer) — audio is not sent to any server for STT
- **Translation** sends recognized text to OpenAI's API — subject to [OpenAI's privacy policy](https://openai.com/policies/privacy-policy)
- **TTS (Piper)** runs fully offline — no data leaves your Mac
- **TTS (OpenAI)** sends translated text to OpenAI for speech synthesis
- **No analytics, telemetry, or tracking** of any kind

## Reporting Vulnerabilities

If you discover a security vulnerability, please email [cetinkayaposta@gmail.com](mailto:cetinkayaposta@gmail.com) instead of opening a public issue.
