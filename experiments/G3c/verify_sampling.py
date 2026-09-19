"""Verification of the sampling fix before the pilot relaunches. Not a registered stage.

1. Timing. A small calibration block (2 worksheets per error count, 42 in all) through the real
   harness on each scale, and 16 pairwise comparisons, timed, so the full pilot can be projected.
2. Exactness. On a single-token scale the harness draws samples from the recorded probability
   vector instead of generating them. That is exact only if the vector is the distribution real
   sampling uses. For 6 worksheets on the 0-9 scale, 256 real samples each are generated with the
   harness's own settings and compared with the vector by total variation distance, against the
   95th percentile of the same distance under multinomial sampling from the vector itself. The
   vector is renormalized over the codebook, so the probability mass real sampling puts outside
   the codebook is reported beside it and allowed for.

    CUDA_VISIBLE_DEVICES=1 python verify_sampling.py --config prereg_config.json --out verify
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--out", default="verify")
    ap.add_argument("--model", default="qwen7b")
    ap.add_argument("--exactness-only", action="store_true")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = {m["key"]: m for m in cfg["models"]}[a.model]
    small = copy.deepcopy(cfg); small["n_cal_per_level"] = 2
    data = judge.make_block(small, "calibration", 12345)
    texts = [s["text"] for s in data["sheets"]]
    t0 = time.time()
    J = judge.LMJudge(spec, "full", cfg)
    report = {"load_seconds": round(time.time() - t0, 1), "n_sheets": len(texts), "scales": {}}
    for scale in ([] if a.exactness_only else cfg["scales"]):
        key = f"{scale['lo']}-{scale['hi']}"
        t1 = time.time()
        recs = J.score(texts, scale, int(cfg["n_samples"]), float(cfg["temperature"]), int(cfg["batch"]))
        dt = time.time() - t1
        report["scales"][key] = {
            "seconds": round(dt, 1), "seconds_per_sheet": round(dt / len(texts), 3),
            "unparsed_argmax": int(sum(1 for r in recs if r["argmax"] != r["argmax"])),
            "samples_source": recs[0].get("samples_source"),
            "unparsed_samples": int(sum(1 for r in recs for s in r.get("samples", []) if s != s)),
            "mass_on_codebook_min": min((r["mass_on_codebook"] for r in recs if "mass_on_codebook" in r), default=None),
            "mass_on_codebook_median": float(np.median([r["mass_on_codebook"] for r in recs if "mass_on_codebook" in r])) if "p" in recs[0] else None,
            "argmax_by_error": {str(s["e"]): r["argmax"] for s, r in list(zip(data["sheets"], recs))[::2]},
        }
        print(json.dumps({key: {k: v for k, v in report["scales"][key].items() if k != "argmax_by_error"}}), flush=True)
    if not a.exactness_only:
        # pairwise timing on 16 pairs, both orders
        t1 = time.time()
        J.pairwise(texts[:16], texts[16:32], int(cfg["batch_pairwise"])); J.pairwise(texts[16:32], texts[:16], int(cfg["batch_pairwise"]))
        report["pairwise_seconds_per_pair_both_orders"] = round((time.time() - t1) / 16, 3)
    # exactness of drawing samples from the recorded vector, 0-9 scale
    torch = J.torch
    scale = {"lo": 0, "hi": 9}
    pick = [s for s in data["sheets"] if s["e"] in (0, 4, 8, 12, 16, 20)][::2][:6]
    rng = np.random.default_rng(0)
    exact = []
    for s in pick:
        rec = J.score([s["text"]], scale, 0, 1.0, 1)[0]
        p = np.array(rec["p"], float)
        p = p / p.sum()          # the record is rounded to six decimals and can sum to just over one
        prompt = J._chat(judge.score_prompt(cfg, s["text"], scale))
        enc = J.tok([prompt], return_tensors="pt").to(J.model.device)
        draws = []
        for _ in range(8):
            with torch.no_grad():
                g = J.model.generate(**enc, max_new_tokens=4, do_sample=True, temperature=1.0, top_p=1.0, top_k=0,
                                     num_return_sequences=32, pad_token_id=J.tok.pad_token_id)
            L = enc["input_ids"].shape[1]
            draws += [judge.parse_int(J.tok.decode(r, skip_special_tokens=True), scale) for r in g[:, L:]]
        draws = np.array(draws, float)
        ok = draws[~np.isnan(draws)].astype(int)
        emp = np.bincount(ok, minlength=10)[:10] / max(1, len(ok))
        tvd = 0.5 * float(np.abs(emp - p).sum())
        null = [0.5 * float(np.abs(rng.multinomial(len(ok), p) / len(ok) - p).sum()) for _ in range(4000)]
        crit = float(np.percentile(null, 95))
        off = 1.0 - rec["mass_on_codebook"]
        exact.append({"e": s["e"], "n_draws": len(draws), "unparsable_draws": int(np.isnan(draws).sum()),
                      "tvd": round(tvd, 4), "null_p95": round(crit, 4), "mass_off_codebook": round(off, 5),
                      "holds": tvd <= crit + off, "p": [round(x, 4) for x in p], "empirical": [round(float(x), 4) for x in emp]})
        print(json.dumps({k: v for k, v in exact[-1].items() if k not in ("p", "empirical")}), flush=True)
    report["exactness"] = exact
    report["exactness_holds"] = bool(all(x["holds"] for x in exact))
    if a.exactness_only:
        J.close()
        json.dump(report, open(out / "verify_exactness.json", "w"), indent=1)
        print("EXACTNESS", "HOLDS" if report["exactness_holds"] else "FAILS")
        return 0 if report["exactness_holds"] else 1
    per = {k: v["seconds_per_sheet"] for k, v in report["scales"].items()}
    n_cal = (int(cfg["n_items"]) + 1) * int(cfg["n_cal_per_level"])
    n_pairs = len(cfg["gap_ladder"]) * int(cfg["n_pairs_per_gap"])
    cal = n_cal * sum(per.values()); test = 2 * n_pairs * sum(per.values()) + n_pairs * report["pairwise_seconds_per_pair_both_orders"]
    report["projection_hours"] = {"calibration": round(cal / 3600, 2), "test": round(test / 3600, 2), "pilot_total": round((cal + test) / 3600, 2)}
    J.close()
    json.dump(report, open(out / "verify_sampling.json", "w"), indent=1)
    print("PROJECTION", json.dumps(report["projection_hours"]), "EXACTNESS", "HOLDS" if report["exactness_holds"] else "FAILS")
    return 0 if report["exactness_holds"] else 1


if __name__ == "__main__":
    sys.exit(main())
