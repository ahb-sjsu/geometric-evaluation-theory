"""Chance or a real difference? The exactness miss at e = 16 (TVD 0.105 on 256 draws, bar 0.073)
is re-measured with 2,048 fresh real draws for e = 16 and e = 12. A chance deviation shrinks
toward the noise level as draws grow; a real difference between the recorded vector and real
sampling does not.
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
pick = [s for s in pick if s["e"] in (12, 16)]
J = judge.LMJudge(spec, "full", cfg)
torch = J.torch
scale = {"lo": 0, "hi": 9}
rng = np.random.default_rng(2)
out = []
for s in pick:
    p = np.array(J.score([s["text"]], scale, 0, 1.0, 1)[0]["p"], float); p /= p.sum()
    enc = J.tok([J._chat(judge.score_prompt(cfg, s["text"], scale))], return_tensors="pt").to(J.model.device)
    L = enc["input_ids"].shape[1]
    draws = []
    for _ in range(64):
        with torch.no_grad():
            g = J.model.generate(**enc, max_new_tokens=4, do_sample=True, temperature=1.0, top_p=1.0, top_k=0,
                                 num_return_sequences=32, pad_token_id=J.tok.pad_token_id)
        draws += [judge.parse_int(J.tok.decode(r, skip_special_tokens=True), scale) for r in g[:, L:]]
    d = np.array(draws, float); ok = d[~np.isnan(d)].astype(int); n = len(ok)
    emp = np.bincount(ok, minlength=10)[:10] / n
    tvd = 0.5 * float(np.abs(emp - p).sum())
    null = np.array([0.5 * np.abs(rng.multinomial(n, p) / n - p).sum() for _ in range(4000)])
    rec = {"e": s["e"], "n_draws": int(n), "unparsable": int(np.isnan(d).sum()), "tvd": round(tvd, 4),
           "null_p95": round(float(np.percentile(null, 95)), 4), "p_value": round(float((null >= tvd).mean()), 4),
           "p": p.round(4).tolist(), "empirical": emp.round(4).tolist()}
    out.append(rec)
    print(json.dumps(rec), flush=True)
J.close()
json.dump(out, open("verify/verify_many_draws.json", "w"), indent=1)
