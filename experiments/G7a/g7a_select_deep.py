#!/usr/bin/env python3
"""G7a: choose which screened positions get the deep label.

PREREG-G7A.md Section 3. A screened position goes to the deep pass when, on the
50,000-node labels, it is undecided and its second-to-third gap is at least
0.04. The cut is deliberately looser than the 0.10 the reader uses, because the
reader's inclusion is decided on the deep labels alone and the screen only has
to avoid losing positions the deep labels would keep. On the shakedown it kept
95.6 percent of them while passing 20 percent of all positions.

The human's move plays no part in the screen. A position is screened on what
the engine sees and never on what the player did, so the screen cannot select
on the outcome.
"""
import argparse
import glob
import json

import numpy as np

import g7a_threshold as T

SCREEN_GAP23 = 0.04


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", required=True, help="glob of screen label shards")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    n = kept = 0
    with open(a.out, "w") as out:
        for p in sorted(glob.glob(a.screen)):
            for line in open(p):
                r = json.loads(line)
                n += 1
                _g12, g23, und = T.gaps_from_cp(np.array(r["cp"], dtype=float))
                if und and g23 >= SCREEN_GAP23:
                    out.write(json.dumps({k: r[k] for k in r
                                          if k not in ("cp", "engine_moves", "choice", "nodes", "engine")}) + "\n")
                    kept += 1
    print(json.dumps({"screened": n, "sent_to_deep": kept, "share": kept / n if n else None}))


if __name__ == "__main__":
    main()
