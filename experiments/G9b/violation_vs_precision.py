"""Is the action space's effect really an estimation-noise effect?

Exploratory. Registered nowhere. This is a candidate explanation for the thing
the surface measures, tested rather than asserted.

The hypothesis. A consequence point is a sample mean over the plays of that
action in that cell. Cutting the menu finer leaves fewer plays per action, so
the points get noisier, and noise on a sample mean pulls it toward the grand
mean. A point pulled toward the middle of a configuration is a point pushed
into the convex hull of the others, and being inside the hull is what a
violation is made of. If that is what is happening, then the violation rate is
a statement about how many plays were averaged and not about how coaches rank
anything.

Three measurements, none of which needs a null.

1. Violation rate against the number of plays behind the violating action.
   If noise drives it, rarely-called actions violate far more often.
2. Distance from the configuration's centroid, for violating and non-violating
   action points. Noise predicts violators sit closer to the middle.
3. A direct perturbation. Each consequence point is jittered by its own
   measured standard error and the violation rate is recomputed. If sampling
   noise of the size actually present can move the rate materially, the
   statistic is not robust at this action count.
"""
import importlib.util
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/claude")
cs = importlib.util.spec_from_file_location("cas", "/home/claude/characterize_action_space.py")
cas = importlib.util.module_from_spec(cs)
sys.modules["cas"] = cas
cs.loader.exec_module(cas)

g2 = sys.modules["g2_hull_law"]
COORDS = cas.COORDS
CELLKEYS = cas.CELLKEYS
FLOOR = cas.FLOOR
OUT = "/home/claude/deploy/violation_vs_precision.json"

# The plane G9 refuted on, and a wider read for contrast.
PLANES = {"epa_fd": ("y1_epa", "y2_first_down"),
          "epa_to": ("y1_epa", "y3_turnover"),
          "epa_fd_to_sd": ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd")}
SPACES = ("A4", "A13")
N_JITTER = 40


def build(df, name):
    pool = cas.SPACES[name]
    d = df.copy()
    base = cas.a13(d)
    d["action"] = base if pool is None else base.map(pool)
    d = d[d["action"].notna()].copy()
    actions = sorted(d["action"].unique())

    g = d.groupby(CELLKEYS + ["action"], observed=True)
    cmap = g.agg(y1_epa=("epa", "mean"), y2_first_down=("fd", "mean"),
                 y3_turnover=("turnover", "mean"), y4_epa_sd=("epa", "std"),
                 y5_clock_stop=("clock_stop", "mean"),
                 n=("epa", "size"),
                 epa_se=("epa", lambda v: float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan),
                 fd_se=("fd", lambda v: float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan),
                 to_se=("turnover", lambda v: float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan),
                 clk_se=("clock_stop", lambda v: float(np.std(v, ddof=1) / np.sqrt(len(v))) if len(v) > 1 else np.nan),
                 ).reset_index()
    wide = cmap.pivot_table(index=CELLKEYS, columns="action", values="n", fill_value=0)
    for a in actions:
        if a not in wide.columns:
            wide[a] = 0
    ok = wide[(wide[list(actions)] >= FLOOR).all(axis=1)].index
    cmap = cmap.set_index(CELLKEYS)
    cmap = cmap.loc[cmap.index.isin(ok)].reset_index()

    # Standardise the coordinates, and carry the standard errors through the
    # same scaling so a jitter is expressed in the same units as the points.
    scale = {}
    for c in COORDS:
        v = cmap[c].astype(float)
        sd = v.std()
        sd = sd if sd and np.isfinite(sd) and sd > 0 else 1.0
        scale[c] = sd
        cmap[c] = (v - v.mean()) / sd
    for c, col in (("y1_epa", "epa_se"), ("y2_first_down", "fd_se"),
                   ("y3_turnover", "to_se"), ("y5_clock_stop", "clk_se")):
        cmap[col] = cmap[col].astype(float) / scale[c]
    cmap["y4_epa_sd_se"] = np.nan   # no closed-form se for a standard deviation here

    counts = d.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
    for a in actions:
        if a not in counts.columns:
            counts[a] = 0
    counts = counts[list(actions)]
    units = counts[(counts >= FLOOR).all(axis=1)]
    return d, cmap, actions, units


SE_COL = {"y1_epa": "epa_se", "y2_first_down": "fd_se", "y3_turnover": "to_se",
          "y5_clock_stop": "clk_se", "y4_epa_sd": "y4_epa_sd_se"}


def analyse(cmap, actions, units, coords, rng):
    blocks = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        b = block.set_index("action")
        if not all(a in b.index for a in actions):
            continue
        blocks[key if isinstance(key, tuple) else (key,)] = b

    by_count = {}
    cen_v, cen_n = [], []
    n_test = base_viol = 0
    jitter_rates = []

    prepared = []
    for idx, row in units.iterrows():
        b = blocks.get(tuple(idx[1:]))
        if b is None:
            continue
        Y = b.loc[list(actions), list(coords)].to_numpy(dtype=float)
        if not np.isfinite(Y).all():
            continue
        T = row.to_numpy(dtype=float)
        ns = b.loc[list(actions), "n"].to_numpy(dtype=float)
        SE = np.stack([b.loc[list(actions), SE_COL[c]].to_numpy(dtype=float) for c in coords], axis=1)
        SE = np.nan_to_num(SE, nan=0.0)
        prepared.append((Y, T, ns, SE))

        r = g2.evaluate_respondent(Y, T)
        if not r.testable:
            continue
        n_test += 1
        base_viol += int(r.violated)
        # per action: is it a violation, how many plays behind it, how far from centroid
        cen = Y.mean(axis=0)
        for i in range(len(actions)):
            better = np.where(T > T[i])[0]
            is_v = bool(better.size and g2.in_hull(Y[i], Y[better]))
            bucket = ("5-9" if ns[i] < 10 else "10-24" if ns[i] < 25 else
                      "25-99" if ns[i] < 100 else "100+")
            e = by_count.setdefault(bucket, {"actions": 0, "violations": 0})
            e["actions"] += 1
            e["violations"] += int(is_v)
            dist = float(np.linalg.norm(Y[i] - cen))
            (cen_v if is_v else cen_n).append(dist)

    for _ in range(N_JITTER):
        v = t = 0
        for Y, T, ns, SE in prepared:
            Yj = Y + rng.normal(size=Y.shape) * SE
            r = g2.evaluate_respondent(Yj, T)
            if not r.testable:
                continue
            t += 1
            v += int(r.violated)
        if t:
            jitter_rates.append(v / t)

    return {
        "testable": n_test,
        "p_unit": (base_viol / n_test) if n_test else None,
        "by_play_count": {k: {"actions": v["actions"], "violations": v["violations"],
                              "rate": v["violations"] / v["actions"] if v["actions"] else None}
                          for k, v in sorted(by_count.items())},
        "centroid_distance_violating_mean": float(np.mean(cen_v)) if cen_v else None,
        "centroid_distance_nonviolating_mean": float(np.mean(cen_n)) if cen_n else None,
        "jitter_p_unit_mean": float(np.mean(jitter_rates)) if jitter_rates else None,
        "jitter_p_unit_sd": float(np.std(jitter_rates)) if jitter_rates else None,
        "n_jitter": len(jitter_rates),
    }


def main():
    rng = np.random.default_rng(31337)
    df = cas.prepare()
    rec = {"floor": FLOOR, "n_jitter": N_JITTER}
    for space in SPACES:
        d, cmap, actions, units = build(df, space)
        rec[space] = {"n_actions": len(actions), "units": int(len(units)), "planes": {}}
        for pname, coords in PLANES.items():
            r = analyse(cmap, actions, units, coords, rng)
            rec[space]["planes"][pname] = r
            print("%-4s n=%2d %-14s testable=%5s P_unit=%s jitter=%s (sd %s)  centroid v=%s nv=%s"
                  % (space, len(actions), pname, r["testable"],
                     "%.4f" % r["p_unit"] if r["p_unit"] is not None else "na",
                     "%.4f" % r["jitter_p_unit_mean"] if r["jitter_p_unit_mean"] is not None else "na",
                     "%.4f" % r["jitter_p_unit_sd"] if r["jitter_p_unit_sd"] is not None else "na",
                     "%.3f" % r["centroid_distance_violating_mean"] if r["centroid_distance_violating_mean"] else "na",
                     "%.3f" % r["centroid_distance_nonviolating_mean"] if r["centroid_distance_nonviolating_mean"] else "na"),
                  flush=True)
            for b, e in r["by_play_count"].items():
                print("        plays %-6s actions=%6d violations=%6d rate=%s"
                      % (b, e["actions"], e["violations"],
                         "%.4f" % e["rate"] if e["rate"] is not None else "na"), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
