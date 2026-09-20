#!/usr/bin/env python3
"""G7a-r grader: the same gate read with the nuisance parameters tied.

The sealed G7a reader fits threshold, shape and lapse freely in every arm. On
July its lapse swung between 0.00 and 0.12 from one arm to the next and the
threshold moved to compensate, so a ratio of two thresholds had a log spread of
0.18 to 0.42 and the gate could not decide (`RESULTS-G7A.md`,
`results/instrument_diagnosis_2026-07.json`).

This reader fits ONE shape and ONE lapse per level, shared by the cohort's
games at the level and the same cohort's games at the reference clock, and a
threshold for each of the two. It is a joint four-parameter fit and it is
redone inside every bootstrap draw, so the interval carries the uncertainty of
the shared parameters.

What tying assumes. That the same players have the same lapse rate and the same
curve shape at both clocks, and differ only in threshold. If lapses really are
more common at short clocks, a tied fit may read some of that as a threshold
difference. The self-test therefore includes worlds where the lapse differs by
clock and the threshold does not, and the reading in those worlds is part of
the record whatever it is.

Everything else is G7a's: the same rows, arms, engine-floor guard, anti-vacuity
floor, player bootstrap, slope through the origin and bars.
"""
import argparse
import glob
import json

import numpy as np
from scipy.optimize import minimize

import g7a_grade as G
import g7a_threshold as T

N_BOOT = 1000


def reader_view(arm, sel=None):
    g12, g23, ch = arm.g12, arm.g23, arm.ch
    if sel is not None:
        g12, g23, ch = g12[sel], g23[sel], ch[sel]
    keep = (ch <= 1) & (g23 >= T.THIRD_CUTOFF) & (g12 > 0)
    return g12[keep].astype(float), (ch[keep] == 0).astype(float)


def _nll(g, y, le, lk, b):
    lam = 0.25 / (1 + np.exp(-b))
    p = 0.5 + (0.5 - lam) * (1 - np.exp(-(g / np.exp(le)) ** np.exp(lk)))
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))


def fit_pair(gl, yl, gr, yr, start=None):
    """Joint fit. Returns (eps_level, eps_ref, shape_k, lapse)."""
    def f(th):
        return _nll(gl, yl, th[0], th[2], th[3]) + _nll(gr, yr, th[1], th[2], th[3])
    starts = [start] if start is not None else [
        [np.log(np.quantile(gl, q)), np.log(np.quantile(gr, q)), -0.4, -2.0] for q in (0.4, 0.7)]
    best = min((minimize(f, s, method="Nelder-Mead",
                         options={"maxiter": 6000, "xatol": 1e-6, "fatol": 1e-8}) for s in starts),
               key=lambda r: r.fun)
    k = float(np.exp(best.x[2]))
    c = np.log(2.0) ** (1.0 / k)
    return float(np.exp(best.x[0]) * c), float(np.exp(best.x[1]) * c), k, \
        float(0.25 / (1 + np.exp(-best.x[3]))), best.x


def grade(rows, engine_floor, n_boot=N_BOOT, seed=20260921):
    rng = np.random.default_rng(seed)
    arms = {k: G.Arm(v) for k, v in G.split_arms(rows).items() if v}
    point, entering, why_not, warm = {}, [], {}, {}
    for L in G.LEVELS:
        if (L, "level") not in arms or (L, "ref") not in arms:
            why_not[L] = "an arm is missing"
            continue
        (gl, yl), (gr, yr) = reader_view(arms[(L, "level")]), reader_view(arms[(L, "ref")])
        if min(len(gl), len(gr)) < G.MIN_ARM:
            why_not[L] = "an arm has fewer than %d positions entering the reader" % G.MIN_ARM
            point[L] = {"n_level": int(len(gl)), "n_ref": int(len(gr))}
            continue
        el, er, k, lam, x = fit_pair(gl, yl, gr, yr)
        point[L] = {"eps_level": el, "eps_ref": er, "ratio": el / er, "shape_k": k, "lapse": lam,
                    "n_level": int(len(gl)), "n_ref": int(len(gr))}
        warm[L] = x
        if engine_floor and min(el, er) < G.FLOOR_MULTIPLE * engine_floor:
            why_not[L] = "a threshold is within %.0f times the engine floor" % G.FLOOR_MULTIPLE
        else:
            entering.append(L)

    boot = {L: [] for L in entering}
    for _ in range(n_boot):
        for L in entering:
            lev, ref = arms[(L, "level")], arms[(L, "ref")]
            gl, yl = reader_view(lev, lev.draw(rng))
            gr, yr = reader_view(ref, ref.draw(rng))
            el, er, _k, _lam, _x = fit_pair(gl, yl, gr, yr, start=warm[L])
            boot[L].append(np.log(el / er))

    rec = {"reader": "tied shape and lapse per level", "levels": {}, "entering": entering,
           "excluded": {str(k): v for k, v in why_not.items()}, "engine_floor": engine_floor}
    for L in G.LEVELS:
        if L not in point:
            continue
        b = np.array(boot.get(L, []))
        rec["levels"][str(L)] = dict(point[L], predicted_ratio=float((L / G.REF) ** -0.5),
                                     log_ratio_sd=float(b.std()) if b.size > 10 else None,
                                     ratio_ci=[float(np.exp(np.quantile(b, 0.025))),
                                               float(np.exp(np.quantile(b, 0.975)))] if b.size > 10 else None)
    if len(entering) < 3:
        rec.update({"exponent": None, "C1": "INDETERMINATE", "C2": "INDETERMINATE",
                    "reason": "fewer than three levels may enter the exponent"})
        return rec
    w = [1.0 / max(np.var(boot[L]), 1e-6) for L in entering]
    rec["exponent"] = G.slope_through_origin(entering, [np.log(point[L]["ratio"]) for L in entering], w)
    draws = [G.slope_through_origin(entering, [boot[L][i] for L in entering], w) for i in range(n_boot)]
    lo, hi = float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
    rec["exponent_ci"] = [lo, hi]
    rec["C1"] = "PASS" if hi < 0 else ("FAIL" if lo > 0 else "INDETERMINATE")
    if hi - lo > G.CI_MAX_WIDTH:
        rec["C2"] = "INDETERMINATE"
    else:
        rec["C2"] = "PASS" if lo <= -0.5 <= hi else "FAIL"
    return rec


# --------------------------------------------------------------------------- self-test

def synthetic_rows(rng, exponent, lapse_of, n_players=300, per_player=130, base_sd=0.06):
    rows = []
    for L in G.LEVELS:
        for p in range(n_players):
            skill = float(np.exp(rng.normal(0, 0.25)))
            for side, b in (("level", L), ("ref", G.REF)):
                sd = base_sd * skill * (b / G.REF) ** exponent
                g12, g23, ch = T.simulate(rng, per_player, sd, "gaussian", lapse=lapse_of(b))
                for a, c, k in zip(g12, g23, ch):
                    es = np.clip([0.85, 0.85 - a, 0.85 - a - c], 0.005, 0.995)
                    cps = [float(np.log(e / (1 - e)) / T.LICHESS_K) for e in es]
                    rows.append({"cp": cps, "choice": int(k), "player": "L%d_p%d" % (L, p),
                                 "arms": [[L, side]]})
    return rows


def selftest() -> int:
    rng = np.random.default_rng(778)
    same = lambda b: 0.03
    # Lapse three times higher at one minute than at thirty, falling with the log of the clock.
    by_clock = lambda b: float(np.interp(np.log(b), [np.log(60), np.log(1800)], [0.12, 0.04]))
    worlds = {
        "inverse_root": (-0.5, same, "PASS", "PASS"),
        "shallow": (-0.15, same, "PASS", "FAIL"),
        "flat": (0.0, same, "not PASS", None),
        "flat_lapse_by_clock": (0.0, by_clock, "REPORT", None),
        "inverse_root_lapse_by_clock": (-0.5, by_clock, "REPORT", None),
    }
    fails, report = [], {}
    for name, (ex, lapse_of, want1, want2) in worlds.items():
        r = grade(synthetic_rows(rng, ex, lapse_of), engine_floor=0.002, n_boot=60)
        report[name] = {"true": ex, "exponent": r.get("exponent"), "ci": r.get("exponent_ci"),
                        "C1": r["C1"], "C2": r["C2"],
                        "log_ratio_sd": {k: v.get("log_ratio_sd") for k, v in r["levels"].items()},
                        "lapse": {k: v.get("lapse") for k, v in r["levels"].items()}}
        print(name, json.dumps(report[name]), flush=True)
        if want1 == "PASS" and r["C1"] != "PASS":
            fails.append("%s: C1 is %s" % (name, r["C1"]))
        if want1 == "not PASS" and r["C1"] == "PASS":
            fails.append("%s: a flat world passed C1" % name)
        if want2 and r["C2"] != want2:
            fails.append("%s: C2 is %s, wanted %s" % (name, r["C2"], want2))
    print(json.dumps(report, indent=1))
    for f in fails:
        print("  -", f)
    print("SELFTEST FAIL" if fails else "SELFTEST PASS")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--labels")
    ap.add_argument("--screen")
    ap.add_argument("--out")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    def load(pattern):
        rows = []
        for f in sorted(glob.glob(pattern)):
            with open(f) as fh:
                rows.extend(json.loads(line) for line in fh)
        return rows
    deep = load(a.labels)
    floor, floor_fit = G.engine_floor_from(load(a.screen), deep)
    rec = grade(deep, floor, n_boot=a.boot)
    rec["engine_floor_fit"] = floor_fit
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps(rec, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
