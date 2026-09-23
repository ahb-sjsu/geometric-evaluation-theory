#!/usr/bin/env python3
"""G3g stimuli: real book reviews, whose quality label is what the reviewer actually did.

G3c and G3e graded arithmetic worksheets. G3f graded summaries against a passage, which is a
harder judgement but still text this campaign generated. Both keep quality exact by construction,
and the standing objection is that neither is a human judgement rendered in real prose.

This family answers that without giving up exactness, by changing what quality MEANS.

The target is not the true quality of the book, which nobody knows and readers dispute. It is the
star rating THIS reviewer gave, which is a recorded fact. So the label is

  * exactly known, because it is what the person did rather than an estimate of anything;
  * a human judgement, rendered by that person in their own prose;
  * genuinely hard to recover, because sarcasm, mixed opinions and faint praise are the norm.

There is no annotator noise term because there is no second annotator to disagree. The judge's
task is to read the review and say what the writer scored the book, which is a deployed use of
LLM judges and not a proxy for one.

Quality is mapped onto the harness's existing scale so nothing downstream changes. A rating `r` in
1..5 becomes an error count `e = 5 - r` in 0..4 with `n_items = 4`, so quality is `1 - e/4`, the
block builder's `range(N + 1)` loop covers every level, and the gap ladder runs 1 to 4.

    python g3g_stimuli.py selftest
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Balanced 40k-per-star sample of Goodreads reviews, already stratified.
DEFAULT_POOL = "/archive/results_aesthetics/bip_sample_200k.jsonl"

N_ITEMS = 4          # e = 5 - rating, so e in 0..4 and quality = 1 - e/4
MIN_CHARS = 400      # long enough to carry an opinion
MAX_CHARS = 3000     # short enough to keep the prompt affordable

_POOL: dict = {}


def load_pool(path: str = DEFAULT_POOL) -> dict:
    """rating -> list of review texts, filtered by length, order fixed by the file."""
    global _POOL
    if _POOL:
        return _POOL
    by = {e: [] for e in range(N_ITEMS + 1)}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            r, t = d.get("rating"), (d.get("text") or "").strip()
            if not isinstance(r, int) or not (1 <= r <= 5):
                continue
            if not (MIN_CHARS <= len(t) <= MAX_CHARS):
                continue
            if "\x00" in t:
                continue
            by[5 - r].append(t)
    if min(len(v) for v in by.values()) == 0:
        raise RuntimeError("a rating level is empty; check the pool path")
    _POOL = by
    return _POOL


def make_review(rng: np.random.Generator, n_items: int, e: int) -> dict:
    """Drop-in for judge.make_worksheet. Same signature, same returned keys.

    Draws WITHOUT replacement within a run, so no review is ever scored twice and a calibration
    review can never reappear in a test block.
    """
    pool = load_pool()
    if n_items != N_ITEMS:
        raise ValueError("this family fixes n_items at %d" % N_ITEMS)
    used = _USED.setdefault(e, set())
    avail = pool[e]
    for _ in range(10000):
        i = int(rng.integers(len(avail)))
        if i not in used:
            used.add(i)
            return {"e": int(e), "text": avail[i]}
    raise RuntimeError("level %d exhausted after 10000 draws" % e)


_USED: dict = {}


def reset_draws() -> None:
    """Clear the without-replacement state. The runner calls this once per block."""
    _USED.clear()


def selftest(pool_path: str = DEFAULT_POOL) -> int:
    pool = load_pool(pool_path)
    print("pool loaded, usable reviews per error count e (e = 5 - rating):")
    for e in sorted(pool):
        print("  e=%d  rating=%d  %6d reviews" % (e, 5 - e, len(pool[e])))
    smallest = min(len(v) for v in pool.values())

    reset_draws()
    rng = np.random.default_rng(20260923)
    seen, texts = set(), []
    for e in range(N_ITEMS + 1):
        for _ in range(400):
            s = make_review(rng, N_ITEMS, e)
            if s["e"] != e:
                print("FAIL: asked e=%d got %d" % (e, s["e"]))
                return 1
            if not (MIN_CHARS <= len(s["text"]) <= MAX_CHARS):
                print("FAIL: length out of band at e=%d" % e)
                return 1
            if s["text"] in seen:
                print("FAIL: a review was drawn twice")
                return 1
            seen.add(s["text"])
            texts.append(s)
    print("\nselftest ok: %d stimuli over 5 levels, none repeated, all within the length band"
          % len(seen))
    print("smallest level supports %d draws, the blocks need far fewer" % smallest)
    lo = next(t for t in texts if t["e"] == 0)
    hi = next(t for t in texts if t["e"] == 4)
    print("\nexample e=0 (reviewer gave 5 stars), quality 1.00:\n  %s" % lo["text"][:240].replace("\n", " "))
    print("\nexample e=4 (reviewer gave 1 star), quality 0.00:\n  %s" % hi["text"][:240].replace("\n", " "))
    return 0


if __name__ == "__main__":
    p = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_POOL
    raise SystemExit(selftest(p))
