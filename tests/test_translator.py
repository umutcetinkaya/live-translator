from unittest.mock import MagicMock
import translator as translator_mod
from translator import AITranslator


def test_translate_pending_calls_provider(monkeypatch):
    fake_provider = MagicMock()
    fake_provider.translate_segment.return_value = "Merhaba"
    monkeypatch.setattr(translator_mod, "get_translation_provider",
                        lambda cfg: fake_provider)
    captured = []
    t = AITranslator(on_translation=captured.append,
                     config={"target_lang": "tr", "model": "gpt-5.4-mini",
                             "translation_provider": "openai"})
    t.update_source("Hello.")
    t._translate_pending()
    fake_provider.translate_segment.assert_called_once()
    assert captured == ["Merhaba"]

def test_provider_error_does_not_crash(monkeypatch):
    from providers.base import ProviderError
    fake_provider = MagicMock()
    fake_provider.translate_segment.side_effect = ProviderError("x")
    monkeypatch.setattr(translator_mod, "get_translation_provider",
                        lambda cfg: fake_provider)
    t = AITranslator(config={"target_lang": "tr", "model": "gpt-5.4-mini",
                             "translation_provider": "openai"})
    t.update_source("Hello.")
    t._translate_pending()  # exception sızdırmamalı
