"""macOS sistem sesleriyle ücretsiz seslendirme.

Gerçek AVSpeechSynthesizer kullanılmaz: ses listesi ve dosyaya yazan
renderer enjekte edilir. Doğrulanan şey ses seçimi (en kaliteli ses, dil
eşleşmesi), hız dönüşümü ve ses yoksa anlamlı hata.
"""

import pytest

import tts as tts_mod
from providers.base import ProviderError
from providers.system_voice import (SystemVoiceTTSProvider, best_voice,
                                    list_voices, DEFAULT_RATE, MAX_RATE)

VOICES = [
    {"id": "tr.compact.yelda", "name": "Yelda", "quality": 1, "language": "tr-TR"},
    {"id": "tr.premium.yelda", "name": "Yelda (Premium)", "quality": 3, "language": "tr-TR"},
    {"id": "tr.enhanced.yelda", "name": "Yelda (Enhanced)", "quality": 2, "language": "tr-TR"},
    {"id": "en.samantha", "name": "Samantha", "quality": 2, "language": "en-US"},
    {"id": "pt.luciana", "name": "Luciana", "quality": 1, "language": "pt-BR"},
]


def lister():
    return list(VOICES)


class Recorder:
    def __init__(self):
        self.calls = []

    def __call__(self, text, voice_id, rate, path):
        self.calls.append((text, voice_id, rate, path))
        with open(path, "wb") as f:
            f.write(b"audio")


def _provider(tmp_path, renderer=None):
    r = renderer or Recorder()
    return SystemVoiceTTSProvider(tmp_dir=str(tmp_path), voice_lister=lister, renderer=r), r


def test_prefers_premium_then_enhanced():
    assert best_voice("tr", lister)["id"] == "tr.premium.yelda"
    assert [v["quality"] for v in list_voices("tr", lister)] == [3, 2, 1]


def test_language_prefix_match():
    assert [v["id"] for v in list_voices("pt", lister)] == ["pt.luciana"]
    assert list_voices("en", lister)[0]["id"] == "en.samantha"


def test_no_partial_language_code_match():
    # "t" ile "tr-TR" eşleşmemeli; sadece tam dil kodu ya da kod + bölge
    assert list_voices("t", lister) == []


def test_best_voice_used_when_none_given(tmp_path):
    p, r = _provider(tmp_path)
    p.synthesize("Merhaba", "tr", "", 1.0)
    assert r.calls[0][1] == "tr.premium.yelda"


def test_explicit_voice_used_when_valid(tmp_path):
    p, r = _provider(tmp_path)
    p.synthesize("Merhaba", "tr", "tr.compact.yelda", 1.0)
    assert r.calls[0][1] == "tr.compact.yelda"


def test_unknown_voice_falls_back_to_best(tmp_path):
    # Başka dilin sesi ya da OpenAI ses adı ("nova") verilirse en iyi sese düş
    p, r = _provider(tmp_path)
    p.synthesize("Merhaba", "tr", "nova", 1.0)
    p.synthesize("Merhaba", "tr", "en.samantha", 1.0)
    assert [c[1] for c in r.calls] == ["tr.premium.yelda", "tr.premium.yelda"]


def test_no_voice_for_language_raises(tmp_path):
    p, _ = _provider(tmp_path)
    with pytest.raises(ProviderError, match="no voice for 'ja'"):
        p.synthesize("こんにちは", "ja", "", 1.0)


def test_speed_maps_to_rate(tmp_path):
    p, r = _provider(tmp_path)
    p.synthesize("a", "tr", "", 1.0)
    p.synthesize("a", "tr", "", 1.5)
    p.synthesize("a", "tr", "", 5.0)
    rates = [c[2] for c in r.calls]
    assert rates[0] == DEFAULT_RATE
    assert rates[1] == pytest.approx(DEFAULT_RATE * 1.5)
    assert rates[2] == MAX_RATE


def test_returns_rendered_file_path(tmp_path):
    p, r = _provider(tmp_path)
    path = p.synthesize("Merhaba", "tr", "", 1.0)
    assert path == r.calls[0][3]
    assert path.startswith(str(tmp_path))
    assert open(path, "rb").read() == b"audio"


def test_renderer_failure_is_provider_error(tmp_path):
    def broken(*a):
        raise RuntimeError("synth timeout")
    p, _ = _provider(tmp_path, renderer=broken)
    with pytest.raises(ProviderError, match="synth timeout"):
        p.synthesize("Merhaba", "tr", "", 1.0)


def test_friendly_hint_for_missing_system_voice():
    msg = tts_mod._friendly("System voice: no voice for 'ja'")
    assert msg.startswith("No system voice for this language")
    assert "Spoken Content" in msg
