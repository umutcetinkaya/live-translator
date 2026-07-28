"""Ayarlar HTML'inin render testleri.

overlay.py native macOS modüllerini import ettiği için tüm modülü yükleyemiyoruz;
_build_html saf bir fonksiyon olduğundan AST ile izole edip çalıştırıyoruz.
Buradaki asıl risk: %-formatlama eksik bir template anahtarında KeyError ile
çöker ve bu ancak uygulama açılırken fark edilir.
"""

import ast
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from config import SOURCE_LANGUAGES, TARGET_LANGUAGES, MODELS, OVERLAY_OPACITY

_OVERLAY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "overlay.py"
)


def _load_build_html():
    """_build_html'i overlay.py'den izole edip çalıştırılabilir hale getir."""
    tree = ast.parse(open(_OVERLAY_PATH).read())
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "_build_html")
    ns = {
        "json": json,
        "SOURCE_LANGUAGES": SOURCE_LANGUAGES,
        "TARGET_LANGUAGES": TARGET_LANGUAGES,
        "MODELS": MODELS,
        "OVERLAY_OPACITY": OVERLAY_OPACITY,
    }
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "<overlay>", "exec"), ns)
    return ns["_build_html"]


def _config(**over):
    cfg = {
        "translation_provider": "openai",
        "openai_api_key": "", "gemini_api_key": "", "anthropic_api_key": "",
        "model": "gpt-5.4-mini", "tts_provider": "piper",
        "tts_speed": 1.0, "tts_voice": "nova", "realtime_mode": False,
    }
    cfg.update(over)
    return cfg


@pytest.fixture(scope="module")
def build_html():
    return _load_build_html()


@pytest.mark.parametrize("provider", ["openai", "gemini", "claude"])
def test_renders_for_every_provider(build_html, provider):
    """Eksik template anahtarı KeyError fırlatır — her provider render olmalı."""
    html = build_html(_config(translation_provider=provider))
    assert len(html) > 1000


def test_claude_option_present(build_html):
    assert "Anthropic Claude" in build_html(_config())


def test_claude_selected_when_active(build_html):
    html = build_html(_config(translation_provider="claude"))
    assert 'value="claude" selected' in html


def test_anthropic_key_rendered(build_html):
    html = build_html(_config(anthropic_api_key="sk-ant-TEST"))
    assert "anthropicKeyRow" in html
    assert "sk-ant-TEST" in html


def test_claude_models_reach_the_dropdown(build_html):
    """Model listesi JSON olarak gömülür; claude modelleri içinde olmalı."""
    html = build_html(_config())
    assert "claude-haiku-4-5" in html
    assert "claude-opus-5" in html


def test_claude_realtime_hint_explains_why(build_html):
    """Realtime kapalıysa kullanıcı nedenini görmeli."""
    assert "Anthropic has no audio API" in build_html(_config())


def test_save_sends_anthropic_key(build_html):
    """saveSettings anahtarı Python tarafına geçirmeli."""
    assert "anthropicKey=" in build_html(_config())
