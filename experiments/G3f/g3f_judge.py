#!/usr/bin/env python3
"""G3f runner. G3c's harness, G3e's served-judge client, one thing changed: the stimuli.

The gate's whole claim rests on nothing else changing, so this file does not reimplement the
block structure, the read-outs, the estimator or the grading. It imports G3c's `judge` module and
replaces exactly one function in it, the one that makes a stimulus, then calls G3c's own
`run_block`. Everything downstream, ids, pairs, the gap ladder, the digit tree, the sampling, the
threshold estimator, is byte-identical code running on different text.

Two seams, both narrow and both recorded here so an auditor can see the whole of the change:

  `judge.make_worksheet`     -> `make_stimulus_sheet`, a passage and summary from g3f_stimuli.
  `judge.SyntheticJudge._z`  -> reads the error count from a registry instead of re-deriving it
                                from the text. G3c's synthetic judge counted wrong arithmetic by
                                re-checking each line, which a summary cannot support without the
                                passage. The registry keeps the synthetic judge exactly as
                                faithful as it was, and it is used only by the self-test.

    python g3f_judge.py run --config g3f_config.json --block calibration --model gemma31b
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

import g3f_stimuli as S  # noqa: E402

# text -> unsupported-statement count, for the synthetic judge of the self-test only.
E_BY_TEXT: dict = {}


def make_stimulus_sheet(rng: np.random.Generator, n_items: int, e: int) -> dict:
    """Drop-in for judge.make_worksheet. Same signature, same returned keys."""
    s = S.make_stimulus(rng, n_items, e)
    E_BY_TEXT[s["text"]] = int(e)
    return {"e": int(e), "text": s["text"]}


def _synthetic_z(self, text: str, tag: str) -> float:
    """judge.SyntheticJudge._z with the error count read rather than re-derived."""
    e = E_BY_TEXT.get(text)
    if e is None:
        raise KeyError("stimulus not in the registry; the synthetic judge cannot score it")
    rng = np.random.default_rng([self.seed, zlib.crc32((tag + text).encode())])
    sd = self.sd * (self.drift if self.block == "test" else 1.0)
    return 1.0 - e / self.N + rng.normal(0.0, sd)


def install() -> None:
    J.make_worksheet = make_stimulus_sheet
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
