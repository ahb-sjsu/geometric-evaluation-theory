#!/usr/bin/env python3
"""Draw G3h's test seed, once, after predictions.json is in a pushed commit.

Refuses unless `run_record/predictions.json` is in HEAD as it stands on disk (line endings
normalized, since git stores the canonical form), and refuses to run twice. Pins the prediction
file's git blob hash and its sha256, both of the canonical LF bytes and of the bytes on disk.

    python g3h_draw_test_seed.py --config flip_config_qwen7b.json --out run_record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
from pathlib import Path


def in_head(path: Path) -> str | None:
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         cwd=str(path.parent)).stdout.strip()
    rel = subprocess.run(["git", "ls-files", "--full-name", "--", str(path)], capture_output=True,
                         text=True, cwd=str(path.parent)).stdout.strip()
    if not top or not rel:
        return None
    r = subprocess.run(["git", "ls-tree", "HEAD", "--", rel], capture_output=True, text=True, cwd=top)
    if r.returncode or not r.stdout.strip():
        return None
    head_blob = r.stdout.split()[2]
    lf = path.read_bytes().replace(b"\r\n", b"\n")
    disk_blob = hashlib.sha1(b"blob %d\0" % len(lf) + lf).hexdigest()
    return head_blob if head_blob == disk_blob else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="run_record")
    a = ap.parse_args()
    cfg_path = Path(a.config).resolve()
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if "test" in cfg.get("seeds", {}):
        raise SystemExit("the test seed is already drawn: %s. It is drawn once." % cfg["seeds"]["test"])
    p = (Path(a.out) / "predictions.json").resolve()
    if not p.exists():
        raise SystemExit("REFUSED: no predictions.json")
    blob = in_head(p)
    if blob is None:
        raise SystemExit("REFUSED: predictions.json is not in HEAD as it stands on disk")
    raw = p.read_bytes()
    seed = secrets.randbits(32)
    cfg["seeds"]["test"] = seed
    cfg_path.write_text(json.dumps(cfg, indent=1) + "\n", encoding="utf-8")
    rec = {"drawn": seed, "method": "secrets.randbits(32)",
           "predictions_pinned": {"blob": blob,
                                  "sha256": hashlib.sha256(raw).hexdigest(),
                                  "sha256_lf": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}}
    (Path(a.out) / "test_seed.json").write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rec, indent=1))
    print("\ntest seed %d written into %s. Commit it before running the test block." % (seed, cfg_path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
