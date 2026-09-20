"""Event-presence probe for G7a: does the threshold track the budget in humans, on chess clocks.

Reads a prefix of one month of the Lichess open database from standard input,
as decompressed PGN text. The month is a shakedown month and will not be an
evaluation month. The file is chronological, so a prefix is the first days of
the month and not a random sample, which is fine for counting what exists and
is said here so nobody mistakes it for more.

It counts what the gate would need and computes nothing of the hypothesis. No
engine is run, no move is scored, and no quality measure of any kind is formed.

  1. Games per time-control category, since the category is the budget and it
     is fixed before the first move, which is what makes it exogenous to the
     position. Lichess's own definition is used: estimated duration is the base
     time plus forty increments.
  2. How many games carry clock tags, which record the budget actually left at
     each move, and how many carry server evaluations.
  3. Rating coverage per category, because the pools differ and any comparison
     across categories has to be made within a rating band.
  4. How many players appear in more than one category inside the sample. A
     within-player comparison holds the evaluator fixed and varies only the
     budget, which is the design the theory actually describes. Usernames are
     hashed in memory with a random salt, are never written anywhere, and only
     counts leave this process.
"""
import collections
import hashlib
import json
import os
import re
import sys

OUT = "/home/claude/deploy/g7a_probe.json"
SALT = os.urandom(16)

TAG = re.compile(r'^\[(\w+) "(.*)"\]')
CLK = re.compile(r"%clk")
EVAL = re.compile(r"%eval")
PLY = re.compile(r"\d+\.(?:\.\.)? ")


def category(tc):
    if not tc or tc == "-":
        return "correspondence"
    try:
        base, inc = tc.split("+")
        est = int(base) + 40 * int(inc)
    except ValueError:
        return "unparsed"
    if est < 30:
        return "ultrabullet"
    if est < 180:
        return "bullet"
    if est < 480:
        return "blitz"
    if est < 1500:
        return "rapid"
    return "classical"


def band(elo):
    try:
        e = int(elo)
    except (TypeError, ValueError):
        return None
    return "%d-%d" % (e // 400 * 400, e // 400 * 400 + 399)


def h(name):
    return hashlib.blake2b(name.encode("utf-8", "replace"), key=SALT, digest_size=8).digest()


def main():
    games = collections.Counter()
    with_clk = collections.Counter()
    with_eval = collections.Counter()
    plies_clk = collections.Counter()
    bands = collections.defaultdict(collections.Counter)
    tcs = collections.defaultdict(collections.Counter)
    player_cats = collections.defaultdict(set)
    first_date = last_date = None

    tags = {}
    n = 0
    for line in sys.stdin:
        if line.startswith("["):
            m = TAG.match(line)
            if m:
                tags[m.group(1)] = m.group(2)
            continue
        if line.startswith("1.") or line.startswith("1 "):
            cat = category(tags.get("TimeControl"))
            games[cat] += 1
            tcs[cat][tags.get("TimeControl", "")] += 1
            d = tags.get("UTCDate")
            if d:
                first_date = first_date or d
                last_date = d
            nclk = len(CLK.findall(line))
            if nclk:
                with_clk[cat] += 1
                plies_clk[cat] += nclk
            if EVAL.search(line):
                with_eval[cat] += 1
            for side in ("White", "Black"):
                b = band(tags.get(side + "Elo"))
                if b:
                    bands[cat][b] += 1
                nm = tags.get(side)
                if nm:
                    player_cats[h(nm)].add(cat)
            tags = {}
            n += 1
            if n % 500000 == 0:
                print("games", n, "date", last_date, flush=True)

    main_cats = ("bullet", "blitz", "rapid", "classical")
    multi = collections.Counter()
    for cats in player_cats.values():
        k = tuple(sorted(c for c in cats if c in main_cats))
        if len(k) >= 2:
            multi["+".join(k)] += 1
    rec = {
        "games_total": n,
        "date_first": first_date, "date_last": last_date,
        "games_by_category": dict(games),
        "games_with_clock_tags": dict(with_clk),
        "games_with_server_eval": dict(with_eval),
        "clock_tagged_plies": dict(plies_clk),
        "rating_bands_by_category": {c: dict(sorted(v.items())) for c, v in bands.items()},
        "top_time_controls": {c: v.most_common(4) for c, v in tcs.items()},
        "distinct_players": len(player_cats),
        "players_in_two_or_more_main_categories": sum(multi.values()),
        "players_by_category_combination": dict(multi.most_common(12)),
        "note": "prefix of a chronological file, so the first days of the month, not a sample of it",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
