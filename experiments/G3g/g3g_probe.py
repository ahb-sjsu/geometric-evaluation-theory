#!/usr/bin/env python3
"""G3g probe. Run before the registration is written, on a probe seed no graded block uses.

It answers the question that decides whether this family is worth a gate: can a judge recover the
rating a reviewer gave, from the review alone? Recovering a stranger's star rating from prose is
genuinely hard, and unlike arithmetic there is no guarantee any judge clears the anti-vacuity bar.
Knowing that before the registration is written is what sizes the gate honestly.

    python g3g_probe.py --config g3g_config.json --models gemma31b gemma12b --per-level 30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
for _c in ("G3c", "g3c"):
    if (_HERE.parent / _c / "judge.py").exists():
        sys.path.insert(0, str(_HERE.parent / _c))
        break
for _c in ("G3e", "g3e"):
    if (_HERE.parent / _c / "api_judge.py").exists():
        sys.path.insert(0, str(_HERE.parent / _c))
        break

import api_judge as A  # noqa: E402
import judge as J  # noqa: E402

import g3g_stimuli as S  # noqa: E402

N = S.N_ITEMS


def bits_about_quality(scores: np.ndarray, e: np.ndarray) -> float:
    """Mutual information between the greedy score and a two-class split of quality, the
    quantity the anti-vacuity bar is stated in. With five levels the split is e<=1 against e>=3."""
    good, bad = e <= 1, e >= 3
    keep = good | bad
    s, y = scores[keep], good[keep]
    h = lambda p: 0.0 if p <= 0 or p >= 1 else -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    base = h(float(y.mean()))
    tot = 0.0
    for v in np.unique(s[~np.isnan(s)]):
        m = s == v
        tot += m.mean() * h(float(y[m].mean()))
    return float(base - tot)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--per-level", type=int, default=30)
    ap.add_argument("--out", default="probe")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    cfg["_role"] = "probe"

    S.reset_draws()
    rng = np.random.default_rng(int(cfg["seeds"]["probe"]))
    sheets = [S.make_review(rng, N, e) for e in range(N + 1) for _ in range(a.per_level)]
    texts = [s["text"] for s in sheets]
    e = np.array([s["e"] for s in sheets])
    print("probe block: %d reviews, %d at each of %d levels\n" % (len(texts), a.per_level, N + 1))

    spec = {m["key"]: m for m in cfg["models"]}
    for key in a.models:
        d = Path(a.out) / key
        d.mkdir(parents=True, exist_ok=True)
        judge = A.APIJudge(spec[key], "served", cfg, cache_path=d / "api_cache.jsonl")
        for scale in cfg["scales"]:
            sk = "%d-%d" % (scale["lo"], scale["hi"])
            recs = judge.score(texts, scale, 0, 1.0, int(cfg["batch"]))
            g = np.array([r["argmax"] for r in recs], float)
            ok = ~np.isnan(g)
            # accuracy at the largest gap, cross pairs of e=0 against e=N
            lo, hi = g[(e == 0) & ok], g[(e == N) & ok]
            acc = float(np.mean([[1.0 if x > y else (0.5 if x == y else 0.0) for y in hi]
                                 for x in lo])) if len(lo) and len(hi) else float("nan")
            book = sorted(set(int(v) for v in g[ok]))
            # does the mean score fall monotonically with e?
            means = [float(np.nanmean(g[e == k])) for k in range(N + 1)]
            print("%-10s %-6s scores_used=%-3d acc_at_gap_%d=%.3f bits=%.3f unparsed=%d"
                  % (key, sk, len(book), N, acc, bits_about_quality(g, e), int((~ok).sum())))
            print("%-10s %-6s mean greedy score by level e=0..%d: %s"
                  % ("", "", N, " ".join("%.2f" % m for m in means)))
        judge.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
