"""Event-presence probe for G9b: the hull law in the full consequence space.

G9 read the law on two coordinates because four actions in a five-dimensional
space can never put a point inside the hull of the others. Measured, 0 testable
menus in 4,000 trials. Projection was therefore forced, and it manufactures
violations at 0.1506 in that configuration, which is half of what the one
refuting plane showed.

The fix is more actions, not a cleverer statistic. By Radon's theorem a menu in
d dimensions needs d + 2 points before a violation is possible at all, so a
five-dimensional consequence space needs at least seven actions, and
comfortably more to be testable often.

This probe asks whether the data supports that. It counts, for several
candidate action spaces, how many state cells carry every action at the floor
and how many units are testable in the FULL five-dimensional space under G2's
own rule. It computes no hull violation and forms no ranking.
"""
import importlib.util
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
OUT = "/home/claude/deploy/g9b_probe.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
CELLKEYS = ["down", "b_togo", "b_yard", "b_score"]
COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")

COLS = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
        "half_seconds_remaining", "score_differential", "play_type",
        "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
        "run_location", "run_gap", "pass_length", "pass_location",
        "epa", "first_down", "interception", "fumble_lost", "incomplete_pass", "touchdown"]


def load():
    return pd.concat([pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=COLS)
                      for s in SEASONS], ignore_index=True)


def prepare():
    df = load()
    df = df[df["season_type"].eq("REG") & df["down"].isin(DOWN_VALUES)]
    df = df[~df["qb_kneel"].eq(1) & ~df["qb_spike"].eq(1)]
    df = df[~df["two_point_attempt"].eq(1) & ~df["penalty"].eq(1)]
    df = df[df["yardline_100"].notna() & df["ydstogo"].notna()]
    df = df[df["score_differential"].notna() & df["half_seconds_remaining"].notna()]
    df = df[df["posteam"].notna() & df["epa"].notna()].copy()
    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")
    df["turnover"] = (df["interception"].fillna(0) + df["fumble_lost"].fillna(0)).clip(0, 1)
    df["clock_stop"] = (df["incomplete_pass"].fillna(0) + df["touchdown"].fillna(0)).clip(0, 1)
    df["fd"] = df["first_down"].fillna(0)
    return df


# --------------------------------------------------------------------------- action spaces

def space_a13(df):
    """Seven run types by gap and side, six pass types by depth and side."""
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


def space_a9(df):
    """Three run sides, six pass types."""
    out = pd.Series(pd.NA, index=df.index, dtype="object")
    r, p = df["play_type"].eq("run"), df["play_type"].eq("pass")
    for side in ("left", "middle", "right"):
        out[r & df["run_location"].eq(side)] = "run_%s" % side
    for d in ("short", "deep"):
        for side in ("left", "middle", "right"):
            out[p & df["pass_length"].eq(d) & df["pass_location"].eq(side)] = "pass_%s_%s" % (d, side)
    return out


def space_a7(df):
    """Three run types, three short passes, deep pass pooled."""
    out = pd.Series(pd.NA, index=df.index, dtype="object")
    r, p = df["play_type"].eq("run"), df["play_type"].eq("pass")
    inside = df["run_gap"].isin(["guard", "tackle"]) | df["run_location"].eq("middle")
    out[r & inside] = "run_inside"
    out[r & df["run_gap"].eq("end") & df["run_location"].eq("left")] = "run_end_left"
    out[r & df["run_gap"].eq("end") & df["run_location"].eq("right")] = "run_end_right"
    for side in ("left", "middle", "right"):
        out[p & df["pass_length"].eq("short") & df["pass_location"].eq(side)] = "pass_short_%s" % side
    out[p & df["pass_length"].eq("deep")] = "pass_deep"
    return out


SPACES = {"A13": space_a13, "A9": space_a9, "A7": space_a7}
FLOORS = (5, 10)


def consequence_map(sub, actions, floor):
    g = sub.groupby(CELLKEYS + ["action"], observed=True)
    cmap = g.agg(y1_epa=("epa", "mean"), y2_first_down=("fd", "mean"),
                 y3_turnover=("turnover", "mean"), y4_epa_sd=("epa", "std"),
                 y5_clock_stop=("clock_stop", "mean"), n=("epa", "size")).reset_index()
    wide = cmap.pivot_table(index=CELLKEYS, columns="action", values="n", fill_value=0)
    for a in actions:
        if a not in wide.columns:
            wide[a] = 0
    ok = wide[(wide[list(actions)] >= floor).all(axis=1)].index
    cmap = cmap.set_index(CELLKEYS)
    cmap = cmap.loc[cmap.index.isin(ok)].reset_index()
    for c in COORDS:
        v = cmap[c].astype(float)
        sd = v.std()
        cmap[c] = (v - v.mean()) / (sd if sd and np.isfinite(sd) and sd > 0 else 1.0)
    return cmap, ok


def testable_cells(cmap, actions):
    """G2's rule, in the FULL five-dimensional space this time."""
    out = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in actions):
            continue
        Y = block.loc[list(actions), list(COORDS)].to_numpy(dtype=float)
        if not np.isfinite(Y).all():
            continue
        t = False
        for i in range(len(actions)):
            if g2.in_hull(Y[i], np.delete(Y, i, axis=0)):
                t = True
                break
        out[key if isinstance(key, tuple) else (key,)] = t
    return out


def main():
    df = prepare()
    rec = {"seasons": SEASONS, "coords": list(COORDS), "radon_bound_for_5d": 7,
           "note": "a menu in five dimensions needs at least seven actions before a violation "
                   "is possible at all"}
    for name, fn in SPACES.items():
        d = df.copy()
        d["action"] = fn(d)
        d = d[d["action"].notna()].copy()
        actions = sorted(d["action"].unique())
        entry = {"n_actions": len(actions), "actions": actions,
                 "decisions": int(len(d)),
                 "action_counts": {k: int(v) for k, v in d["action"].value_counts().items()}}
        for floor in FLOORS:
            cmap, ok = consequence_map(d, actions, floor)
            tc = testable_cells(cmap, actions)
            counts = d.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
            for a in actions:
                if a not in counts.columns:
                    counts[a] = 0
            counts = counts[list(actions)]
            units = counts[(counts >= floor).all(axis=1)]
            keys = units.index.droplevel(0)
            flags = np.array([tc.get(tuple(k) if isinstance(k, tuple) else (k,), False)
                              for k in keys]) if len(units) else np.array([])
            hi = d[d["pressure"] == "high"]
            entry["floor_%d" % floor] = {
                "cells_all_actions": int(len(ok)),
                "cells_testable_full_space": int(sum(tc.values())),
                "units_all_actions": int(len(units)),
                "units_testable_full_space": int(flags.sum()) if flags.size else 0,
                "decisions_high_pressure": int(len(hi)),
            }
            print("%-4s actions=%2d floor=%2d cells=%4d testable_cells=%4d units=%5d testable_units=%5d"
                  % (name, len(actions), floor, len(ok), sum(tc.values()), len(units),
                     int(flags.sum()) if flags.size else 0))
        rec[name] = entry

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
