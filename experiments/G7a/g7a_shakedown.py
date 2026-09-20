#!/usr/bin/env python3
"""G7a shakedown: what the pipeline yields, without seeing what the gate predicts.

Runs on the shakedown month only and writes nothing to any ledger.

The registration will predict the thresholds at bullet, rapid and classical from
a calibration on blitz. A shakedown that fitted a threshold in those categories
would show me the answer before I registered the question, and the shakedown
month is the same population as the evaluation months, so "it was only the
shakedown" would not make it blind.

So this script is split by what it is allowed to look at.

  every category   COUNTS ONLY. How many positions were labelled, how many were
                   undecided, in how many the human played one of the engine's
                   top two, how many are two-alternative, how many survive both.
                   These size the evaluation run. None of them is a quality
                   measure and none is compared across categories for anything
                   but sample size.

  blitz only       the threshold fit, since blitz is the calibration category
                   and its threshold is an input to the prediction and not a
                   thing predicted.

The refusal is in the code and not in my intentions. `fit_threshold` is called
on blitz rows and on nothing else, and the script asserts as much.
"""
import argparse
import glob
import json

import numpy as np

import g7a_threshold as T

CALIBRATION = "blitz"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="glob of label shards")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = []
    for p in sorted(glob.glob(a.labels)):
        rows += [json.loads(l) for l in open(p)]
    cats = sorted({r["category"] for r in rows})
    rec = {"n_rows": len(rows), "third_cutoff": T.THIRD_CUTOFF, "counts": {}}

    for c in cats:
        sub = [r for r in rows if r["category"] == c]
        ch = np.array([r["choice"] for r in sub])
        g23 = np.array([r["gap23"] for r in sub])
        top2 = ch <= 1
        two = g23 >= T.THIRD_CUTOFF
        rec["counts"][c] = {
            "labelled_undecided": len(sub),
            "played_one_of_top_two": int(top2.sum()),
            "two_alternative": int(two.sum()),
            "survive_both": int((top2 & two).sum()),
            "share_survive": float((top2 & two).mean()) if len(sub) else None,
        }

    cal = [r for r in rows if r["category"] == CALIBRATION]
    fitted_on = {r["category"] for r in cal}
    assert fitted_on <= {CALIBRATION}, "the shakedown may fit the calibration category only"
    fit = T.fit_threshold([r["gap12"] for r in cal], [r["gap23"] for r in cal],
                          [r["choice"] for r in cal])
    rec["calibration_category"] = CALIBRATION
    rec["calibration_fit"] = fit
    rec["gap12_quantiles_calibration"] = (
        [float(x) for x in np.quantile([r["gap12"] for r in cal], [0.1, 0.25, 0.5, 0.75, 0.9])]
        if cal else None)

    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
