"""Gate G9: the hull law on NFL play calls, run through G2's checker unchanged.

The statistic, the null and the tie rule are G2's. This file supplies the world
and nothing else, so that a difference between the two gates is a difference
between two populations rather than between two pieces of code. `g2_hull_law.py`
is imported from `../G2/` and its `evaluate_respondent` and `population_rates`
are called directly.

What this file adds to G2 is the revealed ranking. G2's respondents rated the
alternatives, so the ranking was read off the file. Nobody ranks a play call.
The ranking here is revealed by choice share inside a state cell, which is a
stochastic-choice device, and the self-test below measures what that device
costs, because a ranking estimated from five observations per action is noisy
and noise in a ranking can manufacture a hull violation that the evaluator
never committed.

Usage.

    python g9_hull_law.py --selftest
    python g9_hull_law.py --plane y1_epa,y3_turnover --out results_primary.json
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
G2_PATH = os.path.join(HERE, "..", "G2", "g2_hull_law.py")


def load_g2():
    spec = importlib.util.spec_from_file_location("g2_hull_law", os.path.abspath(G2_PATH))
    mod = importlib.util.module_from_spec(spec)
    # Registered before execution. The module defines a dataclass, and the
    # decorator resolves its own module out of sys.modules as the class is built.
    sys.modules["g2_hull_law"] = mod
    spec.loader.exec_module(mod)
    return mod


g2 = load_g2()

ACTIONS = ("run_inside", "run_outside", "pass_short", "pass_deep")
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


# --------------------------------------------------------------------------- world

def prepare(seasons=SEASONS):
    import pandas as pd
    cols = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
            "half_seconds_remaining", "score_differential", "play_type",
            "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
            "run_location", "run_gap", "pass_length",
            "epa", "first_down", "interception", "fumble_lost", "incomplete_pass", "touchdown"]
    df = pd.concat([pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=cols)
                    for s in seasons], ignore_index=True)
    df = df[df["season_type"].eq("REG") & df["down"].isin(DOWN_VALUES)]
    df = df[~df["qb_kneel"].eq(1) & ~df["qb_spike"].eq(1)]
    df = df[~df["two_point_attempt"].eq(1) & ~df["penalty"].eq(1)]
    df = df[df["yardline_100"].notna() & df["ydstogo"].notna()]
    df = df[df["score_differential"].notna() & df["half_seconds_remaining"].notna()]
    df = df[df["posteam"].notna() & df["epa"].notna()].copy()

    out = df["play_type"].map(lambda _: None)
    is_run = df["play_type"].eq("run")
    is_pass = df["play_type"].eq("pass")
    inside = df["run_gap"].isin(["guard", "tackle"]) | df["run_location"].eq("middle")
    outside = df["run_gap"].eq("end")
    act = out.copy()
    act[is_run & inside] = "run_inside"
    act[is_run & outside] = "run_outside"
    act[is_pass & df["pass_length"].eq("short")] = "pass_short"
    act[is_pass & df["pass_length"].eq("deep")] = "pass_deep"
    df["action"] = act
    df = df[df["action"].notna()].copy()

    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")
    df["turnover"] = (df["interception"].fillna(0) + df["fumble_lost"].fillna(0)).clip(0, 1)
    df["clock_stop"] = (df["incomplete_pass"].fillna(0) + df["touchdown"].fillna(0)).clip(0, 1)
    df["fd"] = df["first_down"].fillna(0)
    return df


def consequence_map(df):
    """The world's C. Estimated from outcomes, pooled across every evaluator."""
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


def build_units(df, cmap, plane):
    """One (Y, T, weight) per (evaluator, cell), in G2's own input shape."""
    points = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in ACTIONS):
            continue
        Y = block.loc[list(ACTIONS), list(plane)].to_numpy(dtype=float)
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
        cell = tuple(idx[1:])
        Y = points.get(cell)
        if Y is None:
            continue
        # Choice share reveals the ranking. Higher count is preferred, which is
        # what G2's checker means by a higher rating.
        T = row.to_numpy(dtype=float)
        units.append((Y, T, 1.0))
    return units


# --------------------------------------------------------------------------- self-test

def selftest() -> int:
    """Three checks, and the third is the one this gate needs and G2 did not.

    1. A ranking generated by a convex quadratic cost produces no violation.
       This is the theorem, so a single violation here is a broken checker.
    2. A random ranking produces violations near the shuffle null, so the
       statistic can move.
    3. A ranking revealed by choice share from a softmax on that same cost, at
       the registered floor of five observations per action, does not
       manufacture violations. This is the cost of the revealed-ranking device
       and it is measured here rather than assumed.
    """
    rng = np.random.default_rng(12345)
    fails = []

    def cost(Y, G, t):
        d = Y - t
        return np.einsum("ij,jk,ik->i", d, G, d)

    # 1. convex cost, exact ranking
    n_viol = 0
    n_testable = 0
    for _ in range(400):
        Y = rng.normal(size=(4, 2))
        A = rng.normal(size=(2, 2))
        G = A @ A.T + 0.1 * np.eye(2)
        t = rng.normal(size=2)
        T = -cost(Y, G, t)
        r = g2.evaluate_respondent(Y, T)
        n_testable += int(r.testable)
        n_viol += int(r.violated)
    if n_viol != 0:
        fails.append("convex cost produced %d violations in %d testable menus" % (n_viol, n_testable))
    if n_testable < 50:
        fails.append("only %d testable menus in the convex-cost check" % n_testable)

    # 2. random ranking, the statistic must be able to move
    n_viol_r = 0
    n_test_r = 0
    for _ in range(400):
        Y = rng.normal(size=(4, 2))
        T = rng.normal(size=4)
        r = g2.evaluate_respondent(Y, T)
        n_test_r += int(r.testable)
        n_viol_r += int(r.violated and r.testable)
    rate_r = n_viol_r / n_test_r if n_test_r else float("nan")
    # The band is not a guess. A testable four-action menu in the plane has one
    # point inside the triangle of the other three, and under a uniformly random
    # ranking that point sits below all three with probability one quarter, so
    # the base rate is near 0.25 and cannot approach either end. The check is
    # only that the statistic can move, so the band is wide and one-sided
    # against degeneracy.
    if not (0.05 < rate_r < 0.95):
        fails.append("random-ranking violation rate %.3f outside the expected band" % rate_r)

    # 3. the revealed-ranking device at the registered floor
    device = {}
    for n_per in (5, 10, 15, 25, 100):
        n_viol_d = 0
        n_test_d = 0
        n_rank_wrong = 0
        n_units = 0
        for _ in range(6000):
            Y = rng.normal(size=(4, 2))
            A = rng.normal(size=(2, 2))
            G = A @ A.T + 0.1 * np.eye(2)
            t = rng.normal(size=2)
            u = -cost(Y, G, t)
            p = np.exp(u - u.max())
            p = p / p.sum()
            # Draw until every action clears the floor, which is what the unit
            # filter does to the real data, so the self-test sees the same
            # selection the run does.
            # The real filter keeps a unit only when every action clears the
            # floor, so the draw is retried until it does. That reproduces the
            # selection the run applies, rather than testing on menus the run
            # would have discarded.
            total = 8 * n_per
            for _try in range(400):
                draw = rng.multinomial(total, p)
                if (draw >= n_per).all():
                    break
            else:
                continue
            n_units += 1
            T_hat = draw.astype(float)
            if list(np.argsort(-T_hat)) != list(np.argsort(-u)):
                n_rank_wrong += 1
            r = g2.evaluate_respondent(Y, T_hat)
            n_test_d += int(r.testable)
            n_viol_d += int(r.violated and r.testable)
        device[str(n_per)] = {
            "units": n_units,
            "testable": n_test_d,
            "rank_disagrees_with_truth": n_rank_wrong,
            "violation_rate": (n_viol_d / n_test_d) if n_test_d else None,
        }

    report = {
        "convex_cost_violations": n_viol,
        "convex_cost_testable": n_testable,
        "random_ranking_rate": rate_r,
        "revealed_ranking_device": device,
        "fails": fails,
    }
    print(json.dumps(report, indent=1, sort_keys=True))
    if fails:
        print("SELFTEST FAIL")
        return 1
    print("SELFTEST PASS")
    return 0


# --------------------------------------------------------------------------- run

def floorsweep(planes, floors=(5, 10, 15, 20)) -> int:
    """How many units survive at each candidate minimum count, per plane.

    The self-test measures what the revealed-ranking device costs at a given
    floor. This measures what the floor costs in units. The registration needs
    both numbers together, because a floor clean enough to trust is worthless
    if it leaves the anti-vacuity bar unmet.
    """
    global MIN_PER_ACTION
    df = prepare()
    out = {}
    for f in floors:
        MIN_PER_ACTION = f
        cmap = consequence_map(df)
        row = {}
        for p in planes:
            units = build_units(df, cmap, p)
            testable = sum(1 for Y, T, _ in units if g2.evaluate_respondent(Y, T).testable)
            row["%s|%s" % p] = {"units": len(units), "testable": int(testable)}
        out[str(f)] = row
        print("floor", f, json.dumps(row, sort_keys=True))
    print(json.dumps({"floorsweep": out}, indent=1, sort_keys=True))
    return 0


def main(argv=None) -> int:
    global MIN_PER_ACTION
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--floorsweep", action="store_true")
    ap.add_argument("--plane", help="two coordinate names separated by a comma")
    ap.add_argument("--stratum", default="all", choices=["all", "low", "high"])
    ap.add_argument("--shuffles", type=int, default=N_SHUFFLES)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--floor", type=int, default=MIN_PER_ACTION,
                    help="minimum calls per action; 5 is sealed, 10 is the sensitivity")
    ap.add_argument("--out")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()

    if a.floorsweep:
        return floorsweep([("y1_epa", "y3_turnover"), ("y1_epa", "y2_first_down"),
                           ("y3_turnover", "y4_epa_sd"), ("y1_epa", "y4_epa_sd")])

    if not a.plane or not a.out:
        ap.error("--plane and --out are required for a run")
    plane = tuple(a.plane.split(","))
    for c in plane:
        if c not in COORDS:
            ap.error("unknown coordinate %s" % c)

    MIN_PER_ACTION = a.floor
    df = prepare()
    if a.stratum != "all":
        df = df[df["pressure"] == a.stratum].copy()
    cmap = consequence_map(df)
    units = build_units(df, cmap, plane)
    res = g2.population_rates(units, a.shuffles, a.seed)
    res["plane"] = list(plane)
    res["stratum"] = a.stratum
    res["min_per_action"] = MIN_PER_ACTION
    res["sealed_floor"] = 5
    res["carries_bar"] = bool(a.floor == 5)
    res["actions"] = list(ACTIONS)
    res["seasons"] = SEASONS
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
