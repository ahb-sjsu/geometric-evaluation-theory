"""Characterize the action space: how the hull-law statistic depends on how
finely the menu is cut, and on how much of the consequence space is read.

Exploratory. Registered nowhere. This measures the instrument, not a claim.

Why it exists. G9 read the law with four play calls and found expected points
added against first down probability violating ABOVE its null. G9b reads the
same coordinates with thirteen play calls and finds the same pair BELOW its
null. Both cannot be a fact about coaches. The action space is a free parameter
that G2 and G9 both fixed by hand and neither characterized, and the verdict
moves with it.

Two aggregations are computed, because the one both earlier gates used
saturates. A unit counts as violating if ANY action violates, so a menu of
thirteen actions has thirteen chances to trip it and the rate runs to one. The
per-action rate does not saturate.

    P_unit    fraction of testable units with at least one violation
    P_action  fraction of (unit, action) pairs that are violations

The action spaces form a strict refinement chain, so a coarser space is exactly
a pooling of a finer one and the comparison is not confounded with which plays
are included.

    A4  subset of A7 subset of A13

No null is computed here. The null costs two hundred passes and this is a
survey, so the descriptive surface comes first and the permutation tests go
only where the surface says they are worth running.
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

CACHE = "/home/claude/nfl_cache"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/action_space_surface.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
CELLKEYS = ["down", "b_togo", "b_yard", "b_score"]
COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")
FLOOR = 5

COLS = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
        "half_seconds_remaining", "score_differential", "play_type",
        "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
        "run_location", "run_gap", "pass_length", "pass_location",
        "epa", "first_down", "interception", "fumble_lost", "incomplete_pass", "touchdown"]


def prepare():
    df = pd.concat([pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=COLS)
                    for s in SEASONS], ignore_index=True)
    df = df[df["season_type"].eq("REG") & df["down"].isin(DOWN_VALUES)]
    df = df[~df["qb_kneel"].eq(1) & ~df["qb_spike"].eq(1)]
    df = df[~df["two_point_attempt"].eq(1) & ~df["penalty"].eq(1)]
    df = df[df["yardline_100"].notna() & df["ydstogo"].notna()]
    df = df[df["score_differential"].notna() & df["half_seconds_remaining"].notna()]
    df = df[df["posteam"].notna() & df["epa"].notna()].copy()
    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["turnover"] = (df["interception"].fillna(0) + df["fumble_lost"].fillna(0)).clip(0, 1)
    df["clock_stop"] = (df["incomplete_pass"].fillna(0) + df["touchdown"].fillna(0)).clip(0, 1)
    df["fd"] = df["first_down"].fillna(0)
    return df


# --------------------------------------------------------------------------- the chain

def a13(df):
    out = pd.Series(pd.NA, index=df.index, dtype="object")
    r, p = df["play_type"].eq("run"), df["play_type"].eq("pass")
    loc, gap = df["run_location"], df["run_gap"]
    out[r & loc.eq("middle")] = "run_middle"
    for side in ("left", "right"):
        for g in ("end", "tackle", "guard"):
            out[r & loc.eq(side) & gap.eq(g)] = "run_%s_%s" % (side, g)
    for d in ("short", "deep"):
        for side in ("left", "middle", "right"):
            out[p & df["pass_length"].eq(d) & df["pass_location"].eq(side)] = "pass_%s_%s" % (d, side)
    return out


# Each coarser space is a POOLING of A13, so the chain is a strict refinement
# and a coarser space contains exactly the same plays.
POOL_A7 = {
    "run_middle": "run_inside", "run_left_tackle": "run_inside",
    "run_left_guard": "run_inside", "run_right_tackle": "run_inside",
    "run_right_guard": "run_inside",
    "run_left_end": "run_left_end", "run_right_end": "run_right_end",
    "pass_short_left": "pass_short_left", "pass_short_middle": "pass_short_middle",
    "pass_short_right": "pass_short_right",
    "pass_deep_left": "pass_deep", "pass_deep_middle": "pass_deep",
    "pass_deep_right": "pass_deep",
}
POOL_A4 = {k: ("run_inside" if v == "run_inside" else
               "run_outside" if v.startswith("run_") else
               "pass_short" if v.startswith("pass_short") else "pass_deep")
           for k, v in POOL_A7.items()}
POOL_A9 = {k: (k if k.startswith("pass_") else
               "run_left" if "left" in k else
               "run_right" if "right" in k else "run_middle")
           for k in POOL_A7}

SPACES = {"A4": POOL_A4, "A7": POOL_A7, "A9": POOL_A9, "A13": None}


def consequence_map(df, actions):
    g = df.groupby(CELLKEYS + ["action"], observed=True)
    cmap = g.agg(y1_epa=("epa", "mean"), y2_first_down=("fd", "mean"),
                 y3_turnover=("turnover", "mean"), y4_epa_sd=("epa", "std"),
                 y5_clock_stop=("clock_stop", "mean"), n=("epa", "size")).reset_index()
    wide = cmap.pivot_table(index=CELLKEYS, columns="action", values="n", fill_value=0)
    for a in actions:
        if a not in wide.columns:
            wide[a] = 0
    ok = wide[(wide[list(actions)] >= FLOOR).all(axis=1)].index
    cmap = cmap.set_index(CELLKEYS)
    cmap = cmap.loc[cmap.index.isin(ok)].reset_index()
    for c in COORDS:
        v = cmap[c].astype(float)
        sd = v.std()
        cmap[c] = (v - v.mean()) / (sd if sd and np.isfinite(sd) and sd > 0 else 1.0)
    return cmap, ok


def surface_for(df, name, pool):
    d = df.copy()
    base = a13(d)
    d["action"] = base if pool is None else base.map(pool)
    d = d[d["action"].notna()].copy()
    actions = sorted(d["action"].unique())
    cmap, ok = consequence_map(d, actions)

    counts = d.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
    for a in actions:
        if a not in counts.columns:
            counts[a] = 0
    counts = counts[list(actions)]
    units = counts[(counts >= FLOOR).all(axis=1)]

    points = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in actions):
            continue
        k = key if isinstance(key, tuple) else (key,)
        points[k] = block.loc[list(actions), list(COORDS)].to_numpy(dtype=float)

    entry = {"n_actions": len(actions), "actions": actions,
             "decisions": int(len(d)), "cells": int(len(ok)), "units": int(len(units)),
             "by_dimension": {}}

    for kdim in (2, 3, 4, 5):
        subs = list(itertools.combinations(range(5), kdim))
        rows = []
        for sub in subs:
            cols = list(sub)
            n_test = n_unit_viol = n_act_viol = 0
            viol_counts = []
            for idx, row in units.iterrows():
                Y = points.get(tuple(idx[1:]))
                if Y is None:
                    continue
                P = Y[:, cols]
                if not np.isfinite(P).all():
                    continue
                T = row.to_numpy(dtype=float)
                r = g2.evaluate_respondent(P, T)
                if not r.testable:
                    continue
                n_test += 1
                n_unit_viol += int(r.violated)
                n_act_viol += int(r.n_violations)
                viol_counts.append(int(r.n_violations))
            if n_test:
                rows.append({"coords": [COORDS[i] for i in sub],
                             "testable": n_test,
                             "p_unit": n_unit_viol / n_test,
                             "p_action": n_act_viol / (n_test * len(actions)),
                             "mean_violations_per_unit": float(np.mean(viol_counts))})
        if rows:
            entry["by_dimension"][str(kdim)] = {
                "n_subsets_with_data": len(rows),
                "testable_mean": float(np.mean([r["testable"] for r in rows])),
                "p_unit_mean": float(np.mean([r["p_unit"] for r in rows])),
                "p_action_mean": float(np.mean([r["p_action"] for r in rows])),
                "mean_violations_per_unit": float(np.mean([r["mean_violations_per_unit"] for r in rows])),
                "subsets": rows,
            }
            e = entry["by_dimension"][str(kdim)]
            print("%-4s n=%2d k=%d subsets=%2d testable=%7.1f  P_unit=%.4f  P_action=%.4f  viol/unit=%.2f"
                  % (name, len(actions), kdim, len(rows), e["testable_mean"],
                     e["p_unit_mean"], e["p_action_mean"], e["mean_violations_per_unit"]),
                  flush=True)
    return entry


def main():
    df = prepare()
    rec = {"floor": FLOOR, "coords": list(COORDS),
           "chain": "A4 subset of A7 subset of A13, each coarser space a pooling of A13",
           "aggregations": {"p_unit": "fraction of testable units with at least one violation",
                            "p_action": "fraction of (unit, action) pairs that are violations"}}
    for name, pool in SPACES.items():
        rec[name] = surface_for(df, name, pool)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
