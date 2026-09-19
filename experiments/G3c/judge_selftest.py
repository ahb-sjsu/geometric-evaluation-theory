"""G3c self-test. No GPU. Synthetic judges of known structure go through the real harness and the
real grader, calibration first, predictions written, then the test block.

  synth_judge   perceives quality with Gaussian noise, writes the nearest entry of its codebook,
                and heaps on the 0-100 scale (eight scores in use). Expected:
                  J1 PASS   the calibration block predicts the test block's accuracy curves
                  J2 PASS   the effective codebook beats the nominal-scale rival, and the rival's
                            0-100 threshold is wrong by more than a factor of two
                  J3 PASS   the predicted ordering of thresholds across read-outs is observed,
                            with the expected score and the 8-sample mean below the argmax
  synth_drift   the same judge, whose perception noise triples on the test block. Its
                calibration cannot predict its test block: J1 must FAIL. This is the check that
                the gate rejects a known defect (I0).
  synth_ideal   uses every level of every nominal scale with little noise. The nominal rival
                must then be as good as the effective prediction on 0-100, which is the check
                that J2 does not pass by construction.
  synth_blind   perceives quality through noise ten times larger. It must come out VACUOUS
                from its calibration block, whatever its other verdicts.
  12e           synth_judge graded again at "int4", where its perception noise is 1.2 times
                larger, must stay within the threshold factor of its "full" thresholds (J4 PASS);
                at "int2", four times larger, it must not (J4 FAIL, the I0 for 12e).

Everything the checks saw is written to the output directory (Rule 8).
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402
import judge_grade  # noqa: E402

BASE = json.load(open(Path(__file__).resolve().parent / "prereg_config.json"))
BARS = {"dev_max": 0.12, "z_max": 4.0, "threshold_factor": 1.6, "rank_agreement_min": 0.6,
        "vacuity_acc_min": 0.9, "vacuity_bits_min": 1.0}
HEAPED = {"0-100": [20, 35, 45, 65, 75, 85, 95, 100]}


def config(seed: int) -> dict:
    cfg = copy.deepcopy(BASE)
    cfg["models"] = [
        {"key": "synth_judge", "model_id": "synthetic:judge", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.05, "tau": 0.45, "heaped_codebooks": HEAPED, "seed": 1,
                       "precision_noise": {"int4": 1.2, "int2": 4.0}}},
        {"key": "synth_drift", "model_id": "synthetic:drift", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.05, "tau": 0.45, "heaped_codebooks": HEAPED, "drift": 3.0, "seed": 2}},
        {"key": "synth_ideal", "model_id": "synthetic:ideal", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.004, "tau": 0.2, "heaped_codebooks": {}, "seed": 3}},
        {"key": "synth_blind", "model_id": "synthetic:blind", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.5, "tau": 0.45, "heaped_codebooks": HEAPED, "seed": 4}},
    ]
    cfg["seeds"] = {"calibration": seed, "test": seed + 1}
    cfg["bars"] = dict(BARS)
    return cfg


def one(cfg: dict, key: str, out: Path, precision: str = "full") -> tuple[dict, dict]:
    tag = f"{key}__{precision}"
    judge.run_block(cfg, "calibration", key, precision, str(out))
    cal = out / "calibration" / tag
    pred = judge_grade.predict(str(cal), cfg, n_boot=200)
    json.dump(pred, open(cal / "predictions.json", "w"), indent=1)
    judge.run_block(cfg, "test", key, precision, str(out))
    obs = judge_grade.observed(str(out / "test" / tag), cfg)
    v = judge_grade.grade(pred, obs, cfg["bars"])
    name = f"grade_{key}.json" if precision == "full" else f"grade_{tag}.json"
    json.dump({"predictions": pred, "observed": obs, "verdicts": v}, open(out / name, "w"), indent=1, default=float)
    return pred, v, obs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="selftest"); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cfg = config(a.seed)
    t0 = time.time()
    pj, vj, oj = one(cfg, "synth_judge", out)
    pd_, vd, _ = one(cfg, "synth_drift", out)
    pi, vi, _ = one(cfg, "synth_ideal", out)
    pb, vb, _ = one(cfg, "synth_blind", out)
    _, _, o4 = one(cfg, "synth_judge", out, "int4")
    _, _, o2 = one(cfg, "synth_judge", out, "int2")
    j4_int4 = judge_grade.compare_precisions({"observed": oj}, {"observed": o4}, cfg["bars"])
    j4_int2 = judge_grade.compare_precisions({"observed": oj}, {"observed": o2}, cfg["bars"])
    json.dump({"int4": j4_int4, "int2": j4_int2}, open(out / "j4_precision.json", "w"), indent=1, default=float)
    thr = lambda p, k, n: p["scales"][k]["readouts"][n]["threshold"]
    j2_100 = vj["J2_effective_vs_nominal"]["0-100"]
    checks = [
        {"check": "synth_judge: J1 PASS (calibration predicts the test block)", "pass": vj["J1_prediction"]["verdict"] == "PASS",
         "detail": {k: (round(r["max_abs_dev"], 3), round(r["max_z"], 2)) for k, r in vj["J1_prediction"].items() if isinstance(r, dict)}},
        {"check": "synth_judge: J2 PASS (effective codebook beats the nominal rival)", "pass": vj["J2_effective_vs_nominal"]["verdict"] == "PASS",
         "detail": {k: (r["sse_effective"], r["sse_nominal"]) for k, r in vj["J2_effective_vs_nominal"].items() if isinstance(r, dict)}},
        {"check": "synth_judge: nominal rival's 0-100 threshold wrong by more than 2x",
         "pass": j2_100["observed_threshold"] / j2_100["nominal_threshold"] > 2.0,
         "detail": {"nominal": j2_100["nominal_threshold"], "observed": j2_100["observed_threshold"]}},
        {"check": "synth_judge: J3 PASS (budget ordering predicted)", "pass": vj["J3_budget_ordering"]["verdict"] == "PASS",
         "detail": {"tau": vj["J3_budget_ordering"]["kendall_tau"], "within": vj["J3_budget_ordering"]["share_within_factor"]}},
        {"check": "synth_judge: expected-score threshold below argmax on 0-9", "pass": thr(pj, "0-9", "expected") < thr(pj, "0-9", "argmax"),
         "detail": {"expected": thr(pj, "0-9", "expected"), "argmax": thr(pj, "0-9", "argmax")}},
        {"check": "synth_judge: 8-sample mean threshold below 1-sample on 0-100", "pass": thr(pj, "0-100", "mean_8") < thr(pj, "0-100", "mean_1"),
         "detail": {"mean_8": thr(pj, "0-100", "mean_8"), "mean_1": thr(pj, "0-100", "mean_1")}},
        {"check": "synth_judge: expected-score threshold below argmax on 0-100", "pass": thr(pj, "0-100", "expected") < thr(pj, "0-100", "argmax"),
         "detail": {"expected": thr(pj, "0-100", "expected"), "argmax": thr(pj, "0-100", "argmax")}},
        {"check": "synth_drift: J1 FAIL (I0)", "pass": vd["J1_prediction"]["verdict"] == "FAIL",
         "detail": max(r["max_z"] for r in vd["J1_prediction"].values() if isinstance(r, dict))},
        {"check": "synth_judge: meets anti-vacuity", "pass": vj["anti_vacuity"]["met"], "detail": vj["anti_vacuity"]},
        {"check": "synth_blind: VACUOUS from its calibration block", "pass": vb["gate"] == "VACUOUS", "detail": vb["anti_vacuity"]},
        {"check": "12e: 4-bit noise x1.2 stays within the factor (J4 PASS)", "pass": j4_int4["verdict"] == "PASS",
         "detail": {k: r["ratio"] for k, r in j4_int4["readouts"].items()}},
        {"check": "12e: noise x4 leaves the factor (J4 FAIL, I0)", "pass": j4_int2["verdict"] == "FAIL",
         "detail": {k: r["ratio"] for k, r in j4_int2["readouts"].items()}},
        {"check": "synth_ideal: nominal rival not beaten on 0-100 (J2 is not passed by construction)",
         "pass": not vi["J2_effective_vs_nominal"]["0-100"]["effective_wins"] or
                 abs(vi["J2_effective_vs_nominal"]["0-100"]["sse_effective"] - vi["J2_effective_vs_nominal"]["0-100"]["sse_nominal"]) < 0.02,
         "detail": vi["J2_effective_vs_nominal"]["0-100"]},
    ]
    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    json.dump({"verdict": verdict, "checks": checks, "seconds": round(time.time() - t0, 1), "bars": BARS},
              open(out / "selftest.json", "w"), indent=1, default=float)
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], "" if c["pass"] else c["detail"])
    print("SELFTEST", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
