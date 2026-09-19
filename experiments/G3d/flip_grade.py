"""G3d grader. Prediction reads the calibration block only; grading reads the test block against
the committed prediction.

    python flip_grade.py predict CAL_DIR  --config flip_config.json --out predictions.json
    python flip_grade.py grade   TEST_DIR --config flip_config.json --predictions predictions.json --out grade.json

Model. At each budget k, the log-odds that the judge prefers the sheet of interest adds an
evidence term and a cue term:

    reversal (worse sheet decorated):  L = E_k - C_k
    control  (better sheet decorated): L = E_k + C_k

E_k is measured on the evidence cell (plain pairs at the same gap), C_k on the cue cell (equal
error counts, one sheet decorated). The prediction for a cell mean is the difference or sum of
the calibration means. The prediction for the share of pairs on which the better sheet is
preferred is the share of calibration cross pairs (one evidence pair, one cue pair) whose sum or
difference is positive. The crossover is the budget, on the scale log2(1 + k) and interpolated
linearly, at which the reversal cell's share of pairs preferring the better sheet first reaches
one half.

Checks.
  F1 additivity   every test cell mean at every budget within z_max of its prediction, the
                  standard error combining the calibration bootstrap and the test sample
  F2 crossover    the observed crossover within crossover_z_max of the predicted one, in units of
                  the bootstrap standard deviation of their difference
  F3 rivals       the additive prediction's squared error over both test cells and all budgets is
                  below that of evidence alone (the cue ignored) and of the cue alone (the
                  evidence ignored)
  anti-vacuity    decided from calibration: the predicted reversal share is below one half at the
                  smallest budget and above it at the largest, so a flip is predicted inside the ladder
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


def load(d: str | Path) -> tuple[dict, list[dict]]:
    d = Path(d)
    res = json.load(open(d / "results.json"))
    with gzip.open(d / "pairs.jsonl.gz", "rt", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]
    return res, rows


def by_cell(rows: list[dict], budgets: list[int]) -> dict:
    out = {}
    for r in rows:
        out.setdefault(r["cell"], {k: [] for k in budgets})[r["k"]].append(r["L"])
    return {c: {k: np.array(v, float) for k, v in d.items()} for c, d in out.items()}


def cross_share(a: np.ndarray, b: np.ndarray, sign: int) -> float:
    """Share of (i, j) with a_i + sign * b_j > 0, exactly, by sorting."""
    bb = np.sort(sign * b)
    # a_i + x > 0  <=>  x > -a_i
    return float((len(bb) - np.searchsorted(bb, -a, side="right")).sum() / (len(a) * len(bb)))


def crossover(shares: list[float], budgets: list[int]) -> float:
    """log2(1 + k) at which the share first reaches one half from below; 0 if it starts there,
    inf if it never gets there."""
    x = [math.log2(1 + k) for k in budgets]
    if shares[0] >= 0.5:
        return 0.0
    for i in range(1, len(shares)):
        if shares[i] >= 0.5:
            s0, s1 = shares[i - 1], shares[i]
            return x[i - 1] + (0.5 - s0) / (s1 - s0) * (x[i] - x[i - 1])
    return math.inf


def predict_from(E: dict, C: dict, budgets: list[int]) -> dict:
    out = {"reversal": {"mean": [], "share": []}, "control": {"mean": [], "share": []},
           "evidence_mean": [], "cue_mean": []}
    for k in budgets:
        e, c = E[k], C[k]
        out["evidence_mean"].append(float(e.mean())); out["cue_mean"].append(float(c.mean()))
        out["reversal"]["mean"].append(float(e.mean() - c.mean()))
        out["control"]["mean"].append(float(e.mean() + c.mean()))
        out["reversal"]["share"].append(cross_share(e, c, -1))
        out["control"]["share"].append(cross_share(e, c, +1))
    out["crossover_log2"] = crossover(out["reversal"]["share"], budgets)
    return out


def predict(cal_dir: str, cfg: dict, seed: int = 20260926) -> dict:
    res, rows = load(cal_dir)
    if res["block"] != "calibration":
        raise SystemExit("predictions are made from the calibration block only")
    budgets = [int(k) for k in cfg["budgets"]]
    cells = by_cell(rows, budgets)
    E, C = cells["evidence"], cells["cue"]
    p = predict_from(E, C, budgets)
    rng = np.random.default_rng(seed)
    nb = int(cfg["bars"]["n_boot"])
    bm = {c: np.empty((nb, len(budgets))) for c in ("reversal", "control")}
    bx = np.empty(nb)
    for b in range(nb):
        Eb = {k: rng.choice(E[k], len(E[k])) for k in budgets}
        Cb = {k: rng.choice(C[k], len(C[k])) for k in budgets}
        q = predict_from(Eb, Cb, budgets)
        for c in bm:
            bm[c][b] = q[c]["mean"]
        bx[b] = q["crossover_log2"]
    for c in bm:
        p[c]["mean_sd"] = bm[c].std(0).tolist()
    p["crossover_boot"] = bx.tolist()
    rs = p["reversal"]["share"]
    p["anti_vacuity"] = {"share_smallest_budget": rs[0], "share_largest_budget": rs[-1],
                         "met": bool(rs[0] < 0.5 < rs[-1])}
    p.update({"gate": cfg["gate"], "budgets": budgets, "calibration_seed": res["seed"], "model": res["model"],
              "n_pairs": {c: {k: int(len(v)) for k, v in d.items()} for c, d in cells.items()}})
    return p


def grade(pred: dict, test_dir: str, cfg: dict, seed: int = 20260927) -> dict:
    res, rows = load(test_dir)
    if res["block"] != "test":
        raise SystemExit("grading reads the test block")
    budgets = [int(k) for k in cfg["budgets"]]
    cells = by_cell(rows, budgets)
    bars = cfg["bars"]
    out = {"F1_additivity": {}, "F2_crossover": {}, "F3_rivals": {}}
    ok1 = True
    for c in ("reversal", "control"):
        rec = []
        for i, k in enumerate(budgets):
            o = cells[c][k]
            se = math.sqrt(pred[c]["mean_sd"][i] ** 2 + o.var(ddof=1) / len(o))
            z = (o.mean() - pred[c]["mean"][i]) / se
            rec.append({"k": k, "observed_mean": float(o.mean()), "predicted_mean": pred[c]["mean"][i], "z": float(z),
                        "observed_share": float((o > 0).mean()), "predicted_share": pred[c]["share"][i]})
            ok1 &= abs(z) <= bars["z_max"]
        out["F1_additivity"][c] = rec
    out["F1_additivity"]["verdict"] = "PASS" if ok1 else "FAIL"
    # crossover, observed from the test block's reversal shares; its bootstrap resamples test pairs
    obs_shares = [float((cells["reversal"][k] > 0).mean()) for k in budgets]
    xo = crossover(obs_shares, budgets)
    rng = np.random.default_rng(seed)
    nb = int(bars["n_boot"])
    xb = np.array([crossover([float((rng.choice(cells["reversal"][k], len(cells["reversal"][k])) > 0).mean())
                              for k in budgets], budgets) for _ in range(nb)])
    xp = pred["crossover_log2"]; xpb = np.array(pred["crossover_boot"])
    fin = np.isfinite(xb) & np.isfinite(xpb)
    diff = xb[fin] - xpb[fin]
    sd = float(diff.std()) if fin.sum() > 10 else float("nan")
    zc = (xo - xp) / sd if (math.isfinite(xo) and math.isfinite(xp) and sd > 0) else float("inf")
    out["F2_crossover"] = {"observed_log2": xo, "predicted_log2": xp,
                           "observed_budget": (2 ** xo - 1) if math.isfinite(xo) else None,
                           "predicted_budget": (2 ** xp - 1) if math.isfinite(xp) else None,
                           "sd_difference": sd, "share_boot_finite": float(fin.mean()), "z": zc,
                           "observed_shares": obs_shares,
                           "verdict": "PASS" if abs(zc) <= bars["crossover_z_max"] else "FAIL"}
    # rivals, on cell means
    sse = {"additive": 0.0, "evidence_only": 0.0, "cue_only": 0.0}
    for i, k in enumerate(budgets):
        E, Cc = pred["evidence_mean"][i], pred["cue_mean"][i]
        for c, sgn in (("reversal", -1), ("control", +1)):
            o = float(cells[c][k].mean())
            sse["additive"] += (o - (E + sgn * Cc)) ** 2
            sse["evidence_only"] += (o - E) ** 2
            sse["cue_only"] += (o - sgn * Cc) ** 2
    out["F3_rivals"] = {"sse": sse, "verdict": "PASS" if sse["additive"] < min(sse["evidence_only"], sse["cue_only"]) else "FAIL"}
    vs = [out[k]["verdict"] for k in ("F1_additivity", "F2_crossover", "F3_rivals")]
    out["anti_vacuity"] = pred["anti_vacuity"]
    out["gate"] = ("PASS" if all(v == "PASS" for v in vs) else "FAIL") if pred["anti_vacuity"]["met"] else "VACUOUS"
    return out


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["predict", "grade"]); ap.add_argument("dir")
    ap.add_argument("--config", required=True); ap.add_argument("--predictions"); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    if any(cfg["bars"].get(b) is None for b in ("z_max", "crossover_z_max", "n_boot")):
        raise SystemExit("bars not fixed")
    if a.cmd == "predict":
        p = predict(a.dir, cfg)
        json.dump(p, open(a.out, "w"), indent=1, default=float)
        print("predictions", a.out, "sha256", sha256(a.out))
        print("crossover budget", None if not math.isfinite(p["crossover_log2"]) else round(2 ** p["crossover_log2"] - 1, 1),
              "| reversal share", [round(x, 3) for x in p["reversal"]["share"]], "| anti-vacuity", p["anti_vacuity"]["met"])
        return 0
    pred = json.load(open(a.predictions))
    g = grade(pred, a.dir, cfg)
    g["predictions_sha256"] = sha256(a.predictions)
    json.dump(g, open(a.out, "w"), indent=1, default=float)
    print("GATE", g["gate"], {k: g[k]["verdict"] for k in ("F1_additivity", "F2_crossover", "F3_rivals")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
