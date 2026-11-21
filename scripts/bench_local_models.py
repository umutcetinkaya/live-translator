"""Benchmark on-device translation models for accuracy, speed and memory.

Runs the same code path the app uses (providers/local.py) on sentences where
a wrong translation is easy to miss: weekdays, times, numbers and negations.
Each sentence lists words the translation must contain; misses are counted so
models can be compared without reading every line. Not a test: it downloads
models and needs Apple Silicon.

    .venv/bin/python scripts/bench_local_models.py mlx-community/translategemma-4b-it-4bit ...
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from providers.local import (LocalTranslationProvider, _clean,  # noqa: E402
                             _language_code, _mlx_generate, _mlx_load)

# (source locale, target language, text, words the translation must contain;
# each entry may list alternatives separated by "|").
SAMPLES = [
    ("en-US", "Turkish", "The meeting has been moved to Thursday afternoon.", ["toplantı", "perşembe"]),
    # Speech recognition often delivers text without punctuation; small
    # quantised models get weekdays wrong far more often in this form.
    ("en-US", "Turkish", "good morning everyone the meeting has been moved to Thursday afternoon",
     ["günaydın|merhaba", "perşembe"]),
    ("en-US", "Turkish", "Thursday works for me but Tuesday does not", ["perşembe", "salı"]),
    ("en-US", "Turkish", "The price went up by 15 percent last year.", ["15", "geçen yıl"]),
    ("en-US", "Turkish", "Sarah will call you back tomorrow morning.", ["sarah", "yarın", "sabah"]),
    ("en-US", "Turkish", "She said the results would be ready by Friday, not Wednesday.", ["cuma", "çarşamba"]),
    ("en-US", "Turkish", "We can't ship this until the security review is done.", ["güvenlik", "kadar"]),
    ("en-US", "Turkish", "Let's meet next Tuesday at a quarter past three.", ["salı", "üç|15:15|3:15"]),
    ("en-US", "Turkish", "The doctor told him not to drive for two weeks.", ["iki hafta", "mama|meme"]),
    ("ja-JP", "Turkish", "このお店は朝早くから行列ができていて地元の人にもとても人気があるそうです",
     ["sabah", "popüler|sevil|rağbet"]),
    ("ar-SA", "Turkish", "مرحبا بكم في هذه الحلقة الجديدة سنتحدث اليوم عن تاريخ مدينة إسطنبول القديمة",
     ["istanbul", "tarih"]),
    ("en-US", "German", "We decided to move the meeting to next Thursday because half of the team is traveling.",
     ["donnerstag", "hälfte"]),
    ("en-US", "Spanish", "We can't ship the order until next Friday.", ["pedido", "viernes"]),
    ("en-US", "Spanish", "please call me back tomorrow morning at half past nine",
     ["mañana|manana", "nueve"]),
    ("en-US", "Spanish", "The price went up by 20 percent last year.", ["20", "precio", "pasado"]),
    ("en-US", "Spanish", "Anna asked for the report by Wednesday, not Tuesday.",
     ["anna", "miércoles|miercoles", "martes"]),
]


def run(repo):
    import mlx.core as mx
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo)
    t0 = time.time()
    model, tok = _mlx_load(path)
    load_s = time.time() - t0
    provider = LocalTranslationProvider(config={})
    provider._tokenizer = tok
    times, misses = [], 0
    print(f"\n=== {repo}  (load {load_s:.1f}s)")
    for locale, target, text, must in SAMPLES:
        prompt = provider._prompt(text, _language_code(locale), _language_code(target))
        t = time.time()
        out = _clean(_mlx_generate(model, tok, prompt))
        times.append(time.time() - t)
        low = out.replace("İ", "i").replace("I", "ı").lower()
        missing = [w for w in must if not any(alt in low for alt in w.split("|"))]
        misses += bool(missing)
        flag = f"  MISSING {missing}" if missing else ""
        print(f"  [{locale}->{target}] {times[-1]:.2f}s  {out}{flag}")
    warm = times[1:] or times
    peak = mx.get_peak_memory() / 1e9
    print(f"  {len(SAMPLES) - misses}/{len(SAMPLES)} correct  avg {sum(warm)/len(warm):.2f}s"
          f"  max {max(warm):.2f}s  peak mem {peak:.2f} GB")
    mx.clear_cache()
    mx.reset_peak_memory()


if __name__ == "__main__":
    for r in sys.argv[1:]:
        run(r)
