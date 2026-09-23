#!/usr/bin/env python3
"""Pilot table for the G3g truncation ladder. Grades NOTHING.

For each cell of the pilot ladder (full length, then the first 100, 200 and 400 characters of
each review) this predicts from the pilot calibration block and reads the pilot test block with
G3c's `judge_grade`, unmodified, and prints the statistics the registration's Section 2 and 4
quote: thresholds per read-out, how many read-outs sit at the floor of the gap ladder, the
family-wide deviation, noise units, threshold ratio and Kendall tau, and the bits each scale
carries. Everything here is a pilot number on pilot seeds, disclosed as such, and none of it is
a verdict. The registered run makes its predictions once, commits them, and is graded by the
registered script.

    python g3g_pilot_table.py g3g_config.json pilot_record/pilot
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for cand in ("G3c", "g3c"):
    if (HERE.parent / cand / "judge_grade.py").exists():
        sys.path.insert(0, str(HERE.parent / cand))
        break
import judge_grade as G  # noqa: E402

CELLS = ["full", "trunc100", "trunc200", "trunc400"]
SHOW = ["argmax", "expected", "mean_8"]


def main() -> int:
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    root = Path(sys.argv[2])
    bars = dict(cfg["bars"])
    if bars.get("vacuity_bits_min") is None:
        bars["vacuity_bits_min"] = 1.0  # the a-priori bar of G3c, which this table reports against
    floor_gap = min(int(g) for g in cfg["gap_ladder"])
    table = {}
    for cell in CELLS:
        cal = root / cell / "calibration"
        tst = root / cell / "test"
        cal_dirs = sorted(p for p in cal.glob("*__served") if (p / "results.json").exists()) if cal.exists() else []
        for cd in cal_dirs:
            td = tst / cd.name
            if not (td / "results.json").exists():
                print(f"{cell:9s} {cd.name}: calibration only")
                continue
            pred = G.predict(str(cd), cfg, n_boot=100)
            obs = G.observed(str(td), cfg)
            gr = G.grade(pred, obs, bars)
            j1 = gr["J1_prediction"]
            recs = [v for k, v in j1.items() if k != "verdict"]
            n_floor = sum(1 for v in recs if math.isfinite(v["predicted_threshold"]) and v["predicted_threshold"] <= floor_gap)
            ratios = [v["observed_threshold"] / v["predicted_threshold"] for v in recs
                      if math.isfinite(v["predicted_threshold"]) and math.isfinite(v["observed_threshold"]) and v["predicted_threshold"] > 0]
            unparsed = {}
            for key in pred["scales"]:
                for blk, d in (("cal", cd), ("test", td)):
                    rs = G.load_scores(d, key)
                    unparsed[f"{key}/{blk}"] = sum(1 for r in rs if r.get("unparsed"))
            row = {
                "judge": cd.name,
                "max_abs_dev": round(max(v["max_abs_dev"] for v in recs), 4),
                "max_z": round(max(v["max_z"] for v in recs), 3),
                "max_threshold_ratio": round(max(max(ratios), 1 / min(ratios)), 3) if ratios else None,
                "kendall_tau": round(gr["J3_budget_ordering"]["kendall_tau"], 3),
                "n_readouts_at_floor": n_floor,
                "n_readouts_ranked": len(gr["J3_budget_ordering"]["readouts"]),
                "bits": {k: round(s["codebook"]["information_about_quality_bits"], 3) for k, s in pred["scales"].items()},
                "distinct": {k: s["codebook"]["n_distinct"] for k, s in pred["scales"].items()},
                "vacuity_met": gr["anti_vacuity"]["met"],
                "J2_effective_wins": all(v["effective_wins"] for k, v in gr["J2_effective_vs_nominal"].items() if k != "verdict"),
                "unparsed": unparsed,
                "thresholds": {f"{k}/{n}": [round(j1[f"{k}/{n}"]["predicted_threshold"], 3), round(j1[f"{k}/{n}"]["observed_threshold"], 3)]
                               for k in pred["scales"] for n in SHOW if f"{k}/{n}" in j1},
                "pairwise": {k: gr["J5_pairwise"].get(k) for k in ("predicted_threshold", "observed_threshold", "label")} if gr.get("J5_pairwise") else None,
            }
            table[f"{cell}/{cd.name}"] = row
            print(f"\n=== {cell} {cd.name} ===")
            print(f"  dev {row['max_abs_dev']}  z {row['max_z']}  ratio {row['max_threshold_ratio']}  tau {row['kendall_tau']}"
                  f"  at floor {n_floor}/{row['n_readouts_ranked']}  vacuity {row['vacuity_met']}  channel beats nominal {row['J2_effective_wins']}")
            print(f"  bits {row['bits']}  distinct {row['distinct']}  unparsed {row['unparsed']}")
            for k, v in row["thresholds"].items():
                print(f"  {k:16s} pred {v[0]:6.3f}  obs {v[1]:6.3f}")
            if row["pairwise"]:
                print(f"  pairwise {row['pairwise']}")
    out = root / "pilot_table.json"
    json.dump({"note": "PILOT ONLY, grades nothing", "bars_used": bars, "cells": table}, open(out, "w"), indent=1)
    print("\nwrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
