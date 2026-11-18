"""Cihazda çalışan ücretsiz çeviri sağlayıcısı (MLX).

Gerçek model yüklenmez: loader ve generator enjekte edilir. Doğrulanan şey,
sağlayıcının diğerleriyle aynı istemi kurması, modelin ekstra metnini
temizlemesi ve hataları ProviderError olarak sarmasıdır.
"""

import pytest

import model_store
from providers.base import ProviderError, SEGMENT_SYSTEM_PROMPT
from providers.local import LocalTranslationProvider

REPO = "mlx-community/test-model"


class FakeTokenizer:
    def __init__(self, thinking_kw=True):
        self.thinking_kw = thinking_kw
        self.messages = None

    def apply_chat_template(self, messages, add_generation_prompt=True, **kw):
        if "enable_thinking" in kw and not self.thinking_kw:
            raise TypeError("unexpected keyword 'enable_thinking'")
        self.messages = messages
        return "PROMPT"


@pytest.fixture
def ready(monkeypatch):
    monkeypatch.setattr(model_store, "is_ready", lambda repo: True)
    monkeypatch.setattr(model_store, "model_dir", lambda repo: "/models/" + repo)


def _provider(output="Merhaba dünya", tokenizer=None, loads=None, gen_error=None):
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

    return LocalTranslationProvider(loader=loader, generator=generator), tok


def test_uses_shared_segment_prompt(ready):
    p, tok = _provider()
    p.translate_segment("hello world", "earlier text", "Turkish", REPO)
    system, user = tok.messages
    assert system == {"role": "system", "content": SEGMENT_SYSTEM_PROMPT}
    assert "NEW (translate only this):\nhello world" in user["content"]
    assert "earlier text" in user["content"]
    assert "Target language: Turkish" in user["content"]


def test_returns_clean_translation(ready):
    p, _ = _provider(output="  Merhaba dünya \n")
    assert p.translate_segment("hello world", "", "Turkish", REPO) == "Merhaba dünya"


def test_strips_think_block_and_labels(ready):
    raw = "<think>\nthe user wants turkish\n</think>\nTranslation: \"Merhaba dünya\""
    p, _ = _provider(output=raw)
    assert p.translate_segment("hello world", "", "Turkish", REPO) == "Merhaba dünya"


def test_template_without_thinking_flag(ready):
    p, tok = _provider(tokenizer=FakeTokenizer(thinking_kw=False))
    assert p.translate_segment("hi", "", "Turkish", REPO) == "Merhaba dünya"


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
    p.translate_segment("a", "", "Turkish", REPO + "-small")
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
    assert "NEW (translate only this):\nhello" in tok.messages[1]["content"]
