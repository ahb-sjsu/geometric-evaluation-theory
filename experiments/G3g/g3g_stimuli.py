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

# A length budget on the input, the theory's own construct applied to real prose. None means
# the judge reads the whole review; an integer L means it reads the first L characters, cut
# at the last whitespace before L so no word is split. The LABEL is never truncated: the
# reviewer's rating is what it is however much of their argument the judge is allowed to see.
# The prediction under test is that resolution coarsens as L shrinks, in a predicted order.
TRUNCATE = None


def set_truncate(chars) -> None:
    global TRUNCATE
    TRUNCATE = None if chars in (None, 0, 'full', 'none') else int(chars)


def truncate(text: str) -> str:
    if TRUNCATE is None or len(text) <= TRUNCATE:
        return text
    cut = text[:TRUNCATE]
    sp = cut.rfind(' ')
    return (cut[:sp] if sp > TRUNCATE // 2 else cut).rstrip()


POOL_STATS: dict = {}


def load_pool(path: str = DEFAULT_POOL) -> dict:
    """rating -> list of UNIQUE review texts, filtered by length, order fixed by the file.

    Two passes, because the raw sample repeats reviews and the repeats are not harmless.

    A text that appears twice under DIFFERENT ratings has no well-defined label and is dropped
    outright rather than assigned to either level. A text that appears twice under the same rating
    is kept once. Without the first rule the target would be ambiguous; without the second, the
    parity partition below would put the same review in both the calibration and the test half,
    since it splits positions rather than texts. The selftest found exactly that, 176 shared
    reviews, which is why this is two passes and not one.
    """
    global _POOL
    if _POOL:
        return _POOL
    ratings: dict = {}
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
            ratings.setdefault(t, set()).add(r)
    by = {e: [] for e in range(N_ITEMS + 1)}
    ambiguous = 0
    for t, rs in ratings.items():
        if len(rs) != 1:
            ambiguous += 1
            continue
        by[5 - rs.pop()].append(t)
    if min(len(v) for v in by.values()) == 0:
        raise RuntimeError("a rating level is empty; check the pool path")
    POOL_STATS.update({"unique_texts": len(ratings), "dropped_ambiguous": ambiguous,
                       "kept_per_level": {e: len(v) for e, v in by.items()}})
    _POOL = by
    return _POOL


# Which half of each level's pool the current block draws from. Calibration and test MUST be
# disjoint, and they run in separate processes, so shared state cannot enforce it. The pool is
# partitioned by index parity instead, which makes disjointness a property of the data rather
# than of the order in which things happen to run.
_BLOCK = "calibration"
_HALF = {"calibration": 0, "test": 1, "probe": 0, "pilot_calibration": 0, "pilot_test": 1}


def set_block(block: str) -> None:
    global _BLOCK
    if block not in _HALF:
        raise ValueError("unknown block %r" % block)
    _BLOCK = block


def half_for(e: int, block: str | None = None) -> list:
    """The reviews this block may draw at level e. Parity partition, fixed by the file order."""
    return load_pool()[e][_HALF[block or _BLOCK]::2]


def make_review(rng: np.random.Generator, n_items: int, e: int) -> dict:
    """Drop-in for judge.make_worksheet. Same signature, same returned keys.

    Draws without replacement within a block, and only from that block's half of the pool, so no
    review is scored twice and a calibration review can never reach a test block.
    """
    if n_items != N_ITEMS:
        raise ValueError("this family fixes n_items at %d" % N_ITEMS)
    avail = half_for(e)
    used = _USED.setdefault((_BLOCK, e), set())
    if len(used) >= len(avail):
        raise RuntimeError("level %d exhausted in block %s" % (e, _BLOCK))
    for _ in range(100000):
        i = int(rng.integers(len(avail)))
        if i not in used:
            used.add(i)
            return {"e": int(e), "text": truncate(avail[i])}
    raise RuntimeError("level %d could not find an unused review in block %s" % (e, _BLOCK))


_USED: dict = {}


def reset_draws() -> None:
    """Clear the without-replacement state. The runner calls this once per block."""
    _USED.clear()


def selftest(pool_path: str = DEFAULT_POOL) -> int:
    pool = load_pool(pool_path)
    print("pool loaded: %d unique texts, %d dropped for carrying more than one rating"
          % (POOL_STATS["unique_texts"], POOL_STATS["dropped_ambiguous"]))
    print("usable reviews per error count e (e = 5 - rating):")
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

    # The property the design rests on: a calibration review can never reach a test block.
    overlap = 0
    for e in range(N_ITEMS + 1):
        c = set(half_for(e, "calibration"))
        t = set(half_for(e, "test"))
        overlap += len(c & t)
        if not c or not t:
            print("FAIL: an empty half at e=%d" % e)
            return 1
    print("calibration and test halves are disjoint at every level, shared reviews: %d" % overlap)
    if overlap:
        return 1

    # And the halves are drawn from, not merely defined.
    reset_draws(); set_block("calibration")
    a = {make_review(np.random.default_rng(1), N_ITEMS, 2)["text"] for _ in range(200)}
    reset_draws(); set_block("test")
    b = {make_review(np.random.default_rng(1), N_ITEMS, 2)["text"] for _ in range(200)}
    print("drawn calibration and test sets at e=2 share %d reviews" % len(a & b))
    if a & b:
        return 1
    reset_draws(); set_block("calibration")
    lo = next(t for t in texts if t["e"] == 0)
    hi = next(t for t in texts if t["e"] == 4)
    print("\nexample e=0 (reviewer gave 5 stars), quality 1.00:\n  %s" % lo["text"][:240].replace("\n", " "))
    print("\nexample e=4 (reviewer gave 1 star), quality 0.00:\n  %s" % hi["text"][:240].replace("\n", " "))
    return 0


if __name__ == "__main__":
    p = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_POOL
    raise SystemExit(selftest(p))
