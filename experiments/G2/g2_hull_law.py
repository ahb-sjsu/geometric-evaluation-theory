"""Gate G2: the hull law on spatial-voting data with respondent-placed candidate positions.

The hull law (paper Theorem 3(b), Lean GET.HullLaw.hull_law) says an evaluator with any convex
metric of evaluation cannot rank an action strictly below every action whose consequences
surround it. For a respondent r, candidate a, consequence point y_a (the respondent's own
placement of a on the chosen issue scales), and thermometer rating T(a):

    a is a VIOLATION for r  iff  y_a lies in the convex hull of { y_s : T(s) > T(a) }.

That is equivalent to the paper's form (a strictly below every member of some surrounding set),
because a surrounding set of strictly better candidates is a subset of the strictly-better set,
and conversely the strictly-better set surrounds a when any subset of it does.

Ties in the thermometer are not "strictly better", which is the conservative reading for the law.
Hull membership is decided by linear-programming feasibility (exists lambda >= 0, sum lambda = 1,
sum lambda y_s = y_a), which handles collinear and degenerate placements without a triangulation.

Statistic. Per respondent, VIOLATED = any candidate is a violation. TESTABLE = some candidate's
point lies in the convex hull of the OTHER candidates' points (ignoring ratings), which is the
anti-vacuity count: a respondent whose placements are in convex position cannot violate the law
under any rating. The population statistics are

    p_obs  = #VIOLATED / #TESTABLE
    p_null = mean over K shuffles of ratings within respondent of #VIOLATED_shuffled / #TESTABLE

and the permutation p-value is the fraction of shuffles with rate <= p_obs.

Usage (after the registration is sealed and the owner has placed the data file):

    python g2_hull_law.py --config prereg_config.json --data <file> --out results.json
    python g2_hull_law.py --selftest            # synthetic check of the checker, no data

The config names the file format, the id column, the weight column (optional), the issue-scale
placement columns per candidate, the thermometer columns per candidate, the missing codes, the
minimum number of candidates per respondent, and the number of shuffles and the seed.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

import numpy as np

try:
    from scipy.optimize import linprog
except ImportError:  # pragma: no cover
    linprog = None


# ----------------------------------------------------------------------------- geometry

def in_hull(point: np.ndarray, pts: np.ndarray, tol: float = 1e-9) -> bool:
    """Is `point` in the convex hull of the rows of `pts`? LP feasibility, exact for degenerate
    configurations (collinear rows, repeated rows, fewer rows than dimension + 1)."""
    if pts.shape[0] == 0:
        return False
    if pts.shape[0] == 1:
        return bool(np.allclose(pts[0], point, atol=tol))
    m = pts.shape[0]
    d = pts.shape[1]
    # variables lambda in R^m; constraints: pts^T lambda = point, sum lambda = 1, lambda >= 0
    a_eq = np.vstack([pts.T, np.ones((1, m))])
    b_eq = np.concatenate([point, [1.0]])
    if linprog is None:
        raise RuntimeError("scipy is required for the hull test")
    res = linprog(c=np.zeros(m), A_eq=a_eq, b_eq=b_eq, bounds=[(0, None)] * m, method="highs")
    if not res.success:
        return False
    return bool(np.max(np.abs(a_eq @ res.x - b_eq)) < 1e-7)


# ----------------------------------------------------------------------------- one respondent

@dataclass
class RespondentResult:
    n_candidates: int
    testable: bool
    violated: bool
    n_violations: int


def evaluate_respondent(Y: np.ndarray, T: np.ndarray) -> RespondentResult:
    """Y: (n_cand, d) placements; T: (n_cand,) ratings, higher preferred."""
    n = Y.shape[0]
    testable = False
    n_viol = 0
    for a in range(n):
        others = np.delete(np.arange(n), a)
        if in_hull(Y[a], Y[others]):
            testable = True
        better = np.where(T > T[a])[0]
        if better.size and in_hull(Y[a], Y[better]):
            n_viol += 1
    return RespondentResult(n, testable, n_viol > 0, n_viol)


# ----------------------------------------------------------------------------- population

def population_rates(respondents: list[tuple[np.ndarray, np.ndarray, float]], n_shuffles: int,
                     seed: int) -> dict:
    """respondents: list of (Y, T, weight). Returns observed and null rates (weighted)."""
    rng = np.random.default_rng(seed)
    obs = [evaluate_respondent(Y, T) for Y, T, _ in respondents]
    w = np.array([wt for _, _, wt in respondents], dtype=float)
    testable = np.array([r.testable for r in obs])
    violated = np.array([r.violated for r in obs])
    wt_test = w[testable].sum()
    p_obs = float(w[testable & violated].sum() / wt_test) if wt_test > 0 else float("nan")
    null_rates = []
    for _ in range(n_shuffles):
        v = np.zeros(len(respondents), dtype=bool)
        for i, (Y, T, _) in enumerate(respondents):
            if not testable[i]:
                continue
            Ts = T[rng.permutation(T.size)]
            v[i] = evaluate_respondent(Y, Ts).violated
        null_rates.append(float(w[testable & v].sum() / wt_test) if wt_test > 0 else float("nan"))
    null_rates = np.array(null_rates)
    return {
        "n_respondents": len(respondents),
        "n_testable": int(testable.sum()),
        "weighted_testable": float(wt_test),
        "n_violated": int((testable & violated).sum()),
        "p_obs": p_obs,
        "p_null_mean": float(np.nanmean(null_rates)),
        "p_null_sd": float(np.nanstd(null_rates)),
        "p_value_perm": float(np.mean(null_rates <= p_obs)) if null_rates.size else float("nan"),
        "n_shuffles": n_shuffles,
        "seed": seed,
        "mean_candidates": float(np.mean([r.n_candidates for r in obs])) if obs else float("nan"),
    }


# ----------------------------------------------------------------------------- data loading

def load_respondents(path: str, cfg: dict) -> list[tuple[np.ndarray, np.ndarray, float]]:
    import pandas as pd
    fmt = cfg.get("format", "auto")
    if fmt == "auto":
        fmt = "dta" if path.lower().endswith(".dta") else ("sav" if path.lower().endswith(".sav") else "csv")
    if fmt == "dta":
        df = pd.read_stata(path, convert_categoricals=False)
    elif fmt == "sav":
        df = pd.read_spss(path, convert_categoricals=False)
    else:
        df = pd.read_csv(path, low_memory=False)
    cands = cfg["candidates"]            # {name: {"placements": [col per scale], "thermometer": col}}
    scales = cfg["scales"]               # list of scale names, order = coordinate order
    missing = set(cfg.get("missing_codes", []))
    # thermometers carry their own missing codes (ANES: 98, 99); a score of 0 is a real rating
    missing_t = set(cfg.get("thermometer_missing_codes", missing))
    valid_place = set(cfg.get("valid_placement_values", [1, 2, 3, 4, 5, 6, 7]))
    therm_min, therm_max = cfg.get("thermometer_range", [0, 100])
    min_c = int(cfg.get("min_candidates", 4))
    wcol = cfg.get("weight_column")
    filt = cfg.get("row_filter")         # optional {"column": ..., "values": [...]}
    if filt:
        df = df[df[filt["column"]].isin(filt["values"])]
    out = []
    for _, row in df.iterrows():
        Y, T = [], []
        for name, spec in cands.items():
            place = []
            ok = True
            for col in spec["placements"]:
                v = row.get(col)
                if v is None or (isinstance(v, float) and np.isnan(v)) or v in missing or v not in valid_place:
                    ok = False
                    break
                place.append(float(v))
            t = row.get(spec["thermometer"])
            if not ok or t is None or (isinstance(t, float) and np.isnan(t)) or t in missing_t:
                continue
            t = float(t)
            if t < therm_min or t > therm_max:
                continue
            Y.append(place)
            T.append(t)
        if len(Y) >= min_c:
            wt = float(row[wcol]) if wcol else 1.0
            if wt > 0:
                out.append((np.array(Y), np.array(T), wt))
    assert len(scales) == len(next(iter(cands.values()))["placements"])
    return out


# ----------------------------------------------------------------------------- self test

def selftest() -> int:
    """Checks the checker on synthetic evaluators. A quadratic evaluator with a positive
    semidefinite metric must never violate; a random rater must violate at the geometric base
    rate; a hand-built configuration must be detected."""
    rng = np.random.default_rng(0)
    fails = 0
    # 1. hand-built: a at the centroid of three better candidates is a violation
    Y = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 3.0], [1.0, 1.0]])
    T = np.array([90.0, 80.0, 70.0, 10.0])
    r = evaluate_respondent(Y, T)
    if not (r.testable and r.violated and r.n_violations == 1):
        print("FAIL hand-built violation", r); fails += 1
    # 2. same points, centroid rated best: no violation, still testable
    T2 = np.array([10.0, 20.0, 30.0, 90.0])
    r2 = evaluate_respondent(Y, T2)
    if not (r2.testable and not r2.violated):
        print("FAIL hand-built non-violation", r2); fails += 1
    # 3. convex position: not testable whatever the ratings
    Y3 = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 3.0], [3.0, 3.0]])
    r3 = evaluate_respondent(Y3, rng.permutation(4).astype(float))
    if r3.testable or r3.violated:
        print("FAIL convex position", r3); fails += 1
    # 4. collinear placements on a 7-point grid: the middle point is in the hull of the ends
    Y4 = np.array([[1.0, 4.0], [4.0, 4.0], [7.0, 4.0], [4.0, 1.0]])
    T4 = np.array([80.0, 10.0, 70.0, 50.0])  # middle of the segment rated below both ends
    r4 = evaluate_respondent(Y4, T4)
    if not (r4.testable and r4.violated):
        print("FAIL collinear violation", r4); fails += 1
    # 5. quadratic evaluators never violate; random raters violate at a positive rate
    n_resp, n_cand, d = 300, 6, 2
    quad_resps, rand_resps = [], []
    for _ in range(n_resp):
        Yr = rng.integers(1, 8, size=(n_cand, d)).astype(float)
        A = rng.normal(size=(d, d)); G = A @ A.T + 0.1 * np.eye(d)
        t = rng.uniform(1, 7, size=d)
        cost = np.einsum("ij,jk,ik->i", Yr - t, G, Yr - t)
        quad_resps.append((Yr, -cost, 1.0))
        rand_resps.append((Yr, rng.uniform(0, 100, size=n_cand), 1.0))
    q = population_rates(quad_resps, n_shuffles=5, seed=1)
    if q["n_testable"] == 0 or q["n_violated"] != 0:
        print("FAIL quadratic evaluators violated", q); fails += 1
    if not (q["p_null_mean"] > 0.05):
        print("FAIL null rate implausibly low", q); fails += 1
    rd = population_rates(rand_resps, n_shuffles=5, seed=2)
    if not (abs(rd["p_obs"] - rd["p_null_mean"]) < 0.15):
        print("FAIL random raters differ from their own null", rd); fails += 1
    # 6. ties are not strictly better: a tied better set cannot surround
    Yt = np.array([[0.0, 0.0], [3.0, 0.0], [0.0, 3.0], [1.0, 1.0]])
    Tt = np.array([50.0, 50.0, 50.0, 50.0])
    rt = evaluate_respondent(Yt, Tt)
    if rt.violated:
        print("FAIL ties counted as better", rt); fails += 1
    print(json.dumps({"quadratic": q, "random": rd}, indent=1))
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config")
    ap.add_argument("--data")
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="event-presence probe: placements only, ratings never read")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    cfg = json.load(open(args.config, encoding="utf-8"))
    resps = load_respondents(args.data, cfg)
    if args.probe:
        sizes = [Y.shape[0] for Y, _, _ in resps]
        testable = 0
        for Y, _, _ in resps:
            n = Y.shape[0]
            if any(in_hull(Y[a], Y[np.delete(np.arange(n), a)]) for a in range(n)):
                testable += 1
        probe = {
            "world": cfg.get("world"),
            "n_respondents_with_menu": len(resps),
            "n_testable": testable,
            "menu_size_counts": {int(k): int(v) for k, v in zip(*np.unique(sizes, return_counts=True))},
            "ratings_read": False,
        }
        json.dump(probe, open(args.out or "probe.json", "w", encoding="utf-8"), indent=1)
        print(json.dumps(probe, indent=1))
        return 0
    res = population_rates(resps, int(cfg.get("n_shuffles", 200)), int(cfg.get("seed", 20260907)))
    res["config"] = cfg
    res["data"] = args.data
    json.dump(res, open(args.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("config",)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
