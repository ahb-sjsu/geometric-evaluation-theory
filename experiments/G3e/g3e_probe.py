#!/usr/bin/env python3
"""G3e event-presence probe. Runs BEFORE the registration is sealed, on worksheets drawn from a
probe seed that no graded block uses.

It answers the three questions a registration has to answer before it is written.

  presence   does the judge's score fall with the error count at all, and does it clear the
             anti-vacuity bar G3c sets? A judge that cannot order worksheets twelve errors apart
             is reported and not graded, and knowing that in advance sizes the gate honestly.
  cost       how many requests and how many seconds a worksheet costs on each scale, so the
             registration can state the load it will put on a shared service.
  reading    how much mass the twenty-token wall hides, whether the digit tree stays small, and
             whether both answer letters are visible in the pairwise prompt.

    python g3e_probe.py --config g3e_config.json --models gemma31b gemma12b qwen3_27b --out probe
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

LEVELS = (0, 2, 5, 8, 12, 16, 20)


def bits_about_quality(scores: np.ndarray, e: np.ndarray) -> float:
    """Mutual information between the judge's greedy score and a two-class split of quality,
    the quantity G3c's anti-vacuity bar is stated in."""
    good = e <= 4
    bad = e >= 16
    keep = good | bad
    s, y = scores[keep], good[keep]
    h = lambda p: 0.0 if p <= 0 or p >= 1 else -(p * np.log2(p) + (1 - p) * np.log2(1 - p))
    base = h(float(y.mean()))
    tot = 0.0
    for v in np.unique(s[~np.isnan(s)]):
        m = s == v
        tot += (m.mean()) * h(float(y[m].mean()))
    return float(base - tot)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--per-level", type=int, default=6)
    ap.add_argument("--out", default="probe")
    ap.add_argument("--tree-prune", type=float, help="override, to measure what a coarser tree costs")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    if a.tree_prune is not None:
        cfg["tree_prune"] = a.tree_prune
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    specs = {m["key"]: m for m in cfg["models"]}

    rng = np.random.default_rng([int(cfg["seeds"]["probe"]), 99])
    sheets = [J.make_worksheet(rng, int(cfg["n_items"]), e) for e in LEVELS for _ in range(a.per_level)]
    texts = [s["text"] for s in sheets]
    e = np.array([s["e"] for s in sheets], float)
    # pairs twelve errors apart, the anti-vacuity gap
    lo = [s for s in sheets if s["e"] <= 4][: a.per_level]
    hi = [s for s in sheets if s["e"] >= 16][: a.per_level]

    report = {"probe_seed": cfg["seeds"]["probe"], "sheets": len(sheets), "levels": list(LEVELS),
              "tree_prune": cfg["tree_prune"], "models": {}}
    for key in a.models:
        rec = {"model_id": specs[key]["model_id"], "expected": specs[key].get("served_as"), "scales": {}}
        d = out / key; d.mkdir(parents=True, exist_ok=True)
        judge = A.APIJudge(specs[key], "served", cfg, cache_path=d / "api_cache.jsonl")
        rec["served_as"] = judge.served
        for scale in cfg["scales"]:
            k = f"{scale['lo']}-{scale['hi']}"
            n0, m0, t0 = judge.n_requests, judge.n_asks, time.time()
            recs = judge.score(texts, scale, 0, 1.0, int(cfg["batch"]))
            dt, dn, dm = time.time() - t0, judge.n_requests - n0, judge.n_asks - m0
            arg = np.array([r["argmax"] for r in recs], float)
            ok = ~np.isnan(arg)
            order = float(np.corrcoef(arg[ok], -e[ok])[0, 1]) if ok.sum() > 2 and len(set(arg[ok])) > 1 else float("nan")
            acc = float(np.mean([arg[i] > arg[j] for i in range(len(arg)) for j in range(len(arg))
                                 if e[j] - e[i] == 12 and ok[i] and ok[j]] or [np.nan]))
            s = {"requests": dn, "asks": dm, "seconds": round(dt, 1), "asks_per_sheet": round(dm / len(texts), 2),
                 "requests_per_sheet": round(dn / len(texts), 2),
                 "seconds_per_sheet": round(dt / len(texts), 3),
                 "distinct_scores": int(len(set(arg[ok].tolist()))), "unparsed": int((~ok).sum()),
                 "rank_correlation_with_quality": None if order != order else round(order, 3),
                 "accuracy_at_gap_12": None if acc != acc else round(acc, 3),
                 "bits_about_quality": round(bits_about_quality(arg, e), 3),
                 "mean_mass_on_codebook": round(float(np.mean([r["mass_on_codebook"] for r in recs])), 5),
                 "max_unseen": round(float(max(r.get("unseen_mass", r.get("tree_unseen_bound", 0.0)) for r in recs)), 6),
                 "scores_by_error_count": {str(int(x)): sorted({float(v) for v, y in zip(arg, e) if y == x})
                                           for x in LEVELS}}
            if "tree_invalid_mass" in recs[0]:
                s["max_tree_invalid"] = round(float(max(r["tree_invalid_mass"] for r in recs)), 6)
                s["max_tree_pruned"] = round(float(max(r["tree_pruned_mass"] for r in recs)), 8)
            rec["scales"][k] = s
            print(key, k, json.dumps({q: s[q] for q in ("asks_per_sheet", "requests_per_sheet", "seconds_per_sheet",
                                                        "distinct_scores", "accuracy_at_gap_12", "bits_about_quality",
                                                        "max_unseen")}), flush=True)
        n0, t0 = judge.n_requests, time.time()
        p = judge.pairwise([x["text"] for x in lo], [y["text"] for y in hi], int(cfg["batch_pairwise"]))
        q = judge.pairwise([y["text"] for y in hi], [x["text"] for x in lo], int(cfg["batch_pairwise"]))
        pa = 0.5 * (np.array(p) + 1 - np.array(q))
        rec["pairwise"] = {"requests": judge.n_requests - n0, "seconds": round(time.time() - t0, 1),
                           "order_averaged_accuracy_at_gap_12_plus": round(float(np.mean(pa > 0.5)), 3),
                           "first_position_preference": round(float(np.mean(np.array(p) > 0.5)), 3),
                           "unreadable": int(np.isnan(np.array(p)).sum() + np.isnan(np.array(q)).sum())}
        print(key, "pairwise", json.dumps(rec["pairwise"]), flush=True)
        rec["total_requests"] = judge.n_requests
        judge.close()
        report["models"][key] = rec
    json.dump(report, open(out / "probe.json", "w"), indent=1, default=float)
    print("wrote", out / "probe.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
