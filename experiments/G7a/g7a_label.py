#!/usr/bin/env python3
"""G7a stage 2: ask the engine what the human was choosing between.

For each sampled position the engine reports its three best moves at a fixed
node count. Values are converted to a win expectation with the engine's own
win-draw-loss model, so gaps are in the units the outcome is in rather than in
centipawns, whose meaning changes with the position.

Written per position: the gap between the engine's first and second move, the
gap between its second and third, and where the human's move falls in the
engine's ordering. Nothing is fitted here.

A fixed node count, and not a fixed time, because the labels must not depend on
how busy the machine was. One thread and a fixed hash for the same reason.

Decided positions are dropped. When the better side's expectation is already
outside [0.10, 0.90] the gaps compress toward zero and the player's task has
changed from choosing to converting.
"""
import argparse
import json
import sys

import chess
import chess.engine

DECIDED_LO, DECIDED_HI = 0.10, 0.90


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--nodes", type=int, required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    a = ap.parse_args()

    eng = chess.engine.SimpleEngine.popen_uci(a.engine)
    eng.configure({"Threads": 1, "Hash": 64})
    n = kept = decided = 0
    with open(a.todo) as f, open(a.out, "w") as out:
        for i, line in enumerate(f):
            if i % a.of != a.shard:
                continue
            row = json.loads(line)
            board = chess.Board(row["fen"])
            info = eng.analyse(board, chess.engine.Limit(nodes=a.nodes), multipv=3)
            if len(info) < 3:
                continue
            n += 1
            ex, moves = [], []
            for pv in info:
                sc = pv["score"].pov(board.turn)
                ex.append(sc.wdl(model="sf", ply=board.ply()).expectation())
                moves.append(pv["pv"][0].uci())
            if not (DECIDED_LO <= ex[0] <= DECIDED_HI):
                decided += 1
                continue
            choice = moves.index(row["played"]) if row["played"] in moves else 3
            row.update({"gap12": ex[0] - ex[1], "gap23": ex[1] - ex[2], "best_expectation": ex[0],
                        "choice": choice, "nodes": a.nodes, "engine": eng.id.get("name")})
            row.pop("fen", None)
            out.write(json.dumps(row) + "\n")
            kept += 1
            if n % 500 == 0:
                print("shard", a.shard, "labelled", n, "kept", kept, flush=True)
    eng.quit()
    print(json.dumps({"shard": a.shard, "labelled": n, "kept": kept, "decided_dropped": decided}),
          flush=True)


if __name__ == "__main__":
    main()
