"""Grades a G4b results.json against the sealed bars of PREREG-G4B.md: the G4 per-rank rule
at every eps of the ladder, then the gate verdict at the smallest eps at which P1 holds at
every rank. Usage: python g4b_grade.py results.json [--out grade.json]"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "G4"))
from g4_grade import grade as grade_per_rank  # noqa: E402


def grade(res: dict) -> dict:
    cfg = res["config"]
    eps_ladder = [str(float(e)) for e in cfg["eps_ladder"]]
    out = {"n_cells": len(res["cells"]), "eps": {}, "gate": None, "gate_eps": None, "diagnosis": {}}
    for e in eps_ladder:
        view = {"config": cfg, "cells": [{"layer": c["layer"], "kv_head": c["kv_head"],
                                          "ranks": {k: v["eps"][e] for k, v in c["ranks"].items()}}
                                         for c in res["cells"]]}
        out["eps"][e] = grade_per_rank(view)
        # diagnosis: median over cells of the median ratio measured/predicted, per rank
        out["diagnosis"][e] = {}
        for k in cfg["ranks"]:
            meds = []
            for c in res["cells"]:
                ev = c["ranks"][str(k)]["eps"][e]
                r = [m / max(p, 1e-12) for row in ev["codes"].values() for p, m in zip(row["predicted_distortion"], row["measured_loss"])]
                meds.append(float(np.median(r)))
            out["diagnosis"][e][str(k)] = {"median_ratio": float(np.median(meds)), "min": float(min(meds)), "max": float(max(meds))}
    chosen = None
    for e in sorted(eps_ladder, key=float):
        if all(v["P1"]["holds"] for v in out["eps"][e]["ranks"].values()):
            chosen = e; break
    if chosen is None:
        out["gate"] = "INDETERMINATE"
        out["gate_reason"] = "P1 holds at no eps of the ladder at every rank; the quadratic model is not established, see diagnosis"
    else:
        out["gate_eps"] = chosen
        out["gate"] = out["eps"][chosen]["gate"]
        out["gate_reason"] = f"verdict at the smallest eps ({chosen}) at which P1 holds at every rank"
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
