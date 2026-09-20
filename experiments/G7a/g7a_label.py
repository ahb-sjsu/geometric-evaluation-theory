#!/usr/bin/env python3
"""G7a stage 2: ask the engine what the human was choosing between.

For each sampled position the engine reports its three best moves at a fixed
node count. What is written is RAW: the three centipawn scores from the mover's
side, the three moves, and where the human's move falls among them. No
conversion to win probability happens here and no position is filtered out.

That is a correction. The first version converted scores with the engine's own
win-draw-loss model and dropped "decided" positions as it went, and the
shakedown lost 62 percent of its positions to that filter. The engine's model
describes engines playing engines, where a pawn and a half is nearly a won game.
For humans rated 1200 to 2400 it is not, so the conversion was the wrong
consequence map for this population, and because it was applied inside the
labeller the raw scores were gone and the labels had to be made again. A stage
that can be wrong about an interpretation should persist what it saw and leave
the interpretation to a later stage that can be rerun for free.

A fixed node count, and not a fixed time, because labels must not depend on how
busy the machine was. One thread and a fixed hash for the same reason.
"""
import argparse
import json

import chess
import chess.engine

MATE = 100000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--nodes", type=int, required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="stop after this many, 0 for all")
    a = ap.parse_args()

    eng = chess.engine.SimpleEngine.popen_uci(a.engine)
    eng.configure({"Threads": 1, "Hash": 64})
    n = 0
    with open(a.todo) as f, open(a.out, "w") as out:
        for i, line in enumerate(f):
            if i % a.of != a.shard:
                continue
            row = json.loads(line)
            board = chess.Board(row["fen"])
            info = eng.analyse(board, chess.engine.Limit(nodes=a.nodes), multipv=3)
            if len(info) < 3:
                continue
            cps = [pv["score"].pov(board.turn).score(mate_score=MATE) for pv in info]
            moves = [pv["pv"][0].uci() for pv in info]
            row.update({"cp": cps, "engine_moves": moves,
                        "choice": moves.index(row["played"]) if row["played"] in moves else 3,
                        "nodes": a.nodes, "engine": eng.id.get("name")})
            out.write(json.dumps(row) + "\n")
            n += 1
            if n % 500 == 0:
                print("shard", a.shard, "labelled", n, flush=True)
            if a.limit and n >= a.limit:
                break
    eng.quit()
    print(json.dumps({"shard": a.shard, "labelled": n}), flush=True)


if __name__ == "__main__":
    main()
