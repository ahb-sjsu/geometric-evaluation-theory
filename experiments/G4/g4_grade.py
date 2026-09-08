"""Grades a G4 results.json against the sealed bars of PREREG-G4.md Section 6, per rank and
for the gate. Reads only the result file and the config it carries. Usage:

    python g4_grade.py results.json [--out grade.json]
"""
from __future__ import annotations

import json
import sys


def grade(res: dict) -> dict:
    bars = res["config"]["bars"]
    ranks = [int(k) for k in res["config"]["ranks"]]
    cells = res["cells"]
    n_cells = len(cells)
    out = {"n_cells": n_cells, "ranks": {}, "gate": None}
    verdicts = []
    for k in ranks:
        ks = str(k)
        # P1: relative error of predicted vs measured loss over (cell, code, consumer) triples
        n_tot = n_ok = 0
        for c in cells:
            ev = c["ranks"][ks]
            for name, row in ev["codes"].items():
                if "measured_loss" not in row:
                    continue
                for p, m in zip(row["predicted_distortion"], row["measured_loss"]):
                    n_tot += 1
                    if abs(p - m) / max(abs(m), 1e-12) <= bars["P1_relative_error_max"]:
                        n_ok += 1
        p1_frac = n_ok / max(n_tot, 1)
        p1 = p1_frac >= bars["P1_min_fraction"]
        # P2: own code measured-best within tolerance, counted per cell (all consumers)
        p2_cells = sum(1 for c in cells if max(c["ranks"][ks]["own_code_excess_over_measured_best"])
                       <= bars["P2_own_excess_over_measured_best_max"])
        p2 = p2_cells >= bars["P2_min_cells"]
        # non-vacuous cells at this rank: deficiency bound above the registered fraction of the
        # summed own-optimal top-k sums, the same ratio the probe reported per cell
        nv_cells = [c for c in cells
                    if c["ranks"][ks]["deficiency_over_own"] > bars["nonvacuous_cell_min_deficiency_fraction"]]
        n_nv = len(nv_cells)
        # P3: compromise measured total within tolerance of the bound, over non-vacuous cells
        p3_ok = sum(1 for c in nv_cells if abs(c["ranks"][ks]["compromise_measured_total_regret"] - c["ranks"][ks]["deficiency_bound"])
                    <= bars["P3_compromise_tolerance"] * c["ranks"][ks]["deficiency_bound"])
        p3 = n_nv > 0 and p3_ok / n_nv >= bars["P3_min_fraction_of_nonvacuous_cells"]
        # P4: no code's measured total below the bound by more than the tolerance, any cell
        p4_viol = [(c["layer"], c["kv_head"], c["ranks"][ks]["measured_min_total_code"]) for c in cells
                   if c["ranks"][ks]["any_code_measured_total_below_bound_by"] > bars["P4_beats_bound_tolerance"] * c["ranks"][ks]["deficiency_bound"]]
        p4 = len(p4_viol) == 0
        # P5: compromise is measured-best among non-own codes, over non-vacuous cells
        p5_ok = 0
        for c in nv_cells:
            ev = c["ranks"][ks]
            others = {n: r["measured_weighted_total_regret"] for n, r in ev["codes"].items()
                      if not n.startswith("own_") and "measured_weighted_total_regret" in r}
            if min(others, key=others.get) == "compromise":
                p5_ok += 1
        p5 = n_nv > 0 and p5_ok / n_nv >= bars["P5_min_fraction_of_nonvacuous_cells"]
        if p1 and p2 and p3 and p4 and p5:
            v = "PASS"
        elif p1 and (not p4 or (n_nv > 0 and (p3_ok / n_nv < 0.5 or p5_ok / n_nv < 0.5))):
            v = "FAIL"
        else:
            v = "INDETERMINATE"
        verdicts.append(v)
        out["ranks"][ks] = {
            "P1": {"holds": p1, "fraction_within_tolerance": p1_frac, "triples": n_tot},
            "P2": {"holds": p2, "cells": p2_cells},
            "nonvacuous_cells": n_nv,
            "P3": {"holds": p3, "cells_within_tolerance": p3_ok},
            "P4": {"holds": p4, "violations": p4_viol},
            "P5": {"holds": p5, "cells_compromise_best": p5_ok},
            "verdict": v,
        }
    out["gate"] = "PASS" if all(v == "PASS" for v in verdicts) else ("FAIL" if any(v == "FAIL" for v in verdicts) else "INDETERMINATE")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "results.json"
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    res = json.load(open(path, encoding="utf-8"))
    g = grade(res)
    text = json.dumps(g, indent=1)
    if outp:
        open(outp, "w", encoding="utf-8").write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
