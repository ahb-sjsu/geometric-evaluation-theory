"""Event-presence probe, third question: who is the evaluator?

G2 tested the hull law per respondent. A gate here needs the same thing, so
the unit has to be an evaluator holding a menu, not the league holding a menu.
This counts how many (evaluator, cell) units survive at each of three
candidate evaluator definitions, which is the number that decides which
definition the registration can carry.

Still a probe. Nothing is ranked and no hull violation is computed.
"""
import json
import os

import numpy as np
import pandas as pd

CACHE = "/home/claude/nfl_cache"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/g9_probe3.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
MIN_PER_ACTION = 5
ACTIONS = ("run_inside", "run_outside", "pass_short", "pass_deep")

COLS = ["season", "season_type", "posteam", "down", "ydstogo", "yardline_100",
        "half_seconds_remaining", "score_differential", "play_type",
        "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
        "run_location", "run_gap", "pass_length"]


def load():
    frames = []
    for s in SEASONS:
        frames.append(pd.read_parquet(os.path.join(CACHE, "pbp_%d.parquet" % s), columns=COLS))
    return pd.concat(frames, ignore_index=True)


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
    df = df[df["posteam"].notna()].copy()
    df["action"] = classify(df)
    df = df[df["action"].notna()].copy()

    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")
    df["team_season"] = df["posteam"].astype(str) + "_" + df["season"].astype(str)

    rec = {"decisions": int(len(df)), "min_per_action": MIN_PER_ACTION,
           "n_teams": int(df["posteam"].nunique()),
           "n_team_seasons": int(df["team_season"].nunique())}

    def units(sub, evalcol, need_all_four):
        if len(sub) == 0:
            return {}
        g = sub.groupby([evalcol, "down", "b_togo", "b_yard", "b_score"], observed=True)["action"]
        counts = g.value_counts().unstack(fill_value=0)
        for a in ACTIONS:
            if a not in counts.columns:
                counts[a] = 0
        counts = counts[list(ACTIONS)]
        if need_all_four:
            ok = (counts >= MIN_PER_ACTION).all(axis=1)
        else:
            ok = (counts >= MIN_PER_ACTION).sum(axis=1) >= 3
        n_eval = counts[ok].index.get_level_values(0).nunique() if ok.any() else 0
        return {
            "units_total": int(len(counts)),
            "units_qualifying": int(ok.sum()),
            "evaluators_with_at_least_one_unit": int(n_eval),
            "decisions_in_qualifying_units": int(counts[ok].sum().sum()),
            "median_unit_size": float(counts[ok].sum(axis=1).median()) if ok.any() else None,
        }

    for name, col in (("league", None), ("team", "posteam"), ("team_season", "team_season")):
        if col is None:
            df["_all"] = "league"
            col = "_all"
        rec[name] = {
            "all_four_actions": {
                "overall": units(df, col, True),
                "low_pressure": units(df[df["pressure"] == "low"], col, True),
                "high_pressure": units(df[df["pressure"] == "high"], col, True),
            },
            "three_or_more_actions": {
                "overall": units(df, col, False),
                "high_pressure": units(df[df["pressure"] == "high"], col, False),
            },
        }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
