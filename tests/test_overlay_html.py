"""Ayarlar HTML'inin render testleri.

overlay.py native macOS modüllerini import ettiği için tüm modülü yükleyemiyoruz;
_build_html saf bir fonksiyon olduğundan AST ile izole edip çalıştırıyoruz.
Buradaki asıl risk: %-formatlama eksik bir template anahtarında KeyError ile
çöker ve bu ancak uygulama açılırken fark edilir.
"""

import ast
import re
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from config import SOURCE_LANGUAGES, TARGET_LANGUAGES, MODELS, OVERLAY_OPACITY, normalize_model
from providers.openai import REALTIME_VOICES, realtime_voice

_OVERLAY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "overlay.py"
)


def _load_build_html():
    """_build_html'i overlay.py'den izole edip çalıştırılabilir hale getir."""
    tree = ast.parse(open(_OVERLAY_PATH).read())
    wanted = ("_build_html", "_current_system_volume")
    fns = [n for n in tree.body
           if isinstance(n, ast.FunctionDef) and n.name in wanted]
    ns = {
        "json": json,
        "SOURCE_LANGUAGES": SOURCE_LANGUAGES,
        "TARGET_LANGUAGES": TARGET_LANGUAGES,
        "MODELS": MODELS,
        "normalize_model": normalize_model,
        "REALTIME_VOICES": REALTIME_VOICES,
        "realtime_voice": realtime_voice,
        "OVERLAY_OPACITY": OVERLAY_OPACITY,
    }
    exec(compile(ast.Module(body=fns, type_ignores=[]), "<overlay>", "exec"), ns)
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
    assert "claude-haiku-5-5" in html
    assert "claude-opus-5-5" in html


def test_claude_realtime_hint_explains_why(build_html):
    """Realtime kapalıysa kullanıcı nedenini görmeli."""
    assert "Anthropic has no audio API" in build_html(_config())


def test_save_sends_anthropic_key(build_html):
    """saveSettings anahtarı Python tarafına geçirmeli."""
    assert "anthropicKey=" in build_html(_config())


# --- Ücretsiz mod: yerel çeviri ve sistem sesi seçenekleri ---

from local_models import LOCAL_MODELS

STD, LARGE = LOCAL_MODELS["standard"], LOCAL_MODELS["large"]


def _env(**over):
    env = {
        "local_supported": True,
        "local_models": [
            {"id": STD, "label": "Standard · 4.2 GB", "status": "Ready · 2.2 GB", "warn": ""},
            {"id": LARGE, "label": "Large (most accurate) · 6.7 GB", "status": "Not downloaded", "warn": ""},
        ],
        "system_voices": [
            {"id": "tr.enhanced", "name": "Yelda", "quality": 2},
            {"id": "tr.compact", "name": "Yelda", "quality": 1},
        ],
    }
    env.update(over)
    return env


def test_switching_to_local_preselects_this_macs_default(build_html):
    # Kayıtlı model bulut modeliyken yerel moda geçilirse liste başı (Small) değil,
    # bu Mac için önerilen model seçili gelmeli
    html = build_html(_config(translation_provider="openai", model="gpt-5.4-mini"),
                      env=_env(default_local_model=STD))
    assert f"const DEFAULT_LOCAL_MODEL = {json.dumps(STD)};" in html
    assert "provider === 'local' ? DEFAULT_LOCAL_MODEL" in html


def test_renders_without_env(build_html):
    # Eski çağrı biçimi (env yok) çökmemeli ve yerel seçeneği göstermemeli
    html = build_html(_config())
    assert 'value="local"' not in html


def test_local_option_first_when_supported(build_html):
    html = build_html(_config(), _env())
    sel = html.index('id="providerSelect"')
    assert html.index('value="local"', sel) < html.index('value="openai"', sel)
    assert "On-device (free)" in html


def test_local_option_hidden_when_unsupported(build_html):
    html = build_html(_config(), _env(local_supported=False))
    assert 'value="local"' not in html


def test_local_selected_when_active(build_html):
    html = build_html(_config(translation_provider="local", model=STD), _env())
    assert 'value="local" selected' in html


@pytest.mark.parametrize("tts", ["system", "piper", "openai", "gemini"])
def test_renders_for_every_tts_provider(build_html, tts):
    assert len(build_html(_config(tts_provider=tts), _env())) > 1000


def test_local_hides_key_rows_and_shows_model_row(build_html):
    html = build_html(_config(), _env())
    assert "localModelRow" in html
    assert "provider !== 'local'" in html.replace('"', "'") or \
        "provider === 'local'" in html.replace('"', "'")


def test_local_model_info_embedded(build_html):
    html = build_html(_config(translation_provider="local", model=STD), _env())
    assert "Standard · 4.2 GB" in html
    assert "Not downloaded" in html


def test_system_voice_option_in_both_lists(build_html):
    html = build_html(_config(), _env())
    assert html.count('value="system"') == 2
    assert "System voice (free)" in html


def test_system_voices_rendered_for_target_lang(build_html):
    html = build_html(_config(tts_provider="system", tts_voice_system="tr.compact"), _env())
    assert 'value="tr.compact" selected' in html
    assert "Yelda (Enhanced)" in html


def test_voice_download_hint_only_without_good_voice(build_html):
    hint = "Spoken Content"
    good = build_html(_config(tts_provider="system"), _env())
    only_basic = build_html(_config(tts_provider="system"),
                            _env(system_voices=[{"id": "tr.compact", "name": "Yelda", "quality": 1}]))
    assert hint not in good and hint in only_basic


def test_save_settings_passes_system_voice(build_html):
    assert "&systemVoice=" in build_html(_config(), _env())


def test_delete_model_action_in_page(build_html):
    assert "app://deleteLocalModel?model=" in build_html(_config(), _env())


# --- OpenAI sesleri Realtime API'ye taşındı ---

def test_openai_voice_list_shows_realtime_voices(build_html):
    html = build_html(_config(tts_provider="openai", tts_voice="cedar"))
    start = html.index('id="ttsVoice"')
    block = html[start:html.index("</select>", start)]
    values = re.findall(r'value="([a-z]+)"', block)
    assert values == ["marin", "cedar", "alloy", "ash", "ballad", "coral",
                      "echo", "sage", "shimmer", "verse"]
    assert '<option value="cedar" selected>' in block
    assert "Marin (recommended)" in block


def test_saved_speech_api_voice_shows_its_realtime_match(build_html):
    # "nova" Realtime'da yok; Ayarlar onun karşılığını (marin) seçili göstermeli
    html = build_html(_config(tts_provider="openai", tts_voice="nova"))
    start = html.index('id="ttsVoice"')
    block = html[start:html.index("</select>", start)]
    assert '<option value="marin" selected>' in block
    assert 'value="nova"' not in block
