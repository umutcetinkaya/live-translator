"""Artımlı çeviri testleri.

Doküman modeli her turda 600+ kelimeyi yeniden yazıyordu: çıktı token
sınırına çarpıp kesiliyor, uzun bağlamda model önceki cümleleri tekrar
etmeye başlıyordu. Artık yalnızca yeni segment çevrilir ve donduruIur.
"""

from unittest.mock import MagicMock

import translator as tm
from translator import AITranslator
from providers.base import ProviderError


def _make(monkeypatch, outputs=None, on_translation=None):
    prov = MagicMock()
    if outputs is not None:
        prov.translate_segment.side_effect = outputs
    else:
        prov.translate_segment.return_value = "çeviri"
    monkeypatch.setattr(tm, "get_translation_provider", lambda c: prov)
    t = AITranslator(on_translation=on_translation,
                     config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"})
    return t, prov


def test_translates_only_new_sentence(monkeypatch):
    t, prov = _make(monkeypatch, ["Birinci."])
    t.update_source("First one.")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "First one."


def test_previous_sentence_is_not_resent(monkeypatch):
    """Asıl hata buydu: ikinci turda ilk cümle tekrar çevriliyordu."""
    t, prov = _make(monkeypatch, ["Birinci.", "İkinci."])
    t.update_source("First one.")
    t._translate_pending()
    t.update_source("First one. Second one.")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "Second one."


def test_committed_translation_accumulates(monkeypatch):
    t, prov = _make(monkeypatch, ["Birinci.", "İkinci."])
    t.update_source("First one.")
    t._translate_pending()
    t.update_source("First one. Second one.")
    t._translate_pending()
    assert t._committed == "Birinci. İkinci."


def test_committed_text_is_never_rewritten(monkeypatch):
    """Bir kez gösterilen çeviri değişmemeli — flicker sıfır."""
    t, prov = _make(monkeypatch, ["Birinci.", "İkinci.", "Üçüncü."])
    t.update_source("First one.")
    t._translate_pending()
    snapshot = t._committed
    t.update_source("First one. Second one.")
    t._translate_pending()
    t.update_source("First one. Second one. Third one.")
    t._translate_pending()
    assert t._committed.startswith(snapshot)


def test_incomplete_sentence_is_not_committed(monkeypatch):
    """Kararsız kuyruk STT tarafından revize edilebilir."""
    t, prov = _make(monkeypatch, ["Birinci."])
    t.update_source("First one. And a partial")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "First one."


def test_partial_tail_translated_once_it_completes(monkeypatch):
    t, prov = _make(monkeypatch, ["Birinci.", "Tamamlandı."])
    t.update_source("First one. Now comp")
    t._translate_pending()
    t.update_source("First one. Now complete.")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "Now complete."


def test_context_is_bounded(monkeypatch):
    """Uzun bağlam halüsinasyon yapıyor — birkaç cümleyle sınırlı olmalı."""
    t, _ = _make(monkeypatch)
    t._committed_source = " ".join(f"Sentence {i}." for i in range(30))
    ctx = t._context_sentences()
    assert 0 < len([s for s in ctx.split(".") if s.strip()]) <= 3, ctx


def test_context_passed_to_provider(monkeypatch):
    t, prov = _make(monkeypatch, ["Bir.", "İki."])
    t.update_source("First one.")
    t._translate_pending()
    t.update_source("First one. Second one.")
    t._translate_pending()
    assert "First one." in prov.translate_segment.call_args.args[1]


def test_nothing_new_makes_no_api_call(monkeypatch):
    t, prov = _make(monkeypatch, ["Bir."])
    t.update_source("First one.")
    t._translate_pending()
    prov.translate_segment.reset_mock()
    t._translate_pending()
    assert not prov.translate_segment.called


def test_only_partial_text_makes_no_api_call(monkeypatch):
    """Henüz tamamlanmış cümle yoksa çeviri yapılmamalı."""
    t, prov = _make(monkeypatch)
    t.update_source("just starting to speak")
    t._translate_pending()
    assert not prov.translate_segment.called


def test_callback_receives_committed_text(monkeypatch):
    """Overlay sözleşmesi korunmalı."""
    seen = []
    t, _ = _make(monkeypatch, ["Birinci."], on_translation=seen.append)
    t.update_source("First one.")
    t._translate_pending()
    assert seen and "Birinci." in seen[-1]


def test_clear_resets_committed_state(monkeypatch):
    t, prov = _make(monkeypatch, ["Bir."])
    t.update_source("First one.")
    t._translate_pending()
    t.clear()
    assert t._committed == "" and t._committed_source == ""


def test_recognition_rewrite_resets_state(monkeypatch):
    """STT geçmişi yeniden yazarsa donmuş çeviri geçersizdir."""
    t, prov = _make(monkeypatch, ["Birinci.", "Tamamen farklı."])
    t.update_source("First one.")
    t._translate_pending()
    t.update_source("Totally different text.")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "Totally different text."


def test_provider_error_does_not_commit(monkeypatch):
    """Hata olursa kaynak 'çevrildi' sayılmamalı, yoksa metin kaybolur."""
    prov = MagicMock()
    prov.translate_segment.side_effect = ProviderError("boom")
    monkeypatch.setattr(tm, "get_translation_provider", lambda c: prov)
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"})
    t.update_source("First one.")
    t._translate_pending()
    assert t._committed_source == ""


def test_retry_after_error_translates_same_segment(monkeypatch):
    prov = MagicMock()
    prov.translate_segment.side_effect = [ProviderError("boom"), "Birinci."]
    monkeypatch.setattr(tm, "get_translation_provider", lambda c: prov)
    t = AITranslator(config={"target_lang": "tr", "model": "claude-haiku-4-5",
                             "translation_provider": "claude"})
    t.update_source("First one.")
    t._translate_pending()
    t._translate_pending()
    assert t._committed == "Birinci."


def test_multiple_sentences_arrive_together(monkeypatch):
    """Bir turda iki cümle gelirse ikisi birden çevrilmeli."""
    t, prov = _make(monkeypatch, ["Bir. İki."])
    t.update_source("One. Two.")
    t._translate_pending()
    assert prov.translate_segment.call_args.args[0] == "One. Two."


# --- Duraklamada bekleyen metni çevir ---
# Kalite için tam düşünce bekleniyor; konuşmacı durursa bekleyen metin
# asılı kalmamalı.

def test_pause_flushes_short_pending_text(monkeypatch):
    """Konuşma durunca eşiğin altındaki metin de çevrilmeli."""
    t, prov = _make(monkeypatch, ["Kısa bir düşünce."])
    t.update_source("a short trailing thought with no punctuation")
    t._translate_pending()          # eşik altı — henüz çevirmez
    assert not prov.translate_segment.called
    t.on_speech_pause()             # konuşmacı durdu
    assert prov.translate_segment.called


def test_pause_with_nothing_pending_is_noop(monkeypatch):
    t, prov = _make(monkeypatch)
    t.on_speech_pause()
    assert not prov.translate_segment.called


def test_pause_does_not_retranslate_committed_text(monkeypatch):
    t, prov = _make(monkeypatch, ["Bir.", "İki."])
    t.update_source("First sentence here.")
    t._translate_pending()
    prov.translate_segment.reset_mock()
    t.on_speech_pause()             # yeni bir şey yok
    assert not prov.translate_segment.called
