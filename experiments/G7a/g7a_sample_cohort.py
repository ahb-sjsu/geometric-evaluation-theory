#!/usr/bin/env python3
"""G7a stage 1 for the sealed run: draw positions for the cohort arms. No engine.

An ARM is a cohort read at one budget. For each level L in 60, 180, 600 and 1800
seconds the cohort is the players with at least ten games at L and at least ten
at 300 seconds inside the month, as counted by `g7a_cohort_probe.py`. Arm
(L, level) holds positions where a cohort member is the mover in a game at L.
Arm (L, ref) holds positions where a member of that same cohort is the mover in
a game at 300 seconds. One reference position can serve several cohorts, since
one player can be in several, and it is labelled once and tagged with every arm
it serves.

Which games. A game is taken when a keyed hash of its identifier falls under
the arm's sampling rate. The file is chronological, so taking games until a
quota filled would sample the first days of the month. The hash spreads the
sample over the whole month, is reproducible, and owes nothing to what happened
in the game. Rates are set per arm from the cohort probe's game counts so that
every arm aims at the same number of positions.

Which positions. Up to PER_GAME plies where the cohort member is the mover,
plies 16 to 80, at least three legal moves, drawn by a generator seeded from the
game identifier. PER_GAME is six for every arm. It has to be six for the
1,800-second cohort, which holds about 25,000 games and would otherwise fall
under the anti-vacuity floor, and it is six everywhere so the rule is one rule.
The bootstrap resamples players, so several positions from one game do not
narrow the interval.
"""
import argparse
import hashlib
import io
import json
import os
import pickle
import random
import re
import sys

import chess
import chess.pgn

LEVELS = {"60+0": 60, "180+0": 180, "300+0": 300, "600+0": 600, "1800+0": 1800}
REF = 300
PER_GAME = 6
PLY_MIN, PLY_MAX = 16, 80
RATING_MIN, RATING_MAX = 1200, 2399
CLK = re.compile(r"\[%clk (\d+):(\d+):(\d+)\]")
TAG = re.compile(r'^\[(\w+) "(.*)"\]')


def keyed(name, key, size=8):
    return hashlib.blake2b(name.encode("utf-8", "replace"), key=key, digest_size=size)


def clock_seconds(comment):
    m = CLK.search(comment or "")
    return None if not m else int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def games(stream):
    tags, lines, in_moves = {}, [], False
    for line in stream:
        if line.startswith("["):
            if in_moves:
                yield tags, "".join(lines)
                tags, lines, in_moves = {}, [], False
            m = TAG.match(line)
            if m:
                tags[m.group(1)] = m.group(2)
        elif line.strip():
            in_moves = True
        lines.append(line)
    if in_moves:
        yield tags, "".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohorts", required=True, help="pickle from the cohort probe")
    ap.add_argument("--counts", required=True, help="json from the cohort probe")
    ap.add_argument("--target", type=int, default=100000, help="positions aimed at per arm")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    key = os.environ.get("G7A_PLAYER_KEY", "").encode()
    if len(key) < 16:
        raise SystemExit("G7A_PLAYER_KEY must be set")
    members = pickle.load(open(a.cohorts, "rb"))            # {level: set(player digests)}
    counts = json.load(open(a.counts))["cohorts"]

    # Sampling rate per arm, from the probe's player-game counts. About five
    # usable mover plies per game is assumed, and the rate is capped at one.
    rate = {}
    for L in (60, 180, 600, 1800):
        c = counts[str(L)]["m>=10"]
        rate[(L, "level")] = min(1.0, a.target / (5.0 * max(c["their_games_at_level"], 1)))
        rate[(L, "ref")] = min(1.0, a.target / (5.0 * max(c["their_games_at_reference"], 1)))
    print("sampling rates", {("%d_%s" % k): round(v, 4) for k, v in rate.items()}, flush=True)

    written = {k: 0 for k in rate}
    seen = taken_games = 0
    stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    with open(a.out, "w") as out:
        for tags, text in games(stream):
            seen += 1
            if seen % 5000000 == 0:
                print("games", seen, "taken", taken_games,
                      {("%d_%s" % k): v for k, v in written.items()}, flush=True)
            b = LEVELS.get(tags.get("TimeControl"))
            if b is None:
                continue
            if tags.get("Termination") not in ("Normal", "Time forfeit"):
                continue
            if tags.get("WhiteTitle") == "BOT" or tags.get("BlackTitle") == "BOT":
                continue
            gid = tags.get("Site", "")
            u = int.from_bytes(keyed(gid, key).digest(), "big") / 2.0 ** 64

            # Which arms does each side of this game serve, at this game's hash?
            serve = {}
            for side, colour in (("White", chess.WHITE), ("Black", chess.BLACK)):
                try:
                    elo = int(tags.get(side + "Elo"))
                except (TypeError, ValueError):
                    continue
                if not (RATING_MIN <= elo <= RATING_MAX):
                    continue
                d = keyed(tags.get(side, ""), key).digest()
                arms = []
                if b == REF:
                    arms = [(L, "ref") for L in members if d in members[L] and u < rate[(L, "ref")]]
                elif d in members.get(b, ()) and u < rate[(b, "level")]:
                    arms = [(b, "level")]
                if arms:
                    serve[colour] = (arms, elo, d.hex())
            if not serve:
                continue

            game = chess.pgn.read_game(io.StringIO(text))
            if game is None:
                continue
            nodes = list(game.mainline())
            if len(nodes) <= PLY_MIN + 2:
                continue
            taken_games += 1
            rng = random.Random(gid)
            plies = list(range(PLY_MIN, min(PLY_MAX, len(nodes) - 1)))
            rng.shuffle(plies)
            took = {c: 0 for c in serve}
            for ply in plies:
                node = nodes[ply]
                board = node.parent.board()
                c = board.turn
                if c not in serve or took[c] >= PER_GAME:
                    continue
                if board.legal_moves.count() < 3:
                    continue
                arms, elo, player = serve[c]
                out.write(json.dumps({
                    "game": keyed(gid, key).hexdigest(), "ply": ply, "fen": board.fen(),
                    "played": node.move.uci(), "budget": b, "rating": elo, "player": player,
                    "arms": [[L, s] for L, s in arms],
                    "clock_before": clock_seconds(nodes[ply - 2].comment) if ply >= 2 else None,
                    "clock_after": clock_seconds(node.comment),
                    "termination": tags.get("Termination"),
                }) + "\n")
                took[c] += 1
                for k in arms:
                    written[k] += 1

    print(json.dumps({"games_seen": seen, "games_taken": taken_games,
                      "positions_per_arm": {("%d_%s" % k): v for k, v in written.items()}},
                     indent=1), flush=True)


if __name__ == "__main__":
    main()
