#!/usr/bin/env python3
"""G9 secondary arm: does a smaller budget lower the rank of the metric?

PREREG-G9.md Section 5, secondary. GET says the resolution budget B coarsens
the distinctions an evaluator can make, which lowers the effective rank of its
metric and reverses preference between fixed actions (Theorem 5, prediction
(ii)). G7 would test that in humans and cannot until an ethics protocol exists.
The game clock manipulates the budget with nobody administering it.

Two things about this arm are different from the hull-law arm and both matter.

It works in the full five-dimensional consequence space, not on a plane. The
hull-law arm projects to two coordinates because hull membership is almost
never attained above two dimensions, and that projection was later found to
manufacture violations. Rank estimation has no such need, so nothing is thrown
away here.

Its order of operations is enforced by the registration, not by convention. The
low-pressure fit and the reversal set it predicts are written to a file and
hashed BEFORE any high-pressure row is read. `--fit-low` refuses to look at a
high-pressure row at all, and `--score-high` refuses to run without a committed
fit whose hash it records. A prediction scored after seeing the thing it
predicts is not a prediction.

Usage.

    python g9_budget.py --selftest
    python g9_budget.py --fit-low   --out low_fit.json
    python g9_budget.py --score-high --fit low_fit.json --out budget_results.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.abspath(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


g9 = _load("g9_hull_law", os.path.join(HERE, "g9_hull_law.py"))
g5 = _load("g5_identify", os.path.join(HERE, "..", "G5", "g5_identify.py"))

COORDS = g9.COORDS
ACTIONS = g9.ACTIONS
CELLKEYS = g9.CELLKEYS
# Inherited from G5 and replaced by the calibrated value once rank_cut.json
# exists. The self-test found G5's cut reads one rank too many on this world.
RANK_CUT = g5.RANK_CUT
_CAL = os.path.join(HERE, "rank_cut.json")
if os.path.exists(_CAL):
    RANK_CUT = float(json.load(open(_CAL))["chosen_cut"])


# --------------------------------------------------------------------------- world

def battery(stratum):
    """Consequence points and the strict preferences revealed inside each cell.

    One evaluator, many menus. The metric and the ideal are shared across cells,
    which is what GET's split between the world's (X, A, C) and the evaluator's
    (G, B, K) actually asserts.
    """
    if stratum not in ("low", "high"):
        raise ValueError("stratum must be low or high")
    df = g9.prepare()
    df = df[df["pressure"] == stratum].copy()
    if len(df) == 0:
        raise SystemExit("no rows in stratum %s" % stratum)
    cmap = g9.consequence_map(df)

    counts = df.groupby(["posteam"] + CELLKEYS + ["action"], observed=True).size()
    counts = counts.unstack(fill_value=0)
    for a in ACTIONS:
        if a not in counts.columns:
            counts[a] = 0
    counts = counts[list(ACTIONS)]
    counts = counts[(counts >= g9.MIN_PER_ACTION).all(axis=1)]
    # League evaluator: pool the franchises, which is what the registration says
    # this arm must do, because no per-evaluator definition leaves enough
    # high-pressure units to fit anything.
    pooled = counts.groupby(level=list(range(1, counts.index.nlevels))).sum()

    rows, pairs, meta = [], [], []
    index = {}
    for key, block in cmap.groupby(CELLKEYS, observed=True):
        block = block.set_index("action")
        if not all(a in block.index for a in ACTIONS):
            continue
        k = key if isinstance(key, tuple) else (key,)
        if k not in pooled.index:
            continue
        Y = block.loc[list(ACTIONS), list(COORDS)].to_numpy(dtype=float)
        if not np.isfinite(Y).all():
            continue
        base = len(rows)
        for i, a in enumerate(ACTIONS):
            rows.append(Y[i])
            meta.append({"cell": [int(x) for x in k], "action": a})
        c = pooled.loc[k].to_numpy(dtype=float)
        for i, j in itertools.combinations(range(len(ACTIONS)), 2):
            # Strict only. Equal counts are not strictly better either way,
            # which is the sealed tie rule.
            if c[i] > c[j]:
                pairs.append((base + i, base + j))
            elif c[j] > c[i]:
                pairs.append((base + j, base + i))
    return np.array(rows, dtype=float), pairs, meta


def effective_rank(G, cut=RANK_CUT):
    w = np.linalg.eigvalsh(G)
    w = np.clip(w, 0, None)
    if w.max() <= 0:
        return 0, w.tolist()
    return int((w > cut * w.max()).sum()), w.tolist()


def order_under(G, h, Y, pairs):
    """Which way each registered pair is ordered by this evaluator."""
    q = np.einsum("ij,jk,ik->i", Y, G, Y) - 2.0 * (Y @ h)
    return {(a, b): bool(q[a] < q[b]) for a, b in pairs}


def truncate(G, k):
    w, V = np.linalg.eigh(G)
    idx = np.argsort(w)[::-1][:k]
    return (V[:, idx] * w[idx]) @ V[:, idx].T


# --------------------------------------------------------------------------- stages

def fit_low(out_path):
    Y, pairs, meta = battery("low")
    fit = g5.estimate(Y, pairs)
    G, h = fit["G"], fit["h"]
    rank, eig = effective_rank(G)
    base = order_under(G, h, Y, pairs)

    # The prediction. Theorem 5 says a rank cut reverses preference between
    # fixed actions. For every budget below the fitted rank, the pairs that
    # flip are named now, before any high-pressure row exists to score them.
    predicted = {}
    for k in range(1, max(rank, 1)):
        Gk = truncate(G, k)
        ok = order_under(Gk, h, Y, pairs)
        # The baseline orientation travels with the pair. Scoring later must
        # compare against what the low fit actually said, not against an
        # assumption about which way it said it.
        flips = [[int(a), int(b), bool(base[(a, b)])]
                 for (a, b) in pairs if ok[(a, b)] != base[(a, b)]]
        predicted[str(k)] = flips

    rec = {
        "stratum": "low",
        "n_points": int(Y.shape[0]),
        "n_pairs": int(len(pairs)),
        "margin": fit["margin"],
        "solver_status": fit["status"],
        "effective_rank": rank,
        "eigenvalues": eig,
        "G": G.tolist(),
        "h": h.tolist(),
        "coords": list(COORDS),
        "predicted_reversals_by_budget": predicted,
        "predicted_counts": {k: len(v) for k, v in predicted.items()},
        "meta": meta,
    }
    blob = json.dumps(rec, sort_keys=True).encode()
    rec["self_sha256"] = hashlib.sha256(blob).hexdigest()
    with open(out_path, "w") as f:
        json.dump(rec, f, sort_keys=True)
    print("wrote", out_path)
    print("points %d pairs %d margin %.6f status %s"
          % (rec["n_points"], rec["n_pairs"], rec["margin"], rec["solver_status"]))
    print("effective rank (low) =", rank)
    print("eigenvalues:", ["%.4g" % v for v in sorted(eig, reverse=True)])
    print("predicted reversals per budget:", rec["predicted_counts"])
    print("sha256 of the committed fit:", hashlib.sha256(open(out_path, "rb").read()).hexdigest())
    return 0


def score_high(fit_path, out_path):
    if not os.path.exists(fit_path):
        raise SystemExit("no committed low-pressure fit; run --fit-low first")
    committed_sha = hashlib.sha256(open(fit_path, "rb").read()).hexdigest()
    low = json.load(open(fit_path))
    if low.get("stratum") != "low":
        raise SystemExit("committed fit is not the low-pressure stratum")

    Y, pairs, meta = battery("high")
    fit = g5.estimate(Y, pairs)
    G, h = fit["G"], fit["h"]
    rank_high, eig_high = effective_rank(G)
    rank_low = low["effective_rank"]

    # Score the committed prediction for the budget the high stratum turned out
    # to sit at. The set was fixed before this stratum was opened.
    key = str(rank_high)
    predicted = low["predicted_reversals_by_budget"].get(key, [])

    # The high fit's own ordering, compared with the low fit's ordering on the
    # pairs both strata share. Pairs are addressed by (cell, action), never by
    # row index, because the two strata index their rows differently.
    def addr(m, i):
        return (tuple(m[i]["cell"]), m[i]["action"])

    low_meta = low["meta"]
    high_order = order_under(G, h, Y, pairs)
    high_by_addr = {(addr(meta, a), addr(meta, b)): v for (a, b), v in high_order.items()}

    hits, checked = 0, 0
    for entry in predicted:
        a, b = entry[0], entry[1]
        base_orientation = bool(entry[2]) if len(entry) > 2 else True
        pa, pb = addr(low_meta, a), addr(low_meta, b)
        if (pa, pb) in high_by_addr:
            observed = high_by_addr[(pa, pb)]
        elif (pb, pa) in high_by_addr:
            observed = not high_by_addr[(pb, pa)]
        else:
            continue
        checked += 1
        # A reversal is observed when the high evaluator orders the pair the
        # other way from whatever the low fit said about it.
        if observed != base_orientation:
            hits += 1
    share = (hits / checked) if checked else None

    rank_falls = rank_high < rank_low
    if rank_falls and share is not None and share >= 0.60:
        verdict = "PASS"
    elif rank_high >= rank_low:
        verdict = "FAIL"
    else:
        verdict = "INDETERMINATE"

    rec = {
        "committed_fit_sha256": committed_sha,
        "effective_rank_low": rank_low,
        "effective_rank_high": rank_high,
        "eigenvalues_low": low["eigenvalues"],
        "eigenvalues_high": eig_high,
        "margin_low": low["margin"],
        "margin_high": fit["margin"],
        "n_points_low": low["n_points"],
        "n_points_high": int(Y.shape[0]),
        "n_pairs_low": low["n_pairs"],
        "n_pairs_high": int(len(pairs)),
        "predicted_reversals_scored": int(checked),
        "predicted_reversals_observed": int(hits),
        "observed_share": share,
        "rank_falls": bool(rank_falls),
        "verdict": verdict,
        "bars": {"pass": "rank strictly lower and at least 0.60 of predicted reversals observed",
                 "fail": "rank equal or higher under high pressure"},
    }
    with open(out_path, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    for k in ("effective_rank_low", "effective_rank_high", "predicted_reversals_scored",
              "predicted_reversals_observed", "observed_share", "verdict"):
        print("%-32s %s" % (k, rec[k]))
    return 0


# --------------------------------------------------------------------------- self-test

def calibrate(out_path=None, trials=6, seed=99) -> int:
    """Fix the eigenvalue cut on synthetic evaluators of known rank.

    A registration gap, found by the self-test and recorded rather than papered
    over. PREREG-G9 Section 5 says the statistic is "the effective rank of the
    recovered metric" and never says at what cut an eigenvalue counts. Inherited
    from G5 the cut is 1e-2, and at that cut the estimator reads one rank too
    many on this world, because the max-margin program leaves a small slack
    eigenvalue at a few percent of the top one.

    That matters more here than it did in G5. This arm's entire statistic is
    whether rank falls between two strata, so a readout biased upward by a
    constant would not bias the comparison, but one biased upward by a variable
    amount would. The cut is therefore chosen here, against known truth, before
    either stratum is opened, and committed.
    """
    rng = np.random.default_rng(seed)
    m = 5
    cuts = [0.01, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]
    hits = {str(c): 0 for c in cuts}
    total = 0
    spectra = []
    for true_rank in (1, 2, 3, 4):
        for _ in range(trials):
            V = np.linalg.qr(rng.normal(size=(m, m)))[0]
            w = np.zeros(m)
            w[:true_rank] = np.linspace(1.0, 0.4, true_rank)
            G = (V * w) @ V.T
            t = rng.normal(size=m)
            Y = rng.normal(size=(60, m))
            d = g5.distances(Y, G, t)
            pairs = [(a, b) for a in range(len(Y)) for b in range(len(Y)) if d[a] + 1e-9 < d[b]]
            rng.shuffle(pairs)
            pairs = pairs[:400]
            try:
                fit = g5.estimate(Y, pairs)
            except RuntimeError:
                continue
            total += 1
            ev = np.clip(np.linalg.eigvalsh(fit["G"]), 0, None)
            spectra.append({"true_rank": true_rank,
                            "ratios": sorted((ev / ev.max()).tolist(), reverse=True)})
            for c in cuts:
                if int((ev > c * ev.max()).sum()) == true_rank:
                    hits[str(c)] += 1
    acc = {c: (hits[c] / total if total else 0.0) for c in hits}
    best = max(acc, key=lambda c: (acc[c], -float(c)))
    print("cut calibration on %d synthetic evaluators of known rank" % total)
    for c in cuts:
        print("  cut %-5s exact-rank accuracy %.3f" % (c, acc[str(c)]))
    print("chosen cut:", best, "accuracy %.3f" % acc[best])
    rec = {"trials": total, "cuts": acc, "chosen_cut": float(best),
           "chosen_accuracy": acc[best], "seed": seed,
           "why": "PREREG-G9 named the statistic and not the cut. Chosen against known "
                  "truth before either stratum was opened."}
    if out_path:
        with open(out_path, "w") as f:
            json.dump(rec, f, indent=1, sort_keys=True)
        print("wrote", out_path)
        print("sha256:", hashlib.sha256(open(out_path, "rb").read()).hexdigest())
    return 0 if acc[best] >= 0.8 else 1


def selftest() -> int:
    """Does the estimator see a rank cut when there is one, and not when there is not?"""
    rng = np.random.default_rng(4242)
    fails = []
    m = 5
    report = {}
    for true_rank in (2, 3, 4):
        V = np.linalg.qr(rng.normal(size=(m, m)))[0]
        w = np.zeros(m)
        w[:true_rank] = np.linspace(1.0, 0.4, true_rank)
        G = (V * w) @ V.T
        t = rng.normal(size=m)
        Y = rng.normal(size=(60, m))
        d = g5.distances(Y, G, t)
        pairs = [(a, b) for a in range(len(Y)) for b in range(len(Y)) if d[a] + 1e-9 < d[b]]
        rng.shuffle(pairs)
        pairs = pairs[:400]
        fit = g5.estimate(Y, pairs)
        r, eig = effective_rank(fit["G"])
        report[str(true_rank)] = {"recovered_rank": r,
                                  "eigenvalues": ["%.3g" % v for v in sorted(eig, reverse=True)]}
        if r != true_rank:
            fails.append("true rank %d recovered as %d" % (true_rank, r))
    print(json.dumps(report, indent=1, sort_keys=True))
    if fails:
        for f in fails:
            print("  -", f)
        print("SELFTEST FAIL")
        return 1
    print("SELFTEST PASS")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--fit-low", action="store_true")
    ap.add_argument("--score-high", action="store_true")
    ap.add_argument("--fit", help="the committed low-pressure fit")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.calibrate:
        return calibrate(a.out)
    if a.fit_low:
        if not a.out:
            ap.error("--out is required")
        return fit_low(a.out)
    if a.score_high:
        if not (a.fit and a.out):
            ap.error("--fit and --out are required")
        return score_high(a.fit, a.out)
    ap.error("choose --selftest, --fit-low or --score-high")


if __name__ == "__main__":
    raise SystemExit(main())
