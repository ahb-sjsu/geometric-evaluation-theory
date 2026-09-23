#!/usr/bin/env python3
"""Draw G3g's test seed, once, after every cell's predictions are committed.

One seed for the whole ladder. The test block at every input budget is then the SAME pairs of
reviews, read to 200 characters, to 400, and in full, so the cells differ in nothing but how much
of each review the judge was allowed to see. The script refuses to run unless every judge's
predictions.json at every cell is committed in git as it stands on disk, and refuses to run twice.

    python g3g_draw_test_seed.py --config g3g_config.json --out run_record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
from pathlib import Path


def committed(path: Path) -> str | None:
    """The blob hash HEAD holds for this path, or None if what is on disk is not in a commit.

    Reads the committed tree, not the index. G3e's version read the index, and on 2026-09-23 a
    seed was drawn against predictions that were staged but whose commit had failed on a signing
    timeout, so "committed" meant nothing more than "git add" had run. That seed was never used
    and was discarded, and this check now asks HEAD."""
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         cwd=str(path.parent)).stdout.strip()
    rel = subprocess.run(["git", "ls-files", "--full-name", "--", str(path)], capture_output=True,
                         text=True, cwd=str(path.parent)).stdout.strip()
    if not top or not rel:
        return None
    r = subprocess.run(["git", "ls-tree", "HEAD", "--", rel], capture_output=True, text=True, cwd=top)
    if r.returncode or not r.stdout.strip():
        return None
    in_head = r.stdout.split()[2]
    actual = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True,
                            cwd=str(path.parent)).stdout.strip()
    return in_head if in_head == actual else None


def cell_name(budget) -> str:
    return "full" if budget in (None, 0, "full", "none") else "trunc%d" % int(budget)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="run_record")
    a = ap.parse_args()
    cfg_path = Path(a.config).resolve()
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if "test" in cfg.get("seeds", {}):
        raise SystemExit("the test seed is already drawn: %s. It is drawn once." % cfg["seeds"]["test"])

    problems, pinned = [], {}
    for budget in cfg["truncation_ladder"]:
        cell = cell_name(budget)
        for m in cfg["models"]:
            p = Path(a.out) / cell / "calibration" / f"{m['key']}__served" / "predictions.json"
            if not p.exists():
                problems.append("%s/%s has no predictions.json" % (cell, m["key"]))
                continue
            blob = committed(p.resolve())
            if blob is None:
                problems.append("%s/%s: predictions.json is not committed as it stands on disk" % (cell, m["key"]))
            else:
                pinned["%s/%s" % (cell, m["key"])] = {"blob": blob,
                                                       "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    if problems:
        print("REFUSED: the test seed is drawn only after every cell's predictions are committed")
        for x in problems:
            print("  -", x)
        return 2

    seed = secrets.randbits(32)
    cfg["seeds"]["test"] = seed
    text = json.dumps(cfg, indent=1, ensure_ascii=False)
    cfg_path.write_text(text + "\n", encoding="utf-8")
    rec = {"drawn": seed, "method": "secrets.randbits(32)", "one_seed_for_every_cell": True,
           "predictions_pinned": pinned}
    Path(a.out).joinpath("test_seed.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    print("\ntest seed %d written into %s. Commit it before running any test block." % (seed, cfg_path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
