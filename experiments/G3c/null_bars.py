"""Null distribution of the G3c grading statistics, from the pilot's own worksheets. Fixes the bars.

    python null_bars.py --config prereg_config.json --pilot pilot_record/pilot --reps 1000 --out bars_null.json

Why a simulation. All eighteen read-outs (three scales, six read-outs each) are graded on the same
200 test pairs per gap, so one draw of pairs moves all of them together. The pilot showed exactly
this: deviations at gaps 2, 4 and 6 with one sign on every scale and read-out, while the scores
of calibration and test sheets at equal error counts agree (chi-square p near 0.6 on each scale).
A bar computed as if the 126 cells were independent would be wrong in an unknown direction.

The null is "calibration and test are two draws from one population of worksheets". The
population is every pilot worksheet, calibration and test pooled, about 170 per error count.
Each replicate splits each level's pool at random into two disjoint halves, draws a calibration
block (40 per level) from one half and a test block (200 pairs per gap, the better sheet's error
count uniform on what the gap allows) from the other, both with replacement, exactly as the
design draws them. It then predicts and grades with the functions in judge_grade.py, the same
code the sealed run uses, and records the family-wide statistics of that replicate: the largest
absolute deviation and the largest z over all read-outs and gaps, the largest ratio between
observed and predicted threshold, and the Kendall tau. The prediction's bootstrap uses fewer
resamples than the sealed run (--boot), which only affects the z denominator where the
1/(2n) floor does not already bind.

The pilot's own statistics are placed in this distribution, and the proposed bars are its
upper quantiles, stated with the family-wise false-alarm rate per judge.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_grade as jg  # noqa: E402

PERMISSIVE = {"dev_max": 1.0, "z_max": 1e9, "threshold_factor": 1e9, "rank_agreement_min": -1}


def load_pool(pilot: Path, cfg: dict, tag: str) -> tuple[np.ndarray, dict]:
    """Every pilot worksheet with its error count and every read-out on every scale, aligned by sheet."""
    e_ref, R = None, {}
    for block in ("calibration", "test"):
        e_blk = None
        for scale in cfg["scales"]:
            key = f"{scale['lo']}-{scale['hi']}"
            recs = jg.load_scores(pilot / block / tag, key)
            e = np.array([r["e"] for r in recs])
            ids = [r["id"] for r in recs]
            if ids != list(range(len(recs))):
                raise SystemExit(f"{block} {key}: records not in sheet order")
            if e_blk is None:
                e_blk = e
            elif not np.array_equal(e, e_blk):
                raise SystemExit(f"{block} {key}: error counts disagree across scales")
            for name, v in jg.readouts(cfg, scale, recs).items():
                R.setdefault((key, name), []).append(v)
        e_ref = e_blk if e_ref is None else np.concatenate([e_ref, e_blk])
    return e_ref, {k: np.concatenate(v) for k, v in R.items()}


def one_replicate(rng, e, R, cfg, n_boot):
    N, gaps = int(cfg["n_items"]), [int(g) for g in cfg["gap_ladder"]]
    n_cal, n_pairs = int(cfg["n_cal_per_level"]), int(cfg["n_pairs_per_gap"])
    cal_ix, test_pool = [], {}
    for k in range(N + 1):
        ix = rng.permutation(np.where(e == k)[0]); h = len(ix) // 2
        cal_ix.append(rng.choice(ix[:h], size=n_cal, replace=True)); test_pool[k] = ix[h:]
    cal = np.concatenate(cal_ix); e_cal = e[cal]
    good, bad, gap_of = [], [], []
    for g in gaps:
        ks = rng.integers(0, N - g + 1, size=n_pairs)
        good += [rng.choice(test_pool[k]) for k in ks]; bad += [rng.choice(test_pool[k + g]) for k in ks]
        gap_of += [g] * n_pairs
    good, bad, gap_of = np.array(good), np.array(bad), np.array(gap_of)
    by_level = [np.where(e_cal == k)[0] for k in range(N + 1)]
    pred = {"scales": {}}; obs = {"n_per_gap": n_pairs, "scales": {}}
    for (key, name), v in R.items():
        vc = v[cal]
        acc = jg.predicted_curve(vc, e_cal, N, gaps)
        boots = np.empty((n_boot, len(gaps)))
        for b in range(n_boot):
            take = np.concatenate([rng.choice(ix, size=len(ix), replace=True) for ix in by_level])
            boots[b] = jg.predicted_curve(vc[take], e_cal[take], N, gaps)
        entry = pred["scales"].setdefault(key, {"readouts": {}, "nominal_rival": {"acc": [0.0] * len(gaps), "threshold": math.inf},
                                               "codebook": {"n_distinct": 0}})
        entry["readouts"][name] = {"acc": acc.tolist(), "acc_sd": boots.std(0).tolist(), "threshold": jg.threshold(acc, gaps)}
        with np.errstate(invalid="ignore"):
            correct = v[good] > v[bad]
        o = np.array([correct[gap_of == g].mean() for g in gaps])
        obs["scales"].setdefault(key, {})[name] = {"acc": o.tolist(), "threshold": jg.threshold(o, gaps)}
    return summarize(jg.grade(pred, obs, PERMISSIVE))


def summarize(gr: dict) -> dict:
    cells = {k: v for k, v in gr["J1_prediction"].items() if isinstance(v, dict)}
    ratios = [abs(math.log(v["observed_threshold"] / v["predicted_threshold"])) for v in cells.values()
              if math.isfinite(v["observed_threshold"]) and math.isfinite(v["predicted_threshold"])]
    return {"max_abs_dev": max(v["max_abs_dev"] for v in cells.values()),
            "max_z": max(v["max_z"] for v in cells.values()),
            "max_threshold_ratio": float(math.exp(max(ratios))) if ratios else math.inf,
            "kendall_tau": gr["J3_budget_ordering"]["kendall_tau"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--pilot", required=True)
    ap.add_argument("--tag", default="qwen7b__full"); ap.add_argument("--stats", default=None)
    ap.add_argument("--reps", type=int, default=1000); ap.add_argument("--boot", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260920); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    pilot = Path(a.pilot)
    e, R = load_pool(pilot, cfg, a.tag)
    rng = np.random.default_rng(a.seed)
    rows = []
    for i in range(a.reps):
        rows.append(one_replicate(rng, e, R, cfg, a.boot))
        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{a.reps}", flush=True)
    stats = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    q = {k: {f"q{p}": float(np.percentile(v, p)) for p in (50, 90, 95, 99)} for k, v in stats.items()}
    q["kendall_tau"] = {f"q{p}": float(np.percentile(stats["kendall_tau"], p)) for p in (1, 5, 10, 50)}
    report = {"population": {"sheets": int(len(e)), "per_level_min": int(np.bincount(e).min()), "tag": a.tag},
              "reps": a.reps, "boot": a.boot, "seed": a.seed, "quantiles": q}
    sf = Path(a.stats) if a.stats else pilot / "pilot_stats_full.json"
    if sf.exists():
        pilot_stat = summarize(json.load(open(sf))["comparison"])
        report["pilot"] = pilot_stat
        report["pilot_percentile_in_null"] = {k: float((stats[k] <= pilot_stat[k]).mean() * 100) for k in pilot_stat}
    json.dump(report, open(a.out, "w"), indent=1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
