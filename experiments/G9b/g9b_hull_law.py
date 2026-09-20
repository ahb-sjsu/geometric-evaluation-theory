#!/usr/bin/env python3
"""Gate G9b: the hull law read on subsets of the consequence space, not only planes.

Same statistic, same null, same tie rule, same checker as G2 and G9. The only
new argument is which coordinates are read. That keeps three gates comparable
without adjustment, which is the point of importing `g2_hull_law.py` rather
than reimplementing it for a third time.

Thirteen play calls instead of G9's four, because nothing above two dimensions
is testable with four actions. Probe 1 measured that.

Usage.

    python g9b_hull_law.py --selftest
    python g9b_hull_law.py --coords y1_epa,y2_first_down,y3_turnover --out r.json
"""
from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g2 = _load("g2_hull_law", os.path.join(HERE, "..", "G2", "g2_hull_law.py"))

COORDS = ("y1_epa", "y2_first_down", "y3_turnover", "y4_epa_sd", "y5_clock_stop")
DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
CELLKEYS = ["down", "b_togo", "b_yard", "b_score"]
MIN_PER_ACTION = 5
N_SHUFFLES = 200
SEED = 20260919
CACHE = os.environ.get("G9_CACHE", "/home/claude/nfl_cache")
SEASONS = list(range(2015, 2025))

ACTIONS = tuple(sorted([
    "run_middle",
    "run_left_end", "run_left_tackle", "run_left_guard",
    "run_right_end", "run_right_tackle", "run_right_guard",
    "pass_short_left", "pass_short_middle", "pass_short_right",
    "pass_deep_left", "pass_deep_middle", "pass_deep_right",
]))

COLS = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
        "half_seconds_remaining", "score_differential", "play_type",
        "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
        "run_location", "run_gap", "pass_length", "pass_location",
        "epa", "first_down", "interception", "fumble_lost", "incomplete_pass", "touchdown"]


def classify(df):
    import pandas as pd
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


def prepare():
    import pandas as pd
    df = pd.concat([pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=COLS)
                    for s in SEASONS], ignore_index=True)
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
    df["turnover"] = (df["interception"].fillna(0) + df["fumble_lost"].fillna(0)).clip(0, 1)
    df["clock_stop"] = (df["incomplete_pass"].fillna(0) + df["touchdown"].fillna(0)).clip(0, 1)
    df["fd"] = df["first_down"].fillna(0)
    return df


def consequence_map(df):
    g = df.groupby(CELLKEYS + ["action"], observed=True)
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
    return cmap


def build_units(df, cmap, coords):
    points = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in ACTIONS):
            continue
        Y = block.loc[list(ACTIONS), list(coords)].to_numpy(dtype=float)
        if np.isfinite(Y).all():
            points[key if isinstance(key, tuple) else (key,)] = Y
    counts = df.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size().unstack(fill_value=0)
    for a in ACTIONS:
        if a not in counts.columns:
            counts[a] = 0
    counts = counts[list(ACTIONS)]
    counts = counts[(counts >= MIN_PER_ACTION).all(axis=1)]
    units = []
    for idx, row in counts.iterrows():
        Y = points.get(tuple(idx[1:]))
        if Y is None:
            continue
        units.append((Y, row.to_numpy(dtype=float), 1.0))
    return units


def selftest() -> int:
    """The checker must reproduce the theorem at this action count and dimension."""
    rng = np.random.default_rng(777)
    fails = []
    report = {}
    for dim in (2, 3, 4):
        n_viol = n_test = 0
        for _ in range(500):
            Y = rng.normal(size=(13, dim))
            A = rng.normal(size=(dim, dim))
            G = A @ A.T + 0.1 * np.eye(dim)
            t = rng.normal(size=dim)
            d = Y - t
            T = -np.einsum("ij,jk,ik->i", d, G, d)
            r = g2.evaluate_respondent(Y, T)
            n_test += int(r.testable)
            n_viol += int(r.violated and r.testable)
        report[str(dim)] = {"testable": n_test, "violations": n_viol}
        if n_viol:
            fails.append("dim %d: convex cost produced %d violations" % (dim, n_viol))
        if n_test < 50:
            fails.append("dim %d: only %d testable menus" % (dim, n_test))
    print(json.dumps(report, indent=1, sort_keys=True))
    if fails:
        for f in fails:
            print("  -", f)
        print("SELFTEST FAIL")
        return 1
    print("SELFTEST PASS")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--coords", help="comma separated coordinate names")
    ap.add_argument("--shuffles", type=int, default=N_SHUFFLES)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not (a.coords and a.out):
        ap.error("--coords and --out are required")
    coords = tuple(a.coords.split(","))
    for c in coords:
        if c not in COORDS:
            ap.error("unknown coordinate %s" % c)
    df = prepare()
    cmap = consequence_map(df)
    units = build_units(df, cmap, coords)
    res = g2.population_rates(units, a.shuffles, a.seed)
    res.update({"coords": list(coords), "n_coords": len(coords),
                "actions": list(ACTIONS), "n_actions": len(ACTIONS),
                "min_per_action": MIN_PER_ACTION, "seasons": SEASONS})
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
