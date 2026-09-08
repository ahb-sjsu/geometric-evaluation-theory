"""EXPLORATORY, post-seal diagnostic, not a registered bar. Repeats the G4b measurement at one
eps for chosen cells with fresh noise draws, to tell draw noise from operator error: if a
cell's ratio of measured to predicted loss moves across seeds, the per-cell offset in the
sealed run is the fluctuation of the 64 common draws; if it stays, the recovered operator of
that cell is biased. Same codes, consumer, operating points and operators as the sealed run.

    python g4b_seedcheck.py --config prereg_config.json --cells 16:1,16:4,8:0,8:3 --eps 0.05 --seeds 4 --out seedcheck.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "G4"))
from g4_shared_code import code_family, evaluate_codes, sym_sqrt  # noqa: E402
from g4b_llama import GroupConsumerAll, measure_cell  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--cells", required=True)
    ap.add_argument("--eps", type=float, default=0.05); ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--out", default="seedcheck.json")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config, encoding="utf-8"))
    want = {tuple(int(x) for x in c.split(":")) for c in a.cells.split(",")}
    from g4_llama import capture_qk, load_model
    tok, model = load_model(cfg)
    captured = capture_qk(cfg, tok, model)
    n_kv = int(cfg["n_kv_heads"]); n_q = int(cfg["n_q_heads"]); group = n_q // n_kv
    ranks = [int(k) for k in cfg["ranks"]]; n_pos = int(cfg["n_operating_points"])
    probe_dir = os.path.join(HERE, cfg["probe_dir"]); prefix = cfg["probe_prefix"]
    rng_probe = np.random.default_rng(int(cfg["seed"])); rng_codes = np.random.default_rng(int(cfg["seed"]) + 3)
    out = {"eps": a.eps, "seeds": a.seeds, "cells": []}
    for L, (Q, K) in captured.items():
        T = K.shape[1]
        for hkv in range(n_kv):
            # replay both generators in the sealed run's order so codes and points are identical
            qpos = np.sort(rng_probe.choice(np.arange(T // 4, T), size=int(cfg["n_query_positions"]), replace=False))
            ops = np.sort(rng_probe.choice(np.arange(T), size=n_pos, replace=False))
            Pts = list(np.load(os.path.join(probe_dir, f"{prefix}_L{L}_h{hkv}_Pt.npy")))
            w = np.ones(group)
            codes_by_k = {k: code_family(Pts, w, k, rng_codes, n_random=int(cfg["n_random_codes"])) for k in ranks}
            if (int(L), hkv) not in want:
                continue
            Kh = K[hkv]; Qg = Q[hkv * group:(hkv + 1) * group]
            Sigma = np.load(os.path.join(probe_dir, f"{prefix}_L{L}_h{hkv}_Sigma.npy"))
            S_half, S_ihalf = sym_sqrt(Sigma)
            cons = GroupConsumerAll(Qg, Kh, qpos)
            cell = {"layer": int(L), "kv_head": int(hkv), "per_seed": []}
            base_seed = int(cfg["seed"]) + 100003 * int(L) + 1009 * hkv
            for s in range(a.seeds):
                seed_u = base_seed + 1_000_000 * (s + 1)
                t0 = time.time()
                # the sealed run's codes, replayed above
                m = measure_cell(cons.consumer_at, Kh, S_half, S_ihalf, ops, Pts, w, ranks, [a.eps],
                                 int(cfg["n_random_codes"]), np.random.default_rng(0), seed_u,
                                 codes_by_k=codes_by_k)
                rec = {"seed_u": seed_u, "ranks": {}}
                for k in ranks:
                    ev = evaluate_codes(Pts, w, k, m[k]["codes"], m[k]["eps"][a.eps]["measured_scaled"])
                    ratios = [mm / max(p, 1e-12) for row in ev["codes"].values() for p, mm in zip(row["predicted_distortion"], row["measured_loss"])]
                    rec["ranks"][str(k)] = {"ratio_median": float(np.median(ratios)),
                                            "comp_over_bound": ev["compromise_measured_total_regret"] / ev["deficiency_bound"],
                                            "own_excess_max": float(max(ev["own_code_excess_over_measured_best"]))}
                rec["seconds"] = time.time() - t0
                cell["per_seed"].append(rec)
                print(json.dumps({"layer": L, "kv_head": hkv, "seed": s, **{k: v for k, v in rec["ranks"].items()}}))
            out["cells"].append(cell)
            json.dump(out, open(a.out, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
