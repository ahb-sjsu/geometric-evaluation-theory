#!/usr/bin/env python3
"""G7a: read a discrimination threshold off choices, and test the reader before trusting it.

The object. The engine values its best move, its second and its third. The gap
g between the first two is the question put to the player, in win-probability
units. The share of players who answer it correctly rises with the gap, and the
gap at which the lapse-free curve reaches 75 percent is the indifference
threshold, the same point of the same curve the paper reads for a language-model
judge ordering pairs.

    P(best | g) = 1/2 + (1/2 - lapse) * (1 - exp(-(g / e)^k))        eps = e * ln(2)^(1/k)

Which positions enter, and why. Two restrictions, each forced by a failed
self-test and not chosen for taste.

  1. The player chose one of the engine's top two. Scoring "played the best of
     all legal moves" failed first: the constant linking the reported threshold
     to the true resolution wandered between 1.06 and 1.29, because finding the
     best of six depends on the spacing of the other four as well as on the gap.

  2. The engine's third move is at least THIRD_CUTOFF below its second. With
     restriction 1 alone the constant still drifted, cleanly and monotonically,
     0.975 down to 0.762, and pulled a true exponent of -0.5 to -0.466.
     `g7a_reader_diagnosis.py` showed the cause is selection and not curve
     shape, since a reader that fits no curve at all drifts the same way, and
     only in worlds with more than two moves. Keeping top-two choices
     conditions on those two beating the rest, which favours the better one
     more as noise grows against the spacing of the rest.
     `g7a_reader_diagnosis2.py` then compared the ways out in two noise worlds.
     Under Gumbel noise the uncorrected readers are exact, which is independence
     of irrelevant alternatives. Under Gaussian noise they are biased by 4
     percent in slope, and so is a whole-menu logit model. Nobody knows a chess
     player's noise family, so the reader has to be right in both, and only this
     cutoff is: slope 0.993 Gaussian, 1.014 Gumbel.

The cutoff is in fixed win-probability units on purpose. The threshold is the
thing being measured and cannot be used to decide which positions measure it.

The cost is data. About 13 percent of positions survive in the synthetic worlds.
The probe counted 4.9 million games in two days of one month, so the cost is
affordable, and the share that survives is reported per budget because a share
that moves with the budget is something a reader of the result needs to see.

    python g7a_threshold.py --selftest
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from scipy.optimize import minimize

THIRD_CUTOFF = 0.10          # win-probability units, frozen by the diagnosis
MIN_POSITIONS = 800

# --------------------------------------------------------------------------- the consequence map

# Centipawns to the mover's expected score, by the logistic Lichess publishes
# for its accuracy measure, fitted to games between humans on that site
# (lichess.org/page/accuracy; the constant is to be re-verified against that
# page at seal). It is the world's consequence map for this population. The
# engine's own win-draw-loss model is NOT used: it describes engines playing
# engines, where a pawn and a half is nearly a won game, and the shakedown lost
# 62 percent of its positions to it before the mistake was seen.
LICHESS_K = 0.00368208
DECIDED_LO, DECIDED_HI = 0.10, 0.90


def win_expectation(cp):
    return 1.0 / (1.0 + np.exp(-LICHESS_K * np.asarray(cp, dtype=float)))


def gaps_from_cp(cp3):
    """From the engine's three scores: gap12, gap23, and whether the position is
    still undecided. A decided position is dropped because gaps compress toward
    zero there and the task has changed from choosing to converting."""
    e = win_expectation(cp3)
    undecided = (e[..., 0] >= DECIDED_LO) & (e[..., 0] <= DECIDED_HI)
    return e[..., 0] - e[..., 1], e[..., 1] - e[..., 2], undecided


# --------------------------------------------------------------------------- the reader

def fit_threshold(gap12, gap23, choice):
    """Threshold from two-alternative positions.

    gap12   value of the engine's best move minus its second
    gap23   value of its second minus its third
    choice  index of the move played in the engine's ordering, 0 is its best
    """
    gap12, gap23, choice = map(np.asarray, (gap12, gap23, choice))
    in_top_two = choice <= 1
    two_alternative = gap23 >= THIRD_CUTOFF
    keep = in_top_two & two_alternative & (gap12 > 0)
    n = int(keep.sum())
    info = {"n_positions": int(len(choice)), "n_used": n,
            "share_in_top_two": float(in_top_two.mean()),
            "share_two_alternative": float(two_alternative.mean()),
            "share_used": float(keep.mean())}
    if n < MIN_POSITIONS:
        info["eps"] = None
        return info
    g, y = gap12[keep].astype(float), (choice[keep] == 0).astype(float)

    def nll(th):
        le, lk, b = th
        lam = 0.25 / (1 + np.exp(-b))
        p = 0.5 + (0.5 - lam) * (1 - np.exp(-(g / np.exp(le)) ** np.exp(lk)))
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))

    best = min((minimize(nll, [np.log(q), 0.3, -2.0], method="Nelder-Mead",
                         options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-8})
                for q in np.quantile(g, [0.3, 0.5, 0.8])), key=lambda r: r.fun)
    e, k = np.exp(best.x[0]), np.exp(best.x[1])
    info.update({"eps": float(e * np.log(2.0) ** (1.0 / k)), "shape_k": float(k),
                 "lapse": float(0.25 / (1 + np.exp(-best.x[2]))), "nll": float(best.fun)})
    return info


def exponent(budgets, eps):
    """Least-squares slope of ln eps on ln budget."""
    return float(np.polyfit(np.log(np.asarray(budgets, float)),
                            np.log(np.asarray(eps, float)), 1)[0])


# --------------------------------------------------------------------------- synthetic players

def simulate(rng, n_pos, sd, noise="gaussian", lapse=0.03, k_moves=6):
    """A chooser whose resolution is `sd` by construction. Each move's value is
    perceived with noise of that standard deviation and the largest is played."""
    gap = np.clip(np.exp(rng.normal(np.log(0.03), 1.1, size=n_pos)), 1e-4, 0.6)
    extra = rng.exponential(0.05, size=(n_pos, k_moves - 2))
    vals = np.zeros((n_pos, k_moves))
    vals[:, 1] = -gap
    vals[:, 2:] = -gap[:, None] - np.cumsum(extra, axis=1)
    if noise == "gaussian":
        eps = rng.normal(0, sd, size=vals.shape)
    else:
        eps = rng.gumbel(0, sd * np.sqrt(6) / np.pi, size=vals.shape)
    choice = np.argmax(vals + eps, axis=1)
    slip = rng.random(n_pos) < lapse
    choice[slip] = rng.integers(0, k_moves, size=slip.sum())
    return gap, vals[:, 1] - vals[:, 2], choice


def selftest() -> int:
    """The law is about ratios of thresholds between budgets, so every check is
    a check that ratios, and the exponents made of them, come out right. Each is
    run in both noise worlds, because the reader was chosen for being right in
    both and a self-test in one would not show that."""
    rng = np.random.default_rng(20260920)
    fails, report = [], {}
    N = 240000
    sds = [0.01, 0.02, 0.05, 0.10, 0.20]
    budgets = [60, 180, 300, 600, 1800]

    for noise in ("gaussian", "gumbel"):
        r = {}
        eps = [fit_threshold(*simulate(rng, N, sd, noise))["eps"] for sd in sds]
        slope = float(np.polyfit(np.log(sds), np.log(eps), 1)[0])
        r["ratio_recovery"] = {"eps_over_sd": [e / s for e, s in zip(eps, sds)], "slope": slope}
        if abs(slope - 1.0) > 0.03:
            fails.append("%s: threshold against true resolution has slope %.4f, not 1" % (noise, slope))

        # The bridge built in: n independent reads give resolution sd0 / sqrt(n).
        e_root = [fit_threshold(*simulate(rng, N, 0.40 / np.sqrt(b / 10.0), noise))["eps"] for b in budgets]
        ex = exponent(budgets, e_root)
        r["inverse_root_world"] = ex
        if abs(ex + 0.5) > 0.04:
            fails.append("%s: inverse-root world read as %.4f" % (noise, ex))

        # Negative control: no dependence on budget, so no law may be reported.
        e_flat = [fit_threshold(*simulate(rng, N, 0.05, noise))["eps"] for _ in budgets]
        exf = exponent(budgets, e_flat)
        r["flat_world"] = exf
        if abs(exf) > 0.04:
            fails.append("%s: flat world read as %.4f" % (noise, exf))

        # A rival law, so the reader is shown to tell laws apart.
        e_inv = [fit_threshold(*simulate(rng, N, 3.0 / b, noise))["eps"] for b in budgets]
        exi = exponent(budgets, e_inv)
        r["inverse_world"] = exi
        if abs(exi + 1.0) > 0.06:
            fails.append("%s: inverse world read as %.4f" % (noise, exi))
        report[noise] = r

    print(json.dumps(report, indent=1))
    if fails:
        for f in fails:
            print("  -", f)
        print("SELFTEST FAIL")
        return 1
    print("SELFTEST PASS")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    ap.error("only --selftest is implemented before the registration is drafted")


if __name__ == "__main__":
    raise SystemExit(main())
