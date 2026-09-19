"""Verification of the chunked digit tree, which the 14B judge needs on a 32 GB card. Not a registered stage.

The pilot's sizing run of Qwen 14B ran out of GPU memory at the second digit of the 0-100 tree:
every live two-digit prefix carried its own copy of the prompt cache. With `tree_rows` set, the
tree runs the same single-token step on at most that many prefixes at a time and keeps the cache
only of rows that have children. Three checks.

1. Chunked against unchunked, on the 7B, which fits either way: 24 calibration worksheets across
   the error counts, the whole-frontier tree against the chunked tree at 4 rows. Differences can
   only come from batch composition in bfloat16, which verify_batch_shape.json found to be nil
   on the first token.
2. The chunked 14B tree against brute force, as verify_tree.py does for the 7B: for three
   worksheets, every score the tree gives above 0.01 recomputed by one uncached forward pass.
3. The 14B's peak memory and time per worksheet on 0-100 at the configured tree settings, and
   one pairwise batch at the configured size, which the pilot never ran on the 14B.

    CUDA_VISIBLE_DEVICES=1 python verify_tree_chunked.py --config prereg_config.json --out verify
"""
from __future__ import annotations

import argparse
import copy
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge  # noqa: E402
from verify_tree import brute_force  # noqa: E402

SCALE = {"lo": 0, "hi": 100}


def judge_for(cfg: dict, key: str, overrides: dict):
    spec = {m["key"]: m for m in cfg["models"]}[key]
    c = {**cfg, **{k: spec[k] for k in ("batch", "batch_tree", "batch_pairwise", "tree_rows") if k in spec}, **overrides}
    return judge.LMJudge(spec, "full", c), c


def trees(J, prompts, batch_tree):
    out = []
    for s in range(0, len(prompts), batch_tree):
        out += J.tree_distribution(prompts[s:s + batch_tree], SCALE, float(J.cfg["tree_prune"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--out", default="verify")
    ap.add_argument("--skip-7b", action="store_true")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    small = copy.deepcopy(cfg); small["n_cal_per_level"] = 2
    data = judge.make_block(small, "calibration", 12345)
    sheets = [s for s in data["sheets"] if s["e"] % 2 == 0][:24]
    report = {}

    if not a.skip_7b:
        J, c = judge_for(cfg, "qwen7b", {})
        prompts = [J._chat(judge.score_prompt(c, s["text"], SCALE)) for s in sheets]
        bt = int(c.get("batch_tree", 8))
        J.cfg = {**c, "tree_rows": None}; whole = trees(J, prompts, bt)
        J.cfg = {**c, "tree_rows": 4}; chunk = trees(J, prompts, bt)
        dp = max(float(np.abs(w["p"] - k["p"]).max()) for w, k in zip(whole, chunk))
        dm = max(abs(w[f] - k[f]) for w, k in zip(whole, chunk) for f in ("tree_valid_mass", "tree_invalid_mass", "tree_pruned_mass"))
        report["chunked_vs_whole_7b"] = {"n_sheets": len(sheets), "batch_tree": bt, "tree_rows": 4,
                                         "max_abs_diff_p": dp, "max_abs_diff_masses": dm,
                                         "identical": bool(dp == 0.0 and dm == 0.0)}
        print(json.dumps(report["chunked_vs_whole_7b"]), flush=True)
        J.close(); del J; gc.collect()

    J, c = judge_for(cfg, "qwen14b", {})
    torch = J.torch
    if c.get("tree_rows") is None:
        raise SystemExit("qwen14b has no tree_rows in the config; the unchunked tree does not fit")
    tok_len = [len(J.tok(J._chat(judge.score_prompt(c, s["text"], SCALE)))["input_ids"]) for s in sheets]
    bf = []
    for s in [x for x in sheets if x["e"] in (0, 8, 16)][:3]:
        prompt = J._chat(judge.score_prompt(c, s["text"], SCALE))
        t = J.tree_distribution([prompt], SCALE, float(c["tree_prune"]))[0]
        p = t["p"] / t["p"].sum()
        for v in np.where(p > 0.01)[0]:
            _, pb = brute_force(J, prompt, int(v))
            tv = float(t["p"][v] * t["tree_valid_mass"])
            bf.append({"e": s["e"], "value": int(v), "tree": round(tv, 6), "brute_force": round(pb, 6),
                       "rel_diff": round(abs(tv - pb) / max(pb, 1e-12), 5)})
    report["brute_force_14b"] = {"rows": bf, "max_rel_diff": max(r["rel_diff"] for r in bf),
                                 "reference_7b_max_rel_diff": 0.24057}
    print(json.dumps({k: v for k, v in report["brute_force_14b"].items() if k != "rows"}), flush=True)
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    recs = J.score([s["text"] for s in sheets], SCALE, int(c["n_samples"]), 1.0, int(c["batch"]))
    dt = time.time() - t0
    peak_score = torch.cuda.max_memory_allocated() / 2**30
    torch.cuda.reset_peak_memory_stats()
    t1 = time.time()
    bp = int(c["batch_pairwise"])
    J.pairwise([s["text"] for s in sheets[:bp * 2]], [s["text"] for s in sheets[-bp * 2:]], bp)
    peak_pair = torch.cuda.max_memory_allocated() / 2**30
    report["timing_14b"] = {"batch": c["batch"], "batch_tree": c["batch_tree"], "tree_rows": c["tree_rows"],
                            "batch_pairwise": bp, "prompt_tokens_min_max": [min(tok_len), max(tok_len)],
                            "seconds_per_sheet_0_100": round(dt / len(recs), 3),
                            "projection_hours_calibration_0_100": round(dt / len(recs) * 840 / 3600, 2),
                            "seconds_per_pair_pairwise": round((time.time() - t1) / (bp * 2), 3),
                            "peak_gib_score": round(peak_score, 2), "peak_gib_pairwise": round(peak_pair, 2),
                            "card_gib": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2),
                            "max_pruned_mass": max(r["tree_pruned_mass"] for r in recs)}
    print(json.dumps(report["timing_14b"]), flush=True)
    J.close()
    json.dump(report, open(out / "verify_tree_chunked.json", "w"), indent=1)
    print("VERIFY_CHUNKED_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
