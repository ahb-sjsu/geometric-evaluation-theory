#!/usr/bin/env python3
"""G3g runner. G3c's harness, G3e's served-judge client, real book reviews as the stimuli.

Same seam as G3f and for the same reason: the gate's claim is that nothing but the stimuli
changed, so this file replaces one function in G3c's `judge` module and then calls G3c's own
`run_block`. Everything downstream is byte-identical code on different text.

Three differences from G3f, all forced by the family rather than chosen.

  quality      is the star rating the reviewer actually gave, mapped to `e = 5 - rating` with
               `n_items = 4`, so the block builder's level loop and the gap ladder need no change.
  levels       are five rather than twenty-one, so the gap ladder runs 1 to 4. G3c's bars were
               derived at a different ladder and DO NOT transfer. They must be re-derived by the
               same null-simulation procedure before this gate is sealed.
  draws        are without replacement across a whole block, so no review is scored twice and a
               calibration review can never reappear in a test block. `run_block` builds one block
               per call, so the draw state is cleared here at the start of each.

    python g3g_judge.py run --config g3g_config.json --block calibration --model gemma31b
"""
from __future__ import annotations

import argparse
import json
import sys
import zlib
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
for _cand in ("G3c", "g3c"):
    if (_HERE.parent / _cand / "judge.py").exists():
        sys.path.insert(0, str(_HERE.parent / _cand))
        break
for _cand in ("G3e", "g3e"):
    if (_HERE.parent / _cand / "api_judge.py").exists():
        sys.path.insert(0, str(_HERE.parent / _cand))
        break

import api_judge as A  # noqa: E402
import judge as J  # noqa: E402

import g3g_stimuli as S  # noqa: E402

E_BY_TEXT: dict = {}


def make_review_sheet(rng: np.random.Generator, n_items: int, e: int) -> dict:
    s = S.make_review(rng, n_items, e)
    E_BY_TEXT[s["text"]] = int(e)
    return s


def _synthetic_z(self, text: str, tag: str) -> float:
    """judge.SyntheticJudge._z with the level read rather than re-derived from the text."""
    e = E_BY_TEXT.get(text)
    if e is None:
        raise KeyError("stimulus not in the registry; the synthetic judge cannot score it")
    rng = np.random.default_rng([self.seed, zlib.crc32((tag + text).encode())])
    sd = self.sd * (self.drift if self.block == "test" else 1.0)
    return 1.0 - e / self.N + rng.normal(0.0, sd)


_orig_make_block = J.make_block


def _make_block(cfg, block, seed):
    """Point the stimulus pool at this block's half, and clear the draw state.

    The halves are disjoint by index parity, so calibration and test cannot share a review even
    though they are built in separate processes with no shared state."""
    role = cfg.get('_role', 'run')
    S.set_block(('pilot_' + block) if role == 'pilot' else block)
    S.reset_draws()
    return _orig_make_block(cfg, block, seed)


def install() -> None:
    J.make_worksheet = make_review_sheet
    J.make_block = _make_block
    J.SyntheticJudge._z = _synthetic_z


install()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--config", required=True)
    ap.add_argument("--block", choices=["calibration", "test"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--precision", default="served")
    ap.add_argument("--out", default="run_record")
    ap.add_argument("--role", default="run", choices=["run", "pilot"])
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    cfg["_role"] = a.role
    r = J.run_block(cfg, a.block, a.model, a.precision, a.out,
                    judge_factory=A.factory(a.out, a.block))
    print(json.dumps({"served": r["loaded_revision"], "files": r["files"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
