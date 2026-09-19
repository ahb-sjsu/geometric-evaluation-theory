"""Event-presence probe 4: are the menus genuinely two dimensional?

The hull law is empty on a menu whose consequence points are collinear, which
is why G2's probe counted respondents holding a genuinely two-dimensional
menu before that gate could be sealed. This does the same count here.

It builds the consequence map of the draft registration Section 3 and then
asks, for each state cell and each of the ten consequence planes, whether the
four action points span two dimensions rather than lying on a line.

This reads outcomes and never reads which evaluator called which play. No
ranking is formed and no hull violation is computed.
"""
import itertools
import json
import os

import numpy as np
import pandas as pd

CACHE = "/home/claude/nfl_cache"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/g9_probe4.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
MIN_PER_ACTION = 5
ACTIONS = ("run_inside", "run_outside", "pass_short", "pass_deep")
COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")
# Registered collinearity tolerance. The four centred points are in general
# position when the ratio of the smaller to the larger singular value exceeds
# this, after each coordinate is standardised across cells so the two axes of a
# plane are comparable.
TAU = 0.05

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


def main():
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

    cellkeys = ["down", "b_togo", "b_yard", "b_score"]

    def build(sub, tag):
        g = sub.groupby(cellkeys + ["action"], observed=True)
        cmap = g.agg(y1_epa=("epa", "mean"), y2_first_down=("fd", "mean"),
                     y3_turnover=("turnover", "mean"), y4_epa_sd=("epa", "std"),
                     y5_clock_stop=("clock_stop", "mean"), n=("epa", "size"))
        cmap = cmap.reset_index()
        # A cell enters only when every action is present at the registered floor.
        wide = cmap.pivot_table(index=cellkeys, columns="action", values="n", fill_value=0)
        for a in ACTIONS:
            if a not in wide.columns:
                wide[a] = 0
        ok_cells = wide[(wide[list(ACTIONS)] >= MIN_PER_ACTION).all(axis=1)].index
        cmap = cmap.set_index(cellkeys)
        cmap = cmap.loc[cmap.index.isin(ok_cells)].reset_index()

        # Standardise each coordinate across cells so a plane's two axes are
        # comparable before any collinearity is judged.
        z = cmap.copy()
        for c in COORDS:
            v = z[c].astype(float)
            sd = v.std()
            z[c] = (v - v.mean()) / (sd if sd and np.isfinite(sd) and sd > 0 else 1.0)

        res = {}
        planes = list(itertools.combinations(COORDS, 2))
        grouped = dict(list(z.groupby(cellkeys, observed=True)))
        for p in planes:
            spanning = 0
            total = 0
            ratios = []
            for _, block in grouped.items():
                block = block.set_index("action")
                if not all(a in block.index for a in ACTIONS):
                    continue
                P = block.loc[list(ACTIONS), list(p)].to_numpy(dtype=float)
                if not np.isfinite(P).all():
                    continue
                total += 1
                Q = P - P.mean(axis=0, keepdims=True)
                s = np.linalg.svd(Q, compute_uv=False)
                r = float(s[1] / s[0]) if s[0] > 0 else 0.0
                ratios.append(r)
                if r > TAU:
                    spanning += 1
            res["%s|%s" % p] = {
                "cells_considered": total,
                "cells_in_general_position": spanning,
                "median_singular_ratio": float(np.median(ratios)) if ratios else None,
            }
        return {"n_cells": int(len(ok_cells)), "planes": res}

    rec = {"tau": TAU, "min_per_action": MIN_PER_ACTION, "coords": list(COORDS),
           "decisions": int(len(df))}
    rec["overall"] = build(df, "overall")
    rec["low_pressure"] = build(df[df["pressure"] == "low"], "low")
    rec["high_pressure"] = build(df[df["pressure"] == "high"], "high")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)

    for tag in ("overall", "low_pressure", "high_pressure"):
        print("===", tag, "cells", rec[tag]["n_cells"])
        for k, v in sorted(rec[tag]["planes"].items()):
            print("   %-28s general position %4d of %4d   median ratio %s" % (
                k, v["cells_in_general_position"], v["cells_considered"],
                "%.3f" % v["median_singular_ratio"] if v["median_singular_ratio"] is not None else "na"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
