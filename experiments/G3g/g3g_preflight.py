#!/usr/bin/env python3
"""Refuse to run a G3g block unless the config is the one PREREG-G3G.md describes.

The same guard as G3f's, for the same reason: a constant written twice and checked once is a
defect of the procedure, so the check is code rather than attention. Every value below is read
out of PREREG-G3G.md by name, so the registration and the config cannot drift apart without this
failing.

What this gate keeps from G3c, what it changes by design, and what it must not do, each checked:
the read-outs, scales, sampling and dither ladder are G3c's; the level count, calibration size
and gap ladder are the family's and are checked against the numbers Section 2 states; the prompts
MUST differ from G3c's; the truncation ladder and the bars must be the ones Section 2 and 4 state;
the read-out ordering claim must be graded in no cell, as Section 4 decides.

    python g3g_preflight.py --config g3g_config.json --block calibration
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORDED_BLOBS: tuple = (
    "3f90e5010498416c081237fc33f368ca5610c7b0",   # at seal, 2026-09-23
)

REUSED = ("scales", "n_samples", "temperature", "dither_ladder", "n_pairs_per_gap")
FAMILY = {"n_items": 4, "n_cal_per_level": 168, "gap_ladder": [1, 2, 3, 4]}
LADDER = ["full", 400, 200]
BARS = (("dev_max", 0.14), ("z_max", 4.55), ("threshold_factor", 1.75),
        ("rank_agreement_min", 0.86), ("vacuity_acc_min", 0.9), ("vacuity_bits_min", 0.5))
G3C_BARS = ("dev_max", "z_max", "threshold_factor", "rank_agreement_min", "vacuity_acc_min")


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
    prereg = (HERE / "PREREG-G3G.md").read_text(encoding="utf-8")
    g3c = json.load(open(g3c_dir() / "prereg_config.json", encoding="utf-8"))
    bad = []

    # --- the prune the registration states in prose
    if "`tree_prune = 1e-4`" not in prereg:
        bad.append("the registration no longer states the prune this check knows")
    elif abs(float(cfg["tree_prune"]) - 1e-4) > 1e-12:
        bad.append("tree_prune is %g; Section 3 says 1e-4" % cfg["tree_prune"])

    # --- bars, stated in the registration; five equal to G3c's, the sixth the scaled one
    for name, want in BARS:
        if "| `%s` | %s |" % (name, want) not in prereg:
            bad.append("the registration does not state %s = %s" % (name, want))
        if abs(float(cfg["bars"][name]) - want) > 1e-12:
            bad.append("bars.%s is %s; Section 4 says %s" % (name, cfg["bars"][name], want))
    for name in G3C_BARS:
        if abs(float(g3c["bars"][name]) - float(cfg["bars"][name])) > 1e-12:
            bad.append("bars.%s is not G3c's value, so it is not taken by reference" % name)
    if "log2(5)/log2(21)" not in prereg:
        bad.append("the registration no longer derives vacuity_bits_min from the scale's capacity")

    # --- the truncation ladder and the cells that grade C3g
    if cfg.get("truncation_ladder") != LADDER:
        bad.append("truncation_ladder is %r; Section 2 says %r" % (cfg.get("truncation_ladder"), LADDER))
    if "Three cells: `200`, `400` and `full`." not in prereg:
        bad.append("the registration no longer states the three-cell ladder this check knows")
    if cfg.get("c3g_graded_cells") != []:
        bad.append("c3g_graded_cells is %r; Section 4 grades C3g in no cell" % cfg.get("c3g_graded_cells"))
    if "`c3g_graded_cells = []`" not in prereg:
        bad.append("the registration no longer records that C3g is graded in no cell")

    # --- judges and their order, from the Section 2 table
    order = re.findall(r"^\| `(\w+)` \| `([\w.-]+)` \| `([^`]+)` \|$", prereg, re.M)
    if [k for k, _, _ in order] != [m["key"] for m in cfg["models"]]:
        bad.append("judges or their order differ from Section 2: %s against %s"
                   % ([k for k, _, _ in order], [m["key"] for m in cfg["models"]]))
    for (key, asked, served), m in zip(order, cfg["models"]):
        if m["model_id"] != "api:" + asked or m.get("served_as") != served:
            bad.append("judge %s: config asks %r expecting %r; Section 2 says %r and %r"
                       % (key, m["model_id"], m.get("served_as"), "api:" + asked, served))

    # --- what G3c fixed and this gate reuses unchanged
    for k in REUSED:
        if k not in cfg:
            bad.append("%s is missing from the config; G3c sets it and the registration reuses it" % k)
        elif cfg[k] != g3c[k]:
            bad.append("%s differs from G3c, which the registration says is reused unchanged" % k)

    # --- what the family changes, and the numbers Section 2 states for it
    for k, want in FAMILY.items():
        if cfg.get(k) != want:
            bad.append("%s is %r; Section 2 says %r" % (k, cfg.get(k), want))
    for phrase in ("`n_items = 4`", "168 reviews at each of the 5 levels", "200\npairs at each gap of 1, 2, 3 and 4"):
        if phrase not in prereg:
            bad.append("the registration no longer states %r" % phrase)

    # --- the one thing that MUST differ
    if cfg.get("prompts") == g3c.get("prompts"):
        bad.append("the prompts are G3c's; this gate exists to change the stimulus family")
    if "{sheet}" not in cfg["prompts"]["score"] or "{first}" not in cfg["prompts"]["pairwise"]:
        bad.append("a prompt has lost its substitution slot")

    # --- seeds
    if a.block == "test" and "test" not in cfg.get("seeds", {}):
        bad.append("no test seed: it is drawn only after every predictions.json is committed (Section 9)")
    if a.block == "calibration" and "test" in cfg.get("seeds", {}):
        bad.append("a test seed exists already; calibration must be run before it is drawn")
    for s in ("probe", "pilot_calibration", "pilot_test"):
        if cfg["seeds"]["calibration"] == cfg["seeds"].get(s):
            bad.append("the calibration seed is the %s seed" % s)

    # --- the registration is the sealed one, or a recorded correction of it
    if RECORDED_BLOBS:
        try:
            blob = subprocess.run(["git", "hash-object", str(HERE / "PREREG-G3G.md")],
                                  capture_output=True, text=True, cwd=str(HERE)).stdout.strip()
            if blob and blob not in RECORDED_BLOBS:
                bad.append("PREREG-G3G.md is %s, which is not the sealed blob nor any correction "
                           "recorded in it (%s); a change after the seal must be recorded"
                           % (blob[:12], ", ".join(b[:12] for b in RECORDED_BLOBS)))
        except OSError:
            pass
    else:
        bad.append("no sealed blob is recorded in this file; the registration is not sealed")

    if bad:
        print("PREFLIGHT REFUSED")
        for b in bad:
            print("  -", b)
        return 2
    print("preflight ok: config matches PREREG-G3G.md for the %s block" % a.block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
