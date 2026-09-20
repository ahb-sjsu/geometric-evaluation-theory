#!/usr/bin/env python3
"""G7a shakedown: what the pipeline yields, without seeing what the gate predicts.

Runs on the shakedown month only and writes nothing to any ledger.

The registration will predict the thresholds at bullet, rapid and classical from
a calibration on blitz. A shakedown that fitted a threshold in those categories
would show me the answer before I registered the question, and the shakedown
month is the same population as the evaluation months, so "it was only the
shakedown" would not make it blind.

So this script is split by what it is allowed to look at.

  every category   COUNTS ONLY. How many positions were labelled, how many are
                   undecided, in how many the human played one of the engine's
                   top two, how many are two-alternative, how many survive all
                   three. These size the evaluation run. None is a quality
                   measure and none is compared across categories for anything
                   but sample size.

  blitz only       the threshold fit, since blitz is the calibration category
                   and its threshold is an input to the prediction and not a
                   thing predicted.

  no category      engine sensitivity. The same positions labelled at two node
                   counts, pooled over categories, to see whether the labels
                   depend on how hard the engine looked. Pooled on purpose, so
                   it cannot show a difference between budgets.

The refusal is in the code and not in my intentions. `fit_threshold` is called
on blitz rows and on nothing else, and the script asserts as much.
"""
import argparse
import glob
import json

import numpy as np

import g7a_threshold as T

CALIBRATION = "blitz"


def load(pattern):
    rows = []
    for p in sorted(glob.glob(pattern)):
        rows += [json.loads(l) for l in open(p)]
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="glob of label shards")
    ap.add_argument("--labels-deep", help="glob of the same positions at a higher node count")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rows = load(a.labels)
    cp = np.array([r["cp"] for r in rows], dtype=float)
    g12, g23, und = T.gaps_from_cp(cp)
    ch = np.array([r["choice"] for r in rows])
    cat = np.array([r["category"] for r in rows])
    rec = {"n_rows": len(rows), "third_cutoff": T.THIRD_CUTOFF,
           "consequence_map": "Lichess logistic, k=%g" % T.LICHESS_K, "counts": {}}

    for c in sorted(set(cat)):
        m = cat == c
        top2, two = ch[m] <= 1, g23[m] >= T.THIRD_CUTOFF
        keep = und[m] & top2 & two
        rec["counts"][c] = {
            "labelled": int(m.sum()), "undecided": int(und[m].sum()),
            "played_one_of_top_two": int((und[m] & top2).sum()),
            "two_alternative": int((und[m] & two).sum()),
            "survive_all": int(keep.sum()),
            "share_of_labelled_surviving": float(keep.mean()),
        }

    m = (cat == CALIBRATION) & und
    assert set(cat[m]) <= {CALIBRATION}, "the shakedown may fit the calibration category only"
    rec["calibration_category"] = CALIBRATION
    rec["calibration_fit"] = T.fit_threshold(g12[m], g23[m], ch[m])
    rec["gap12_quantiles_calibration"] = [float(x) for x in
                                          np.quantile(g12[m], [0.1, 0.25, 0.5, 0.75, 0.9])]

    if a.labels_deep:
        deep = {(r["game"], r["ply"]): r for r in load(a.labels_deep)}
        pairs = [(r, deep[(r["game"], r["ply"])]) for r in rows if (r["game"], r["ply"]) in deep]
        if pairs:
            s_cp = np.array([p[0]["cp"] for p in pairs], float)
            d_cp = np.array([p[1]["cp"] for p in pairs], float)
            s12, s23, su = T.gaps_from_cp(s_cp)
            d12, d23, du = T.gaps_from_cp(d_cp)
            s_ch = np.array([p[0]["choice"] for p in pairs])
            d_ch = np.array([p[1]["choice"] for p in pairs])
            s_keep = su & (s_ch <= 1) & (s23 >= T.THIRD_CUTOFF)
            d_keep = du & (d_ch <= 1) & (d23 >= T.THIRD_CUTOFF)
            both = s_keep & d_keep
            rec["engine_sensitivity_pooled"] = {
                "positions_compared": len(pairs),
                "nodes": [pairs[0][0]["nodes"], pairs[0][1]["nodes"]],
                "same_best_move": float(np.mean([p[0]["engine_moves"][0] == p[1]["engine_moves"][0]
                                                 for p in pairs])),
                "same_choice_index": float((s_ch == d_ch).mean()),
                "kept_at_shallow": int(s_keep.sum()), "kept_at_deep": int(d_keep.sum()),
                "kept_at_both": int(both.sum()),
                "correct_at_shallow_among_both": float((s_ch[both] == 0).mean()) if both.any() else None,
                "correct_at_deep_among_both": float((d_ch[both] == 0).mean()) if both.any() else None,
                "gap12_correlation_among_both": float(np.corrcoef(s12[both], d12[both])[0, 1])
                if both.sum() > 2 else None,
            }

    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
