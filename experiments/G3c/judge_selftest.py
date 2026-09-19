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
BARS = {"dev_max": 0.12, "z_max": 4.0, "threshold_factor": 1.6, "rank_agreement_min": 0.6}
HEAPED = {"0-100": [20, 35, 45, 65, 75, 85, 95, 100]}


def config(seed: int) -> dict:
    cfg = copy.deepcopy(BASE)
    cfg["models"] = [
        {"key": "synth_judge", "model_id": "synthetic:judge", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.05, "tau": 0.45, "heaped_codebooks": HEAPED, "seed": 1}},
        {"key": "synth_drift", "model_id": "synthetic:drift", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.05, "tau": 0.45, "heaped_codebooks": HEAPED, "drift": 3.0, "seed": 2}},
        {"key": "synth_ideal", "model_id": "synthetic:ideal", "precisions": ["full"],
         "synthetic": {"noise_sd": 0.004, "tau": 0.2, "heaped_codebooks": {}, "seed": 3}},
    ]
    cfg["seeds"] = {"calibration": seed, "test": seed + 1}
    cfg["bars"] = dict(BARS)
    return cfg


def one(cfg: dict, key: str, out: Path) -> tuple[dict, dict]:
    judge.run_block(cfg, "calibration", key, "full", str(out))
    cal = out / "calibration" / f"{key}__full"
    pred = judge_grade.predict(str(cal), cfg, n_boot=200)
    json.dump(pred, open(cal / "predictions.json", "w"), indent=1)
    judge.run_block(cfg, "test", key, "full", str(out))
    obs = judge_grade.observed(str(out / "test" / f"{key}__full"), cfg)
    v = judge_grade.grade(pred, obs, cfg["bars"])
    json.dump({"predictions": pred, "observed": obs, "verdicts": v}, open(out / f"grade_{key}.json", "w"), indent=1, default=float)
    return pred, v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="selftest"); ap.add_argument("--seed", type=int, default=20260918)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cfg = config(a.seed)
    t0 = time.time()
    pj, vj = one(cfg, "synth_judge", out)
    pd_, vd = one(cfg, "synth_drift", out)
    pi, vi = one(cfg, "synth_ideal", out)
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
        {"check": "synth_drift: J1 FAIL (I0)", "pass": vd["J1_prediction"]["verdict"] == "FAIL",
         "detail": max(r["max_z"] for r in vd["J1_prediction"].values() if isinstance(r, dict))},
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
