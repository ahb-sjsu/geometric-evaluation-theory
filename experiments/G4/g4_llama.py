"""Gate G4 on Llama-3.2-3B: probe and run.

    python g4_llama.py --probe --config prereg_config.json --out probe.json
    python g4_llama.py --run   --config prereg_config.json --out results.json

Probe mode recovers, per cell (layer, KV head), the key covariance and the three query heads'
read operators with readscope, and writes the anti-vacuity quantities. It computes no loss
under any code. Run mode (after sealing) builds the codes of PREREG-G4 Section 4 and measures
the losses of Section 5.

The consumer at key position j for query head g: replace key j by the input vector, recompute
the attention weights of the sampled query positions over all keys (causal), and return the
square roots of those weights concatenated over the sampled queries. Its squared output change
is half the summed KL to second order.

The read operator recovered here is the Jacobian Gram of the square-root-attention output map,
which is the softmax-weighted operator a finite-difference probe recovers and the object the
second-order loss prediction needs. It is not the unweighted query covariance Q^T Q / n that
earlier gates graded against; the program's calibration C-10 showed the two differ by about
0.3 in subspace overlap, so the registration names the Jacobian Gram explicitly. The versions
of transformers and readscope on Atlas are recorded in the config at sealing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from g4_shared_code import (code_family, deficiency, evaluate_codes, sym_sqrt, topk_projector,
                            topk_sum, whiten_operator)


# ----------------------------------------------------------------------------- model access

def load_model(cfg):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(int(cfg.get("cpu_threads", 16)))
    tok = AutoTokenizer.from_pretrained(cfg["model_id"], revision=cfg.get("revision"))
    model = AutoModelForCausalLM.from_pretrained(cfg["model_id"], revision=cfg.get("revision"),
                                                 torch_dtype=torch.float32)
    model.eval().to("cuda")
    return tok, model


def capture_qk(cfg, tok, model):
    """Run the workload once and capture post-rotary queries and keys of the chosen layers by
    the observation-theory program's method: wrap `apply_rotary_pos_emb` in
    transformers.models.llama.modeling_llama and record its outputs per layer call.
    Returns {layer: (Q [n_qheads, T, d], K [n_kvheads, T, d])} as float32 numpy arrays."""
    import torch
    from transformers.models.llama import modeling_llama as ml
    text = open(cfg["workload_file"], encoding="utf-8").read()
    ids = tok(text, return_tensors="pt").input_ids[:, : int(cfg["n_tokens"])].to("cuda")
    layers = {int(x) for x in cfg["layers"]}
    captured, counter = {}, {"i": 0}
    original = ml.apply_rotary_pos_emb

    def wrapped(q, k, cos, sin, *args, **kwargs):
        qe, ke = original(q, k, cos, sin, *args, **kwargs)
        L = counter["i"]; counter["i"] += 1
        if L in layers:
            captured[L] = (qe[0].detach().float().cpu().numpy(), ke[0].detach().float().cpu().numpy())
        return qe, ke

    ml.apply_rotary_pos_emb = wrapped
    try:
        with torch.no_grad():
            model(ids)
    finally:
        ml.apply_rotary_pos_emb = original
    missing = layers - set(captured)
    if missing:
        raise RuntimeError(f"layers not captured: {sorted(missing)}; layer calls seen: {counter['i']}")
    return captured


# ----------------------------------------------------------------------------- consumer

class GroupConsumer:
    """Attention of the query heads of one KV group over that KV head's keys."""

    def __init__(self, Q_group: np.ndarray, K: np.ndarray, query_positions: np.ndarray):
        # Q_group: [n_q_in_group, T, d]; K: [T, d]
        self.Q = Q_group.astype(np.float64)
        self.K = K.astype(np.float64)
        self.qpos = query_positions
        self.d = K.shape[1]
        self.T = K.shape[0]
        self.scale = 1.0 / np.sqrt(self.d)

    def sqrt_weights(self, g: int, K: np.ndarray) -> np.ndarray:
        """Square-root attention weights of query head g at the sampled positions, causal,
        concatenated. Output length = sum over sampled positions of (position + 1)."""
        out = []
        for t in self.qpos:
            s = (K[: t + 1] @ self.Q[g, t]) * self.scale
            s = s - s.max()
            p = np.exp(s); p /= p.sum()
            out.append(np.sqrt(p))
        return np.concatenate(out)

    def kl_loss(self, g: int, K_coded: np.ndarray) -> tuple[float, float]:
        """(mean squared sqrt-weight change, mean KL) over sampled positions, original vs
        coded keys."""
        sq, kl = 0.0, 0.0
        for t in self.qpos:
            s0 = (self.K[: t + 1] @ self.Q[g, t]) * self.scale; s0 -= s0.max()
            p0 = np.exp(s0); p0 /= p0.sum()
            s1 = (K_coded[: t + 1] @ self.Q[g, t]) * self.scale; s1 -= s1.max()
            p1 = np.exp(s1); p1 /= p1.sum()
            sq += float(np.sum((np.sqrt(p0) - np.sqrt(p1)) ** 2))
            kl += float(np.sum(p0 * (np.log(p0 + 1e-300) - np.log(p1 + 1e-300))))
        return sq / len(self.qpos), kl / len(self.qpos)

    def consumer_at(self, g: int, j: int):
        """Callable x -> sqrt-weights when key j is replaced by x. Only positions t >= j see
        key j; the others are constant and contribute nothing to the Jacobian."""
        base = self.K.copy()
        def f(x: np.ndarray) -> np.ndarray:
            K = base.copy(); K[j] = x
            return self.sqrt_weights(g, K)
        return f


# ----------------------------------------------------------------------------- probe

def recover_read_operator(consumer, x0: np.ndarray, h: float, n_directions: int,
                          rng: np.random.Generator) -> np.ndarray:
    """Jacobian Gram J^T J of the consumer at x0, recovered by readscope.jacobian_probe
    (readscope 0.2.0 signature: consumer, points, *, n_directions, eps, rng, batched,
    output_metric). With n_directions >= d the recovery is exact up to finite-difference
    error, which is the budget cliff of the instrument; the program's published protocol used
    160 directions at d = 128 and central differences, 2 * n_directions calls per point."""
    from readscope import jacobian_probe
    probe = jacobian_probe(consumer, x0[None, :], n_directions=n_directions, eps=h, rng=rng)
    return np.asarray(probe.S, dtype=np.float64)


def probe(cfg, out_path):
    rng = np.random.default_rng(int(cfg["seed"]))
    tok, model = load_model(cfg)
    captured = capture_qk(cfg, tok, model)
    n_kv = int(cfg["n_kv_heads"]); n_q = int(cfg["n_q_heads"]); group = n_q // n_kv
    ranks = [int(k) for k in cfg["ranks"]]
    n_pos = int(cfg["n_operating_points"]); h = float(cfg["probe_step"])
    result = {"cells": [], "config": cfg, "ratings_read": False, "losses_computed": False,
              "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    for L, (Q, K) in captured.items():
        T = K.shape[1]
        for hkv in range(n_kv):
            Kh = K[hkv]                                   # [T, d]
            Qg = Q[hkv * group:(hkv + 1) * group]         # [group, T, d]
            Sigma = np.cov(Kh.T) + 1e-6 * np.eye(Kh.shape[1])
            S_half, S_ihalf = sym_sqrt(Sigma)
            qpos = np.sort(rng.choice(np.arange(T // 4, T), size=int(cfg["n_query_positions"]), replace=False))
            cons = GroupConsumer(Qg, Kh, qpos)
            ops = np.sort(rng.choice(np.arange(T), size=n_pos, replace=False))
            Pts = []
            for g in range(group):
                P = np.zeros((Kh.shape[1], Kh.shape[1]))
                for j in ops:
                    f = cons.consumer_at(g, int(j))
                    # probe in whitened units: x = S_half z, so J_z = J_x S_half
                    fz = lambda z, f=f: f(S_half @ z)
                    z0 = S_ihalf @ Kh[j]
                    P += recover_read_operator(fz, z0, h, int(cfg["n_directions"]),
                                               np.random.default_rng(int(cfg["seed"]) + 7919 * int(j) + 104729 * g))
                Pts.append(0.5 * (P + P.T) / len(ops))   # already whitened by construction
            ew = np.linalg.eigvalsh(Sigma)
            cell = {
                "layer": int(L), "kv_head": int(hkv), "n_keys": int(T),
                "sigma_condition": float(ew.max() / max(ew.min(), 1e-12)),
                "sigma_effective_rank": float(ew.sum() ** 2 / (ew ** 2).sum()),
                "Pt_effective_rank": [float((np.linalg.eigvalsh(Pt).clip(0).sum() ** 2) / max((np.linalg.eigvalsh(Pt).clip(0) ** 2).sum(), 1e-30)) for Pt in Pts],
                "deficiency_over_own": {},
                "principal_angles_top16_deg": [],
            }
            w = np.ones(group)
            for k in ranks:
                own = sum(topk_sum(Pt, k) for Pt in Pts)
                cell["deficiency_over_own"][str(k)] = float(deficiency(Pts, w, k) / max(own, 1e-12))
            U = [np.linalg.eigh(Pt)[1][:, ::-1][:, :16] for Pt in Pts]
            for a in range(group):
                for b in range(a + 1, group):
                    s = np.linalg.svd(U[a].T @ U[b], compute_uv=False)
                    cell["principal_angles_top16_deg"].append([int(a), int(b), float(np.degrees(np.arccos(np.clip(s.min(), -1, 1))))])
            result["cells"].append(cell)
            np.save(out_path.replace(".json", f"_L{L}_h{hkv}_Pt.npy"), np.stack(Pts))
            np.save(out_path.replace(".json", f"_L{L}_h{hkv}_Sigma.npy"), Sigma)
            print(json.dumps({k: v for k, v in cell.items() if k != "principal_angles_top16_deg"}))
    n_cells = len(result["cells"])
    ok = sum(1 for c in result["cells"] if c["deficiency_over_own"].get("16", 0) > 0.05)
    result["anti_vacuity"] = {"cells_with_bound_over_5pct_at_k16": ok, "n_cells": n_cells, "bar": 12}
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(result["anti_vacuity"]))


# ----------------------------------------------------------------------------- run

def run(cfg, out_path):
    rng = np.random.default_rng(int(cfg["seed"]) + 1)
    tok, model = load_model(cfg)
    captured = capture_qk(cfg, tok, model)
    n_kv = int(cfg["n_kv_heads"]); n_q = int(cfg["n_q_heads"]); group = n_q // n_kv
    ranks = [int(k) for k in cfg["ranks"]]
    probe_prefix = cfg["probe_prefix"]
    result = {"cells": [], "config": cfg, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    for L, (Q, K) in captured.items():
        T = K.shape[1]
        for hkv in range(n_kv):
            Kh = K[hkv]; Qg = Q[hkv * group:(hkv + 1) * group]
            Pts = list(np.load(f"{probe_prefix}_L{L}_h{hkv}_Pt.npy"))
            Sigma = np.load(f"{probe_prefix}_L{L}_h{hkv}_Sigma.npy")
            S_half, S_ihalf = sym_sqrt(Sigma)
            qpos = np.sort(rng.choice(np.arange(T // 4, T), size=int(cfg["n_query_positions"]), replace=False))
            cons = GroupConsumer(Qg, Kh, qpos)
            w = np.ones(group)
            cell = {"layer": int(L), "kv_head": int(hkv), "ranks": {}}
            for k in ranks:
                codes = code_family(Pts, w, k, rng, n_random=int(cfg["n_random_codes"]))
                codes["key_pca"] = topk_projector(S_ihalf @ Sigma @ S_ihalf, k)  # identity in whitened coords; kept for the record
                codes["key_pca_original"] = S_ihalf @ topk_projector(Sigma, k) @ S_half
                measured, measured_kl = {}, {}
                for name, Qc in codes.items():
                    R = S_half @ Qc @ S_ihalf
                    K_coded = Kh @ R.T
                    sq, kl = zip(*[cons.kl_loss(g, K_coded) for g in range(group)])
                    measured[name] = list(map(float, sq)); measured_kl[name] = list(map(float, kl))
                ev = evaluate_codes(Pts, w, k, {n: c for n, c in codes.items() if n != "key_pca_original"}, measured)
                ev["measured_kl"] = measured_kl
                cell["ranks"][str(k)] = ev
                print(json.dumps({"layer": L, "kv_head": hkv, "k": k, "bound": ev["deficiency_bound"],
                                  "compromise_total": ev["codes"]["compromise"]["weighted_total_regret"],
                                  "any_beats": ev["any_code_beats_bound"]}))
            result["cells"].append(cell)
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args(argv)
    cfg = json.load(open(args.config, encoding="utf-8"))
    cfg["workload_sha256"] = hashlib.sha256(open(cfg["workload_file"], "rb").read()).hexdigest()
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "1")
    if args.probe:
        probe(cfg, args.out)
    elif args.run:
        run(cfg, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
