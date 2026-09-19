"""Verification of the digit tree on the 0-100 scale before the pilot relaunches. Not a registered stage.

1. The tree against brute force. For each of six worksheets, the probability of every score the
   tree gives above 0.01 is recomputed without the cache: one full forward pass over the prompt
   plus the score's digits, the repetition penalty applied at each position, the product of the
   digit probabilities times the probability of a non-digit next. The two must agree.
2. The tree against real sampling. 1,024 real samples per worksheet from generate() at
   temperature one, top-k and top-p off, compared with the tree by total variation distance,
   against the 95th percentile of multinomial noise. Invalid and unparsable draws are counted.
3. Timing of the new 0-100 path on 42 worksheets, and a projection for the pilot.

    CUDA_VISIBLE_DEVICES=1 python verify_tree.py --config prereg_config.json --out verify
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402


def brute_force(J, prompt: str, value: int) -> tuple[float, float]:
    """P(first token is a digit), and P(the digits of value, then a non-digit | first is a digit),
    from one uncached forward pass over prompt + digits."""
    torch = J.torch
    digits = [J._single(d) for d in str(value)]
    all_digits = torch.tensor([J._single(str(d)) for d in range(10)], device=J.model.device)
    enc = J.tok([prompt], return_tensors="pt").to(J.model.device)
    ids = torch.cat([enc["input_ids"], torch.tensor([digits], device=J.model.device)], dim=1)
    with torch.no_grad():
        logits = J.model(input_ids=ids).logits[0].float()
    L = enc["input_ids"].shape[1]
    first = torch.softmax(J._penalize(logits[L - 1:L], ids[:, :L]), -1)[0]
    p_first_digit = float(first[all_digits].sum())
    p = float(first[digits[0]]) / p_first_digit
    for k in range(1, len(digits)):
        pr = torch.softmax(J._penalize(logits[L + k - 1:L + k], ids[:, :L + k]), -1)[0]
        p *= float(pr[digits[k]])
    pr = torch.softmax(J._penalize(logits[L + len(digits) - 1:L + len(digits)], ids[:, :L + len(digits)]), -1)[0]
    return p_first_digit, p * (1.0 - float(pr[all_digits].sum()))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--out", default="verify")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = {m["key"]: m for m in cfg["models"]}["qwen7b"]
    small = copy.deepcopy(cfg); small["n_cal_per_level"] = 2
    data = judge.make_block(small, "calibration", 12345)
    J = judge.LMJudge(spec, "full", cfg)
    torch = J.torch
    scale = {"lo": 0, "hi": 100}
    report = {"brute_force": [], "sampling": []}
    # 3. timing on 42 worksheets through the harness path
    t0 = time.time()
    recs = J.score([s["text"] for s in data["sheets"]], scale, int(cfg["n_samples"]), 1.0, int(cfg["batch"]))
    dt = time.time() - t0
    report["timing"] = {"seconds_per_sheet_0_100": round(dt / len(recs), 3), "n": len(recs),
                        "max_pruned_mass": max(r["tree_pruned_mass"] for r in recs),
                        "max_invalid_mass": max(r["tree_invalid_mass"] for r in recs),
                        "min_mass_first_digit": min(r["mass_on_codebook"] for r in recs),
                        "unparsed_argmax": int(sum(1 for r in recs if r["argmax"] != r["argmax"]))}
    print(json.dumps({"timing": report["timing"]}), flush=True)
    pick = [s for s in data["sheets"] if s["e"] in (0, 4, 8, 12, 16, 20)][::2][:6]
    rng = np.random.default_rng(3)
    for s in pick:
        prompt = J._chat(judge.score_prompt(cfg, s["text"], scale))
        t = J.tree_distribution([prompt], scale, float(cfg["tree_prune"]))[0]
        p = t["p"] / t["p"].sum()
        # 1. brute force on every value above 0.01
        for v in np.where(p > 0.01)[0]:
            pf, pb = brute_force(J, prompt, int(v))
            tree_joint = float(t["p"][v]) * t["tree_valid_mass"] / max(t["tree_valid_mass"], 1e-30)
            rec = {"e": s["e"], "value": int(v), "tree": round(float(t["p"][v] * t["tree_valid_mass"]), 6),
                   "brute_force": round(pb, 6), "rel_diff": round(abs(float(t["p"][v] * t["tree_valid_mass"]) - pb) / max(pb, 1e-12), 5),
                   "first_digit_mass_tree": round(t["mass_on_codebook"], 6), "first_digit_mass_brute": round(pf, 6)}
            report["brute_force"].append(rec)
        # 2. real sampling
        enc = J.tok([prompt], return_tensors="pt").to(J.model.device)
        L = enc["input_ids"].shape[1]
        draws = []
        for _ in range(32):
            with torch.no_grad():
                g = J.model.generate(**enc, max_new_tokens=4, do_sample=True, temperature=1.0, top_p=1.0, top_k=0,
                                     num_return_sequences=32, pad_token_id=J.tok.pad_token_id)
            draws += [judge.parse_int(J.tok.decode(r, skip_special_tokens=True), scale) for r in g[:, L:]]
        d = np.array(draws, float); ok = d[~np.isnan(d)].astype(int); n = len(ok)
        emp = np.bincount(ok, minlength=101)[:101] / n
        tvd = 0.5 * float(np.abs(emp - p).sum())
        null = np.array([0.5 * np.abs(rng.multinomial(n, p) / n - p).sum() for _ in range(4000)])
        srec = {"e": s["e"], "n_draws": len(d), "unparsable_or_out_of_range": int(np.isnan(d).sum()),
                "tree_invalid_mass": round(t["tree_invalid_mass"], 6), "tree_pruned_mass": t["tree_pruned_mass"],
                "tvd": round(tvd, 4), "null_p95": round(float(np.percentile(null, 95)), 4),
                "p_value": round(float((null >= tvd).mean()), 4),
                "top_tree": {int(v): round(float(p[v]), 4) for v in np.argsort(p)[::-1][:5]},
                "top_empirical": {int(v): round(float(emp[v]), 4) for v in np.argsort(emp)[::-1][:5]}}
        report["sampling"].append(srec)
        print(json.dumps(srec), flush=True)
    J.close()
    worst = max(r["rel_diff"] for r in report["brute_force"])
    report["brute_force_max_rel_diff"] = worst
    report["sampling_all_within_p95"] = bool(all(r["tvd"] <= r["null_p95"] for r in report["sampling"]))
    n_cal = (int(cfg["n_items"]) + 1) * int(cfg["n_cal_per_level"])
    n_pairs = len(cfg["gap_ladder"]) * int(cfg["n_pairs_per_gap"])
    report["projection_hours_0_100"] = {"calibration": round(n_cal * report["timing"]["seconds_per_sheet_0_100"] / 3600, 2),
                                        "test": round(2 * n_pairs * report["timing"]["seconds_per_sheet_0_100"] / 3600, 2)}
    json.dump(report, open(out / "verify_tree.json", "w"), indent=1)
    print("BRUTE_FORCE_MAX_REL_DIFF", worst, "SAMPLING_ALL_WITHIN_P95", report["sampling_all_within_p95"],
          "PROJECTION_0_100", json.dumps(report["projection_hours_0_100"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
