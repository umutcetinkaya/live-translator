"""Çeviri hatalarının kullanıcıya ULAŞTIĞINI doğrulayan testler.

TTS'teki sorunla aynı: geçersiz anahtar veya kota aşımı yalnızca terminale
yazılıyordu. Kullanıcı ekranda boş bir panel görüp neyin bozuk olduğunu
anlayamıyordu.
"""

from unittest.mock import MagicMock

import translator as translator_mod
from translator import AITranslator
from providers.base import ProviderError


def _make(monkeypatch, provider):
    monkeypatch.setattr(translator_mod, "get_translation_provider",
                        lambda cfg: provider)
    errors = []
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"},
                     on_error=errors.append)
    return t, errors


def test_provider_error_reaches_the_user(monkeypatch):
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError("Claude: no API key")
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    assert errors, "çeviri hatası kullanıcıya iletilmedi"


def test_missing_key_message_is_actionable(monkeypatch):
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError("Claude: no API key")
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    assert "settings" in errors[0].lower()


def test_invalid_key_message_is_actionable(monkeypatch):
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError(
        "Claude translation error: 401 authentication_error invalid x-api-key")
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    assert "settings" in errors[0].lower()


def test_rate_limit_is_explained(monkeypatch):
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError(
        "Claude translation error: 429 rate_limit_error")
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    assert "rate limit" in errors[0].lower() or "too many" in errors[0].lower()


def test_repeated_error_reported_once(monkeypatch):
    """3 sn'de bir tekrarlamamalı."""
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError("Claude: no API key")
    t, errors = _make(monkeypatch, prov)
    for _ in range(5):
        t._do_translate("Hello")
    assert len(errors) == 1


def test_success_clears_error_state(monkeypatch):
    """Düzelip tekrar bozulursa yeniden bildirilmeli."""
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError("Claude: no API key")
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    prov.translate_document.side_effect = None
    prov.translate_document.return_value = "Merhaba"
    t._do_translate("Hello there")
    prov.translate_document.side_effect = ProviderError("Claude: no API key")
    t._do_translate("Hello again")
    assert len(errors) == 2


def test_success_reports_nothing(monkeypatch):
    prov = MagicMock()
    prov.translate_document.return_value = "Merhaba"
    t, errors = _make(monkeypatch, prov)
    t._do_translate("Hello")
    assert errors == []


def test_works_without_callback(monkeypatch):
    prov = MagicMock()
    prov.translate_document.side_effect = ProviderError("x")
    monkeypatch.setattr(translator_mod, "get_translation_provider",
                        lambda cfg: prov)
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"})
    t._do_translate("Hello")   # çökmemeli
