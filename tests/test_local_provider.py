"""Cihazda çalışan ücretsiz çeviri sağlayıcısı (MLX, TranslateGemma).

Gerçek model yüklenmez: loader ve generator enjekte edilir. TranslateGemma
genel sohbet modeli değil, çeviri modelidir: kendi istemini şablondan kurar
ve tek bir mesajda kaynak dil kodu, hedef dil kodu ve metin bekler. Bağlam
için ayrı bir alanı yoktur; bağlamı metne katmak onu da çevirtir.
"""

import pytest

import model_store
from providers.base import ProviderError
from providers.local import LocalTranslationProvider

REPO = "mlx-community/test-model"


class FakeTokenizer:
    def __init__(self):
        self.messages = None

    def apply_chat_template(self, messages, add_generation_prompt=True, **kw):
        self.messages = messages
        return "PROMPT"


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(model_store, "is_ready", lambda repo: True)
    monkeypatch.setattr(model_store, "model_dir", lambda repo: "/models/" + repo)


def _provider(output="Merhaba dünya", tokenizer=None, loads=None, gen_error=None,
              config=None):
    tok = tokenizer or FakeTokenizer()

    def loader(path):
        if loads is not None:
            loads.append(path)
        return object(), tok

    def generator(model, tokenizer, prompt):
        if gen_error:
            raise gen_error
        assert prompt == "PROMPT"
        return output

    cfg = config if config is not None else {"source_locale": "en-US"}
    return LocalTranslationProvider(config=cfg, loader=loader, generator=generator), tok


def _item(tok):
    (msg,) = tok.messages
    assert msg["role"] == "user"
    (item,) = msg["content"]
    return item


def test_uses_translategemma_message_format(ready):
    p, tok = _provider()
    p.translate_segment("hello world", "earlier text", "Turkish", REPO)
    assert _item(tok) == {"type": "text", "source_lang_code": "en",
                          "target_lang_code": "tr", "text": "hello world"}


def test_context_is_not_sent(ready):
    # Bağlam metne eklenirse model onu da çevirir ve tekrar okunur
    p, tok = _provider()
    p.translate_segment("hello", "earlier text", "Turkish", REPO)
    assert "earlier" not in _item(tok)["text"]


def test_source_follows_live_language_change(ready):
    # Pipeline dil değişince aynı config sözlüğünü günceller; sağlayıcı yeniden kurulmaz
    cfg = {"source_locale": "en-US"}
    p, tok = _provider(config=cfg)
    cfg["source_locale"] = "de-DE"
    p.translate_segment("Guten Tag", "", "English", REPO)
    assert _item(tok)["source_lang_code"] == "de"
    assert _item(tok)["target_lang_code"] == "en"


@pytest.mark.parametrize("locale,code", [("zh-CN", "zh"), ("pt-BR", "pt"), ("ja-JP", "ja")])
def test_locale_maps_to_language_code(ready, locale, code):
    p, tok = _provider(config={"source_locale": locale})
    p.translate_segment("x", "", "Turkish", REPO)
    assert _item(tok)["source_lang_code"] == code


@pytest.mark.parametrize("name,code", [("Turkish", "tr"), ("German", "de"), ("Chinese", "zh"),
                                       ("Portuguese", "pt"), ("tr", "tr")])
def test_target_name_maps_to_code(ready, name, code):
    p, tok = _provider()
    p.translate_segment("x", "", name, REPO)
    assert _item(tok)["target_lang_code"] == code


def test_returns_clean_translation(ready):
    p, _ = _provider(output="  Merhaba dünya<end_of_turn>\n")
    assert p.translate_segment("hello world", "", "Turkish", REPO) == "Merhaba dünya"


def test_strips_labels_and_quotes(ready):
    p, _ = _provider(output="Translation: \"Merhaba dünya\"")
    assert p.translate_segment("hello world", "", "Turkish", REPO) == "Merhaba dünya"


def test_unsupported_language_is_provider_error(ready):
    class Picky(FakeTokenizer):
        def apply_chat_template(self, messages, **kw):
            raise Exception("'dict object' has no attribute 'xx'")
    p, _ = _provider(tokenizer=Picky())
    with pytest.raises(ProviderError, match="language"):
        p.translate_segment("hi", "", "Turkish", REPO)


def test_model_loaded_once_per_model(ready):
    loads = []
    p, _ = _provider(loads=loads)
    p.translate_segment("a", "", "Turkish", REPO)
    p.translate_segment("b", "", "Turkish", REPO)
    assert loads == ["/models/" + REPO]


def test_switching_model_reloads(ready):
    loads = []
    p, _ = _provider(loads=loads)
    p.translate_segment("a", "", "Turkish", REPO)
    p.translate_segment("a", "", "Turkish", REPO + "-large")
    assert len(loads) == 2


def test_not_ready_raises_provider_error(monkeypatch):
    monkeypatch.setattr(model_store, "is_ready", lambda repo: False)
    p, _ = _provider()
    with pytest.raises(ProviderError, match="not ready"):
        p.translate_segment("hi", "", "Turkish", REPO)


def test_generation_error_wrapped(ready):
    p, _ = _provider(gen_error=RuntimeError("metal oom"))
    with pytest.raises(ProviderError, match="metal oom"):
        p.translate_segment("hi", "", "Turkish", REPO)


def test_document_translation_uses_segment_path(ready):
    p, tok = _provider()
    assert p.translate_document("hello", "", "Turkish", REPO) == "Merhaba dünya"
    assert _item(tok)["text"] == "hello"


def test_factory_passes_live_config():
    from providers import get_translation_provider
    cfg = {"translation_provider": "local", "source_locale": "fr-FR"}
    p = get_translation_provider(cfg)
    assert p._config is cfg
