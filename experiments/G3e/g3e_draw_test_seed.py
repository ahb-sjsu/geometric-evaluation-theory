#!/usr/bin/env python3
"""Draw G3e's test seed, once, after the predictions are committed.

The gate's whole claim is that a judge's calibration block predicts a test block it has not seen.
That is only true if the test worksheets did not exist when the predictions were written, so this
script refuses to run unless every judge's `predictions.json` is committed in git, and it refuses
to run twice.

    python g3e_draw_test_seed.py --config g3e_config.json --out run_record
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
    """The blob hash git holds for this path, or None if what is on disk is not committed."""
    r = subprocess.run(["git", "ls-files", "-s", "--", str(path)], capture_output=True, text=True,
                       cwd=str(path.parent))
    if r.returncode or not r.stdout.strip():
        return None
    indexed = r.stdout.split()[1]
    actual = subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True,
                            cwd=str(path.parent)).stdout.strip()
    return indexed if indexed == actual else None


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
    for m in cfg["models"]:
        p = Path(a.out) / "calibration" / f"{m['key']}__served" / "predictions.json"
        if not p.exists():
            problems.append("%s has no predictions.json" % m["key"])
            continue
        blob = committed(p.resolve())
        if blob is None:
            problems.append("%s: predictions.json is not committed as it stands on disk" % m["key"])
        else:
            pinned[m["key"]] = {"blob": blob,
                                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    if problems:
        print("REFUSED: the test seed is drawn only after the predictions are committed")
        for x in problems:
            print("  -", x)
        return 2

    seed = secrets.randbits(32)
    cfg["seeds"]["test"] = seed
    text = json.dumps(cfg, indent=1, ensure_ascii=False)
    cfg_path.write_text(text + "\n", encoding="utf-8")
    rec = {"drawn": seed, "method": "secrets.randbits(32)", "predictions_pinned": pinned}
    Path(a.out).joinpath("test_seed.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))
    print("\ntest seed %d written into %s. Commit it before running the test block." % (seed, cfg_path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
