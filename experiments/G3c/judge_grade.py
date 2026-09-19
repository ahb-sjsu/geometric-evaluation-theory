"""G3c grader. Prediction and grading are separate commands, because the claim is that the
budget predicts the threshold before the threshold is measured.

    python judge_grade.py predict CAL_DIR --config prereg_config.json --out predictions.json
        Reads the calibration block only. Writes, for every scale and read-out, the predicted
        accuracy at every ladder gap with a bootstrap interval, the predicted threshold, the
        codebook the judge actually used, and the rival prediction of an ideal quantizer that
        uses every level of the nominal scale. Prints the file's sha256, which is committed
        before the test seed is drawn.

    python judge_grade.py grade TEST_DIR --predictions predictions.json --config prereg_config.json
        Reads the test block, computes the observed curves on the disjoint worksheets, and
        grades them against the committed predictions.

A read-out turns a worksheet into a number, higher is better. A test pair is ordered correctly
when the sheet with fewer errors gets the strictly larger number; ties and unparsable reports
count against. The prediction for a gap is the same quantity computed across calibration levels:
the share of cross pairs (one sheet at e errors, one at e + gap) that are ordered correctly,
averaged over e with the weights the test block uses.
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

LEVEL = 0.75
REQUIRED_BARS = ("dev_max", "z_max", "threshold_factor", "rank_agreement_min", "vacuity_acc_min", "vacuity_bits_min")
PERMISSIVE = {"dev_max": 1.0, "z_max": 1e9, "threshold_factor": 1e9, "rank_agreement_min": -1,
              "vacuity_acc_min": 0.0, "vacuity_bits_min": 0.0}


# ----------------------------------------------------------------------------- read-outs

def load_scores(d: Path, key: str) -> list[dict]:
    with gzip.open(d / f"scores_{key}.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def readouts(cfg: dict, scale: dict, recs: list[dict]) -> dict[str, np.ndarray]:
    lo = scale["lo"]
    out = {"argmax": np.array([r["argmax"] for r in recs], float)}
    if "p" in recs[0]:
        grid = np.arange(lo, scale["hi"] + 1, dtype=float)
        out["expected"] = np.array([float(np.dot(grid, r["p"])) for r in recs])
    if recs[0].get("samples"):
        S = np.array([r["samples"] for r in recs], float)
        for n in cfg["dither_ladder"]:
            with np.errstate(invalid="ignore"):
                out[f"mean_{n}"] = np.nanmean(S[:, :n], axis=1) if n > 1 else S[:, 0]
    return out


def predicted_curve(values: np.ndarray, e: np.ndarray, N: int, gaps: list[int]) -> np.ndarray:
    """Share of calibration cross pairs ordered correctly at each gap, NaN never counting as greater."""
    by = {k: values[e == k] for k in range(N + 1)}
    out = []
    for g in gaps:
        accs = []
        for k in range(0, N - g + 1):
            good, bad = by[k], by[k + g]
            n_tot = len(good) * len(bad)
            gg = good[~np.isnan(good)]; bb = np.sort(bad[~np.isnan(bad)])
            wins = np.searchsorted(bb, gg, side="left").sum() if len(gg) and len(bb) else 0
            accs.append(wins / n_tot if n_tot else 0.0)
        out.append(float(np.mean(accs)))
    return np.array(out)


def threshold(acc: np.ndarray, gaps: list[int], level: float = LEVEL) -> float:
    for i, a in enumerate(acc):
        if a >= level:
            if i == 0:
                return float(gaps[0])
            a0 = acc[i - 1]
            return float(gaps[i - 1] + (level - a0) / (a - a0) * (gaps[i] - gaps[i - 1])) if a > a0 else float(gaps[i])
    return float("inf")


def nominal_curve(scale: dict, N: int, gaps: list[int]) -> np.ndarray:
    """An ideal judge that uses every level of the nominal scale: score = round of the scale
    position of the true quality."""
    L = scale["hi"] - scale["lo"]
    s = lambda k: round(L * (1 - k / N))
    return np.array([np.mean([1.0 if s(k) > s(k + g) else 0.0 for k in range(0, N - g + 1)]) for g in gaps])


def codebook_stats(scores: np.ndarray, e: np.ndarray) -> dict:
    ok = ~np.isnan(scores)
    s, ee = scores[ok], e[ok]
    vals, counts = np.unique(s, return_counts=True)
    p = counts / counts.sum()
    H = float(-(p * np.log2(p)).sum())
    Hc = 0.0
    for k in np.unique(ee):
        sk = s[ee == k]
        _, c = np.unique(sk, return_counts=True)
        pk = c / c.sum()
        Hc += (len(sk) / len(s)) * float(-(pk * np.log2(pk)).sum())
    return {"distinct_scores": [float(v) for v in vals], "n_distinct": int(len(vals)),
            "levels_carrying_95pct": int(np.searchsorted(np.cumsum(np.sort(p)[::-1]), 0.95) + 1),
            "entropy_bits": round(H, 3), "information_about_quality_bits": round(H - Hc, 3),
            "unparsed_share": round(float(1 - ok.mean()), 4)}


# ----------------------------------------------------------------------------- predict

def predict(cal_dir: str, cfg: dict, n_boot: int = 500, seed: int = 20260919) -> dict:
    d = Path(cal_dir)
    res = json.load(open(d / "results.json"))
    if res["block"] != "calibration":
        raise SystemExit("predictions are made from the calibration block only")
    N, gaps = int(cfg["n_items"]), [int(g) for g in cfg["gap_ladder"]]
    rng = np.random.default_rng(seed)
    out = {"gate": cfg["gate"], "model": res["model"], "precision": res["precision"], "calibration_seed": res["seed"],
           "level": LEVEL, "gaps": gaps, "scales": {}}
    for scale in cfg["scales"]:
        key = f"{scale['lo']}-{scale['hi']}"
        recs = load_scores(d, key)
        e = np.array([r["e"] for r in recs])
        R = readouts(cfg, scale, recs)
        idx_by = {k: np.where(e == k)[0] for k in range(N + 1)}
        entry = {"codebook": codebook_stats(R["argmax"], e), "readouts": {},
                 "nominal_rival": {"acc": nominal_curve(scale, N, gaps).round(4).tolist()}}
        entry["nominal_rival"]["threshold"] = threshold(np.array(entry["nominal_rival"]["acc"]), gaps)
        for name, v in R.items():
            acc = predicted_curve(v, e, N, gaps)
            boots = np.empty((n_boot, len(gaps)))
            for b in range(n_boot):
                take = np.concatenate([rng.choice(ix, size=len(ix), replace=True) for ix in idx_by.values()])
                boots[b] = predicted_curve(v[take], e[take], N, gaps)
            thr_b = np.array([threshold(x, gaps) for x in boots])
            entry["readouts"][name] = {"acc": acc.round(4).tolist(), "acc_sd": boots.std(0).round(4).tolist(),
                                       "threshold": threshold(acc, gaps),
                                       "threshold_ci": [float(np.percentile(thr_b, 2.5)), float(np.percentile(thr_b, 97.5))]}
        out["scales"][key] = entry
    floor = min(((rd["threshold"], f"{k}/{n}") for k, s in out["scales"].items() for n, rd in s["readouts"].items()),
                key=lambda x: x[0])
    out["pairwise_prediction"] = {"claim": "the pairwise elicitation resolves at the floor of the pointwise read-outs",
                                  "floor_readout": floor[1], "threshold": floor[0],
                                  "acc": out["scales"][floor[1].split("/")[0]]["readouts"][floor[1].split("/")[1]]["acc"]}
    return out


# ----------------------------------------------------------------------------- grade

def observed(test_dir: str, cfg: dict) -> dict:
    d = Path(test_dir)
    with gzip.open(d / "stimuli.json.gz", "rt", encoding="utf-8") as f:
        stim = json.load(f)
    gaps = [int(g) for g in cfg["gap_ladder"]]
    pairs = stim["pairs"]
    gap_of = np.array([p["gap"] for p in pairs]); good = np.array([p["good"] for p in pairs]); bad = np.array([p["bad"] for p in pairs])
    out = {"n_per_gap": int((gap_of == gaps[0]).sum()), "scales": {}}
    for scale in cfg["scales"]:
        key = f"{scale['lo']}-{scale['hi']}"
        recs = load_scores(d, key)
        R = readouts(cfg, scale, recs)
        out["scales"][key] = {}
        for name, v in R.items():
            with np.errstate(invalid="ignore"):
                correct = v[good] > v[bad]
            acc = np.array([correct[gap_of == g].mean() for g in gaps])
            out["scales"][key][name] = {"acc": acc.round(4).tolist(), "threshold": threshold(acc, gaps),
                                        "plateau": float(acc[-1])}
    pw = d / "pairwise.jsonl.gz"
    if pw.exists():
        with gzip.open(pw, "rt") as f:
            rows = [json.loads(l) for l in f]
        pref = np.array([0.5 * (r["p_first_when_good_first"] + 1 - r["p_first_when_bad_first"]) for r in rows])
        g = np.array([r["gap"] for r in rows])
        acc = np.array([(pref[g == x] > 0.5).mean() for x in gaps])
        out["pairwise"] = {"acc": acc.round(4).tolist(), "threshold": threshold(acc, gaps),
                           "mean_p_first": float(np.mean([r["p_first_when_good_first"] for r in rows] +
                                                         [r["p_first_when_bad_first"] for r in rows]))}
    return out


def kendall(a: list[float], b: list[float]) -> float:
    n, c, t = len(a), 0, 0
    for i in range(n):
        for j in range(i + 1, n):
            s = np.sign(a[i] - a[j]) * np.sign(b[i] - b[j])
            c += s; t += 1
    return float(c / t) if t else float("nan")


def grade(pred: dict, obs: dict, bars: dict) -> dict:
    n = obs["n_per_gap"]
    out = {"bars": bars, "J1_prediction": {}, "J2_effective_vs_nominal": {}, "J3_budget_ordering": {}, "J5_pairwise": {}}
    names, p_thr, o_thr = [], [], []
    ok1 = True
    for key, entry in pred["scales"].items():
        for name, rd in entry["readouts"].items():
            p = np.array(rd["acc"]); o = np.array(obs["scales"][key][name]["acc"])
            # Noise units that do not collapse as accuracy approaches one: a Laplace-shrunk binomial
            # variance for the observation, and a finite-sample floor on the prediction's own
            # bootstrap sd, which reads zero when every calibration cross pair was ordered correctly.
            # Without both, a prediction of 0.9995 against two misordered pairs in 200 scored z = 5.9.
            pt = (p * n + 1.0) / (n + 2.0)
            se = np.sqrt(pt * (1 - pt) / n + np.maximum(np.array(rd["acc_sd"]), 1.0 / (2 * n)) ** 2)
            z = np.abs(o - p) / se
            rec = {"max_abs_dev": float(np.abs(o - p).max()), "max_z": float(z.max()),
                   "predicted_threshold": rd["threshold"], "observed_threshold": obs["scales"][key][name]["threshold"]}
            rec["holds"] = bool(rec["max_abs_dev"] <= bars["dev_max"] and rec["max_z"] <= bars["z_max"])
            ok1 &= rec["holds"]
            out["J1_prediction"][f"{key}/{name}"] = rec
            if math.isfinite(rd["threshold"]) and math.isfinite(rec["observed_threshold"]):
                names.append(f"{key}/{name}"); p_thr.append(rd["threshold"]); o_thr.append(rec["observed_threshold"])
    out["J1_prediction"]["verdict"] = "PASS" if ok1 else "FAIL"
    ok2 = True
    for key, entry in pred["scales"].items():
        o = np.array(obs["scales"][key]["argmax"]["acc"])
        e_eff = float(((o - np.array(entry["readouts"]["argmax"]["acc"])) ** 2).sum())
        e_nom = float(((o - np.array(entry["nominal_rival"]["acc"])) ** 2).sum())
        rec = {"sse_effective": round(e_eff, 4), "sse_nominal": round(e_nom, 4), "effective_wins": e_eff < e_nom,
               "nominal_threshold": entry["nominal_rival"]["threshold"], "effective_threshold": entry["readouts"]["argmax"]["threshold"],
               "observed_threshold": obs["scales"][key]["argmax"]["threshold"], "codebook_levels": entry["codebook"]["n_distinct"],
               "nominal_levels": int(key.split("-")[1]) - int(key.split("-")[0]) + 1}
        ok2 &= rec["effective_wins"]
        out["J2_effective_vs_nominal"][key] = rec
    out["J2_effective_vs_nominal"]["verdict"] = "PASS" if ok2 else "FAIL"
    F = bars["threshold_factor"]
    within = [1 / F <= (o / p) <= F for p, o in zip(p_thr, o_thr)]
    tau = kendall(p_thr, o_thr)
    out["J3_budget_ordering"] = {"readouts": names, "predicted": p_thr, "observed": o_thr, "kendall_tau": tau,
                                 "share_within_factor": float(np.mean(within)) if within else None,
                                 "verdict": "PASS" if (within and all(within) and tau >= bars["rank_agreement_min"]) else "FAIL"}
    if "pairwise" in obs:
        pt, ot = pred["pairwise_prediction"]["threshold"], obs["pairwise"]["threshold"]
        label = "AT FLOOR" if (math.isfinite(ot) and 1 / F <= ot / pt <= F) else ("COARSER" if ot > pt else "FINER")
        out["J5_pairwise"] = {"predicted_floor_readout": pred["pairwise_prediction"]["floor_readout"], "predicted_threshold": pt,
                              "observed_threshold": ot, "observed_acc": obs["pairwise"]["acc"],
                              "mean_p_first": obs["pairwise"]["mean_p_first"], "label": label}
    vs = [out[k]["verdict"] for k in ("J1_prediction", "J2_effective_vs_nominal", "J3_budget_ordering")]
    out["anti_vacuity"] = anti_vacuity(pred, bars)
    out["gate"] = ("PASS" if all(v == "PASS" for v in vs) else "FAIL") if out["anti_vacuity"]["met"] else "VACUOUS"
    return out


def anti_vacuity(pred: dict, bars: dict) -> dict:
    """Decided from the calibration block alone: on at least one scale the argmax orders pairs at
    the largest gap with at least the bar's accuracy, and the argmax carries at least the bar's
    information about quality. A judge that fails it barely perceives quality, and the gate says
    nothing about it either way."""
    rows = {}
    for key, s in pred["scales"].items():
        a = float(s["readouts"]["argmax"]["acc"][-1]); b = float(s["codebook"]["information_about_quality_bits"])
        rows[key] = {"argmax_acc_largest_gap": a, "bits": b,
                     "met": a >= bars.get("vacuity_acc_min", 0.0) and b >= bars.get("vacuity_bits_min", 0.0)}
    return {"scales": rows, "met": any(r["met"] for r in rows.values())}


def wilson(k: float, n: int, zc: float = 1.96) -> list[float]:
    if n == 0:
        return [float("nan"), float("nan")]
    ph = k / n; d = 1 + zc * zc / n
    c = (ph + zc * zc / (2 * n)) / d; h = zc * math.sqrt(ph * (1 - ph) / n + zc * zc / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]


def compare_precisions(full: dict, low: dict, bars: dict) -> dict:
    """GET-12e. The same model at bfloat16 and at 4-bit, graded on the same test block. Every
    read-out's observed threshold at 4-bit must lie within the threshold factor of its bfloat16
    value; a read-out that never reaches the level must fail to reach it at both. The accuracy at
    the largest gap is reported with a Wilson interval and is not graded."""
    F = bars["threshold_factor"]; n = int(full["observed"]["n_per_gap"])
    rows, ok = {}, True
    for key, sc in full["observed"]["scales"].items():
        for name, r in sc.items():
            a, b = r["threshold"], low["observed"]["scales"][key][name]["threshold"]
            fin = math.isfinite(a) and math.isfinite(b)
            within = (1 / F <= b / a <= F) if fin else (math.isfinite(a) == math.isfinite(b))
            pa, pb = r["plateau"], low["observed"]["scales"][key][name]["plateau"]
            rows[f"{key}/{name}"] = {"threshold_full": a, "threshold_low": b, "ratio": (b / a) if fin else None,
                                     "within_factor": bool(within),
                                     "acc_largest_gap_full": pa, "ci_full": wilson(round(pa * n), n),
                                     "acc_largest_gap_low": pb, "ci_low": wilson(round(pb * n), n)}
            ok &= bool(within)
    return {"readouts": rows, "factor": F, "verdict": "PASS" if ok else "FAIL"}


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["predict", "grade", "compare"])
    ap.add_argument("dir")
    ap.add_argument("--config", required=True)
    ap.add_argument("--predictions")
    ap.add_argument("--out")
    ap.add_argument("--pilot", action="store_true", help="grade: report statistics, no verdicts")
    ap.add_argument("--against", help="compare: the 4-bit grade.json; DIR is the bfloat16 grade.json")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    if a.cmd == "compare":
        bars = cfg.get("bars", {})
        if bars.get("threshold_factor") is None:
            raise SystemExit("bars not fixed: ['threshold_factor']")
        full, low = json.load(open(a.dir)), json.load(open(a.against))
        if full.get("predictions_sha256") == low.get("predictions_sha256"):
            raise SystemExit("both grades were made against the same predictions; pass the bfloat16 and the 4-bit grade")
        r = compare_precisions(full, low, bars)
        json.dump(r, open(a.out or "j4_precision.json", "w"), indent=1, default=float)
        print("J4", r["verdict"])
        return 0
    if a.cmd == "predict":
        p = predict(a.dir, cfg)
        out = a.out or str(Path(a.dir) / "predictions.json")
        json.dump(p, open(out, "w"), indent=1)
        print("predictions", out, "sha256", sha256(out))
        for key, s in p["scales"].items():
            print(key, "codebook", s["codebook"]["n_distinct"], "levels,", s["codebook"]["information_about_quality_bits"], "bits |",
                  {n: round(r["threshold"], 2) for n, r in s["readouts"].items()}, "| nominal rival", round(s["nominal_rival"]["threshold"], 2))
        return 0
    pred = json.load(open(a.predictions))
    obs = observed(a.dir, cfg)
    report = {"predictions_sha256": sha256(a.predictions), "observed": obs}
    bars = cfg.get("bars", {})
    missing = [b for b in REQUIRED_BARS if bars.get(b) is None]
    if a.pilot or missing:
        if missing and not a.pilot:
            raise SystemExit(f"bars not fixed: {missing}")
        report["comparison"] = grade(pred, obs, PERMISSIVE)
        report["verdicts"] = None
    else:
        report["verdicts"] = grade(pred, obs, bars)
        print("GATE", report["verdicts"]["gate"])
    out = a.out or str(Path(a.dir) / ("pilot_stats.json" if a.pilot else "grade.json"))
    json.dump(report, open(out, "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
