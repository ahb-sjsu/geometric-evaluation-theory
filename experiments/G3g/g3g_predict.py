#!/usr/bin/env python3
"""G3g: write each judge's predictions from its calibration block at every input budget, and hash them.

G3e's step, run once per cell of the truncation ladder. Everything the grader will later compare
against comes from the calibration block of that cell alone, so the cell at 200 characters is
predicted from what the judge did with 200 characters and nothing longer. The sha256 of every
predictions.json is committed before the one test seed is drawn, which is what makes each
comparison a prediction rather than a fit.

    python g3g_predict.py --config g3g_config.json --out run_record
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


def cell_name(budget) -> str:
    return "full" if budget in (None, 0, "full", "none") else "trunc%d" % int(budget)


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
    for budget in cfg["truncation_ladder"]:
        cell = cell_name(budget)
        for m in cfg["models"]:
            d = Path(a.out) / cell / "calibration" / f"{m['key']}__served"
            if not (d / "results.json").exists():
                print(cell, m["key"], "no calibration block, skipped")
                continue
            pred = judge_grade.predict(str(d), cfg, n_boot=a.n_boot)
            pred["input_budget_chars"] = None if cell == "full" else int(budget)
            text = json.dumps(pred, indent=1, sort_keys=True, default=float)
            (d / "predictions.json").write_text(text, encoding="utf-8")
            sha = hashlib.sha256(text.encode()).hexdigest()
            av = judge_grade.anti_vacuity(pred, cfg["bars"])
            summary[f"{cell}/{m['key']}"] = {
                "cell": cell, "judge": m["key"],
                "served_as": json.load(open(d / "results.json"))["loaded_revision"],
                "sha256": sha,
                "anti_vacuity_met": av["met"],
                "anti_vacuity": av,
                "codebook_sizes": {k: len(v["codebook"]["distinct_scores"]) for k, v in pred["scales"].items()},
                "predicted_thresholds": {k: {n: r["threshold"] for n, r in v["readouts"].items()}
                                         for k, v in pred["scales"].items()},
            }
            s = summary[f"{cell}/{m['key']}"]
            print("%-9s %-9s %s vacuity met %s codebook %s | predicted greedy thresholds %s"
                  % (cell, m["key"], sha[:16], av["met"], s["codebook_sizes"],
                     {k: round(t["argmax"], 3) for k, t in s["predicted_thresholds"].items()}), flush=True)
    Path(a.out).joinpath("predictions_summary.json").write_text(
        json.dumps(summary, indent=1, default=float), encoding="utf-8")
    print("wrote", Path(a.out) / "predictions_summary.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
