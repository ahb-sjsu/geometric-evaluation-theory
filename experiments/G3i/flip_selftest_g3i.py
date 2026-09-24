#!/usr/bin/env python3
"""Run G3d's self-test, unmodified, against each G3h config.

`flip_selftest.py` reads `flip_config.json` from beside itself into a module constant `BASE`
and derives every synthetic deliberator from it. This wrapper imports it from `../G3d`, swaps
`BASE` for a G3h config, and calls its `main`, so the synthetic judges are exercised on THIS
ladder with THIS gap and pair count and nothing else changes.

    python flip_selftest_g3i.py flip_config_qwen7b.json selftest_qwen7b [a1=0.2,c_decay=0.25]

The optional third argument rescales the synthetic deliberators' budget dependence. G3d's
synthetic judges are parameterized to cross near 150 tokens, which sits inside G3d's ladder and
outside this one, so on the ladder 0 to 96 the additive judge would read VACUOUS for a reason
that has nothing to do with the harness. The override moves the synthetic crossing inside this
ladder and changes nothing else; the interaction and cue-blind judges take the same override,
so the checks they exist for (rejecting a known defect, refusing a judge the cue cannot move)
are exercised at the same scale. The values used are recorded in PREREG-G3I.md Section 6.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for cand in ("G3d", "g3d"):
    if (HERE.parent / cand / "flip_selftest.py").exists():
        sys.path.insert(0, str(HERE.parent / cand))
        break
else:
    raise SystemExit("G3d not found beside this directory")

import flip_selftest as T  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    cfg_path, out = Path(sys.argv[1]), sys.argv[2]
    T.BASE = json.load(open(cfg_path, encoding="utf-8"))
    if len(sys.argv) > 3:
        over = {k: float(v) for k, v in (kv.split("=") for kv in sys.argv[3].split(","))}
        for name, spec in T.JUDGES.items():
            for k, v in over.items():
                if not (name == "cueblind" and k == "c0"):
                    spec[k] = v
        print("synthetic override", over)
    print("self-test on", cfg_path.name, "budgets", T.BASE["budgets"], "gap", T.BASE["gap"],
          "n_pairs", T.BASE["n_pairs"])
    sys.argv = [sys.argv[0], out]
    return T.main()


if __name__ == "__main__":
    sys.exit(main())
