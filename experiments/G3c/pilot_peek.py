"""Pilot peek: grade the test-block scales that have finished against the committed pilot
predictions, before the remaining scale and the pairwise block are done. Pilot data only; the
sealed run is graded by judge_grade.py grade in full."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_grade as G  # noqa: E402

done = sys.argv[1].split(",") if len(sys.argv) > 1 else ["1-5", "0-9"]
cfg = json.load(open("prereg_config.json"))
part = copy.deepcopy(cfg)
part["scales"] = [s for s in cfg["scales"] if f"{s['lo']}-{s['hi']}" in done]
pred = json.load(open("pilot/predictions_qwen7b__full.json"))
pred_part = dict(pred, scales={k: v for k, v in pred["scales"].items() if k in done})
obs = G.observed("pilot/test/qwen7b__full", part)
v = G.grade(pred_part, obs, {"dev_max": 1.0, "z_max": 1e9, "threshold_factor": 1e9, "rank_agreement_min": -1})
print("gaps", pred["gaps"])
for k, r in v["J1_prediction"].items():
    if not isinstance(r, dict):
        continue
    sc, name = k.split("/")
    p = pred["scales"][sc]["readouts"][name]["acc"]
    o = obs["scales"][sc][name]["acc"]
    print(f"{k:16s} pred {[round(x, 3) for x in p]}")
    print(f"{'':16s} obs  {[round(x, 3) for x in o]}  max|dev| {r['max_abs_dev']:.3f}  max z {r['max_z']:.2f}  "
          f"threshold pred {r['predicted_threshold']:.2f} obs {r['observed_threshold']:.2f}")
for k, r in v["J2_effective_vs_nominal"].items():
    if isinstance(r, dict):
        print("J2", k, "sse effective", r["sse_effective"], "nominal", r["sse_nominal"],
              "| codebook", r["codebook_levels"], "of", r["nominal_levels"], "levels")
print("J3 kendall tau", round(v["J3_budget_ordering"]["kendall_tau"], 3))
json.dump({"note": f"pilot peek on scales {done}, taken before the test block finished", "grade": v, "observed": obs},
          open(f"pilot/peek_{'_'.join(done)}.json", "w"), indent=1, default=float)
