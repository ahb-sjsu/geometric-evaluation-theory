#!/usr/bin/env python3
"""EXPLORATORY, run after both gates were graded. Where does the gap ladder stop measuring?

J3 asks whether the ordering of thresholds across read-outs is the ordering their symbol budgets
predict, and scores it with Kendall's tau. A threshold is read off a ladder of gaps, the smallest of
which is one wrong answer in twenty. A read-out finer than that has nowhere to land: its threshold
is reported at the floor, and read-outs tied there cannot be ranked, which costs tau whatever the
judge is doing.

This counts, for every graded judge of G3c and G3e, how many of its read-outs sit at the floor, and
puts that beside its tau. It tests nothing. Both gates are graded and their bars are spent; this is
a question about the instrument, asked of records that already exist, and it is labelled so.

    python ladder_floor_check.py --out ladder_floor.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows_for(gate: str, pattern: str, floor: float):
    out = []
    for f in sorted(glob.glob(pattern)):
        d = json.load(open(f, encoding="utf-8"))
        v = d.get("verdicts", d)
        j3 = v.get("J3_budget_ordering")
        if not j3:
            continue
        pred = j3["predicted"]
        at = [n for n, p in zip(j3["readouts"], pred) if abs(p - floor) < 1e-9]
        out.append({"gate": gate, "judge": os.path.basename(f)[6:-5],
                    "vacuous": not v.get("anti_vacuity", {}).get("met", True),
                    "J3": j3["verdict"], "kendall_tau": j3["kendall_tau"],
                    "readouts": len(pred), "at_floor": len(at), "at_floor_names": at,
                    "share_within_factor": j3.get("share_within_factor")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="ladder_floor.json")
    a = ap.parse_args()
    g3c = HERE.parent / ("G3c" if (HERE.parent / "G3c").exists() else "g3c")
    rows = rows_for("G3c", str(g3c / "run_record" / "grade_*.json"), 1.0)
    rows += rows_for("G3e", str(HERE / "run_record" / "grade_*.json"), 1.0)
    print("%-5s %-16s %-8s %-6s %6s %8s %9s" % ("gate", "judge", "status", "J3", "tau", "at floor", "read-outs"))
    for r in rows:
        print("%-5s %-16s %-8s %-6s %6.3f %8d %9d" % (
            r["gate"], r["judge"], "VACUOUS" if r["vacuous"] else "graded", r["J3"],
            r["kendall_tau"], r["at_floor"], r["readouts"]))
    graded = [r for r in rows if not r["vacuous"]]
    with_floor = [r for r in graded if r["at_floor"]]
    without = [r for r in graded if not r["at_floor"]]
    summary = {
        "exploratory": True,
        "why": "both gates were graded before this was run; it asks where the ladder stops measuring",
        "ladder_floor": 1.0,
        "rows": rows,
        "graded_judges": len(graded),
        "graded_with_a_readout_at_the_floor": [r["judge"] for r in with_floor],
        "their_J3": sorted({r["J3"] for r in with_floor}) or None,
        "J3_of_graded_judges_without_one": sorted({r["J3"] for r in without}) or None,
    }
    json.dump(summary, open(a.out, "w"), indent=1, default=float)
    print("\ngraded judges with a read-out at the floor:", summary["graded_with_a_readout_at_the_floor"] or "none")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
