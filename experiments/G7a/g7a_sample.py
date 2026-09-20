#!/usr/bin/env python3
"""G7a stage 1: draw positions from a Lichess PGN stream. No engine, no scoring.

Reads decompressed PGN on standard input and writes one JSON line per sampled
position: the position, the move the human played there, and what is known
about the decision before it was made. Nothing here says whether the move was
good. That is stage 2, and keeping the stages apart means the sample is fixed
before any quality is known, so it cannot be steered by it.

What is kept, and why.

  games      rated standard games between two humans, in one of the four main
             categories. Bots are dropped. Abandoned games and rule infractions
             are dropped. Games lost on time are KEPT, and how each game ended is
             recorded. A first version dropped them, and that was a confound of
             my own making: losses on time are far commoner in bullet, so
             dropping them keeps, in the fast categories only, the games where
             players managed their clocks well, which is selection on the budget
             variable through something correlated with move quality.
  positions  at most PER_GAME positions per game, at plies drawn by a generator
             seeded from the game's own identifier, so the draw is reproducible
             and owes nothing to what happened in the game. Plies 16 to 80, which
             skips opening theory, where moves are recalled and not decided.
             Positions with fewer than three legal moves are skipped since there
             is no third move to be far below.
  budget     the time control, fixed before the first move. The clock left when
             the move was made is recorded as well, as a secondary variable.
  player     a keyed hash of the username, so the same person can be followed
             across time controls without the name being stored. The key comes
             from the environment and is not in the repository.
"""
import argparse
import hashlib
import io
import json
import os
import random
import re
import sys

import chess
import chess.pgn

PER_GAME = 2
PLY_MIN, PLY_MAX = 16, 80
CLK = re.compile(r"\[%clk (\d+):(\d+):(\d+)\]")
MAIN = ("bullet", "blitz", "rapid", "classical")


def category(tc):
    try:
        base, inc = tc.split("+")
        base, inc = int(base), int(inc)
    except (ValueError, AttributeError):
        return None, None, None
    est = base + 40 * inc
    if est < 30:
        return "ultrabullet", base, inc
    if est < 180:
        return "bullet", base, inc
    if est < 480:
        return "blitz", base, inc
    if est < 1500:
        return "rapid", base, inc
    return "classical", base, inc


def keyed(name, key):
    return hashlib.blake2b(name.encode("utf-8", "replace"), key=key, digest_size=8).hexdigest()


def clock_seconds(comment):
    m = CLK.search(comment or "")
    return None if not m else int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quota", required=True,
                    help="games wanted per category, e.g. bullet=3000,blitz=12000")
    ap.add_argument("--rating-min", type=int, default=1200)
    ap.add_argument("--rating-max", type=int, default=2399)
    a = ap.parse_args()

    key = os.environ.get("G7A_PLAYER_KEY", "").encode()
    if len(key) < 16:
        raise SystemExit("G7A_PLAYER_KEY must be set to at least 16 bytes and kept out of the repo")
    quota = {k: int(v) for k, v in (kv.split("=") for kv in a.quota.split(","))}
    got = {k: 0 for k in quota}
    seen = dropped = written = 0
    why = {}

    TAG = re.compile(r'^\[(\w+) "(.*)"\]')

    def games(stream):
        """Split the stream into games by line and parse only the wanted ones.
        Parsing every game in full just to discard nineteen in twenty of them is
        the difference between minutes and hours on a file this size."""
        tags, lines, in_moves = {}, [], False
        for line in stream:
            if line.startswith("["):
                # A tag line after movetext starts the next game. The blank line
                # Lichess puts after the moves means the previous line cannot be
                # used to tell, so the moves are tracked with a flag.
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

    stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    with open(a.out, "w") as out:
        for tags, text in games(stream):
            if all(got[k] >= quota[k] for k in quota):
                break
            seen += 1

            def drop(reason):
                nonlocal dropped
                dropped += 1
                why[reason] = why.get(reason, 0) + 1

            # Cheap rejections first, on the raw tags, before any parsing.
            cat0 = category(tags.get("TimeControl"))[0]
            if cat0 not in quota or got[cat0] >= quota[cat0]:
                drop("category not wanted or quota full")
                continue
            if tags.get("Termination") not in ("Normal", "Time forfeit"):
                drop("abandoned, unterminated or rule infraction")
                continue
            try:
                ok = all(a.rating_min <= int(tags.get(k)) <= a.rating_max
                         for k in ("WhiteElo", "BlackElo"))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                drop("unrated or outside the rating window")
                continue
            game = chess.pgn.read_game(io.StringIO(text))
            if game is None:
                drop("unparseable")
                continue
            h = game.headers
            cat, base, inc = category(h.get("TimeControl"))
            if h.get("WhiteTitle") == "BOT" or h.get("BlackTitle") == "BOT":
                drop("bot")
                continue
            try:
                elo = {"w": int(h.get("WhiteElo")), "b": int(h.get("BlackElo"))}
            except (TypeError, ValueError):
                drop("unrated player")
                continue
            if not all(a.rating_min <= e <= a.rating_max for e in elo.values()):
                drop("outside the rating window")
                continue

            nodes = list(game.mainline())
            if len(nodes) <= PLY_MIN + 2:
                drop("too short")
                continue
            gid = h.get("Site", "") or str(seen)
            rng = random.Random(gid)
            candidates = list(range(PLY_MIN, min(PLY_MAX, len(nodes) - 1)))
            rng.shuffle(candidates)

            taken = 0
            for ply in candidates:
                if taken >= PER_GAME:
                    break
                node = nodes[ply]
                board = node.parent.board()
                if board.legal_moves.count() < 3:
                    continue
                mover = "w" if board.turn == chess.WHITE else "b"
                # The mover's clock before this move is the clock after their
                # previous move, two plies back.
                before = clock_seconds(nodes[ply - 2].comment) if ply >= 2 else None
                after = clock_seconds(node.comment)
                out.write(json.dumps({
                    "game": keyed(gid, key), "ply": ply, "fen": board.fen(),
                    "played": node.move.uci(), "category": cat, "base": base, "inc": inc,
                    "budget": base + 40 * inc, "rating": elo[mover],
                    "player": keyed(h.get("White" if mover == "w" else "Black", ""), key),
                    "clock_before": before, "clock_after": after,
                    "termination": h.get("Termination"),
                }) + "\n")
                taken += 1
                written += 1
            if taken:
                got[cat] += 1
            if seen % 20000 == 0:
                print("seen", seen, "got", got, flush=True)

    print(json.dumps({"games_seen": seen, "games_used": got, "positions_written": written,
                      "dropped": why}, indent=1), flush=True)


if __name__ == "__main__":
    main()
