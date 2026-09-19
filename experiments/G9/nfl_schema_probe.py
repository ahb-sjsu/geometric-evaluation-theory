"""Schema probe: what does nflfastR play-by-play actually carry?

Written before any registration. This opens the file only to enumerate
columns and count rows, which is what protocol rule 2 requires a probe to do
before a gate can be sealed. No statistic of any hypothesis is computed here.
"""
import io
import os
import sys
import urllib.request

import pandas as pd

CACHE = "/home/claude/nfl_cache"
URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_%d.parquet"


def fetch(season):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "pbp_%d.parquet" % season)
    if not os.path.exists(path):
        req = urllib.request.Request(URL % season, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def main():
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    path = fetch(season)
    df = pd.read_parquet(path)
    print("season", season, "rows", len(df), "cols", len(df.columns))
    print("file bytes", os.path.getsize(path))
    print()

    groups = {
        "situation": ["down", "ydstogo", "yardline_100", "goal_to_go", "quarter", "qtr",
                      "game_seconds_remaining", "half_seconds_remaining", "score_differential",
                      "posteam_timeouts_remaining", "defteam_timeouts_remaining"],
        "action": ["play_type", "play_type_nfl", "pass", "rush", "qb_dropback", "qb_scramble",
                   "field_goal_attempt", "punt_attempt", "fourth_down_converted",
                   "fourth_down_failed", "two_point_attempt", "pass_length", "pass_location",
                   "run_location", "run_gap", "shotgun", "no_huddle"],
        "consequence": ["ep", "epa", "wp", "wpa", "vegas_wp", "vegas_wpa", "def_wp",
                        "yards_gained", "first_down", "touchdown", "interception", "fumble_lost",
                        "field_goal_result", "kick_distance", "punt_blocked", "return_yards",
                        "series_result", "fixed_drive_result"],
        "identity": ["game_id", "play_id", "posteam", "defteam", "home_team", "season",
                     "season_type", "week", "desc"],
    }
    cols = set(df.columns)
    for name, want in groups.items():
        have = [c for c in want if c in cols]
        miss = [c for c in want if c not in cols]
        print("[%s] present %d: %s" % (name, len(have), ", ".join(have)))
        if miss:
            print("    absent: %s" % ", ".join(miss))
        print()

    print("play_type value counts:")
    print(df["play_type"].value_counts(dropna=False).head(15).to_string())
    print()
    print("fourth-down rows:", int((df["down"] == 4).sum()))
    print("regular season rows:", int((df["season_type"] == "REG").sum()))


if __name__ == "__main__":
    main()
