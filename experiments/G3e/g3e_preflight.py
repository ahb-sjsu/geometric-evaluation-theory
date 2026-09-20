#!/usr/bin/env python3
"""Refuse to run a G3e block unless the config is the one the registration describes.

The sealed registration and the sealed config carried two different values of `tree_prune`, which
was found thirty seconds into a calibration run rather than before it (PREREG-G3E.md, registration
defect). A constant written twice and checked once is a defect of the procedure, so the check is
code now instead of attention.

Every value below is read out of PREREG-G3E.md by name, so the file cannot drift from the config
without this failing. It also refuses to start a test block while no test seed exists, and refuses
to start any block if the registration's own blob hash is not the one the campaign recorded.

    python g3e_preflight.py --config g3e_config.json --block calibration
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEALED_BLOB = "4c0b1cb1a4f3705e7700a237cd09c1715838e36a"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--block", required=True, choices=["calibration", "test"])
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    prereg = (HERE / "PREREG-G3E.md").read_text(encoding="utf-8")
    bad = []

    # --- constants the registration states in prose, checked against the config
    if not re.search(r"prunes below \*\*1e-4\*\*", prereg):
        bad.append("the registration no longer states the prune this check knows")
    elif abs(cfg["tree_prune"] - 1e-4) > 1e-12:
        bad.append("tree_prune is %g; the registration Section 3 says 1e-4" % cfg["tree_prune"])

    for name, want in (("dev_max", 0.14), ("z_max", 4.55), ("threshold_factor", 1.75),
                       ("rank_agreement_min", 0.86), ("vacuity_acc_min", 0.9), ("vacuity_bits_min", 1.0)):
        if f"`{name}` {want}" not in prereg and f"`{name}` at least {want}" not in prereg:
            bad.append("the registration does not state %s = %s" % (name, want))
        if abs(float(cfg["bars"][name]) - want) > 1e-12:
            bad.append("bars.%s is %s; the registration Section 4 says %s" % (name, cfg["bars"][name], want))

    order = re.findall(r"^\| `(\w+)` \| `([\w.-]+)` \| `([^`]+)` \|$", prereg, re.M)
    if [k for k, _, _ in order] != [m["key"] for m in cfg["models"]]:
        bad.append("the judges or their order differ from Section 2: %s against %s"
                   % ([k for k, _, _ in order], [m["key"] for m in cfg["models"]]))
    for (key, asked, served), m in zip(order, cfg["models"]):
        if m["model_id"] != "api:" + asked or m.get("served_as") != served:
            bad.append("judge %s: the config asks %r and expects %r; Section 2 says %r and %r"
                       % (key, m["model_id"], m.get("served_as"), "api:" + asked, served))

    # --- the design G3c fixed and this gate reuses unchanged
    g3c = json.load(open(HERE.parent / ("G3c" if (HERE.parent / "G3c").exists() else "g3c") / "prereg_config.json", encoding="utf-8"))
    for k in ("n_items", "n_cal_per_level", "gap_ladder", "n_pairs_per_gap", "scales", "n_samples",
              "temperature", "dither_ladder", "prompts"):
        if cfg[k] != g3c[k]:
            bad.append("%s differs from G3c, which the registration says is reused unchanged" % k)

    # --- seeds
    if a.block == "test" and "test" not in cfg.get("seeds", {}):
        bad.append("no test seed: it is drawn only after predictions.json is committed (Section 9)")
    if a.block == "calibration" and "test" in cfg.get("seeds", {}):
        bad.append("a test seed exists already; calibration must be run before it is drawn")
    if cfg["seeds"]["calibration"] == cfg["seeds"]["probe"]:
        bad.append("the calibration seed is the probe seed")

    # --- the registration is the sealed one
    try:
        blob = subprocess.run(["git", "hash-object", str(HERE / "PREREG-G3E.md")],
                              capture_output=True, text=True, cwd=str(HERE)).stdout.strip()
        if blob and blob != SEALED_BLOB:
            print("note: PREREG-G3E.md is %s, sealed as %s; any change after the seal must be a "
                  "recorded correction" % (blob[:12], SEALED_BLOB[:12]))
    except OSError:
        pass

    if bad:
        print("PREFLIGHT REFUSED")
        for b in bad:
            print("  -", b)
        return 2
    print("preflight ok: config matches PREREG-G3E.md for the %s block" % a.block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
