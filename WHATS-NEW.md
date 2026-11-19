# What's new in Live Translator 0.2

## Free for everyone

Until now, Live Translator needed an API key from OpenAI, Google or Anthropic, and every minute of translation cost a little money. That kept a lot of people out.

**Version 0.2 removes that.** Install the app, pick your languages, press play. Translation runs on your own Mac, translations are read aloud with your Mac's own voices, and there is nothing to sign up for or pay. No account, no API key, no usage limits.

<p align="center">
  <a href="https://github.com/umutcetinkaya/live-translator/releases/latest/download/LiveTranslator-v0.2.1-macOS.dmg">
    <img src="https://img.shields.io/badge/⬇_Download_Live_Translator_0.2-free-brightgreen?style=for-the-badge&logo=apple&logoColor=white" alt="Download" height="36">
  </a>
</p>

## What you get

**🆓 Free translation on your Mac.** Live Translator now ships with a free mode built on [TranslateGemma](https://huggingface.co/collections/google/translategemma), Google's open translation model, running through Apple's [MLX](https://github.com/ml-explore/mlx). It is the default for new installs.

**🔊 Translations you can hear.** Speech is on from the start and uses the voices built into macOS: free, offline, instant, in every supported language. If you download an Enhanced or Premium voice, the app picks it up automatically.

**🔒 Private by design.** Translation and voice happen on your Mac, and nothing is sent to an AI company. Speech recognition is Apple's own, and runs on-device for every language whose dictation model is installed (see [below](#is-my-audio-sent-anywhere)).

**💻 A model that fits your Mac.** The app looks at how much memory your Mac has and picks a model that runs comfortably next to the video you're watching:

| Your Mac | Model | Download |
|---|---|---|
| 8 GB | TranslateGemma 4B (4-bit) | 2.2 GB |
| 16 GB or more | TranslateGemma 4B (8-bit) | 4.2 GB |
| 32 GB or more, optional | TranslateGemma 12B, the most accurate | 6.7 GB |

The model downloads once, in the background, the first time you start the app. The panel shows the progress, and you can switch or delete models in Settings at any time.

**🧭 A smoother first run.** The setup wizard offers the free mode first. An API key is optional, and you can add one later in Settings.

## How we chose the model

A translation that reads nicely but says the wrong day is worse than no translation. So the model was chosen by testing exactly what usually goes wrong: weekdays, times, numbers and negations, in sentences with and without punctuation (speech recognition often leaves punctuation out).

General-purpose AI models of this size, the kind that run on a laptop, kept turning "Thursday" into the wrong day in Turkish and dropping "not" from sentences. TranslateGemma, a model trained for translation, got them right. The small 4-bit version still slipped on weekdays in unpunctuated speech, which is why Macs with enough memory get the 8-bit one.

The test is in the repository as [`scripts/bench_local_models.py`](scripts/bench_local_models.py), so anyone can rerun it or try another model.

## Already using Live Translator?

**Your settings are kept.** If you use an OpenAI, Gemini or Anthropic key, the app keeps using it after the update. To try the free mode, open **⚙ Settings**, choose **On-device (free)** as the translation provider and press **Save**. The model downloads in the background.

The first launch after updating can take about a minute while the app installs its new components.

## Questions

### Is it really free?

Yes. The app is open source under the MIT license, and the free mode uses no paid service. The translation model comes from Google under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms) and is downloaded straight from Hugging Face.

### Is my audio sent anywhere?

Translation and voice never leave your Mac. Speech recognition uses Apple's speech framework and asks for on-device recognition. English usually works on-device out of the box; for other languages, add them under **System Settings › Keyboard › Dictation** and macOS downloads the on-device model. Until then, Apple's speech service recognises that language over the internet, as with Siri dictation. Nothing goes to OpenAI, Google or Anthropic unless you add your own key.

### Does it work offline?

Yes, once the translation model is downloaded, for every language your Mac recognises on-device.

### Which Macs are supported?

The free mode needs a Mac with Apple Silicon (M1 or later) and macOS 14 or later. On Intel Macs, Live Translator still works with your own API key.

### How good is it compared with GPT or Gemini?

For following a video, a podcast or a meeting, it is accurate and fast: well under a second per sentence on a recent Mac. The big cloud models are still better with idioms and nuance. If you need that, add a key in Settings; you can switch back to free at any time.

### Where are the models stored, and how do I remove them?

In `~/Library/Application Support/LiveTranslator/models`. Delete a model from Settings, or remove the folder.

## Everything else in this release

- Anthropic Claude as a cloud translation provider
- Live voice controls above the translation: voice on/off, voice provider and volume
- Sentence-by-sentence translation that stays fast in long sessions
- Spoken translations are loudness-normalised, and the original audio is turned down while they play
- Errors are shown on screen instead of failing silently
- Many fixes; see the [changelog](CHANGELOG.md) for the full list

## Thank you

Free mode stands on the work of Google's TranslateGemma team, Apple's MLX team and the open-source community around them. If Live Translator helps you, a ⭐ on [GitHub](https://github.com/umutcetinkaya/live-translator) helps others find it, and [issues](https://github.com/umutcetinkaya/live-translator/issues) with feedback are very welcome.
