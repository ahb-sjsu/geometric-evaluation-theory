#!/usr/bin/env python3
"""G3e: grade each judge's test block against its committed predictions.

The grading is G3c's, by import. This file only points it at the right blocks, refuses to grade
against predictions that are not the committed ones, and writes the record.

    python g3e_grade.py --config g3e_config.json --out run_record

Each judge gets `run_record/grade_<key>.json` holding the predictions it was graded against, the
observed curves, and the verdicts. `run_record/verdicts.json` holds the gate's summary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import judge_grade as G  # noqa: E402


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

    # The label only. Every verdict below is computed by judge_grade from the config and the
    # records, so reading the gate name from the config lets a later gate reuse this
    # orchestrator unchanged. G3e's own config says "G3e", so this is identical for G3e.
    summary = {"gate": cfg.get("gate", "G3e"), "test_seed": cfg["seeds"].get("test"), "judges": {}}
    for m in cfg["models"]:
        key = m["key"]
        cal = out / "calibration" / f"{key}__served"
        test = out / "test" / f"{key}__served"
        if not (test / "results.json").exists():
            print(key, "no test block yet, skipped")
            continue
        pred_path = cal / "predictions.json"
        sha = hashlib.sha256(pred_path.read_bytes()).hexdigest()
        if key in pinned and sha != pinned[key]:
            raise SystemExit("%s: predictions.json is %s, the test seed was drawn against %s"
                             % (key, sha[:16], pinned[key][:16]))
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
        obs = G.observed(str(test), cfg)
        v = G.grade(pred, obs, cfg["bars"])
        json.dump({"predictions_sha256": sha, "predictions": pred, "observed": obs, "verdicts": v},
                  open(out / f"grade_{key}.json", "w"), indent=1, default=float)
        j1 = [r for r in v["J1_prediction"].values() if isinstance(r, dict)]
        j3 = v["J3_budget_ordering"]
        summary["judges"][key] = {
            "served_as": json.load(open(test / "results.json"))["loaded_revision"],
            "predictions_sha256": sha,
            "gate": v["gate"],
            "anti_vacuity_met": v["anti_vacuity"]["met"],
            "J1": v["J1_prediction"]["verdict"],
            "J1_max_dev": max(r["max_abs_dev"] for r in j1),
            "J1_max_z": max(r["max_z"] for r in j1),
            "J2": v["J2_effective_vs_nominal"]["verdict"],
            "J2_sse": {k: {"effective": r["sse_effective"], "nominal": r["sse_nominal"]}
                       for k, r in v["J2_effective_vs_nominal"].items() if isinstance(r, dict)},
            "J3": j3["verdict"],
            "J3_kendall_tau": j3["kendall_tau"],
            "J3_share_within_factor": j3.get("share_within_factor"),
            "J3_predicted_at_ladder_floor": sum(1 for p in j3["predicted"] if abs(p - min(cfg["gap_ladder"])) < 1e-9),
            "J3_readouts": len(j3["readouts"]),
            "J5_pairwise": v.get("J5_pairwise"),
            "thresholds": {n: {"predicted": p, "observed": o}
                           for n, p, o in zip(j3["readouts"], j3["predicted"], j3["observed"])},
        }
        s = summary["judges"][key]
        print("%-10s gate %-8s J1 %-4s (dev %.3f, z %.2f)  J2 %-4s  J3 %-4s (tau %.3f, %d of %d at the ladder floor)"
              % (key, s["gate"], s["J1"], s["J1_max_dev"], s["J1_max_z"], s["J2"], s["J3"],
                 s["J3_kendall_tau"], s["J3_predicted_at_ladder_floor"], s["J3_readouts"]), flush=True)

    graded = [j for j in summary["judges"].values() if j["anti_vacuity_met"]]
    if graded:
        for claim, key in (("C1e", "J1"), ("C2e", "J2"), ("C3e", "J3")):
            summary[claim] = "PASS" if all(j[key] == "PASS" for j in graded) else "FAIL"
        summary["gate"] = "PASS" if all(summary[c] == "PASS" for c in ("C1e", "C2e", "C3e")) else "FAIL"
    else:
        summary["gate"] = "VACUOUS"
    json.dump(summary, open(out / "verdicts.json", "w"), indent=1, default=float)
    print("\nGATE", summary["gate"], {c: summary.get(c) for c in ("C1e", "C2e", "C3e")})
    print("wrote", out / "verdicts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
