"""Event-presence probe, second action space: the play call.

The fourth-down probe measured 35,406 decisions but only 41 state cells in
which all three actions are observed at least three times, and 11 of those
under time pressure. The hull law needs a menu of at least three actions whose
consequences are not collinear, so a gate built on fourth downs would be
testable in 41 cells against G2's 489 respondents. That is the probe doing its
job, and the reason this second probe exists.

The play call sits one level down and is contested on every snap. The action
space is four calls that nflfastR records directly, chosen because their
consequence vectors differ in more than one coordinate: an inside run, an
outside run, a short pass and a deep pass trade yards against clock, against
turnover risk, against variance.

Still a probe. No hypothesis statistic is computed and no action is ranked.
"""
import json
import os
import urllib.request

import numpy as np
import pandas as pd

CACHE = "/home/claude/nfl_cache"
URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_%d.parquet"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/g9_probe2.json"

DOWN_VALUES = (1, 2, 3)
YDSTOGO_BINS = [0, 3, 6, 10, 100]
YARDLINE_BINS = [0, 20, 50, 80, 100]
SCOREDIFF_BINS = [-100, -8, -3, 3, 8, 100]
MIN_PER_ACTION = 5

ACTIONS = ("run_inside", "run_outside", "pass_short", "pass_deep")

COLS = [
    "game_id", "play_id", "season", "season_type", "down", "ydstogo", "yardline_100",
    "qtr", "half_seconds_remaining", "score_differential", "posteam_timeouts_remaining",
    "play_type", "qb_kneel", "qb_spike", "penalty", "two_point_attempt",
    "run_location", "run_gap", "pass_length", "pass_location",
    "ep", "epa", "wp", "wpa", "yards_gained", "first_down", "interception", "fumble_lost",
    "sack", "incomplete_pass", "touchdown",
]


def fetch(season):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "pbp_%d.parquet" % season)
    if not os.path.exists(path):
        req = urllib.request.Request(URL % season, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def load():
    return pd.concat([pd.read_parquet(fetch(s), columns=COLS) for s in SEASONS],
                     ignore_index=True)


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
    rec = {"seasons": SEASONS, "rows_all": int(len(df)), "actions": list(ACTIONS)}
    steps = []

    def keep(mask, why):
        nonlocal df
        before = len(df)
        df = df[mask].copy()
        steps.append({"rule": why, "before": int(before), "after": int(len(df)),
                      "dropped": int(before - len(df))})

    keep(df["season_type"].eq("REG"), "regular season only")
    keep(df["down"].isin(DOWN_VALUES), "first, second and third down")
    keep(~df["qb_kneel"].eq(1), "drop kneels")
    keep(~df["qb_spike"].eq(1), "drop spikes")
    keep(~df["two_point_attempt"].eq(1), "drop two point plays")
    keep(~df["penalty"].eq(1), "drop penalty-nullified plays")
    keep(df["yardline_100"].notna() & df["ydstogo"].notna(), "need field position and distance")
    keep(df["score_differential"].notna() & df["half_seconds_remaining"].notna(), "need score and clock")
    rec["exclusions"] = steps

    df["action"] = classify(df)
    unclassified = int(df["action"].isna().sum())
    rec["unclassified_plays"] = unclassified
    rec["unclassified_play_types"] = {
        str(k): int(v) for k, v in df[df["action"].isna()]["play_type"].value_counts().head(8).items()
    }
    keep(df["action"].notna(), "action must be one of the four registered calls")

    rec["decisions"] = int(len(df))
    rec["action_counts"] = {k: int(v) for k, v in df["action"].value_counts().items()}
    rec["per_season"] = {str(k): int(v) for k, v in df["season"].value_counts().sort_index().items()}

    # The consequence coordinates are computed from outcomes of the play, never
    # from which play was called. Count their presence.
    rec["consequence_coordinate_presence"] = {
        c: int(df[c].notna().sum()) for c in
        ("epa", "yards_gained", "first_down", "interception", "fumble_lost", "sack",
         "incomplete_pass", "touchdown", "ep", "wp")
    }

    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")

    def cell_report(sub):
        if len(sub) == 0:
            return {"decisions": 0, "cells": 0}
        g = sub.groupby(["down", "b_togo", "b_yard", "b_score"], observed=True)["action"]
        counts = g.value_counts().unstack(fill_value=0)
        for a in ACTIONS:
            if a not in counts.columns:
                counts[a] = 0
        counts = counts[list(ACTIONS)]
        three = (counts > 0).sum(axis=1) >= 3
        four = (counts > 0).all(axis=1)
        at_min3 = (counts >= MIN_PER_ACTION).sum(axis=1) >= 3
        at_min4 = (counts >= MIN_PER_ACTION).all(axis=1)
        return {
            "decisions": int(len(sub)),
            "cells": int(len(counts)),
            "cells_with_3plus_actions": int(three.sum()),
            "cells_with_all_4_actions": int(four.sum()),
            "cells_3plus_at_min": int(at_min3.sum()),
            "cells_all4_at_min": int(at_min4.sum()),
            "decisions_in_cells_all4_at_min": int(counts[at_min4].sum().sum()),
            "median_cell_size_all4_at_min": float(counts[at_min4].sum(axis=1).median()) if at_min4.any() else None,
            "min_cell_size_all4_at_min": int(counts[at_min4].sum(axis=1).min()) if at_min4.any() else None,
        }

    rec["cells_overall"] = cell_report(df)
    rec["cells_by_pressure"] = {p: cell_report(df[df["pressure"] == p]) for p in ("low", "high")}

    # Per team and season, since the evaluator is a team's decision-maker and a
    # per-evaluator gate needs each member populated.
    per_team = df.groupby(["season"], observed=True).size()
    rec["per_evaluator_note"] = {
        "seasons": int(df["season"].nunique()),
        "median_decisions_per_season": float(per_team.median()),
    }
    rec["min_per_action"] = MIN_PER_ACTION
    rec["bins"] = {"ydstogo": YDSTOGO_BINS, "yardline_100": YARDLINE_BINS,
                   "score_differential": SCOREDIFF_BINS, "pressure_half_seconds": 240,
                   "downs": list(DOWN_VALUES)}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    for k in ("decisions", "action_counts", "cells_overall", "cells_by_pressure",
              "unclassified_plays", "unclassified_play_types"):
        print(k, "=", json.dumps(rec[k], indent=1, sort_keys=True))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
