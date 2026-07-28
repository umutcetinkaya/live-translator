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


# --- Noktalamasız STT çıktısı ---
# SFSpeechRecognizer noktalama ÜRETMİYOR: metin "hello world how are you"
# şeklinde geliyor. Yalnızca noktalamaya bakan segmentasyon hiçbir şeyi
# kararlı saymıyordu ve çeviri hiç tetiklenmiyordu.

def test_unpunctuated_speech_still_yields_a_segment():
    """Noktalama yoksa da yeterince uzun metin çevrilebilmeli.

    Eşik = segment boyutu + kararsız kuyruk; altında beklemek doğru."""
    text = ("hello and welcome back to the channel today we are looking at "
            "how large language models handle real time translation and why "
            "latency matters so much when you are watching a live stream with "
            "subtitles running at the bottom of your screen right now")
    stable, tail = stable_prefix(text)
    assert stable, "noktalamasız metin hiç çevrilemiyordu"


def test_unpunctuated_keeps_recent_words_unstable():
    """Son kelimeler STT tarafından revize edilebilir — dondurulmamalı."""
    text = " ".join(f"word{i}" for i in range(40))
    stable, tail = stable_prefix(text)
    assert tail, "kararsız kuyruk bırakılmalı"
    assert len(tail.split()) >= 3


def test_short_unpunctuated_text_waits():
    """Birkaç kelime henüz segment değil — konuşmanın oturması beklenir."""
    stable, tail = stable_prefix("hello there")
    assert stable == ""
    assert tail == "hello there"


def test_punctuation_still_wins_when_present():
    """Noktalama varsa cümle sınırı kullanılmalı — kelime sayısı değil."""
    stable, tail = stable_prefix("Short one. and then some more words here")
    assert stable == "Short one."


def test_unpunctuated_prefix_is_monotonic():
    """Donmuş çeviri için: kararlı kısım geri gitmemeli."""
    words = [f"word{i}" for i in range(60)]
    a, _ = stable_prefix(" ".join(words[:30]))
    b, _ = stable_prefix(" ".join(words))
    assert b.startswith(a), (a, b)


def _incremental_segments(words, step=1):
    """STT'nin kelime kelime büyümesini taklit et, üretilen segmentleri topla."""
    committed, segments = "", []
    for i in range(1, len(words) + 1, step):
        settled, _ = stable_prefix(" ".join(words[:i]))
        new = settled[len(committed):].strip()
        if new:
            segments.append(new)
            committed = settled
    return segments


def test_segments_are_not_single_words():
    """Kelime başına segment = kelime başına API çağrısı.

    Eşik aşıldığında her yeni kelimede kesmek bu hataya yol açıyordu."""
    words = ("hello and welcome back to the channel today we are looking at "
             "how large language models handle real time translation and why "
             "latency matters so much when you are watching a live stream").split()
    segs = _incremental_segments(words)
    tiny = [s for s in segs if len(s.split()) < 3]
    assert not tiny, f"çok küçük segmentler: {tiny}"


def test_segment_count_stays_reasonable():
    """~35 kelimelik konuşma birkaç segment olmalı, düzinelerce değil."""
    words = ("hello and welcome back to the channel today we are looking at "
             "how large language models handle real time translation and why "
             "latency matters so much when you are watching a live stream").split()
    segs = _incremental_segments(words)
    assert len(segs) <= 5, f"{len(segs)} segment üretildi: {segs}"


def test_segments_reconstruct_the_source():
    """Hiçbir kelime kaybolmamalı ve tekrar etmemeli."""
    words = [f"w{i}" for i in range(40)]
    segs = _incremental_segments(words)
    joined = " ".join(segs).split()
    assert joined == words[:len(joined)], joined[:12]


# --- Segment boyutu ve çeviri kalitesi ---
# Yarım cümle hiçbir dile düzgün çevrilemez: Türkçe/Japonca/Korece/Almanca
# fiili sona koyar, yani İngilizce cümlenin yarısında hedef dilin ana fiili
# henüz gelmemiştir. Ölçüldü: 14 kelimelik parça "Bugün bakıyoruz nasıl büyük"
# üretiyordu; tam düşünce "Bugün büyük dil modellerinin ... inceliyoruz."

def test_segment_balances_quality_against_delay():
    """Segment tam düşünce taşımalı ama konuşma akarken de tetiklenmeli.

    28 kelime kaliteliydi fakat çeviri yalnızca konuşmacı durunca geliyordu
    ("durdurunca geç geldi"). Yarım cümle de anlamsız çıktı üretiyordu, o
    yüzden aralık dar: bir yan cümleyi taşıyacak kadar uzun, akışı
    durdurmayacak kadar kısa."""
    import segmenter
    assert 16 <= segmenter.UNPUNCTUATED_SEGMENT_WORDS <= 22


def test_segments_carry_a_full_thought():
    words = ("hello and welcome back to the channel today we are looking at "
             "how large language models handle real time translation and why "
             "latency matters so much when you are watching a live stream "
             "with subtitles running at the bottom of your screen").split()
    segs = _incremental_segments(words)
    assert segs, "hiç segment üretilmedi"
    for s in segs:
        assert len(s.split()) >= 12, f"çok kısa segment: {s!r}"


def test_pause_flushes_pending_text():
    """Konuşmacı durunca bekleyen metin çevrilmeli — yoksa son cümle kaybolur."""
    from segmenter import flush_prefix
    settled, tail = flush_prefix("a short trailing thought")
    assert settled == "a short trailing thought"
    assert tail == ""


def test_flush_is_noop_on_empty():
    from segmenter import flush_prefix
    assert flush_prefix("") == ("", "")
