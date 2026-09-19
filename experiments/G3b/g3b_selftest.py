"""G3b self-test, PREREG-G3B Section 7 item 1. No GPU.

Part 1, the pipeline end to end. Synthetic judges of known structure are run through the real
harness (g3b.run_cells, the same code path as a language model) and graded by the real grader.

  synth_char    exact evaluator, one character per token, weights at full, int8, int4 with a
                per-report garble of 0, 0, 0.03. Must PASS 11b on both tasks and 11c, with a
                positive lapse difference at 4-bit.
  synth_group3  exact evaluator whose tokenizer groups up to three digits, like Llama-3. Must
                PASS 11d graded with its own report grid, and must FAIL 11b when graded with the
                one-character grid, which is the check that a wrong grid is caught.
  synth_coarse  resolves twice the step it is shown, at every rendering. Must FAIL 11b, which is
                the check that the grid law rejects a judge it does not describe above its floor.
  synth_noise   Gaussian noise of sd 0.02 on the consequence. Its noise is a floor: the fitted
                floor must sit between one and four noise standard deviations, and above three
                times the floor the law must not fail. (A first version of this self-test
                expected FAIL here, which was wrong: noise below the graded grids is a floor.)

Part 2, the estimator. For steps 0.01, 0.1 and 1 and per-report garbles 0, 0.03 and 0.1, repeated
seeds: the mean fitted step within 3 percent of the true step, the mean fitted lapse within 0.01
of the true lapse (measured on a large run of the same synthetic judge), and the bootstrap
interval covering the true step at a rate between 0.85 and 0.995.

Everything the checks saw is written to the output directory (Rule 8).

    python g3b_selftest.py --out selftest
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3b  # noqa: E402
import g3b_grade  # noqa: E402

BASE = json.load(open(Path(__file__).resolve().parent / "prereg_config.json"))

SELFTEST_BARS = {"anti_vacuity_acc_gap20": 0.95, "floor_max": 0.3, "h_ratio_factor": 1.5,
                 "law_max_abs_dev": 0.12, "weights_step_factor": 1.5, "delta_min_factor": 1.6,
                 "p3_min_acc": 0.9, "p3_min_gaps": 3}


def synthetic_config(seed: int) -> dict:
    cfg = copy.deepcopy(BASE)
    cfg["models"] = [
        {"key": "synth_char", "model_id": "synthetic:char", "precisions": ["full", "int8", "int4"], "tasks": ["A", "B"],
         "synthetic": {"kind": "exact", "tokenizer": "char", "garble": {"full": 0.0, "int8": 0.0, "int4": 0.03}, "seed": 1}},
        {"key": "synth_group3", "model_id": "synthetic:group3", "precisions": ["full"], "tasks": ["A"],
         "report_grid": {str(k): v for k, v in g3b.afforded_steps(g3b.split_group3("27.375"), BASE["report_token_budgets"]).items()},
         "synthetic": {"kind": "exact", "tokenizer": "group3", "garble": {"full": 0.0}, "seed": 2}},
        {"key": "synth_noise", "model_id": "synthetic:noise", "precisions": ["full"], "tasks": ["A"],
         "synthetic": {"kind": "noise", "noise_sd": 0.02, "tokenizer": "char", "garble": {"full": 0.0}, "seed": 3}},
        {"key": "synth_coarse", "model_id": "synthetic:coarse", "precisions": ["full"], "tasks": ["A"],
         "synthetic": {"kind": "coarse", "coarsen": 2.0, "tokenizer": "char", "garble": {"full": 0.0}, "seed": 4}},
    ]
    cfg["seeds"] = {"probe": seed, "pilot": seed, "run": seed}
    cfg["bars"] = dict(SELFTEST_BARS)
    return cfg


def part1(out: Path, seed: int, n_boot: int) -> tuple[list[dict], dict]:
    cfg = synthetic_config(seed)
    rdir = out / "pipeline"
    ids = [c["id"] for c in g3b.generation_cells(cfg)]
    t0 = time.time()
    g3b.run_cells(cfg, "run", ids, str(rdir))
    res = json.load(open(rdir / "results.json"))
    res["config"] = cfg
    json.dump(res, open(rdir / "results.json", "w"), indent=1)
    A = g3b_grade.analyse(res, cfg, str(rdir), n_boot=n_boot)
    V = g3b_grade.verdicts(A, cfg, cfg["bars"])
    # the same group3 judge graded with the one-character grid
    cfg_wrong = copy.deepcopy(cfg)
    for m in cfg_wrong["models"]:
        if m["key"] == "synth_group3":
            m["report_grid"] = {str(k): v for k, v in g3b.afforded_steps(g3b.split_char("27.375"), cfg["report_token_budgets"]).items()}
    A_w = g3b_grade.analyse(res, cfg_wrong, str(rdir), n_boot=n_boot)
    V_w = g3b_grade.verdicts(A_w, cfg_wrong, cfg_wrong["bars"])
    json.dump({"verdicts": V, "verdicts_wrong_grid": V_w, "cells": g3b_grade.table(A), "seconds": round(time.time() - t0, 1)},
              open(out / "part1_grade.json", "w"), indent=1, default=float)
    checks = [
        {"check": "synth_char A: 11b PASS", "pass": V["GET-11b"].get("synth_char/A", {}).get("verdict") == "PASS",
         "detail": V["GET-11b"].get("synth_char/A", {}).get("verdict")},
        {"check": "synth_char B: 11b PASS", "pass": V["GET-11b"].get("synth_char/B", {}).get("verdict") == "PASS",
         "detail": V["GET-11b"].get("synth_char/B", {}).get("verdict")},
        {"check": "synth_char: 11c PASS (step unchanged under weights)", "pass": V["GET-11c"].get("synth_char", {}).get("verdict") == "PASS",
         "detail": V["GET-11c"].get("synth_char", {}).get("verdict")},
        {"check": "synth_char int4: lapse difference interval above zero",
         "pass": all(r["lapse_diff_ci"][0] > 0 for k, r in V["GET-11c"].get("synth_char", {}).get("cells", {}).items() if "__int4__" in k),
         "detail": {k: r["lapse_diff_ci"] for k, r in V["GET-11c"].get("synth_char", {}).get("cells", {}).items()}},
        {"check": "synth_group3: 11d PASS with its own grid", "pass": V["GET-11d"].get("synth_group3", {}).get("verdict") == "PASS",
         "detail": V["GET-11d"].get("synth_group3", {}).get("verdict")},
        {"check": "synth_group3 graded with the one-character grid: 11b FAIL (I0)",
         "pass": V_w["GET-11b"].get("synth_group3/A", {}).get("verdict") == "FAIL",
         "detail": V_w["GET-11b"].get("synth_group3/A", {}).get("verdict")},
        {"check": "synth_coarse: 11b FAIL (I0)", "pass": V["GET-11b"].get("synth_coarse/A", {}).get("verdict") == "FAIL",
         "detail": V["GET-11b"].get("synth_coarse/A", {}).get("verdict")},
        {"check": "synth_noise: floor between 1 and 4 noise sd",
         "pass": 0.02 <= V["anti_vacuity"].get("synth_noise/A", {}).get("floor", 0) <= 0.08,
         "detail": V["anti_vacuity"].get("synth_noise/A", {}).get("floor")},
        {"check": "synth_noise: 11b not FAIL above its floor", "pass": V["GET-11b"].get("synth_noise/A", {}).get("verdict") in ("PASS", "INDETERMINATE"),
         "detail": V["GET-11b"].get("synth_noise/A", {}).get("verdict")},
    ]
    return checks, V


def simulate_curves(cfg: dict, seed: int, k: int, garble: float, n_rep_seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Correct-flags per pair for an exact char-token judge at 3 decimals truncated to k tokens."""
    spec = {"model_id": "synthetic:char", "synthetic": {"kind": "exact", "tokenizer": "char",
                                                        "garble": {"full": garble}, "seed": n_rep_seed}}
    judge = g3b.SyntheticScorer(spec, "full", cfg)
    pairs = g3b.make_pairs(cfg, "A", seed)
    tstr = g3b.render_target(cfg, "A", 3)
    vals = list(dict.fromkeys(g3b.render_value("A", p[s], 3) for p in pairs for s in ("close", "far")))
    gens = {g["value"]: g for g in judge.generate("A", tstr, vals, 12, [k])}
    a = np.array([g3b.parse_report(gens[g3b.render_value("A", p["close"], 3)]["prefix"][str(k)]) for p in pairs])
    b = np.array([g3b.parse_report(gens[g3b.render_value("A", p["far"], 3)]["prefix"][str(k)]) for p in pairs])
    correct = (a < b) & ~np.isnan(a) & ~np.isnan(b)
    return correct, np.array([p["gap"] for p in pairs])


def part2(out: Path, n_seeds: int, n_boot: int) -> list[dict]:
    cfg = copy.deepcopy(BASE)
    gaps = np.array(sorted(float(g) for g in cfg["gap_ladder"]))
    k_for = {1.0: 2, 0.1: 4, 0.01: 5}
    checks, record = [], []
    rng = np.random.default_rng(7)
    for h, k in k_for.items():
        for garble in (0.0, 0.03, 0.1):
            big = copy.deepcopy(cfg); big["n_pairs_per_gap"] = 4000
            cb, gb = simulate_curves(big, 999, k, garble, 5)
            acc_big = np.array([cb[gb == x].mean() for x in gaps])
            lam_true = 1.0 - float(acc_big[gaps >= 2 * h].mean())
            hs, lams, cover = [], [], 0
            for s in range(n_seeds):
                c, g = simulate_curves(cfg, 1000 + s, k, garble, 5)
                acc = np.array([c[g == x].mean() for x in gaps])
                f = g3b_grade.fit_curves(acc[None, :], gaps)
                hs.append(float(f["h"][0])); lams.append(1.0 - float(f["c1"][0]))
                B = np.empty((n_boot, len(gaps)))
                for gi, x in enumerate(gaps):
                    rows = c[g == x]
                    B[:, gi] = rows[rng.integers(0, len(rows), size=(n_boot, len(rows)))].mean(1)
                fb = g3b_grade.fit_curves(B, gaps)["h"]
                lo, hi = np.percentile(fb, 2.5), np.percentile(fb, 97.5)
                cover += int(lo <= h <= hi)
            rec = {"h": h, "k": k, "garble": garble, "lapse_true": lam_true,
                   "mean_ratio": float(np.mean(hs) / h), "mean_lapse": float(np.mean(lams)),
                   "coverage": cover / n_seeds, "n_seeds": n_seeds, "h_hats": hs, "lapses": lams}
            record.append(rec)
            checks.append({"check": f"h={h} garble={garble}: mean step within 3%", "pass": abs(rec["mean_ratio"] - 1) <= 0.03,
                           "detail": round(rec["mean_ratio"], 4)})
            checks.append({"check": f"h={h} garble={garble}: mean lapse within 0.01 of true", "pass": abs(rec["mean_lapse"] - lam_true) <= 0.01,
                           "detail": {"fit": round(rec["mean_lapse"], 4), "true": round(lam_true, 4)}})
            checks.append({"check": f"h={h} garble={garble}: interval coverage in [0.85, 0.995]", "pass": 0.85 <= rec["coverage"] <= 0.995,
                           "detail": rec["coverage"]})
            print(json.dumps({k2: rec[k2] for k2 in ("h", "garble", "lapse_true", "mean_ratio", "mean_lapse", "coverage")}), flush=True)
    json.dump(record, open(out / "part2_estimator.json", "w"), indent=1)
    return checks


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="selftest")
    ap.add_argument("--seed", type=int, default=20260918)
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--boot", type=int, default=400)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    c1, _ = part1(out, a.seed, a.boot)
    c2 = part2(out, a.seeds, a.boot)
    checks = c1 + c2
    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    json.dump({"verdict": verdict, "n_checks": len(checks), "n_failed": sum(not c["pass"] for c in checks),
               "checks": checks, "seconds": round(time.time() - t0, 1), "env": g3b.env_versions()},
              open(out / "selftest.json", "w"), indent=1, default=float)
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], "" if c["pass"] else c["detail"])
    print("SELFTEST", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
