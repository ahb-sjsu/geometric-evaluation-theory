#!/usr/bin/env python3
"""Event-presence probe for the phase after G7a: berserk, and the shape of the budget.

Reads tag lines and the first line of movetext. From the movetext it takes only
the first two clock tags, which are the two starting clocks. It parses no move,
runs no engine and forms no quality measure, so it can run on a month before
any registration that uses the month is sealed.

Berserk. In a Lichess arena a player may halve their own clock for an extra
tournament point. No tag records it. It is visible because the berserking
player's starting clock is half the base time. That gives a budget cut chosen
inside one format, one pool and one evening, which is a far narrower selection
than choosing to play bullet instead of classical.

Counted here, per exact time control:

  games, arena games, games with one berserker, games with two
  players with at least m berserk games AND at least m plain arena games at
      that same control, and the games they hold, which is the within-player
      cohort a gate would need
  players with at least m games as the full-clock OPPONENT of a berserker and
      at least m plain arena games, which is the placebo arm: their budget did
      not change, so the bridge predicts their threshold does not either
  the mean rating edge of a berserker over their opponent, since players
      berserk when they expect to win and a gate must match on it

And for the shape question, the count of games at every time control with its
estimated duration, so that pairs of equal length and different shape can be
found if they exist.
"""
import collections
import hashlib
import json
import os
import re
import sys

CLK = re.compile(r"%clk (\d+):(\d+):(\d+)")
MS = (5, 10, 20)
RATING_MIN, RATING_MAX = 1200, 2399


def main():
    out = sys.argv[1]
    key = os.environ.get("G7A_PLAYER_KEY", "").encode()
    if len(key) < 16:
        raise SystemExit("G7A_PLAYER_KEY must be set")

    tc_games = collections.Counter()
    tc_arena = collections.Counter()
    tc_one = collections.Counter()
    tc_both = collections.Counter()
    # per (player, tc): [berserk games, plain arena games, games as full-clock opponent of a berserker]
    pl = collections.defaultdict(lambda: [0, 0, 0])
    edge_sum = collections.Counter()
    edge_n = collections.Counter()
    tags = {}
    n = 0
    for line in sys.stdin:
        if line[0] == "[":
            sp = line.find(" ")
            tags[line[1:sp]] = line[sp + 2:line.rfind('"')]
            continue
        n += 1
        tc = tags.get("TimeControl", "")
        tc_games[tc] += 1
        ok = (tags.get("Termination") in ("Normal", "Time forfeit")
              and tags.get("WhiteTitle") != "BOT" and tags.get("BlackTitle") != "BOT"
              and "tournament" in tags.get("Event", "").lower())
        if ok:
            try:
                base, inc = (int(x) for x in tc.split("+"))
                we, be = int(tags.get("WhiteElo")), int(tags.get("BlackElo"))
            except (TypeError, ValueError):
                ok = False
        if ok and base >= 30:
            tc_arena[tc] += 1
            c = CLK.findall(line[:400])[:2]
            if len(c) == 2:
                w, b = (int(h) * 3600 + int(m) * 60 + int(s) for h, m, s in c)
                bw, bb = abs(w - base / 2) <= 1, abs(b - base / 2) <= 1
                if bw and bb:
                    tc_both[tc] += 1
                elif bw or bb:
                    tc_one[tc] += 1
                    edge = (we - be) if bw else (be - we)
                    edge_sum[tc] += edge
                    edge_n[tc] += 1
                for side, elo, mine, theirs in (("White", we, bw, bb), ("Black", be, bb, bw)):
                    if not (RATING_MIN <= elo <= RATING_MAX):
                        continue
                    h = hashlib.blake2b(tags.get(side, "").encode("utf-8", "replace"),
                                        key=key, digest_size=8).digest()
                    rec = pl[(h, tc)]
                    if mine:
                        rec[0] += 1
                    elif theirs:
                        rec[2] += 1
                    else:
                        rec[1] += 1
        tags = {}
        if n % 5000000 == 0:
            print("games", n, "player-controls", len(pl), flush=True)

    top = [tc for tc, _ in tc_arena.most_common(14)]
    rec = {"games_scanned": n, "controls": {}, "all_controls_top40": []}
    for tc in top:
        cohorts, placebo = {}, {}
        for m in MS:
            a = [(v[0], v[1]) for (h, t), v in pl.items() if t == tc and v[0] >= m and v[1] >= m]
            p = [(v[2], v[1]) for (h, t), v in pl.items() if t == tc and v[2] >= m and v[1] >= m]
            cohorts["m>=%d" % m] = {"players": len(a), "berserk_games": sum(x for x, _ in a),
                                    "plain_arena_games": sum(y for _, y in a)}
            placebo["m>=%d" % m] = {"players": len(p), "games_facing_berserker": sum(x for x, _ in p),
                                    "plain_arena_games": sum(y for _, y in p)}
        rec["controls"][tc] = {
            "games": tc_games[tc], "arena_games": tc_arena[tc],
            "one_berserker": tc_one[tc], "two_berserkers": tc_both[tc],
            "mean_rating_edge_of_berserker": (edge_sum[tc] / edge_n[tc]) if edge_n[tc] else None,
            "within_player_cohort": cohorts, "placebo_opponent_cohort": placebo,
        }
    for tc, g in tc_games.most_common(40):
        try:
            base, inc = (int(x) for x in tc.split("+"))
            est = base + 40 * inc
        except ValueError:
            est = None
        rec["all_controls_top40"].append({"control": tc, "estimated_seconds": est, "games": g})
    with open(out, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print("wrote", out, flush=True)


if __name__ == "__main__":
    main()
