"""Cümle segmentasyonu testleri.

Zaman tabanlı kesme (her 1.2 sn) cümle ortasından bölüyordu; literatürde
segmentasyon politikası cümle sınırı + sessizlik. Kararsız kuyruk ayrılır
çünkü STT son cümleyi hâlâ revize edebilir.
"""

from segmenter import split_sentences, stable_prefix


def test_splits_on_sentence_end():
    assert split_sentences("Hello world. How are you?") == [
        "Hello world.", "How are you?"]


def test_keeps_incomplete_sentence():
    assert split_sentences("Hello world. How are") == [
        "Hello world.", "How are"]


def test_empty_text_gives_no_segments():
    assert split_sentences("") == []


def test_whitespace_only_gives_no_segments():
    assert split_sentences("   \n  ") == []


def test_handles_multiple_punctuation():
    assert split_sentences("Wait... What?! Yes.") == [
        "Wait...", "What?!", "Yes."]


def test_does_not_split_decimals():
    """3.14 bir cümle sonu değil."""
    assert split_sentences("Pi is 3.14 exactly.") == ["Pi is 3.14 exactly."]


def test_does_not_split_common_abbreviations():
    assert split_sentences("Dr. Smith arrived. He was late.") == [
        "Dr. Smith arrived.", "He was late."]


def test_stable_prefix_separates_incomplete_tail():
    stable, tail = stable_prefix("First one. Second one. And a partial")
    assert stable == "First one. Second one."
    assert tail == "And a partial"


def test_stable_prefix_with_no_complete_sentence():
    stable, tail = stable_prefix("just some words")
    assert stable == ""
    assert tail == "just some words"


def test_stable_prefix_when_everything_complete():
    stable, tail = stable_prefix("Done. Finished.")
    assert stable == "Done. Finished."
    assert tail == ""


def test_stable_prefix_empty_input():
    assert stable_prefix("") == ("", "")


def test_short_tail_is_held_back():
    """Tamamlanmamış kuyruk, kısa da olsa kararsızdır."""
    stable, tail = stable_prefix("Complete one. Hi")
    assert stable == "Complete one."
    assert tail == "Hi"


def test_turkish_sentences_split():
    """Hedef dil Türkçe de olabilir; noktalama aynı."""
    assert split_sentences("Merhaba dünya. Nasılsın?") == [
        "Merhaba dünya.", "Nasılsın?"]


def test_committed_prefix_grows_monotonically():
    """Metin uzadıkça kararlı kısım yalnızca büyümeli — donmuş çeviri için şart."""
    a, _ = stable_prefix("One. Two.")
    b, _ = stable_prefix("One. Two. Three.")
    assert b.startswith(a)
