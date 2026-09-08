"""Gate G4: incompatibility regret of a shared rank-k code read by several consumers.

Theory (paper Theorem 7, Lean GET.Incompatibility). Whiten the shared representation by the
source covariance Sigma, so that the source is isotropic. Each consumer i then has a whitened
read operator

    Pt_i = Sigma^{1/2} P_i Sigma^{1/2},

and a shared rank-k orthogonal projection Q in whitened coordinates costs consumer i the read
distortion

    D_i(Q) = tr( Pt_i (I - Q) )                       (exact for a linear consumer)

whose minimum over rank-k projections is the sum of the trailing eigenvalues of Pt_i, attained
by a top-k eigenspace (Ky Fan). The regret of Q for consumer i is

    r_i(Q) = D_i(Q) - min_Q' D_i(Q') = sum_{j<=k} lambda_j(Pt_i) - tr(Q Pt_i)  >= 0,

the weighted total regret is bounded below by the deficiency

    sum_i w_i sum_{j<=k} lambda_j(Pt_i) - sum_{j<=k} lambda_j( sum_i w_i Pt_i ),

and the bound is attained by the top-k eigenspace of the weighted sum (the compromise code).

What the experiment measures. For each consumer, the downstream loss under a shared code is
measured directly (for a real attention head, the relative KL of its attention distribution
after the keys are replaced by their coded version). The theory's read distortion is its
second-order prediction of that loss. The gate compares, per consumer and per code, measured
loss against predicted loss, and checks three predictions: own-optimal codes have zero regret,
the compromise attains the deficiency bound, and no code found beats the bound for every
consumer.

This module holds the formulas, the code constructions, and a synthetic self-test in which
the consumers are linear so the second-order prediction is exact. The model-specific probe and
run live in `g4_llama.py`.
"""
from __future__ import annotations

import json
import sys

import numpy as np


# ----------------------------------------------------------------------------- linear algebra

def sym_sqrt(S: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Symmetric square root and inverse square root of a positive definite matrix."""
    w, V = np.linalg.eigh(S)
    w = np.clip(w, 1e-12, None)
    return (V * np.sqrt(w)) @ V.T, (V / np.sqrt(w)) @ V.T


def whiten_operator(P: np.ndarray, S_half: np.ndarray) -> np.ndarray:
    """Pt = Sigma^{1/2} P Sigma^{1/2}, symmetrized."""
    Pt = S_half @ P @ S_half
    return 0.5 * (Pt + Pt.T)


def topk_projector(M: np.ndarray, k: int) -> np.ndarray:
    """Orthogonal projector onto a top-k eigenspace of the symmetric matrix M."""
    w, V = np.linalg.eigh(M)
    U = V[:, np.argsort(w)[::-1][:k]]
    return U @ U.T


def topk_sum(M: np.ndarray, k: int) -> float:
    w = np.linalg.eigvalsh(M)
    return float(np.sort(w)[::-1][:k].sum())


def random_projector(d: int, k: int, rng: np.random.Generator) -> np.ndarray:
    Q, _ = np.linalg.qr(rng.normal(size=(d, k)))
    return Q @ Q.T


# ----------------------------------------------------------------------------- predictions

def predicted_distortion(Pt: np.ndarray, Q: np.ndarray) -> float:
    d = Pt.shape[0]
    return float(np.trace(Pt @ (np.eye(d) - Q)))


def regret(Pt: np.ndarray, Q: np.ndarray, k: int) -> float:
    return topk_sum(Pt, k) - float(np.trace(Q @ Pt))


def deficiency(Pts: list[np.ndarray], w: np.ndarray, k: int) -> float:
    total = sum(w[i] * topk_sum(Pts[i], k) for i in range(len(Pts)))
    Pbar = sum(w[i] * Pts[i] for i in range(len(Pts)))
    return float(total - topk_sum(Pbar, k))


def compromise_projector(Pts: list[np.ndarray], w: np.ndarray, k: int) -> np.ndarray:
    Pbar = sum(w[i] * Pts[i] for i in range(len(Pts)))
    return topk_projector(Pbar, k)


# ----------------------------------------------------------------------------- codes

def code_family(Pts: list[np.ndarray], w: np.ndarray, k: int, rng: np.random.Generator,
                n_random: int = 32) -> dict[str, np.ndarray]:
    """The shared codes the gate evaluates, all rank-k orthogonal projectors in whitened
    coordinates: each consumer's own optimum, the compromise, and random projectors."""
    codes = {f"own_{i}": topk_projector(Pt, k) for i, Pt in enumerate(Pts)}
    codes["compromise"] = compromise_projector(Pts, w, k)
    for r in range(n_random):
        codes[f"random_{r}"] = random_projector(Pts[0].shape[0], k, rng)
    return codes


def evaluate_codes(Pts: list[np.ndarray], w: np.ndarray, k: int,
                   codes: dict[str, np.ndarray],
                   measured: dict[str, list[float]] | None = None) -> dict:
    """Per code: predicted distortion, regret, weighted total regret, and, if given, measured
    losses. Also the deficiency bound and whether any code beats it for every consumer."""
    N = len(Pts)
    bound = deficiency(Pts, w, k)
    own_min = [topk_sum(Pt, k) for Pt in Pts]
    out = {"k": k, "n_consumers": N, "deficiency_bound": bound,
           "summed_own_topk": float(sum(w[i] * own_min[i] for i in range(N))),
           "deficiency_over_own": float(bound / max(sum(w[i] * own_min[i] for i in range(N)), 1e-12)),
           "codes": {}}
    beats_all = []
    for name, Q in codes.items():
        pred = [predicted_distortion(Pt, Q) for Pt in Pts]
        reg = [regret(Pt, Q, k) for Pt in Pts]
        total = float(sum(w[i] * reg[i] for i in range(N)))
        row = {"predicted_distortion": pred, "regret": reg, "weighted_total_regret": total}
        if measured is not None and name in measured:
            row["measured_loss"] = measured[name]
        out["codes"][name] = row
        # "beats the bound for every consumer" means every regret strictly below the
        # per-consumer share it would need for the total to fall under the bound; the
        # operational check is simply total < bound.
        beats_all.append(total < bound - 1e-9)
    out["any_code_beats_bound"] = bool(any(beats_all))
    out["compromise_attains_bound"] = bool(abs(out["codes"]["compromise"]["weighted_total_regret"] - bound) < 1e-7)
    out["own_regret_zero"] = [bool(abs(out["codes"][f"own_{i}"]["regret"][i]) < 1e-7) for i in range(N)]
    # Measured regrets. The predicted regrets above are exact consequences of the theorem and
    # so can never contradict it; the measured ones can. A consumer's measured regret under a
    # code is its measured loss under that code minus its measured loss under its own code.
    if measured is not None and all(f"own_{i}" in measured for i in range(N)):
        own_meas = [float(measured[f"own_{i}"][i]) for i in range(N)]
        min_meas = [float(min(m[i] for m in measured.values())) for i in range(N)]
        out["own_measured_loss"] = own_meas
        out["min_measured_loss_over_codes"] = min_meas
        out["own_code_excess_over_measured_best"] = [own_meas[i] / max(min_meas[i], 1e-12) - 1.0 for i in range(N)]
        totals = {}
        for name, row in out["codes"].items():
            if name in measured:
                mreg = [float(measured[name][i]) - own_meas[i] for i in range(N)]
                row["measured_regret"] = mreg
                row["measured_weighted_total_regret"] = float(sum(w[i] * mreg[i] for i in range(N)))
                totals[name] = row["measured_weighted_total_regret"]
        out["measured_min_total_code"] = min(totals, key=totals.get)
        out["measured_min_total_regret"] = float(min(totals.values()))
        out["compromise_measured_total_regret"] = totals.get("compromise")
        out["any_code_measured_total_below_bound_by"] = float(bound - min(totals.values()))
    return out


# ----------------------------------------------------------------------------- self test

def selftest() -> int:
    """Linear consumers y_i = A_i x with output metric G_i, Gaussian source with covariance
    Sigma. The read operator is P_i = A_i^T G_i A_i. A shared code reconstructs
    xhat = Sigma^{1/2} Q Sigma^{-1/2} x. Measured loss E ||A_i (x - xhat)||_{G_i}^2 by Monte
    Carlo must equal the predicted whitened distortion; own codes must have zero regret; the
    compromise must attain the bound; no random code may beat the bound."""
    rng = np.random.default_rng(0)
    d, N, k, n_mc = 12, 4, 3, 200_000
    fails = 0
    B = rng.normal(size=(d, d)); Sigma = B @ B.T / d + 0.2 * np.eye(d)
    S_half, S_ihalf = sym_sqrt(Sigma)
    A = [rng.normal(size=(rng.integers(2, 5), d)) for _ in range(N)]
    G = []
    for a in A:
        m = a.shape[0]; C = rng.normal(size=(m, m)); G.append(C @ C.T + 0.1 * np.eye(m))
    P = [A[i].T @ G[i] @ A[i] for i in range(N)]
    Pts = [whiten_operator(Pi, S_half) for Pi in P]
    w = rng.uniform(0.5, 2.0, size=N)
    codes = code_family(Pts, w, k, rng, n_random=64)
    # Monte Carlo measured losses
    X = rng.multivariate_normal(np.zeros(d), Sigma, size=n_mc)
    measured = {}
    for name, Q in codes.items():
        R = S_half @ Q @ S_ihalf                       # reconstruction map in original coords
        E = X - X @ R.T                                # error x - xhat
        measured[name] = [float(np.mean(np.einsum("nj,jk,nk->n", E @ A[i].T, G[i], E @ A[i].T)))
                          for i in range(N)]
    res = evaluate_codes(Pts, w, k, codes, measured)
    # 1. measured equals predicted within Monte Carlo error (relative 3%)
    worst = 0.0
    for name, row in res["codes"].items():
        for p, m in zip(row["predicted_distortion"], row["measured_loss"]):
            worst = max(worst, abs(p - m) / max(abs(p), 1e-9))
    if worst > 0.03:
        print("FAIL measured vs predicted, worst relative error", worst); fails += 1
    # 2. own codes have zero regret
    if not all(res["own_regret_zero"]):
        print("FAIL own regret", res["own_regret_zero"]); fails += 1
    # 3. compromise attains the bound
    if not res["compromise_attains_bound"]:
        print("FAIL compromise", res["codes"]["compromise"]["weighted_total_regret"], res["deficiency_bound"]); fails += 1
    # 4. no code beats the bound
    if res["any_code_beats_bound"]:
        print("FAIL a code beat the bound"); fails += 1
    # 5. the bound is strictly positive here (geometries differ) and own codes cost others
    if not res["deficiency_bound"] > 1e-6:
        print("FAIL bound not positive", res["deficiency_bound"]); fails += 1
    # 6. measured regrets: own codes are measured-best within Monte Carlo error, the compromise's
    #    measured total is within 3% of the bound, and no code's measured total is below the
    #    bound by more than 3% of it
    if max(res["own_code_excess_over_measured_best"]) > 0.03:
        print("FAIL own code not measured-best", res["own_code_excess_over_measured_best"]); fails += 1
    if abs(res["compromise_measured_total_regret"] - res["deficiency_bound"]) > 0.03 * res["deficiency_bound"]:
        print("FAIL compromise measured total", res["compromise_measured_total_regret"], res["deficiency_bound"]); fails += 1
    if res["any_code_measured_total_below_bound_by"] > 0.03 * res["deficiency_bound"]:
        print("FAIL a code's measured total beat the bound", res["measured_min_total_code"], res["measured_min_total_regret"]); fails += 1
    summary = {
        "worst_relative_error_measured_vs_predicted": worst,
        "deficiency_bound": res["deficiency_bound"],
        "compromise_total_regret": res["codes"]["compromise"]["weighted_total_regret"],
        "min_random_total_regret": min(v["weighted_total_regret"] for n, v in res["codes"].items() if n.startswith("random")),
        "compromise_measured_total_regret": res["compromise_measured_total_regret"],
        "measured_min_total_code": res["measured_min_total_code"],
        "own_code_total_regrets": [res["codes"][f"own_{i}"]["weighted_total_regret"] for i in range(N)],
    }
    print(json.dumps(summary, indent=1))
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 0)
