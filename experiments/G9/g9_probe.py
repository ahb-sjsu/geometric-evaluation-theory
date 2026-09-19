"""Event-presence probe for a proposed GET gate on fourth-down decisions.

Protocol rule 2 requires a committed probe showing that the events a gate will
count are present, before the registration is sealed. G2's probe counted
respondents holding a menu of at least four objects and computed no statistic
of the hypothesis. This does the same thing for football.

What it counts.
  1. Fourth-down decisions per season after the registered exclusions.
  2. State cells, and how many carry all three actions at a minimum count, so
     a revealed ranking can be formed at all.
  3. Whether the consequence map can be built, by counting the outcome events
     the map is estimated from (conversion attempts by distance, field goals
     by kick distance, punts by field position).
  4. The same counts inside and outside the time-pressure stratum, since the
     budget prediction needs both halves populated.

No hypothesis statistic is computed. Nothing here ranks actions or measures a
hull violation.
"""
import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

CACHE = "/home/claude/nfl_cache"
URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_%d.parquet"
SEASONS = list(range(2015, 2025))
OUT = "/home/claude/deploy/g9_probe.json"

# Cell definition, stated here so the probe and any later registration share one
# source. Bins are coarse enough that a cell can accumulate all three actions.
YDSTOGO_BINS = [0, 1, 2, 3, 5, 8, 100]
YARDLINE_BINS = [0, 5, 20, 35, 45, 60, 75, 100]
SCOREDIFF_BINS = [-100, -14, -7, -3, 0, 3, 7, 14, 100]
# Time pressure is the budget manipulation. Low pressure is the first three
# quarters with the clock not near a half boundary; high pressure is the last
# four minutes of either half.
MIN_PER_ACTION = 3

ACTIONS = ("go", "field_goal", "punt")


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


COLS = [
    "game_id", "play_id", "season", "season_type", "week", "posteam", "defteam",
    "down", "ydstogo", "yardline_100", "goal_to_go", "qtr",
    "game_seconds_remaining", "half_seconds_remaining", "score_differential",
    "posteam_timeouts_remaining", "defteam_timeouts_remaining",
    "play_type", "field_goal_attempt", "punt_attempt", "two_point_attempt",
    "qb_kneel", "qb_spike", "penalty",
    "ep", "wp", "vegas_wp", "epa", "wpa",
    "fourth_down_converted", "fourth_down_failed",
    "field_goal_result", "kick_distance", "yards_gained", "first_down",
]


def load():
    frames = []
    for s in SEASONS:
        df = pd.read_parquet(fetch(s), columns=[c for c in COLS])
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def classify(df):
    """Map a play to one of the three fourth-down actions, or to None."""
    pt = df["play_type"]
    go = pt.isin(["pass", "run"])
    fg = pt.eq("field_goal") | df["field_goal_attempt"].eq(1)
    punt = pt.eq("punt") | df["punt_attempt"].eq(1)
    out = pd.Series(pd.NA, index=df.index, dtype="object")
    out[go] = "go"
    out[fg] = "field_goal"
    out[punt] = "punt"
    return out


def main():
    df = load()
    rec = {}
    rec["seasons"] = SEASONS
    rec["rows_all"] = int(len(df))

    # Registered exclusions, applied in order and each one counted so the
    # attrition is readable from the record rather than inferred.
    steps = []

    def keep(mask, why):
        nonlocal df
        before = len(df)
        df = df[mask].copy()
        steps.append({"rule": why, "before": int(before), "after": int(len(df)),
                      "dropped": int(before - len(df))})

    keep(df["season_type"].eq("REG"), "regular season only")
    keep(df["down"].eq(4), "fourth down only")
    keep(~df["qb_kneel"].eq(1), "drop kneels")
    keep(~df["qb_spike"].eq(1), "drop spikes")
    keep(~df["two_point_attempt"].eq(1), "drop two point plays")
    keep(df["play_type"].notna(), "drop rows with no play type")
    keep(~df["penalty"].eq(1), "drop penalty-nullified plays")
    keep(df["yardline_100"].notna() & df["ydstogo"].notna(), "need field position and distance")
    keep(df["score_differential"].notna() & df["half_seconds_remaining"].notna(), "need score and clock")
    rec["exclusions"] = steps

    df["action"] = classify(df)
    keep(df["action"].notna(), "action must be one of go, field goal, punt")
    rec["decisions"] = int(len(df))
    rec["action_counts"] = {k: int(v) for k, v in df["action"].value_counts().items()}
    rec["per_season"] = {str(k): int(v) for k, v in df["season"].value_counts().sort_index().items()}

    # The consequence map is estimated from outcomes, never from choices. Count
    # the outcome events each piece of it needs.
    go = df[df["action"].eq("go")]
    fg = df[df["action"].eq("field_goal")]
    pu = df[df["action"].eq("punt")]
    conv = go["fourth_down_converted"].fillna(0).astype(int)
    rec["consequence_map_inputs"] = {
        "go_attempts": int(len(go)),
        "go_conversions": int(conv.sum()),
        "go_attempts_by_ydstogo_1_to_5": {
            str(int(d)): int((go["ydstogo"] == d).sum()) for d in range(1, 6)
        },
        "fg_attempts": int(len(fg)),
        "fg_made": int((fg["field_goal_result"] == "made").sum()),
        "fg_kick_distance_min": float(fg["kick_distance"].min()) if len(fg) else None,
        "fg_kick_distance_max": float(fg["kick_distance"].max()) if len(fg) else None,
        "punts": int(len(pu)),
        "wp_present": int(df["wp"].notna().sum()),
        "vegas_wp_present": int(df["vegas_wp"].notna().sum()),
        "ep_present": int(df["ep"].notna().sum()),
    }

    # Menu admissibility, read off the data rather than assumed. A field goal
    # is treated as admissible where the league has actually attempted one.
    rec["observed_admissibility"] = {
        "fg_attempted_yardline_100_max": float(fg["yardline_100"].max()) if len(fg) else None,
        "punt_yardline_100_min": float(pu["yardline_100"].min()) if len(pu) else None,
        "go_yardline_100_min": float(go["yardline_100"].min()) if len(go) else None,
        "go_yardline_100_max": float(go["yardline_100"].max()) if len(go) else None,
    }

    # Cells.
    df["b_togo"] = pd.cut(df["ydstogo"], YDSTOGO_BINS, right=True, labels=False)
    df["b_yard"] = pd.cut(df["yardline_100"], YARDLINE_BINS, right=True, labels=False)
    df["b_score"] = pd.cut(df["score_differential"], SCOREDIFF_BINS, right=True, labels=False)
    df["pressure"] = np.where(df["half_seconds_remaining"] <= 240, "high", "low")

    def cell_report(sub):
        if len(sub) == 0:
            return {"decisions": 0, "cells": 0, "cells_all_three": 0,
                    "cells_all_three_at_min": 0, "decisions_in_qualifying_cells": 0}
        g = sub.groupby(["b_togo", "b_yard", "b_score"], observed=True)["action"]
        counts = g.value_counts().unstack(fill_value=0)
        for a in ACTIONS:
            if a not in counts.columns:
                counts[a] = 0
        counts = counts[list(ACTIONS)]
        all_three = (counts > 0).all(axis=1)
        at_min = (counts >= MIN_PER_ACTION).all(axis=1)
        return {
            "decisions": int(len(sub)),
            "cells": int(len(counts)),
            "cells_all_three": int(all_three.sum()),
            "cells_all_three_at_min": int(at_min.sum()),
            "decisions_in_qualifying_cells": int(counts[at_min].sum().sum()),
            "median_cell_size_qualifying": float(counts[at_min].sum(axis=1).median()) if at_min.any() else None,
        }

    rec["cells_overall"] = cell_report(df)
    rec["cells_by_pressure"] = {p: cell_report(df[df["pressure"] == p]) for p in ("low", "high")}
    rec["min_per_action"] = MIN_PER_ACTION
    rec["bins"] = {"ydstogo": YDSTOGO_BINS, "yardline_100": YARDLINE_BINS,
                   "score_differential": SCOREDIFF_BINS, "pressure_half_seconds": 240}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))
    print()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
