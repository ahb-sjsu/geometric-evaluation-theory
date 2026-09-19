"""Event-presence probe 5: testable under G2's own definition.

Probe 4 counted cells whose four consequence points span two dimensions. That
is not the count G2 used. G2's anti-vacuity test is stronger and is the right
one, because a menu whose points are in convex position cannot violate the
hull law under any ranking whatsoever. Its testable count is the number of
units in which some point lies in the convex hull of the others.

This probe imports G2's own checker so the two worlds are counted by identical
code. It reads outcomes and never reads which evaluator called which play. No
ranking is formed and no violation is computed.
"""
import importlib.util
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

G2 = "/home/claude/g2_hull_law.py"
spec = importlib.util.spec_from_file_location("g2", G2)
g2 = importlib.util.module_from_spec(spec)
# Register before executing. The module defines a dataclass, and the decorator
# resolves its own module out of sys.modules while the class body is built.
sys.modules["g2"] = g2
spec.loader.exec_module(g2)

CACHE = "/home/claude/nfl_cache"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/g9_probe5.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
MIN_PER_ACTION = 5
ACTIONS = ("run_inside", "run_outside", "pass_short", "pass_deep")
COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")

COLS = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
        "half_seconds_remaining", "score_differential", "play_type",
        "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
        "run_location", "run_gap", "pass_length",
        "epa", "first_down", "interception", "fumble_lost", "incomplete_pass", "touchdown"]


def load():
    return pd.concat(
        [pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=COLS)
         for s in SEASONS], ignore_index=True)


def classify(df):
    out = pd.Series(pd.NA, index=df.index, dtype="object")
    is_run = df["play_type"].eq("run")
    is_pass = df["play_type"].eq("pass")
    inside = df["run_gap"].isin(["guard", "tackle"]) | df["run_location"].eq("middle")
    outside = df["run_gap"].eq("end")
    out[is_run & inside] = "run_inside"
    out[is_run & outside] = "run_outside"
    out[is_pass & df["pass_length"].eq("short")] = "pass_short"
    out[is_pass & df["pass_length"].eq("deep")] = "pass_deep"
    return out


def prepare():
    df = load()
    df = df[df["season_type"].eq("REG") & df["down"].isin(DOWN_VALUES)]
    df = df[~df["qb_kneel"].eq(1) & ~df["qb_spike"].eq(1)]
    df = df[~df["two_point_attempt"].eq(1) & ~df["penalty"].eq(1)]
    df = df[df["yardline_100"].notna() & df["ydstogo"].notna()]
    df = df[df["score_differential"].notna() & df["half_seconds_remaining"].notna()]
    df = df[df["posteam"].notna() & df["epa"].notna()].copy()
    df["action"] = classify(df)
    df = df[df["action"].notna()].copy()
    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")
    df["turnover"] = (df["interception"].fillna(0) + df["fumble_lost"].fillna(0)).clip(0, 1)
    df["clock_stop"] = (df["incomplete_pass"].fillna(0) + df["touchdown"].fillna(0)).clip(0, 1)
    df["fd"] = df["first_down"].fillna(0)
    return df


CELLKEYS = ["down", "b_togo", "b_yard", "b_score"]


def consequence_map(sub):
    g = sub.groupby(CELLKEYS + ["action"], observed=True)
    cmap = g.agg(y1_epa=("epa", "mean"), y2_first_down=("fd", "mean"),
                 y3_turnover=("turnover", "mean"), y4_epa_sd=("epa", "std"),
                 y5_clock_stop=("clock_stop", "mean"), n=("epa", "size")).reset_index()
    wide = cmap.pivot_table(index=CELLKEYS, columns="action", values="n", fill_value=0)
    for a in ACTIONS:
        if a not in wide.columns:
            wide[a] = 0
    ok = wide[(wide[list(ACTIONS)] >= MIN_PER_ACTION).all(axis=1)].index
    cmap = cmap.set_index(CELLKEYS)
    cmap = cmap.loc[cmap.index.isin(ok)].reset_index()
    for c in COORDS:
        v = cmap[c].astype(float)
        sd = v.std()
        cmap[c] = (v - v.mean()) / (sd if sd and np.isfinite(sd) and sd > 0 else 1.0)
    return cmap, ok


def testable_cells(cmap, plane):
    """G2's rule. A menu is testable when some point lies in the convex hull of the others."""
    out = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in ACTIONS):
            continue
        Y = block.loc[list(ACTIONS), list(plane)].to_numpy(dtype=float)
        if not np.isfinite(Y).all():
            continue
        t = False
        for i in range(len(ACTIONS)):
            others = np.delete(Y, i, axis=0)
            if g2.in_hull(Y[i], others):
                t = True
                break
        out[key if isinstance(key, tuple) else (key,)] = t
    return out


def main():
    df = prepare()
    rec = {"min_per_action": MIN_PER_ACTION, "coords": list(COORDS),
           "testable_rule": "some action point lies in the convex hull of the other three, G2 rule"}

    for tag, sub in (("overall", df), ("low_pressure", df[df["pressure"] == "low"]),
                     ("high_pressure", df[df["pressure"] == "high"])):
        cmap, ok = consequence_map(sub)
        # Units are (team, cell) with every action present at the floor.
        gu = sub.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
        for a in ACTIONS:
            if a not in gu.columns:
                gu[a] = 0
        unit_ok = (gu[list(ACTIONS)] >= MIN_PER_ACTION).all(axis=1)
        units = gu[unit_ok]
        planes = {}
        for p in itertools.combinations(COORDS, 2):
            tc = testable_cells(cmap, p)
            n_cells_testable = int(sum(tc.values()))
            keys = units.index.droplevel(0)
            flags = np.array([tc.get(tuple(k) if isinstance(k, tuple) else (k,), False) for k in keys])
            planes["%s|%s" % p] = {
                "cells_total": int(len(tc)),
                "cells_testable": n_cells_testable,
                "units_total": int(len(units)),
                "units_testable": int(flags.sum()),
            }
        rec[tag] = {"n_cells": int(len(ok)), "n_units": int(len(units)), "planes": planes}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)

    for tag in ("overall", "low_pressure", "high_pressure"):
        print("===", tag, "cells", rec[tag]["n_cells"], "units", rec[tag]["n_units"])
        for k, v in sorted(rec[tag]["planes"].items(), key=lambda kv: -kv[1]["units_testable"]):
            print("   %-28s cells testable %4d/%4d   units testable %5d/%5d" % (
                k, v["cells_testable"], v["cells_total"], v["units_testable"], v["units_total"]))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
