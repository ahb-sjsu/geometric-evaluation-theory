"""Probe 2: how does testability depend on how many coordinates you read?

Probe 1 killed the design it was written for. Thirteen actions in the full
five-dimensional consequence space give 3 testable units, and seven actions
give none at all, even though seven clears Radon's bound of d + 2. The bound
is necessary and not sufficient. Real consequence points lie close to a
low-dimensional curved set inside the five-dimensional space, and a point on a
surface is almost never inside the convex hull of other points on that surface.

So the question worth asking is not "can we avoid projecting" but "what does
the violation rate do as we project less". That is measurable here and it is
the quantity the projection article left open.

This probe walks the dimension ladder. For every subset of the five
coordinates of each size, it counts testable units, and it also reports the
effective dimension of the consequence cloud so the cause is on the record
rather than asserted.

No ranking is formed and no violation is computed.
"""
import importlib.util
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

G2 = "/home/claude/g9_dir/G2/g2_hull_law.py"
spec = importlib.util.spec_from_file_location("g2_hull_law", G2)
g2 = importlib.util.module_from_spec(spec)
sys.modules["g2_hull_law"] = g2
spec.loader.exec_module(g2)

probe1 = importlib.util.spec_from_file_location("g9b_probe", "/home/claude/g9b_probe.py")
p1 = importlib.util.module_from_spec(probe1)
sys.modules["g9b_probe"] = p1
probe1.loader.exec_module(p1)

OUT = "/home/claude/deploy/g9b_probe2.json"
COORDS = p1.COORDS
CELLKEYS = p1.CELLKEYS
FLOOR = 5


def main():
    df = p1.prepare()
    rec = {"floor": FLOOR, "coords": list(COORDS)}

    for name in ("A13", "A9"):
        d = df.copy()
        d["action"] = p1.SPACES[name](d)
        d = d[d["action"].notna()].copy()
        actions = sorted(d["action"].unique())
        cmap, ok = p1.consequence_map(d, actions, FLOOR)

        counts = d.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
        for a in actions:
            if a not in counts.columns:
                counts[a] = 0
        counts = counts[list(actions)]
        units = counts[(counts >= FLOOR).all(axis=1)]
        unit_cells = [tuple(k) for k in units.index.droplevel(0)]

        # Effective dimension of the consequence cloud, so the cause of the
        # collapse is measured and not asserted.
        M = cmap[list(COORDS)].to_numpy(dtype=float)
        M = M[np.isfinite(M).all(axis=1)]
        sv = np.linalg.svd(M - M.mean(0), compute_uv=False)
        energy = (sv ** 2) / (sv ** 2).sum()
        cum = np.cumsum(energy)

        entry = {"n_actions": len(actions), "cells": int(len(ok)), "units": int(len(units)),
                 "singular_energy": [float(x) for x in energy],
                 "cumulative_energy": [float(x) for x in cum],
                 "dims_for_95pct_energy": int(np.searchsorted(cum, 0.95) + 1),
                 "by_dimension": {}}

        for k in (2, 3, 4, 5):
            subsets = list(itertools.combinations(range(5), k))
            tu, tc = [], []
            for sub in subsets:
                cols = [COORDS[i] for i in sub]
                tcell = {}
                for key, block in cmap.groupby(CELLKEYS, observed=True):
                    block = block.set_index("action")
                    if not all(a in block.index for a in actions):
                        continue
                    Y = block.loc[list(actions), cols].to_numpy(dtype=float)
                    if not np.isfinite(Y).all():
                        continue
                    t = False
                    for i in range(len(actions)):
                        if g2.in_hull(Y[i], np.delete(Y, i, axis=0)):
                            t = True
                            break
                    tcell[key if isinstance(key, tuple) else (key,)] = t
                tc.append(int(sum(tcell.values())))
                tu.append(int(sum(1 for c in unit_cells if tcell.get(c, False))))
            entry["by_dimension"][str(k)] = {
                "n_subsets": len(subsets),
                "testable_cells_mean": float(np.mean(tc)),
                "testable_cells_max": int(max(tc)),
                "testable_units_mean": float(np.mean(tu)),
                "testable_units_max": int(max(tu)),
                "testable_units_min": int(min(tu)),
            }
            print("%-4s dim=%d subsets=%2d testable_units mean=%7.1f max=%5d  cells mean=%6.1f"
                  % (name, k, len(subsets), np.mean(tu), max(tu), np.mean(tc)), flush=True)
        rec[name] = entry
        print("%-4s consequence cloud: %d dims carry 95 pct of the energy, shares %s"
              % (name, entry["dims_for_95pct_energy"],
                 ["%.3f" % x for x in entry["singular_energy"]]), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
