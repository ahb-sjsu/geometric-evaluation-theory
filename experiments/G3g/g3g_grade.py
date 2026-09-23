#!/usr/bin/env python3
"""G3g: grade every cell's test block against its committed predictions.

The grading is G3c's `judge_grade`, by import and unmodified. This file only points it at the
right blocks, refuses to grade against predictions that are not the ones the test seed was drawn
against, applies the registration's rule for which cells the read-out ordering claim is graded
in, checks the one claim that runs ACROSS cells, and writes the record.

    python g3g_grade.py --config g3g_config.json --out run_record

Each cell and judge gets `run_record/<cell>/grade_<key>.json` holding the predictions it was
graded against, the observed curves and the verdicts. `run_record/verdicts.json` holds the gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import judge_grade as G  # noqa: E402


def cell_name(budget) -> str:
    return "full" if budget in (None, 0, "full", "none") else "trunc%d" % int(budget)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="run_record")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    out = Path(a.out)
    pinned = {}
    seed_rec = out / "test_seed.json"
    if seed_rec.exists():
        pinned = {k: v["sha256"] for k, v in json.load(open(seed_rec))["predictions_pinned"].items()}
    ladder = [cell_name(b) for b in cfg["truncation_ladder"]]
    c3g_cells = set(cell_name(b) for b in cfg["c3g_graded_cells"])
    floor = min(cfg["gap_ladder"])

    summary = {"gate": cfg.get("gate", "G3g"), "test_seed": cfg["seeds"].get("test"),
               "truncation_ladder": ladder, "c3g_graded_cells": sorted(c3g_cells), "cells": {}}
    for cell in ladder:
        summary["cells"][cell] = {}
        for m in cfg["models"]:
            key = m["key"]
            cal = out / cell / "calibration" / f"{key}__served"
            test = out / cell / "test" / f"{key}__served"
            if not (test / "results.json").exists():
                print(cell, key, "no test block yet, skipped")
                continue
            pred_path = cal / "predictions.json"
            sha = hashlib.sha256(pred_path.read_bytes()).hexdigest()
            pin = pinned.get(f"{cell}/{key}")
            if pin is not None and sha != pin:
                raise SystemExit("%s/%s: predictions.json is %s, the test seed was drawn against %s"
                                 % (cell, key, sha[:16], pin[:16]))
            pred = json.loads(pred_path.read_text(encoding="utf-8"))
            obs = G.observed(str(test), cfg)
            v = G.grade(pred, obs, cfg["bars"])
            json.dump({"predictions_sha256": sha, "predictions": pred, "observed": obs, "verdicts": v},
                      open(out / cell / f"grade_{key}.json", "w"), indent=1, default=float)
            j1 = [r for r in v["J1_prediction"].values() if isinstance(r, dict)]
            j3 = v["J3_budget_ordering"]
            s = {
                "served_as": json.load(open(test / "results.json"))["loaded_revision"],
                "predictions_sha256": sha,
                "anti_vacuity_met": v["anti_vacuity"]["met"],
                "anti_vacuity": v["anti_vacuity"],
                "J1": v["J1_prediction"]["verdict"],
                "J1_max_dev": max(r["max_abs_dev"] for r in j1),
                "J1_max_z": max(r["max_z"] for r in j1),
                "J2": v["J2_effective_vs_nominal"]["verdict"],
                "J2_sse": {k: {"effective": r["sse_effective"], "nominal": r["sse_nominal"]}
                           for k, r in v["J2_effective_vs_nominal"].items() if isinstance(r, dict)},
                "J3": j3["verdict"],
                "J3_graded_here": cell in c3g_cells,
                "J3_kendall_tau": j3["kendall_tau"],
                "J3_share_within_factor": j3.get("share_within_factor"),
                "J3_predicted_at_ladder_floor": sum(1 for p in j3["predicted"] if abs(p - floor) < 1e-9),
                "J3_readouts": len(j3["readouts"]),
                "J5_pairwise": v.get("J5_pairwise"),
                "thresholds": {n: {"predicted": p, "observed": o}
                               for n, p, o in zip(j3["readouts"], j3["predicted"], j3["observed"])},
            }
            # The per-cell verdict is G3c's, except that J3 counts only where the registration
            # says the instrument can rank read-outs at all.
            if s["anti_vacuity_met"]:
                parts = [s["J1"], s["J2"]] + ([s["J3"]] if s["J3_graded_here"] else [])
                s["cell_verdict"] = "PASS" if all(p == "PASS" for p in parts) else "FAIL"
            else:
                s["cell_verdict"] = "VACUOUS"
            summary["cells"][cell][key] = s
            print("%-9s %-9s %-8s J1 %-4s (dev %.3f, z %.2f)  J2 %-4s  J3 %-4s%s (tau %.3f, %d of %d at the floor)"
                  % (cell, key, s["cell_verdict"], s["J1"], s["J1_max_dev"], s["J1_max_z"], s["J2"], s["J3"],
                     "" if s["J3_graded_here"] else " (reported, not graded here)",
                     s["J3_kendall_tau"], s["J3_predicted_at_ladder_floor"], s["J3_readouts"]), flush=True)

    # Claims. C1g, C2g and C4g per cell over graded judges; C3g over graded judges in the cells
    # the registration names; C5g across the ends of the ladder.
    graded = [(c, k, s) for c, d in summary["cells"].items() for k, s in d.items() if s["anti_vacuity_met"]]
    if graded:
        summary["C1g"] = "PASS" if all(s["J1"] == "PASS" for _, _, s in graded) else "FAIL"
        summary["C2g"] = "PASS" if all(s["J2"] == "PASS" for _, _, s in graded) else "FAIL"
        c3 = [s for c, _, s in graded if c in c3g_cells]
        summary["C3g"] = ("PASS" if all(s["J3"] == "PASS" for s in c3) else "FAIL") if c3 else "NOT GRADED"
        summary["C4g"] = {f"{c}/{k}": (s["J5_pairwise"] or {}).get("label") for c, k, s in graded}
        # C5g: on every scale of every graded judge, the observed greedy threshold at the shortest
        # budget exceeds the one at full length, and the predicted greedy thresholds are
        # non-increasing along the whole ladder. Both ends must be graded for the judge.
        # The registration states C5g along the ladder 200, 400, full: shortest budget first.
        # The config lists cells longest first, and the first grading run walked that order and
        # tested the reverse direction (recorded in PREREG-G3G.md Section 9). Walk it as stated.
        rungs = list(reversed(ladder))
        short, long_ = rungs[0], rungs[-1]
        c5 = {}
        for m in cfg["models"]:
            key = m["key"]
            cells_ok = all(key in summary["cells"].get(c, {}) and summary["cells"][c][key]["anti_vacuity_met"] for c in rungs)
            if not cells_ok:
                c5[key] = "NOT GRADED"
                continue
            ok = True
            detail = {}
            for sc in [f"{x['lo']}-{x['hi']}" for x in cfg["scales"]]:
                rd = f"{sc}/argmax"
                obs_chain = [summary["cells"][c][key]["thresholds"][rd]["observed"] for c in rungs]
                pred_chain = [summary["cells"][c][key]["thresholds"][rd]["predicted"] for c in rungs]
                ends = obs_chain[0] > obs_chain[-1]
                mono = all(pred_chain[i] >= pred_chain[i + 1] - 1e-9 for i in range(len(pred_chain) - 1))
                detail[sc] = {"observed_by_cell": dict(zip(rungs, obs_chain)),
                              "predicted_by_cell": dict(zip(rungs, pred_chain)),
                              "observed_%s_exceeds_%s" % (short, long_): ends,
                              "predicted_non_increasing": mono}
                ok &= ends and mono
            c5[key] = {"verdict": "PASS" if ok else "FAIL", "scales": detail}
        summary["C5g_detail"] = c5
        verdicts = [v["verdict"] for v in c5.values() if isinstance(v, dict)]
        summary["C5g"] = ("PASS" if all(v == "PASS" for v in verdicts) else "FAIL") if verdicts else "NOT GRADED"
        gate_parts = [summary["C1g"], summary["C2g"], summary["C5g"]] + ([summary["C3g"]] if c3 else [])
        summary["gate"] = "PASS" if all(p == "PASS" for p in gate_parts) else "FAIL"
    else:
        summary["gate"] = "VACUOUS"
    json.dump(summary, open(out / "verdicts.json", "w"), indent=1, default=float)
    print("\nGATE", summary["gate"], {c: summary.get(c) for c in ("C1g", "C2g", "C3g", "C5g")})
    print("wrote", out / "verdicts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
