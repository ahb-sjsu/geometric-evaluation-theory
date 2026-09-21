#!/usr/bin/env python3
"""Would a longer worksheet uncensor the judge the ladder could not resolve?

G3e's gap ladder is 1 to 12 wrong answers out of twenty, so its finest step is a quality gap of
0.05. Seven of `gemma31b`'s eighteen read-outs were already past the 0.75 crossing at the first
rung, so their thresholds were reported at the floor rather than measured, and read-outs tied there
cannot be ranked, which is why C3e failed.

A worksheet of a hundred items makes one wrong answer a quality gap of 0.01, so the same integer
ladder becomes five times finer without changing the estimator or any bar. This probe asks whether
that is enough, and what it would cost, before anything is registered. It measures:

  uncensoring   the share of pairs one item apart that each read-out orders correctly. Below 0.75
                means the threshold would be measured rather than censored.
  the codebook  how many distinct scores the judge uses inside the narrow quality band a hundred
                items and at most twenty wrong answers allows. Narrowing the band could make the
                greedy read-out coarser, which would be a cost of the fix and not a benefit.
  the bill      prompt length, requests and seconds per worksheet.

Exploratory. It is run on a probe seed, tests nothing, and grades nothing.

    python longsheet_probe.py --config g3e_config.json --models gemma31b gemma12b --out longsheet
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import api_judge as A  # noqa: E402
import judge as J  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--items", type=int, default=100)
    ap.add_argument("--pairs", type=int, default=30, help="pairs per gap")
    ap.add_argument("--gaps", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--out", default="longsheet")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    cfg = {**cfg, "n_items": a.items}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    specs = {m["key"]: m for m in cfg["models"]}

    rng = np.random.default_rng([20260921, a.items])
    sheets, pairs = [], []
    for gap in a.gaps:
        for _ in range(a.pairs):
            e_good = int(rng.integers(0, 20 - gap + 1))     # the band a contiguous calibration allows
            g = J.make_worksheet(rng, a.items, e_good); g["id"] = len(sheets); sheets.append(g)
            b = J.make_worksheet(rng, a.items, e_good + gap); b["id"] = len(sheets); sheets.append(b)
            pairs.append({"gap": gap, "good": g["id"], "bad": b["id"]})
    texts = [s["text"] for s in sheets]
    chars = int(np.mean([len(t) for t in texts]))
    report = {"exploratory": True, "n_items": a.items, "gaps": a.gaps, "pairs_per_gap": a.pairs,
              "sheets": len(sheets), "mean_sheet_chars": chars, "error_counts_band": [0, 20],
              "models": {}}
    print("worksheets of %d items, %d sheets, mean %d characters each" % (a.items, len(sheets), chars))

    for key in a.models:
        rec = {"scales": {}}
        d = out / key; d.mkdir(parents=True, exist_ok=True)
        judge = A.APIJudge(specs[key], "served", cfg, cache_path=d / "api_cache.jsonl")
        rec["served_as"] = judge.served
        for scale in cfg["scales"]:
            k = f"{scale['lo']}-{scale['hi']}"
            n0, m0, t0 = judge.n_requests, judge.n_asks, time.time()
            recs = judge.score(texts, scale, 8, 1.0, int(cfg["batch"]))
            dt, dn, dm = time.time() - t0, judge.n_requests - n0, judge.n_asks - m0
            grid = np.arange(scale["lo"], scale["hi"] + 1, dtype=float)
            vals = {"argmax": np.array([r["argmax"] for r in recs], float),
                    "expected": np.array([float(np.dot(grid, r["p"])) for r in recs]),
                    "mean_8": np.array([float(np.mean(r["samples"])) for r in recs])}
            s = {"requests": dn, "asks": dm, "seconds": round(dt, 1),
                 "asks_per_sheet": round(dm / len(texts), 2), "seconds_per_sheet": round(dt / len(texts), 3),
                 "distinct_greedy_scores_in_band": int(len({v for v in vals["argmax"] if v == v})),
                 "unparsed": int(sum(1 for v in vals["argmax"] if v != v)),
                 "max_unseen": round(float(max(r.get("unseen_mass", r.get("tree_unseen_bound", 0.0)) for r in recs)), 6),
                 "accuracy_by_gap": {}}
            for name, v in vals.items():
                acc = {}
                for gap in a.gaps:
                    sel = [p for p in pairs if p["gap"] == gap]
                    ok = [1.0 if v[p["good"]] > v[p["bad"]] else 0.0 for p in sel
                          if v[p["good"]] == v[p["good"]] and v[p["bad"]] == v[p["bad"]]]
                    acc[gap] = round(float(np.mean(ok)), 3) if ok else None
                s["accuracy_by_gap"][name] = acc
            rec["scales"][k] = s
            cens = {n: ("censored" if (v.get(a.gaps[0]) or 0) >= 0.75 else "measurable")
                    for n, v in s["accuracy_by_gap"].items()}
            print("%-10s %-6s acc@gap1 %s | %s | %d scores in band | %.2f asks/sheet, %.2f s/sheet"
                  % (key, k, {n: v.get(a.gaps[0]) for n, v in s["accuracy_by_gap"].items()}, cens,
                     s["distinct_greedy_scores_in_band"], s["asks_per_sheet"], s["seconds_per_sheet"]), flush=True)
        rec["total_requests"] = judge.n_requests
        judge.close()
        report["models"][key] = rec
    json.dump(report, open(out / "longsheet_probe.json", "w"), indent=1, default=float)
    print("wrote", out / "longsheet_probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
