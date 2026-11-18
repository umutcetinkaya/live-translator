"""Benchmark candidate on-device translation models.

Measures load time, per-segment latency, peak memory and prints the
translations so quality can be judged side by side. Not a test: it downloads
models and needs Apple Silicon.

    .venv/bin/python scripts/bench_local_models.py mlx-community/Qwen3-4B-Instruct-2507-4bit ...
"""

import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from providers.base import SEGMENT_SYSTEM_PROMPT, build_segment_prompt  # noqa: E402

# (source language, target language, context, segment). Segments are ~18
# words, the size the segmenter cuts unpunctuated speech into.
SAMPLES = [
    ("English", "Turkish", "Today we are looking at how large language models work.",
     "and the first thing you need to understand is that they predict the next word based on everything before it"),
    ("English", "Turkish", "",
     "if you have ever wondered why your phone battery dies so fast in the winter this video is for you"),
    ("Japanese", "Turkish", "今日は東京の有名なラーメン屋に来ています。",
     "このお店は朝早くから行列ができていて地元の人にもとても人気があるそうです"),
    ("Arabic", "Turkish", "",
     "مرحبا بكم في هذه الحلقة الجديدة سنتحدث اليوم عن تاريخ مدينة إسطنبول القديمة وأهم معالمها"),
    ("English", "German", "",
     "we decided to move the meeting to next Thursday because half of the team is traveling this week"),
    ("English", "Japanese", "",
     "the weather was terrible all weekend so we stayed home and watched old movies together"),
]

_THINK = re.compile(r"<think>.*?</think>", re.S)


def run(repo):
    import mlx.core as mx
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler

    t0 = time.time()
    model, tok = load(repo)
    load_s = time.time() - t0
    sampler = make_sampler(temp=0.2)
    times = []
    print(f"\n=== {repo}  (load {load_s:.1f}s)")
    for src, tgt, ctx, seg in SAMPLES:
        msgs = [{"role": "system", "content": SEGMENT_SYSTEM_PROMPT},
                {"role": "user", "content": build_segment_prompt(seg, ctx, tgt)}]
        try:
            prompt = tok.apply_chat_template(msgs, add_generation_prompt=True,
                                             enable_thinking=False)
        except TypeError:
            prompt = tok.apply_chat_template(msgs, add_generation_prompt=True)
        t = time.time()
        out = generate(model, tok, prompt=prompt, max_tokens=250, sampler=sampler)
        dt = time.time() - t
        times.append(dt)
        out = _THINK.sub("", out).strip()
        print(f"  [{src}->{tgt}] {dt:.2f}s  {out}")
    peak = mx.get_peak_memory() / 1e9
    print(f"  avg {sum(times)/len(times):.2f}s  max {max(times):.2f}s  peak mem {peak:.2f} GB")
    mx.clear_cache()
    mx.reset_peak_memory()


if __name__ == "__main__":
    for r in sys.argv[1:]:
        run(r)
