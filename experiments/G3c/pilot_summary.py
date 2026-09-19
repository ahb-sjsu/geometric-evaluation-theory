"""Print the pilot grade written by `judge_grade.py grade --pilot`: every comparison, no verdicts."""
import json
import sys

r = json.load(open(sys.argv[1]))
c = r["comparison"]
print("predictions sha256", r["predictions_sha256"][:16])
print("J1, per read-out: max |observed - predicted|, max z, threshold predicted -> observed")
for k, v in c["J1_prediction"].items():
    if isinstance(v, dict):
        print(f"  {k:16s} {v['max_abs_dev']:.3f}  z {v['max_z']:.2f}  {v['predicted_threshold']:.2f} -> {v['observed_threshold']:.2f}")
print("J2, effective codebook against the nominal-scale rival:")
for k, v in c["J2_effective_vs_nominal"].items():
    if isinstance(v, dict):
        print(f"  {k:7s} sse effective {v['sse_effective']:.4f} nominal {v['sse_nominal']:.4f} | thresholds nominal "
              f"{v['nominal_threshold']:.2f} effective {v['effective_threshold']:.2f} observed {v['observed_threshold']:.2f} "
              f"| codebook {v['codebook_levels']} of {v['nominal_levels']}")
j3 = c["J3_budget_ordering"]
print("J3, Kendall tau between predicted and observed thresholds:", round(j3["kendall_tau"], 3))
p = c.get("J5_pairwise", {})
if p:
    print(f"J5, pairwise: {p['label']} | floor read-out {p['predicted_floor_readout']} at {p['predicted_threshold']:.2f} | "
          f"observed {p['observed_threshold']} | accuracy {p['observed_acc']} | P(first) {p['mean_p_first']:.3f}")
