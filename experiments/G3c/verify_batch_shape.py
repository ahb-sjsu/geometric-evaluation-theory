"""Is the one exactness miss (e = 16) numerical, from bfloat16 logits changing with batch shape?

For the same worksheets as verify_sampling.py, the first-token distribution over the 0-9
codebook is recomputed three ways: alone (batch of 1, how the exactness check recorded it), as 32
identical copies in one batch (the shape the real sampler used), and inside a padded batch of 16
mixed worksheets (the shape the harness uses). If the batch-of-32 vector matches the real draws
where the batch-of-1 vector did not, the miss is the model's numerics and not the sampling fix.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402

cfg = json.load(open("prereg_config.json", encoding="utf-8"))
spec = {m["key"]: m for m in cfg["models"]}["qwen7b"]
small = copy.deepcopy(cfg); small["n_cal_per_level"] = 2
data = judge.make_block(small, "calibration", 12345)
pick = [s for s in data["sheets"] if s["e"] in (0, 4, 8, 12, 16, 20)][::2][:6]
prior = {x["e"]: x for x in json.load(open("verify/verify_exactness.json"))["exactness"]}
J = judge.LMJudge(spec, "full", cfg)
scale = {"lo": 0, "hi": 9}
mixed = [s["text"] for s in data["sheets"][:10]]
rng = np.random.default_rng(1)
out = []
for s in pick:
    alone = np.array(J.score([s["text"]], scale, 0, 1.0, 1)[0]["p"], float)
    b32 = J.score([s["text"]] * 32, scale, 0, 1.0, 32)
    rows32 = np.array([r["p"] for r in b32], float)
    in16 = np.array(J.score(mixed[:15] + [s["text"]], scale, 0, 1.0, 16)[-1]["p"], float)
    emp = np.array(prior[s["e"]]["empirical"], float)
    n = prior[s["e"]]["n_draws"]
    def tvd(a, b): return 0.5 * float(np.abs(a / a.sum() - b / b.sum()).sum())
    p32 = rows32[0] / rows32[0].sum()
    null = float(np.percentile([0.5 * np.abs(rng.multinomial(n, p32) / n - p32).sum() for _ in range(4000)], 95))
    rec = {"e": s["e"], "tvd_empirical_vs_alone": round(tvd(emp, alone), 4), "tvd_empirical_vs_batch32": round(tvd(emp, rows32[0]), 4),
           "null_p95_batch32": round(null, 4), "tvd_alone_vs_batch32": round(tvd(alone, rows32[0]), 4),
           "tvd_alone_vs_in_mixed_batch16": round(tvd(alone, in16), 4),
           "batch32_rows_identical": bool(np.allclose(rows32, rows32[0], atol=1e-6)),
           "p_alone": alone.round(3).tolist(), "p_batch32": rows32[0].round(3).tolist(), "empirical": emp.round(3).tolist()}
    rec["holds_against_batch32"] = rec["tvd_empirical_vs_batch32"] <= null
    out.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if not k.startswith(("p_", "emp"))}), flush=True)
J.close()
json.dump(out, open("verify/verify_batch_shape.json", "w"), indent=1)
print("ALL_HOLD_AGAINST_BATCH32", all(r["holds_against_batch32"] for r in out))
