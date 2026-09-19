"""G3d self-test. No GPU. Synthetic deliberating judges of known structure run through the real
harness and the real grader, calibration first, predictions written, then the test block.

  additive     evidence grows and the cue fades with the budget, and they add on the log-odds
               scale, with a flip near k = 170. Expected: F1, F2, F3 PASS, anti-vacuity met.
  interaction  the same, but the cue is discounted when the evidence is strong, so the cue
               measured at equal quality overstates its pull in the test cells. F1 must FAIL (I0).
  cueblind     no cue at all. No flip is predicted, so the gate must read VACUOUS.
"""
from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flip  # noqa: E402
import flip_grade  # noqa: E402

BASE = json.load(open(Path(__file__).resolve().parent / "flip_config.json", encoding="utf-8"))
SYN = {"a0": 0.05, "a1": 0.06, "c0": 3.0, "c_decay": 0.1, "noise": 0.8, "position": 0.8}
JUDGES = {"additive": {**SYN, "seed": 1},
          "interaction": {**SYN, "interaction": 1.5, "seed": 2},
          "cueblind": {**SYN, "c0": 0.0, "seed": 3}}


def one(name: str, out: Path) -> dict:
    cfg = copy.deepcopy(BASE)
    cfg["model"] = {"key": f"synth_{name}", "model_id": f"synthetic:{name}", "synthetic": JUDGES[name]}
    cfg["seeds"] = {"calibration": 101, "test": 102}
    d = out / name
    flip.run_block(cfg, "calibration", str(d))
    pred = flip_grade.predict(str(d / "calibration"), cfg)
    json.dump(pred, open(d / "predictions.json", "w"), indent=1, default=float)
    flip.run_block(cfg, "test", str(d))
    g = flip_grade.grade(pred, str(d / "test"), cfg)
    json.dump(g, open(d / "grade.json", "w"), indent=1, default=float)
    return g


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "selftest")
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ga, gi, gc = one("additive", out), one("interaction", out), one("cueblind", out)
    maxz = lambda g: max(abs(r["z"]) for c in ("reversal", "control") for r in g["F1_additivity"][c])
    checks = [
        {"check": "additive: F1 PASS", "pass": ga["F1_additivity"]["verdict"] == "PASS", "detail": maxz(ga)},
        {"check": "additive: F2 PASS (crossover predicted)", "pass": ga["F2_crossover"]["verdict"] == "PASS",
         "detail": {k: ga["F2_crossover"][k] for k in ("predicted_budget", "observed_budget", "z")}},
        {"check": "additive: F3 PASS (beats both rivals)", "pass": ga["F3_rivals"]["verdict"] == "PASS", "detail": ga["F3_rivals"]["sse"]},
        {"check": "additive: anti-vacuity met", "pass": ga["anti_vacuity"]["met"], "detail": ga["anti_vacuity"]},
        {"check": "interaction: F1 FAIL (I0)", "pass": gi["F1_additivity"]["verdict"] == "FAIL", "detail": maxz(gi)},
        {"check": "cueblind: VACUOUS", "pass": gc["gate"] == "VACUOUS", "detail": gc["anti_vacuity"]},
    ]
    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    json.dump({"verdict": verdict, "checks": checks, "seconds": round(time.time() - t0, 1)},
              open(out / "selftest.json", "w"), indent=1, default=float)
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"], c["detail"])
    print("SELFTEST", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
