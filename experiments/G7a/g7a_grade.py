#!/usr/bin/env python3
"""G7a grader: thresholds per arm, ratios within cohort, the exponent, and the bars.

Input is labelled positions with raw centipawns. Every interpretation happens
here, so a change of consequence map or cutoff is a recomputation and not a
rerun of the engine.

An ARM is a cohort read at one budget. For each level L other than the reference
there are two arms, cohort L at L and the same cohort at 300 seconds, and the
ratio of their thresholds is what the law predicts. A position at the reference
can belong to several cohorts' reference arms at once, since one player can be
in several cohorts.

The exponent is the slope of ln(ratio) on ln(L / 300) THROUGH THE ORIGIN, since
the ratio is one at the reference by construction, weighted by inverse bootstrap
variance. The bootstrap resamples PLAYERS, not positions, because one player
contributes many positions and up to six from a single game.

    python g7a_grade.py --selftest
    python g7a_grade.py --labels 'deep_*.jsonl' --screen 'screen_*.jsonl' --out grade.json
"""
from __future__ import annotations

import argparse
import glob
import json

import numpy as np

import g7a_threshold as T

REF = 300
LEVELS = (60, 180, 600, 1800)
MIN_ARM = 3000
FLOOR_MULTIPLE = 3.0
N_BOOT = 1000
CI_MAX_WIDTH = 0.30


# --------------------------------------------------------------------------- arms and ratios

class Arm:
    """One arm as arrays, built once. The first grader rebuilt these from a list
    of dictionaries on every bootstrap draw, which was correct and slow, and it
    runs on a machine whose electricity somebody pays for."""

    def __init__(self, rows):
        cp = np.array([r["cp"] for r in rows], dtype=float).reshape(-1, 3)
        self.g12, self.g23, und = T.gaps_from_cp(cp)
        self.ch = np.array([r["choice"] for r in rows])
        # Only undecided positions can ever enter the reader, so drop the rest now.
        self.g12, self.g23, self.ch = self.g12[und], self.g23[und], self.ch[und]
        who = np.array([r["player"] for r in rows])[und]
        self.players = sorted(set(who.tolist()))
        order = np.argsort(who, kind="stable")
        bounds = np.searchsorted(who[order], self.players, side="left")
        ends = np.searchsorted(who[order], self.players, side="right")
        self.idx = [order[a:b] for a, b in zip(bounds, ends)]

    def threshold(self, sel=None):
        if sel is None:
            fit = T.fit_threshold(self.g12, self.g23, self.ch)
        else:
            fit = T.fit_threshold(self.g12[sel], self.g23[sel], self.ch[sel])
        return fit.get("eps"), fit.get("n_used", 0)

    def draw(self, rng):
        pick = rng.integers(0, len(self.players), size=len(self.players))
        return np.concatenate([self.idx[j] for j in pick])


def arm_threshold(rows):
    if not rows:
        return None, 0
    return Arm(rows).threshold()


def ratios(arms):
    """arms[(L, 'level' or 'ref')] -> Arm. Returns per-level dict."""
    out = {}
    for L in LEVELS:
        e_l, n_l = arms[(L, "level")].threshold() if (L, "level") in arms else (None, 0)
        e_r, n_r = arms[(L, "ref")].threshold() if (L, "ref") in arms else (None, 0)
        out[L] = {"eps_level": e_l, "eps_ref": e_r, "n_level": n_l, "n_ref": n_r,
                  "ratio": (e_l / e_r) if (e_l and e_r) else None}
    return out


def slope_through_origin(levels, log_ratios, weights):
    x = np.log(np.asarray(levels, float) / REF)
    y, w = np.asarray(log_ratios, float), np.asarray(weights, float)
    return float(np.sum(w * x * y) / np.sum(w * x * x))


def split_arms(rows):
    by_arm = {}
    for r in rows:
        for arm in r["arms"]:
            by_arm.setdefault((arm[0], arm[1]), []).append(r)
    return by_arm


def grade(rows, engine_floor, n_boot=N_BOOT, seed=20260920):
    rng = np.random.default_rng(seed)
    by_arm = split_arms(rows)
    arms = {k: Arm(v) for k, v in by_arm.items() if v}
    point = ratios(arms)

    # Which levels may enter: both arms populated, both thresholds clear of the engine floor.
    entering, why_not = [], {}
    for L in LEVELS:
        p = point[L]
        if p["ratio"] is None or min(p["n_level"], p["n_ref"]) < MIN_ARM:
            why_not[L] = "an arm has fewer than %d positions entering the reader" % MIN_ARM
        elif engine_floor and min(p["eps_level"], p["eps_ref"]) < FLOOR_MULTIPLE * engine_floor:
            why_not[L] = "a threshold is within %.0f times the engine floor" % FLOOR_MULTIPLE
        else:
            entering.append(L)

    # Cluster bootstrap over players, within each arm.
    boot = {L: [] for L in LEVELS}
    for _ in range(n_boot):
        for L in entering:
            es = []
            for side in ("level", "ref"):
                arm = arms[(L, side)]
                e, _n = arm.threshold(arm.draw(rng))
                es.append(e)
            if all(es):
                boot[L].append(np.log(es[0] / es[1]))

    rec = {"levels": {}, "entering": entering, "excluded": {str(k): v for k, v in why_not.items()},
           "engine_floor": engine_floor}
    for L in LEVELS:
        b = np.array(boot[L])
        rec["levels"][str(L)] = dict(point[L], predicted_ratio=float((L / REF) ** -0.5),
                                     log_ratio_sd=float(b.std()) if b.size > 10 else None,
                                     ratio_ci=[float(np.exp(np.quantile(b, 0.025))),
                                               float(np.exp(np.quantile(b, 0.975)))] if b.size > 10 else None)
    if len(entering) < 3:
        rec.update({"exponent": None, "C1": "INDETERMINATE", "C2": "INDETERMINATE",
                    "reason": "fewer than three levels may enter the exponent"})
        return rec

    w = [1.0 / max(np.var(boot[L]), 1e-6) for L in entering]
    rec["exponent"] = slope_through_origin(entering, [np.log(point[L]["ratio"]) for L in entering], w)
    n_ok = min(len(boot[L]) for L in entering)
    draws = [slope_through_origin(entering, [boot[L][i] for L in entering], w) for i in range(n_ok)]
    lo, hi = float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
    rec["exponent_ci"] = [lo, hi]
    rec["C1"] = "PASS" if hi < 0 else ("FAIL" if lo > 0 else "INDETERMINATE")
    if hi - lo > CI_MAX_WIDTH:
        rec["C2"] = "INDETERMINATE"
    else:
        rec["C2"] = "PASS" if lo <= -0.5 <= hi else "FAIL"
    return rec


# --------------------------------------------------------------------------- self-test

def synthetic_rows(rng, exponent, n_players=500, per_player=130, base_sd=0.06, noise="gaussian"):
    """Cohorts of players whose resolution follows sd = base * (budget/300)^exponent,
    with a per-player skill factor so that players differ, as they do."""
    rows = []
    for L in LEVELS:
        for p in range(n_players):
            skill = float(np.exp(rng.normal(0, 0.25)))
            for side, b in (("level", L), ("ref", REF)):
                sd = base_sd * skill * (b / REF) ** exponent
                g12, g23, ch = T.simulate(rng, per_player, sd, noise)
                for a, c, k in zip(g12, g23, ch):
                    # invert the consequence map so the rows look like labelled positions
                    # Start high but undecided, and clip, so a large gap cannot
                    # push an expected score below zero and into a log of nothing.
                    e1 = 0.85
                    es = np.clip([e1, e1 - a, e1 - a - c], 0.005, 0.995)
                    cps = [float(np.log(e / (1 - e)) / T.LICHESS_K) for e in es]
                    rows.append({"cp": cps, "choice": int(k), "player": "L%d_p%d" % (L, p),
                                 "arms": [[L, side]]})
    return rows


def selftest() -> int:
    """The bars themselves, on cohorts whose law is known. A grader that passes
    the law it was built for and nothing else proves nothing, so the flat world
    must not pass C1 and the inverse world must fail C2."""
    rng = np.random.default_rng(777)
    fails, report = [], {}
    worlds = {"inverse_root": (-0.5, "PASS", "PASS"), "flat": (0.0, "not PASS", None),
              "inverse": (-1.0, "PASS", "FAIL")}
    for name, (ex, want1, want2) in worlds.items():
        rows = synthetic_rows(rng, ex)
        r = grade(rows, engine_floor=0.002, n_boot=100)
        report[name] = {"true": ex, "exponent": r.get("exponent"), "ci": r.get("exponent_ci"),
                        "C1": r["C1"], "C2": r["C2"], "entering": r["entering"],
                        "ratios": {k: v["ratio"] for k, v in r["levels"].items()}}
        if want1 == "PASS" and r["C1"] != "PASS":
            fails.append("%s: C1 is %s" % (name, r["C1"]))
        if want1 == "not PASS" and r["C1"] == "PASS":
            fails.append("%s: a flat world passed C1" % name)
        if want2 and r["C2"] != want2:
            fails.append("%s: C2 is %s, wanted %s" % (name, r["C2"], want2))
    print(json.dumps(report, indent=1))
    if fails:
        for f in fails:
            print("  -", f)
        print("SELFTEST FAIL")
        return 1
    print("SELFTEST PASS")
    return 0


def engine_floor_from(screen_rows, deep_rows):
    """Score the screen engine as a player against the deep labels."""
    deep = {(r["game"], r["ply"]): r for r in deep_rows}
    g12, g23, ch = [], [], []
    for s in screen_rows:
        d = deep.get((s["game"], s["ply"]))
        if not d:
            continue
        a, b, und = T.gaps_from_cp(np.array(d["cp"], float))
        if not und:
            continue
        top = d["engine_moves"]
        pick = s["engine_moves"][0]
        g12.append(float(a)); g23.append(float(b))
        ch.append(top.index(pick) if pick in top else 3)
    fit = T.fit_threshold(g12, g23, ch)
    return fit.get("eps"), fit


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--labels")
    ap.add_argument("--screen")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    load = lambda pat: [json.loads(l) for p in sorted(glob.glob(pat)) for l in open(p)]
    deep, screen = load(a.labels), load(a.screen)
    floor, floor_fit = engine_floor_from(screen, deep)
    rec = grade(deep, floor)
    rec["engine_floor_fit"] = floor_fit
    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    print(json.dumps({k: rec[k] for k in ("exponent", "exponent_ci", "C1", "C2", "entering",
                                          "excluded", "engine_floor") if k in rec}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
