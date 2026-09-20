#!/usr/bin/env python3
"""G3e: write each judge's predictions from its calibration block, and hash them.

Everything the grader will later compare against comes from the calibration block alone. The
sha256 printed here is committed before the test seed is drawn, which is what makes the
comparison a prediction rather than a fit.

    python g3e_predict.py --config g3e_config.json --out run_record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next((_HERE.parent / d for d in ("G3c", "g3c") if (_HERE.parent / d / "judge.py").exists()), _HERE.parent / "G3c")))
import judge_grade  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="run_record")
    ap.add_argument("--n-boot", type=int, default=500)
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    if "test" in cfg.get("seeds", {}):
        raise SystemExit("a test seed already exists; predictions are written before it is drawn")
    summary = {}
    for m in cfg["models"]:
        d = Path(a.out) / "calibration" / f"{m['key']}__served"
        if not (d / "results.json").exists():
            print(m["key"], "no calibration block, skipped")
            continue
        pred = judge_grade.predict(str(d), cfg, n_boot=a.n_boot)
        text = json.dumps(pred, indent=1, sort_keys=True, default=float)
        (d / "predictions.json").write_text(text, encoding="utf-8")
        sha = hashlib.sha256(text.encode()).hexdigest()
        av = judge_grade.anti_vacuity(pred, cfg["bars"])
        summary[m["key"]] = {
            "served_as": json.load(open(d / "results.json"))["loaded_revision"],
            "sha256": sha,
            "anti_vacuity_met": av["met"],
            "anti_vacuity": av,
            "codebook_sizes": {k: len(v["codebook"]["distinct_scores"]) for k, v in pred["scales"].items()},
            "predicted_thresholds": {k: {n: r["threshold"] for n, r in v["readouts"].items()}
                                     for k, v in pred["scales"].items()},
        }
        print(m["key"], sha[:16], "vacuity met", av["met"],
              "codebook", summary[m["key"]]["codebook_sizes"],
              "| predicted thresholds 0-100",
              {n: round(t, 3) for n, t in summary[m["key"]]["predicted_thresholds"]["0-100"].items()}, flush=True)
    Path(a.out).joinpath("predictions_summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print("wrote", Path(a.out) / "predictions_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
