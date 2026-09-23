#!/usr/bin/env python3
"""Refuse to run a G3f block unless the config is the one PREREG-G3F.md describes.

G3e learned this the hard way: a constant written twice and checked once is a defect of the
procedure, so the check is code rather than attention. G3f then proved the lesson again from the
other side. `dither_ladder` was missing from the config entirely and was found by a rehearsal of
the prediction step, not by a guard, because this file did not exist yet and G3e's version is
bound to G3e's registration. Accounting beats recall.

Every value below is read out of PREREG-G3F.md by name, so the registration and the config cannot
drift apart without this failing.

One check is inverted from G3e's. That gate reused G3c's prompts unchanged and asserted they were
identical. This gate exists to change the stimulus family, so its prompts MUST differ from G3c's
and everything else must not. Asserting sameness there would refuse the very thing being tested.

    python g3f_preflight.py --config g3f_config.json --block calibration
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDED_BLOBS = (
    "dd5dc2268cfb759404f0cb940107895b48968e1c",   # at seal
    "85c626cd7b06e40a4442e43af2ece129528ec11f",   # + stimulus defect, 23:02Z
    "0a89b1638c25edb32a7da7c2af32e4766ce5dc6e",   # + config defect, 23:15Z
    "f92610225a704af34e5afa4d21cc63d0b988b1de",   # + qwen3_flash withdrawn, 00:50Z
)

# Reused from G3c unchanged. `prompts` is deliberately absent: see the module docstring.
REUSED = ("n_items", "n_cal_per_level", "gap_ladder", "n_pairs_per_gap", "scales", "n_samples",
          "temperature", "dither_ladder")

BARS = (("dev_max", 0.14), ("z_max", 4.55), ("threshold_factor", 1.75),
        ("rank_agreement_min", 0.86), ("vacuity_acc_min", 0.9), ("vacuity_bits_min", 1.0))


def g3c_dir() -> Path:
    for cand in ("G3c", "g3c"):
        if (HERE.parent / cand / "prereg_config.json").exists():
            return HERE.parent / cand
    raise SystemExit("cannot find G3c beside this gate")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--block", required=True, choices=["calibration", "test"])
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    prereg = (HERE / "PREREG-G3F.md").read_text(encoding="utf-8")
    g3c = json.load(open(g3c_dir() / "prereg_config.json", encoding="utf-8"))
    bad = []

    # --- the prune the registration states in prose
    if "`tree_prune = 1e-4`" not in prereg:
        bad.append("the registration no longer states the prune this check knows")
    elif abs(float(cfg["tree_prune"]) - 1e-4) > 1e-12:
        bad.append("tree_prune is %g; Section 3 says 1e-4" % cfg["tree_prune"])

    # --- bars, stated in the registration AND equal to G3c's, since they are taken by reference
    for name, want in BARS:
        if "| `%s` | %s |" % (name, want) not in prereg:
            bad.append("the registration does not state %s = %s" % (name, want))
        if abs(float(cfg["bars"][name]) - want) > 1e-12:
            bad.append("bars.%s is %s; Section 4 says %s" % (name, cfg["bars"][name], want))
        if abs(float(g3c["bars"][name]) - want) > 1e-12:
            bad.append("bars.%s is not G3c's value, so it is not taken by reference" % name)

    # --- judges and their order, from the Section 2 table
    order = re.findall(r"^\| `(\w+)` \| `([\w.-]+)` \| `([^`]+)` \| \w+ \|$", prereg, re.M)
    if [k for k, _, _ in order] != [m["key"] for m in cfg["models"]]:
        bad.append("judges or their order differ from Section 2: %s against %s"
                   % ([k for k, _, _ in order], [m["key"] for m in cfg["models"]]))
    for (key, asked, served), m in zip(order, cfg["models"]):
        if m["model_id"] != "api:" + asked or m.get("served_as") != served:
            bad.append("judge %s: config asks %r expecting %r; Section 2 says %r and %r"
                       % (key, m["model_id"], m.get("served_as"), "api:" + asked, served))

    # --- the design G3c fixed and this gate reuses unchanged
    for k in REUSED:
        if k not in cfg:
            bad.append("%s is missing from the config; G3c sets it and the registration reuses it" % k)
        elif cfg[k] != g3c[k]:
            bad.append("%s differs from G3c, which the registration says is reused unchanged" % k)

    # --- the one thing that MUST differ
    if cfg.get("prompts") == g3c.get("prompts"):
        bad.append("the prompts are G3c's; this gate exists to change the stimulus family")
    for p in ("score", "pairwise"):
        if "{sheet}" not in cfg["prompts"]["score"] or "{first}" not in cfg["prompts"]["pairwise"]:
            bad.append("prompts.%s has lost its substitution slot" % p)

    # --- seeds
    if a.block == "test" and "test" not in cfg.get("seeds", {}):
        bad.append("no test seed: it is drawn only after predictions.json is committed (Section 9)")
    if a.block == "calibration" and "test" in cfg.get("seeds", {}):
        bad.append("a test seed exists already; calibration must be run before it is drawn")
    if cfg["seeds"]["calibration"] == cfg["seeds"]["probe"]:
        bad.append("the calibration seed is the probe seed")

    # --- the registration is the sealed one, or a recorded correction of it
    try:
        blob = subprocess.run(["git", "hash-object", str(HERE / "PREREG-G3F.md")],
                              capture_output=True, text=True, cwd=str(HERE)).stdout.strip()
        if blob and blob not in RECORDED_BLOBS:
            bad.append("PREREG-G3F.md is %s, which is not the sealed blob nor any correction "
                       "recorded in it (%s); a change after the seal must be recorded"
                       % (blob[:12], ", ".join(b[:12] for b in RECORDED_BLOBS)))
    except OSError:
        pass

    if bad:
        print("PREFLIGHT REFUSED")
        for b in bad:
            print("  -", b)
        return 2
    print("preflight ok: config matches PREREG-G3F.md for the %s block" % a.block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
