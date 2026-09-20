#!/usr/bin/env python3
"""G7a cohort probe: how many players can be followed across time budgets.

Reads game HEADERS from a pre-filtered stream and counts. It never sees a move,
runs no engine and forms no quality measure, which is what lets it run on an
evaluation month before the seal, as G2's placement-only probe ran on its
evaluation file.

Why cohorts. Lichess ratings are kept per category, so a 1600 in bullet and a
1600 in classical are different numbers from different pools, and skill cannot
be equated across time controls by rating. Comparing thresholds between the
players who happen to play bullet and the players who happen to play classical
would confound the budget with who shows up. Following the same players across
budgets holds the evaluator fixed and moves only the budget, which is the
design the theory describes.

Five exact time controls, all without increment so the budget is unambiguous:
60, 180, 300, 600 and 1800 seconds. 300 is the reference. For each other level
L the cohort is the players with at least m games at L and at least m games at
300 inside the month. The probe reports cohort sizes and the games they hold,
for several m, and writes the membership to a file outside the repository for
the sampler to use.

Input lines are expected to be only the tag lines named below and the first
line of movetext, which marks the end of a game. The filtering is done upstream
by grep because it is some three times faster than doing it here.
"""
import collections
import hashlib
import json
import os
import pickle
import sys

LEVELS = {"60+0": 60, "180+0": 180, "300+0": 300, "600+0": 600, "1800+0": 1800}
REF = 300
RATING_MIN, RATING_MAX = 1200, 2399
MS = (5, 10, 20)


def main():
    out_json, out_pkl = sys.argv[1], sys.argv[2]
    key = os.environ.get("G7A_PLAYER_KEY", "").encode()
    if len(key) < 16:
        raise SystemExit("G7A_PLAYER_KEY must be set")

    counts = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    order = [60, 180, 300, 600, 1800]
    idx = {b: i for i, b in enumerate(order)}
    games = collections.Counter()
    used = collections.Counter()
    tags = {}
    n = 0
    for line in sys.stdin:
        if line[0] == "[":
            sp = line.find(" ")
            tags[line[1:sp]] = line[sp + 2:line.rfind('"')]
            continue
        n += 1
        tc = tags.get("TimeControl")
        b = LEVELS.get(tc)
        if b is not None:
            games[b] += 1
            ok = tags.get("Termination") in ("Normal", "Time forfeit") \
                and tags.get("WhiteTitle") != "BOT" and tags.get("BlackTitle") != "BOT"
            if ok:
                for side in ("White", "Black"):
                    try:
                        elo = int(tags.get(side + "Elo"))
                    except (TypeError, ValueError):
                        continue
                    if RATING_MIN <= elo <= RATING_MAX:
                        h = hashlib.blake2b(tags.get(side, "").encode("utf-8", "replace"),
                                            key=key, digest_size=8).digest()
                        counts[h][idx[b]] += 1
                        used[b] += 1
        tags = {}
        if n % 5000000 == 0:
            print("games", n, "players", len(counts), flush=True)

    rec = {"games_scanned": n, "games_at_level": {str(k): v for k, v in sorted(games.items())},
           "player_games_in_window": {str(k): v for k, v in sorted(used.items())},
           "players_seen": len(counts), "reference": REF, "cohorts": {}}
    members = {}
    r = idx[REF]
    for b in order:
        if b == REF:
            continue
        i = idx[b]
        rec["cohorts"][str(b)] = {}
        for m in MS:
            sel = [h for h, c in counts.items() if c[i] >= m and c[r] >= m]
            rec["cohorts"][str(b)]["m>=%d" % m] = {
                "players": len(sel),
                "their_games_at_level": int(sum(counts[h][i] for h in sel)),
                "their_games_at_reference": int(sum(counts[h][r] for h in sel)),
            }
            if m == 10:
                members[b] = set(sel)
    with open(out_json, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    with open(out_pkl, "wb") as f:
        pickle.dump(members, f)
    print(json.dumps(rec, indent=1, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
