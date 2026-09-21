#!/usr/bin/env python3
"""EXPLORATORY, run after the gates were graded. Where does the predictive power enter?

The paper compares one predictor built from a judge's calibration block against one rival that
assumes the judge uses every level of the nominal scale. A reader can fairly object that the
comparison is lopsided: the calibrated predictor knows the judge's whole conditional score
distribution and the rival knows nothing, so of course it wins, and the win does not say which
part of that knowledge did the work.

This puts four predictors of the same quantity on one ladder, each knowing strictly more than the
one before, and scores them all against the same observed test curve.

  1 nominal      every level of the nominal scale, evenly spaced. What the scale promises.
  2 cardinality  only HOW MANY distinct scores the judge used, assumed evenly spaced. This is the
                 budget and nothing else: a count of symbols.
  3 codebook     how many AND WHERE: the judge's own distinct scores, with quality mapped to the
                 nearest of them. Still deterministic, still no noise.
  4 channel      the calibrated predictor of the registration: the judge's conditional score
                 distribution at every quality level, noise included.

All four predict the accuracy curve of the greedy read-out, so the comparison is like for like.
The score is the squared error against the observed curve summed over the gap ladder, which is the
statistic the registration already uses for its own rival.

If rung 2 already lands near rung 4, the claim is about a budget, a count of symbols. If it does
not, the claim is about the effective channel, and this says so in the same units.

    python budget_ladder.py --out budget_ladder.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def cross_pair_curve(s, N, gaps):
    """Accuracy of a deterministic scorer s(k) over cross pairs, the shape nominal_curve uses."""
    return np.array([np.mean([1.0 if s(k) > s(k + g) else 0.0 for k in range(0, N - g + 1)]) for g in gaps])


def rung_nominal(scale, N, gaps, book):
    L = scale["hi"] - scale["lo"]
    return cross_pair_curve(lambda k: round(L * (1 - k / N)), N, gaps)


def rung_cardinality(scale, N, gaps, book):
    K = len(book)
    if K < 2:
        return np.zeros(len(gaps))
    return cross_pair_curve(lambda k: round((K - 1) * (1 - k / N)), N, gaps)


def rung_codebook(scale, N, gaps, book):
    v = np.array(sorted(book), dtype=float)
    lo, L = scale["lo"], scale["hi"] - scale["lo"]
    def s(k):
        target = lo + L * (1 - k / N)
        return float(v[int(np.argmin(np.abs(v - target)))])
    return cross_pair_curve(s, N, gaps)


def rung_bits(scale, N, gaps, book, bits=None):
    """The theory names a rate in bits as one of its three budget forms. The judge's calibration
    block says how many bits its greedy score carries about quality, so the levels this rung gets
    is 2 to that power: not how many scores it wrote, but how many it used to effect."""
    if bits is None or bits <= 0:
        return np.zeros(len(gaps))
    K = max(2, int(round(2.0 ** bits)))
    return cross_pair_curve(lambda k: round((K - 1) * (1 - k / N)), N, gaps)


RUNGS = [("1_nominal", rung_nominal), ("2_cardinality", rung_cardinality),
         ("2b_bits", rung_bits), ("3_codebook", rung_codebook)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grades", nargs="+", default=[str(HERE / "run_record" / "grade_*.json"),
                                                    str(HERE.parent / "G3e" / "run_record" / "grade_*.json")])
    ap.add_argument("--out", default="budget_ladder.json")
    a = ap.parse_args()

    rows, files = [], []
    for pat in a.grades:
        files += sorted(glob.glob(pat))
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        judge = os.path.basename(f)[6:-5]
        obs, v = d["observed"], d.get("verdicts", {})
        # G3e keeps the predictions inside the grade record; G3c keeps them beside it.
        pred = d.get("predictions")
        if pred is None:
            side = Path(f).with_name("predictions_%s.json" % judge)
            if not side.exists():
                print("no predictions for", judge, "- skipped"); continue
            pred = json.load(open(side, encoding="utf-8"))
        gate = pred.get("gate", "?")
        vacuous = not v.get("anti_vacuity", {}).get("met", True)
        N = 20
        gaps = pred["gaps"]
        for key, entry in pred["scales"].items():
            lo, hi = (int(x) for x in key.split("-"))
            scale = {"lo": lo, "hi": hi}
            book = entry["codebook"]["distinct_scores"]
            observed = np.array(obs["scales"][key]["argmax"]["acc"], float)
            row = {"gate": gate, "judge": judge, "vacuous": vacuous, "scale": key,
                   "nominal_levels": hi - lo + 1, "codebook_size": len(book), "sse": {}, "threshold": {}}
            from_pred = np.array(entry["readouts"]["argmax"]["acc"], float)
            bits = entry["codebook"].get("information_about_quality_bits")
            row["bits"] = bits
            row["effective_levels"] = None if not bits or bits <= 0 else max(2, int(round(2.0 ** bits)))
            for name, fn in RUNGS:
                c = fn(scale, N, gaps, book, bits) if name == "2b_bits" else fn(scale, N, gaps, book)
                row["sse"][name] = round(float(((c - observed) ** 2).sum()), 5)
            row["sse"]["4_channel"] = round(float(((from_pred - observed) ** 2).sum()), 5)
            rows.append(row)

    print("%-5s %-14s %-6s %4s %4s %4s | %8s %8s %8s %8s %8s" %
          ("gate", "judge", "scale", "nom", "book", "eff", "1 nomin", "2 cardin", "2b bits", "3 codebk", "4 channel"))
    for r in rows:
        if r["vacuous"]:
            continue
        s = r["sse"]
        print("%-5s %-14s %-6s %4d %4d %4s | %8.4f %8.4f %8.4f %8.4f %8.4f" %
              (r["gate"], r["judge"], r["scale"], r["nominal_levels"], r["codebook_size"],
               str(r["effective_levels"]), s["1_nominal"], s["2_cardinality"], s["2b_bits"],
               s["3_codebook"], s["4_channel"]))

    graded = [r for r in rows if not r["vacuous"]]
    summary = {"exploratory": True,
               "why": "run after the gates were graded; it asks which part of the calibration does the predicting",
               "statistic": "squared error of a predicted greedy-accuracy curve against the observed one, summed over the gap ladder",
               "rows": rows}
    if graded:
        for name in ("1_nominal", "2_cardinality", "2b_bits", "3_codebook", "4_channel"):
            vals = [r["sse"][name] for r in graded]
            summary["median_sse_" + name] = round(float(np.median(vals)), 5)
        # How far along the road from the nominal rival to the calibrated channel does each rung get?
        # Only cells where there is a road: a judge already near perfect leaves nothing to explain.
        live = [r for r in graded if r["sse"]["1_nominal"] - r["sse"]["4_channel"] > 0.05]
        for name in ("2_cardinality", "2b_bits", "3_codebook"):
            fr = [(r["sse"]["1_nominal"] - r["sse"][name]) / (r["sse"]["1_nominal"] - r["sse"]["4_channel"])
                  for r in live]
            summary["share_of_the_gap_closed_by_" + name] = round(float(np.median(fr)), 3)
        summary["live_cells"] = [len(live), len(graded)]
        print("")
        print("of the distance from the nominal rival to the calibrated channel, the median cell closes")
        print("  %.0f percent knowing only how many scores the judge used"
              % (100 * summary["share_of_the_gap_closed_by_2_cardinality"]))
        print("  %.0f percent knowing the bits its score carries about quality"
              % (100 * summary["share_of_the_gap_closed_by_2b_bits"]))
        print("  %.0f percent knowing how many scores and where they sit"
              % (100 * summary["share_of_the_gap_closed_by_3_codebook"]))
        print("  the rest needs the conditional distribution, over %d of %d cells with room to explain"
              % tuple(summary["live_cells"]))
        for name in ("2_cardinality", "2b_bits", "3_codebook"):
            summary["cells_" + name + "_beats_nominal"] = [
                sum(1 for r in graded if r["sse"][name] < r["sse"]["1_nominal"]), len(graded)]
        print("beats the nominal rival in: cardinality %d of %d, bits %d of %d, codebook %d of %d"
              % tuple(summary["cells_2_cardinality_beats_nominal"] + summary["cells_2b_bits_beats_nominal"]
                      + summary["cells_3_codebook_beats_nominal"]))
        wins = sum(1 for r in graded if r["sse"]["4_channel"] <= min(r["sse"][n] for n, _ in RUNGS))
        summary["cells_where_the_channel_is_best"] = [wins, len(graded)]
        best_budget = sum(1 for r in graded if r["sse"]["2_cardinality"] <= r["sse"]["4_channel"])
        summary["cells_where_cardinality_alone_matches_the_channel"] = [best_budget, len(graded)]
        print("")
        print("median squared error: nominal %.4f  cardinality %.4f  bits %.4f  codebook %.4f  channel %.4f"
              % tuple(summary["median_sse_" + n] for n in
                      ("1_nominal", "2_cardinality", "2b_bits", "3_codebook", "4_channel")))
        print("the channel is the best of the four in %d of %d graded cells" % tuple(summary["cells_where_the_channel_is_best"]))
        print("cardinality alone matches or beats it in %d of %d" % tuple(summary["cells_where_cardinality_alone_matches_the_channel"]))
    json.dump(summary, open(a.out, "w"), indent=1, default=float)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
