"""G4b: incompatibility regret of a shared key code in the second-order regime.

The theorem's predicted loss for a rank-k code Q, in whitened coordinates, is
tr(Pt_i (I - Q)): the read distortion of an error whose second moment is the identity on the
discarded subspace. G4 measured the loss of truncating all 1,024 keys to rank 2, 4 or 8 at
once, which is far outside the regime where that formula applies. G4b measures exactly the
formula's object: at each operating point j that the G4 probe recovered the operators at,
key j alone is perturbed by eps * (I - Q) u with u standard normal in whitened coordinates,
so that E[delta delta^T] = eps^2 (I - Q), and the loss is the summed squared change of the
square-root attention weights over the same sampled query positions the operator was
recovered for. An antithetic pair (+delta, -delta) cancels the third-order term. The same u
is used for every code, rank and consumer at a point (common random numbers), so regrets,
which are differences of losses, are estimated far more precisely than losses.

    python g4b_llama.py --selftest                     # linear consumer, real instrument
    python g4b_llama.py --run --config prereg_config.json --out results.json
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
from g4_shared_code import code_family, evaluate_codes, sym_sqrt, topk_projector, whiten_operator  # noqa: E402


class GroupConsumerAll:
    """Square-root attention weights of all query heads of one KV group at the sampled query
    positions, causal, concatenated per head. Same definition as g4_llama.GroupConsumer, all
    heads at once. Output shape (n_heads, sum over sampled positions of (position + 1))."""

    def __init__(self, Q_group: np.ndarray, K: np.ndarray, query_positions: np.ndarray):
        self.Q = Q_group.astype(np.float64)          # [g, T, d]
        self.K = K.astype(np.float64)                # [T, d]
        self.qpos = query_positions
        self.d = K.shape[1]
        self.T = K.shape[0]
        self.scale = 1.0 / np.sqrt(self.d)

    def sqrt_weights_all(self, K: np.ndarray) -> np.ndarray:
        out = []
        for t in self.qpos:
            s = (K[: t + 1] @ self.Q[:, t, :].T) * self.scale     # [t+1, g]
            s = s - s.max(axis=0, keepdims=True)
            p = np.exp(s); p /= p.sum(axis=0, keepdims=True)
            out.append(np.sqrt(p).T)                                # [g, t+1]
        return np.concatenate(out, axis=1)

    def consumer_at(self, j: int):
        base = self.K.copy()
        def f(x: np.ndarray) -> np.ndarray:
            K = base.copy(); K[j] = x
            return self.sqrt_weights_all(K)
        return f


def measure_cell(f_at, Kh, S_half, S_ihalf, ops, Pts, w, ranks, eps_ladder, n_random, rng_codes, seed_u):
    """Returns {k: {"codes": codes, "eps": {eps: measured_scaled (dict code -> [per consumer]),
    "plus": ..., "minus": ...}}} with measured losses divided by eps^2."""
    d = Kh.shape[1]; group = len(Pts)
    codes_by_k = {k: code_family(Pts, w, k, rng_codes, n_random=n_random) for k in ranks}
    acc = {k: {e: {n: {"pm": np.zeros(group), "plus": np.zeros(group), "minus": np.zeros(group)}
                    for n in codes_by_k[k]} for e in eps_ladder} for k in ranks}
    complements = {k: {n: np.eye(d) - Q for n, Q in codes_by_k[k].items()} for k in ranks}
    for j in ops:
        f = f_at(int(j))
        z0 = S_ihalf @ Kh[j]
        f0 = f(Kh[j])
        u = np.random.default_rng(seed_u + int(j)).standard_normal(d)
        for k in ranks:
            for n, C in complements[k].items():
                v = C @ u
                for e in eps_ladder:
                    dl = e * v
                    fp = f(S_half @ (z0 + dl)); fm = f(S_half @ (z0 - dl))
                    lp = np.sum((fp - f0) ** 2, axis=1); lm = np.sum((fm - f0) ** 2, axis=1)
                    a = acc[k][e][n]
                    a["plus"] += lp; a["minus"] += lm; a["pm"] += 0.5 * (lp + lm)
    out = {}
    n_ops = len(ops)
    for k in ranks:
        out[k] = {"codes": codes_by_k[k], "eps": {}}
        for e in eps_ladder:
            out[k]["eps"][e] = {
                "measured_scaled": {n: list((a["pm"] / n_ops / e ** 2)) for n, a in acc[k][e].items()},
                "plus_scaled": {n: list((a["plus"] / n_ops / e ** 2)) for n, a in acc[k][e].items()},
                "minus_scaled": {n: list((a["minus"] / n_ops / e ** 2)) for n, a in acc[k][e].items()},
            }
    return out


def run(cfg, out_path):
    from g4_llama import capture_qk, load_model
    tok, model = load_model(cfg)
    captured = capture_qk(cfg, tok, model)
    n_kv = int(cfg["n_kv_heads"]); n_q = int(cfg["n_q_heads"]); group = n_q // n_kv
    ranks = [int(k) for k in cfg["ranks"]]
    eps_ladder = [float(e) for e in cfg["eps_ladder"]]
    n_pos = int(cfg["n_operating_points"])
    probe_dir = os.path.join(HERE, cfg["probe_dir"]); prefix = cfg["probe_prefix"]
    # replay the probe's seeded sampling so the consumer (its query positions) and the
    # operating points are the ones the operators were recovered for
    rng_probe = np.random.default_rng(int(cfg["seed"]))
    rng_codes = np.random.default_rng(int(cfg["seed"]) + 3)
    result = {"cells": [], "config": cfg, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    for L, (Q, K) in captured.items():
        T = K.shape[1]
        for hkv in range(n_kv):
            Kh = K[hkv]; Qg = Q[hkv * group:(hkv + 1) * group]
            qpos = np.sort(rng_probe.choice(np.arange(T // 4, T), size=int(cfg["n_query_positions"]), replace=False))
            ops = np.sort(rng_probe.choice(np.arange(T), size=n_pos, replace=False))
            Pts = list(np.load(os.path.join(probe_dir, f"{prefix}_L{L}_h{hkv}_Pt.npy")))
            Sigma = np.load(os.path.join(probe_dir, f"{prefix}_L{L}_h{hkv}_Sigma.npy"))
            S_half, S_ihalf = sym_sqrt(Sigma)
            cons = GroupConsumerAll(Qg, Kh, qpos)
            w = np.ones(group)
            t0 = time.time()
            m = measure_cell(cons.consumer_at, Kh, S_half, S_ihalf, ops, Pts, w, ranks, eps_ladder,
                             int(cfg["n_random_codes"]), rng_codes, int(cfg["seed"]) + 100003 * int(L) + 1009 * hkv)
            cell = {"layer": int(L), "kv_head": int(hkv), "n_operating_points": int(len(ops)), "ranks": {}}
            for k in ranks:
                codes = m[k]["codes"]
                cell["ranks"][str(k)] = {"eps": {}}
                for e in eps_ladder:
                    ev = evaluate_codes(Pts, w, k, codes, m[k]["eps"][e]["measured_scaled"])
                    ev["plus_scaled"] = m[k]["eps"][e]["plus_scaled"]
                    ev["minus_scaled"] = m[k]["eps"][e]["minus_scaled"]
                    cell["ranks"][str(k)]["eps"][str(e)] = ev
                    print(json.dumps({"layer": L, "kv_head": hkv, "k": k, "eps": e,
                                      "bound": ev["deficiency_bound"],
                                      "compromise_measured_total": ev["compromise_measured_total_regret"],
                                      "measured_min_total_code": ev["measured_min_total_code"],
                                      "own_excess": [round(x, 3) for x in ev["own_code_excess_over_measured_best"]],
                                      "ratio_median": float(np.median([mm / max(p, 1e-12) for n, row in ev["codes"].items()
                                                                       for p, mm in zip(row["predicted_distortion"], row["measured_loss"])]))}))
            cell["seconds"] = time.time() - t0
            result["cells"].append(cell)
            json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)


def selftest() -> int:
    """A linear vector consumer f(x) = A x with a known covariance. (1) The real instrument
    (readscope.jacobian_probe, 160 directions, step 0.01, whitened coordinates, as the G4
    probe used it) must recover Pt = S^{1/2} A^T A S^{1/2} to 1e-6. (2) The measurement of
    this file, at every eps, must match eps^2 tr(Pt (I - Q)) within Monte Carlo error, own
    codes must be measured-best, the compromise's measured total regret must sit at the bound,
    and no code's measured total may fall below it beyond Monte Carlo error."""
    from readscope import jacobian_probe
    rng = np.random.default_rng(0)
    d, N, n_pts = 24, 3, 256
    B = rng.normal(size=(d, d)); Sigma = B @ B.T / d + 0.2 * np.eye(d)
    S_half, S_ihalf = sym_sqrt(Sigma)
    A = [rng.normal(size=(rng.integers(2, 5), d)) for _ in range(N)]
    P = [A[i].T @ A[i] for i in range(N)]
    Pts_true = [whiten_operator(Pi, S_half) for Pi in P]
    fails = 0
    # (1) instrument
    X = rng.multivariate_normal(np.zeros(d), Sigma, size=4)
    for i in range(N):
        f = lambda x, i=i: A[i] @ x
        fz = lambda z: f(S_half @ z)
        for x0 in X:
            S = jacobian_probe(fz, (S_ihalf @ x0)[None, :], n_directions=2 * d + 8, eps=0.01, rng=np.random.default_rng(1)).S
            err = np.abs(np.asarray(S) - Pts_true[i]).max() / np.abs(Pts_true[i]).max()
            if err > 1e-6:
                print("FAIL instrument recovery, relative error", err); fails += 1; break
    # (2) measurement
    Kh = rng.multivariate_normal(np.zeros(d), Sigma, size=n_pts)
    # the heads have outputs of different lengths; pad with zero rows so they stack
    m_max = max(a.shape[0] for a in A)
    A_pad = [np.vstack([a, np.zeros((m_max - a.shape[0], d))]) for a in A]
    def f_at(j):
        def f(x):
            return np.stack([Ap @ x for Ap in A_pad])
        return f
    ranks = [2, 4]; eps_ladder = [0.05, 0.2]
    w = np.ones(N)
    m = measure_cell(f_at, Kh, S_half, S_ihalf, np.arange(n_pts), Pts_true, w, ranks, eps_ladder, 16,
                     np.random.default_rng(3), 12345)
    worst = 0.0
    for k in ranks:
        for e in eps_ladder:
            ev = evaluate_codes(Pts_true, w, k, m[k]["codes"], m[k]["eps"][e]["measured_scaled"])
            for n, row in ev["codes"].items():
                for p, mm in zip(row["predicted_distortion"], row["measured_loss"]):
                    worst = max(worst, abs(p - mm) / max(p, 1e-12))
            if max(ev["own_code_excess_over_measured_best"]) > 0.08:
                print("FAIL own code not measured-best", k, e, ev["own_code_excess_over_measured_best"]); fails += 1
            if abs(ev["compromise_measured_total_regret"] - ev["deficiency_bound"]) > 0.15 * ev["deficiency_bound"]:
                print("FAIL compromise measured total", k, e, ev["compromise_measured_total_regret"], ev["deficiency_bound"]); fails += 1
            if ev["any_code_measured_total_below_bound_by"] > 0.15 * ev["deficiency_bound"]:
                print("FAIL a code's measured total beat the bound", k, e, ev["measured_min_total_code"]); fails += 1
            # antithetic pair: for a linear consumer plus and minus agree exactly
            pm = m[k]["eps"][e]
            for n in ev["codes"]:
                if np.abs(np.array(pm["plus_scaled"][n]) - np.array(pm["minus_scaled"][n])).max() > 1e-9:
                    print("FAIL antithetic asymmetry on a linear consumer"); fails += 1; break
    print(json.dumps({"worst_relative_error_measured_vs_predicted": worst, "n_points": n_pts}))
    if worst > 0.20:
        print("FAIL measured vs predicted beyond Monte Carlo tolerance", worst); fails += 1
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config"); ap.add_argument("--out", default="results.json")
    ap.add_argument("--run", action="store_true"); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = json.load(open(a.config, encoding="utf-8"))
    if a.run:
        run(cfg, a.out)
        return 0
    ap.print_help(); return 1


if __name__ == "__main__":
    sys.exit(main())
