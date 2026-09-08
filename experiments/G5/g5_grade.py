"""Grades a G5 results.json against the sealed bars of PREREG-G5.md Section 5. Every bar is a
per-cell statement about medians over the cell's evaluators, relative to each evaluator's
chance level (the median error of guesses from the evaluator prior).

    python g5_grade.py results.json [--out grade.json]
"""
from __future__ import annotations

import json
import sys

import numpy as np


def med(rows, key, chance=False):
    vals = [r["chance"][key] if chance else r[key] for r in rows if key in (r["chance"] if chance else r)]
    return float(np.median(vals)) if vals else float("nan")


def frac(rows, key, factor, ckey=None):
    ckey = ckey or key
    vals = [r[key] <= factor * r["chance"][ckey] for r in rows if key in r and ckey in r["chance"]]
    return float(np.mean(vals)) if vals else float("nan")


def grade(res: dict) -> dict:
    b = res["config"]["bars"]
    REC, UNREV, FRAC_REC, CONV = b["recovery_factor"], b["unrevealed_factor"], b["recovered_fraction_max"], b["convergence_factor"]
    MIN_EV = int(b.get("min_evaluators_to_grade", 20))
    cells = res["cells"]
    keys = sorted({(c["m"], c["rank"], c["eps_mode"]) for c in cells})
    out = {"bars": b, "cells": {}, "gate": None}
    fail_flags = {"weak_order_not_recovered_at_largest_battery": False, "recovery_below_bound": False, "kernel_recovered": False}
    all_pass = True
    for m, rank, eps in keys:
        gen = {c["offset"]: [r for r in c["rows"] if not r.get("skipped")] for c in cells
               if (c["m"], c["rank"], c["eps_mode"], c["kind"]) == (m, rank, eps, "general")}
        sub = [[r for r in c["rows"] if not r.get("skipped")] for c in cells
               if (c["m"], c["rank"], c["eps_mode"], c["kind"]) == (m, rank, eps, "subspace")]
        top = max(gen)
        rows32 = gen[top]
        rec = {}
        # P1 recovery at the largest battery: weak order both metric and ideal; semiorder metric,
        # with the ideal required to converge (median at the largest battery at most CONV times
        # the median at offset 8)
        g_ratio = med(rows32, "g_rel_err") / med(rows32, "g_rel_err", True)
        t_ratio = med(rows32, "t_range_err") / med(rows32, "t_range_err", True)
        t_conv = med(rows32, "t_range_err") / med(gen[8], "t_range_err") if 8 in gen else float("nan")
        if eps == "zero":
            p1 = g_ratio <= REC and t_ratio <= REC
            if g_ratio > 0.5 or t_ratio > 0.5:
                fail_flags["weak_order_not_recovered_at_largest_battery"] = True
        else:
            p1 = g_ratio <= REC and t_conv <= CONV
        rec["P1"] = {"holds": bool(p1), "g_median_over_chance": g_ratio, "t_median_over_chance": t_ratio, "t_convergence_32_over_8": t_conv}
        # P2 monotone: median metric error non-increasing over offsets 4, 8, 16, 32
        seq = [(o, med(gen[o], "g_rel_err")) for o in sorted(gen) if o >= 4]
        p2 = all(seq[i + 1][1] <= seq[i][1] * 1.05 for i in range(len(seq) - 1))
        rec["P2"] = {"holds": bool(p2), "median_g_by_offset": {str(o): v for o, v in seq}}
        # P3 cliff at n <= m: the metric is not recovered in the median (a battery of n points
        # spans an affine subspace of dimension n - 1 < m and reveals nothing off it, but it can
        # reveal the in-span part, so single evaluators may land near the truth)
        p3 = True; best_ratio = float("inf"); fracs = {}
        for o in [o for o in gen if o <= 0]:
            if len(gen[o]) < MIN_EV:
                continue    # too few evaluators with any strict pair to grade; reported, not graded
            r_med = med(gen[o], "g_rel_err") / med(gen[o], "g_rel_err", True)
            best_ratio = min(best_ratio, r_med)
            fracs[str(o)] = frac(gen[o], "g_rel_err", 0.25)
            if r_med < UNREV:
                p3 = False
        if best_ratio < REC:
            fail_flags["recovery_below_bound"] = True
        rec["P3"] = {"holds": bool(p3), "min_median_over_chance_below_bound": best_ratio, "fraction_within_quarter_of_chance": fracs}
        # P4 subspace battery: in-span block recovered, normal entry unrevealed
        p4 = True
        if sub and sub[0]:
            s = sub[0]
            span_ratio = med(s, "g_span_rel_err") / med(s, "g_rel_err", True)
            normal_ratio = med(s, "g_normal_abs_err") / med(s, "g_normal_abs_err", True)
            p4 = span_ratio <= REC and normal_ratio >= UNREV
            rec["P4"] = {"holds": bool(p4), "span_median_over_chance": span_ratio, "normal_median_over_chance": normal_ratio}
        # P5 kernel (singular metric): range component recovered as P1, kernel unrevealed
        p5 = True
        if rank < m:
            k_ratio = med(rows32, "t_kernel_err") / med(rows32, "t_kernel_err", True)
            k_frac = frac(rows32, "t_kernel_err", 0.25)
            p5 = p1 and k_ratio >= UNREV and k_frac <= 2 * FRAC_REC
            if k_frac > 0.3:
                fail_flags["kernel_recovered"] = True
            rec["P5"] = {"holds": bool(p5), "kernel_median_over_chance": k_ratio, "kernel_recovered_fraction": k_frac}
        cell_pass = p1 and p2 and p3 and p4 and p5
        all_pass = all_pass and cell_pass
        rec["verdict"] = "PASS" if cell_pass else "not all bars"
        out["cells"][f"m{m}_r{rank}_{eps}"] = rec
    if all_pass:
        out["gate"] = "PASS"
    elif any(fail_flags.values()):
        out["gate"] = "FAIL"; out["fail_reason"] = fail_flags
    else:
        out["gate"] = "INDETERMINATE"
    out["cells_passing"] = sum(1 for v in out["cells"].values() if v["verdict"] == "PASS")
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0] if argv else "results.json"
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    g = grade(json.load(open(path, encoding="utf-8")))
    text = json.dumps(g, indent=1)
    if outp:
        open(outp, "w", encoding="utf-8").write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
