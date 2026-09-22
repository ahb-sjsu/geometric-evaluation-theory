"""Read-only rehearsal of the prediction step on whichever calibration blocks already exist.

Writes NOTHING. The committed predictions must be produced in one pass, by g3e_predict.py, after
every calibration block is done; this only exercises the same code path early so a defect in it
surfaces now rather than after the last block lands. Uses a small bootstrap because the numbers
here are not the artifact, only evidence that the path runs.

    python dryrun_predict.py g3f_config.json run_record
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for cand in ("G3c", "g3c"):
    if (HERE.parent / cand / "judge_grade.py").exists():
        sys.path.insert(0, str(HERE.parent / cand))
        break
import judge_grade  # noqa: E402

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
root = Path(sys.argv[2])

if "test" in cfg.get("seeds", {}):
    raise SystemExit("a test seed exists already; this must run before it is drawn")

for m in cfg["models"]:
    d = root / "calibration" / ("%s__served" % m["key"])
    if not (d / "results.json").exists():
        print("%-12s no calibration block yet" % m["key"])
        continue
    pred = judge_grade.predict(str(d), cfg, n_boot=50)
    av = judge_grade.anti_vacuity(pred, cfg["bars"])
    books = {k: len(v["codebook"]["distinct_scores"]) for k, v in pred["scales"].items()}
    thr = {k: round(v["readouts"]["argmax"]["threshold"], 3) for k, v in pred["scales"].items()}
    exp = {k: round(v["readouts"]["expected"]["threshold"], 3) for k, v in pred["scales"].items()
           if "expected" in v["readouts"]}
    print("%-12s vacuity_met=%s codebook=%s greedy_thr=%s expected_thr=%s"
          % (m["key"], av["met"], books, thr, exp))
print("\nDRY RUN ONLY. Nothing written. The committed predictions come from g3e_predict.py "
      "after every block is complete.")
