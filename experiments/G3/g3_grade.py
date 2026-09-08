"""Grades a G3 results.json against the sealed bars of PREREG-G3.md Section 5.
Usage: python g3_grade.py results.json --tol TOL [--out grade.json]"""
from __future__ import annotations

import json
import math
import sys


def grade(res: dict, tol: float) -> dict:
    cfg = res["config"]
    full_budget = int(cfg.get("max_new_tokens", 12))
    cells = {(c["weight_precision"], c["decimals"]): c for c in res["cells"] if c.get("report_tokens", full_budget) == full_budget}
    rcells = {int(c["report_tokens"]): c for c in res["cells"] if c["weight_precision"] == "full" and c["decimals"] == max(int(d) for d in cfg["decimals_ladder"])}
    wps = list(cfg["weight_precisions"]); decs = [int(d) for d in cfg["decimals_ladder"]]
    dmax = max(decs)
    floor = cells[(wps[0], dmax)]["threshold"]
    smallest_gap = min(float(g) for g in cfg["gap_ladder"])
    floor_censored = floor <= smallest_gap
    out = {"tol": tol, "floor_full_precision_max_decimals": floor, "floor_censored_at_smallest_gap": floor_censored,
           "thresholds": {}, "P1": {}, "P1b": {}, "P2": {}, "P3": {}, "gate": None}
    for (wp, d), c in cells.items():
        out["thresholds"][f"{wp}_{d}dec"] = c["threshold"]
    for k, c in rcells.items():
        out["thresholds"][f"full_{dmax}dec_{k}tok"] = c["threshold"]
    fail = False
    # P1b report-length ladder: predicted resolution per budget for two-digit distances
    def predicted_resolution(k: int) -> float:
        return 10.0 if k <= 1 else (1.0 if k <= 3 else 10.0 ** (-(k - 3)))
    ks = sorted(rcells)
    p1b_rec = {"thresholds": {str(k): rcells[k]["threshold"] for k in ks}, "monotone": True, "tracks_budget": {}}
    for k0, k1 in zip(ks, ks[1:]):
        if rcells[k1]["threshold"] > rcells[k0]["threshold"] * tol:
            p1b_rec["monotone"] = False
        if rcells[k0]["threshold"] < rcells[k1]["threshold"] / tol:
            fail = True
    for k in ks:
        pred = predicted_resolution(k)
        if k >= 2 and (not math.isfinite(floor) or pred >= 3 * max(floor, smallest_gap)):
            thr = rcells[k]["threshold"]
            ok = (thr <= pred * tol) and (thr >= pred / tol)
            p1b_rec["tracks_budget"][str(k)] = {"predicted": pred, "threshold": thr, "within_tol": bool(ok)}
    p1b = p1b_rec["monotone"] and all(v["within_tol"] for v in p1b_rec["tracks_budget"].values())
    p1b_rec["holds"] = bool(p1b) if rcells else True
    out["P1b"] = p1b_rec
    # P1 rendering ladder per weight precision
    p1_all = True
    for wp in wps:
        thr = {d: cells[(wp, d)]["threshold"] for d in decs}
        rec = {"thresholds": thr, "monotone": True, "tracks_step": {}}
        for d0, d1 in zip(decs, decs[1:]):          # more decimals must not raise the threshold beyond tol
            if thr[d1] > thr[d0] * tol:
                rec["monotone"] = False
            if thr[d0] < thr[d1] / tol:            # coarser rendering gave a smaller threshold: falsifier
                fail = True
        for d in decs:
            step = 10.0 ** (-d)
            if math.isfinite(floor) and step >= 3 * max(floor, smallest_gap):
                ok = (thr[d] <= step * tol) and (thr[d] >= step / tol)
                rec["tracks_step"][str(d)] = {"step": step, "threshold": thr[d], "within_tol": bool(ok)}
        holds = rec["monotone"] and all(v["within_tol"] for v in rec["tracks_step"].values())
        rec["holds"] = bool(holds); p1_all = p1_all and holds
        out["P1"][wp] = rec
    out["P1"]["holds"] = bool(p1_all)
    # P2 weight ladder at max decimals
    thr_w = [cells[(wp, dmax)]["threshold"] for wp in wps]
    p2 = all(thr_w[i + 1] * tol >= thr_w[i] for i in range(len(thr_w) - 1))
    for i in range(len(thr_w) - 1):
        if thr_w[i + 1] < thr_w[i] / tol:
            fail = True
    out["P2"] = {"holds": bool(p2), "thresholds_by_precision": dict(zip(wps, thr_w))}
    # P3 well-separated ordering
    finite = [c["threshold"] for c in res["cells"] if math.isfinite(c["threshold"])]
    tmax = max(finite) if finite else float("inf")
    sep = [g for g in cfg["gap_ladder"] if g >= 2 * tmax]
    worst = 1.0; p3 = True
    for c in res["cells"]:
        for g in sep:
            a = c["accuracy_by_gap"][str(float(g))]["accuracy"]
            worst = min(worst, a)
            if a < 0.95:
                p3 = False
            if a < 0.8:
                fail = True
    out["P3"] = {"holds": bool(p3), "largest_threshold": tmax, "well_separated_gaps": sep, "worst_accuracy": worst}
    if p1_all and p1b and p2 and p3:
        out["gate"] = "PASS"
    elif fail:
        out["gate"] = "FAIL"
    else:
        out["gate"] = "INDETERMINATE"
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = argv[0]
    tol = float(argv[argv.index("--tol") + 1])
    outp = argv[argv.index("--out") + 1] if "--out" in argv else None
    g = grade(json.load(open(path, encoding="utf-8")), tol)
    text = json.dumps(g, indent=1)
    if outp:
        open(outp, "w", encoding="utf-8").write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
