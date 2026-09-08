"""G5: identification of the metric and the ideal from choices, synthetic stage.

Theorem 4 (uniqueness): two evaluations inducing the same weak order on an open set have
G_2 = lambda G_1 and G_1 (t_2 - t_1) = 0. On a finite battery of consequences the choices reveal
a cone of representations, the feasible set of the semidefinite program of Theorem 3(a), and
that cone shrinks to the truth as the battery grows, provided the consequences span the space
affinely (the design bound: at least m + 1 affinely independent consequences in R^m).

The estimator is that program with a margin: over G positive semidefinite with unit trace and
h in R^m, maximise delta subject to Q(y_b) - Q(y_a) >= delta for every revealed strict
preference a > b, where Q(y) = y^T G y - 2 y^T h, so h = G t. The ideal is read back as
t = G^+ h, which fixes it up to the kernel of G, exactly the theorem's ambiguity.

    python g5_identify.py --selftest
    python g5_identify.py --config prereg_config.json --seed-role pilot --out pilot.json
    python g5_identify.py --config prereg_config.json --seed-role run --out results.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np


# ----------------------------------------------------------------------------- world

def make_evaluator(m: int, rank: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """A metric of the given rank with eigenvalues log-uniform on [0.2, 5], and an ideal."""
    V, _ = np.linalg.qr(rng.normal(size=(m, m)))
    lam = np.zeros(m)
    lam[:rank] = np.exp(rng.uniform(np.log(0.2), np.log(5.0), size=rank))
    G = V @ np.diag(lam) @ V.T
    G = 0.5 * (G + G.T)
    t = rng.normal(size=m)
    return G, t


def battery(n: int, m: int, rng: np.random.Generator, subspace: bool = False) -> np.ndarray:
    """n consequences in R^m in general position, or, with subspace, inside one random affine
    subspace of dimension m - 1, which violates the design bound at every n."""
    Y = rng.normal(size=(n, m))
    if subspace:
        normal = rng.normal(size=m); normal /= np.linalg.norm(normal)
        offset = rng.normal()
        Y = Y - np.outer(Y @ normal, normal) + offset * normal
    return Y


def distances(Y: np.ndarray, G: np.ndarray, t: np.ndarray) -> np.ndarray:
    D = Y - t
    return np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", D, G, D), 0.0))


def strict_pairs(d: np.ndarray, eps: float) -> list[tuple[int, int]]:
    """Revealed strict preferences of the semiorder: a > b iff d(a) + eps < d(b)."""
    n = d.size
    return [(a, b) for a in range(n) for b in range(n) if a != b and d[a] + eps < d[b]]


def threshold_for_indifference_share(d: np.ndarray, share: float) -> float:
    """The eps at which the given share of unordered pairs is indifferent (|d(a) - d(b)| <= eps)."""
    n = d.size
    gaps = np.array([abs(d[a] - d[b]) for a in range(n) for b in range(a + 1, n)])
    return float(np.quantile(gaps, share)) if gaps.size else 0.0


# ----------------------------------------------------------------------------- estimator

def estimate(Y: np.ndarray, pairs: list[tuple[int, int]], solver: str | None = None,
             h_bound: float | None = None) -> dict:
    """Max-margin solution of the representation program of Theorem 3(a). The constraints are
    homogeneous in (G, h, delta), so the scale is fixed on the whole parameter, the Euclidean
    norm of (G, h) at most one, as for a max-margin separator; fixing only tr G would let the
    margin grow by inflating h, and the earlier draft did that. The metric is reported at
    unit trace afterwards and the ideal t = G^+ h is scale-free."""
    import cvxpy as cp
    n, m = Y.shape
    G = cp.Variable((m, m), PSD=True)
    h = cp.Variable(m)
    delta = cp.Variable()
    cons = [cp.norm(cp.hstack([cp.vec(G, order="F"), h]), 2) <= 1.0]
    for a, b in pairs:
        qa = cp.quad_form(Y[a], G) - 2 * Y[a] @ h
        qb = cp.quad_form(Y[b], G) - 2 * Y[b] @ h
        cons.append(qb - qa >= delta)
    prob = cp.Problem(cp.Maximize(delta), cons)
    kw = {"solver": solver} if solver else {}
    prob.solve(**kw)
    if G.value is None:
        prob.solve(solver="SCS")
    if G.value is None:
        raise RuntimeError(f"representation program returned no point: status {prob.status}")
    Gh = 0.5 * (np.asarray(G.value) + np.asarray(G.value).T)
    hh = np.asarray(h.value).ravel()
    return {"G": Gh, "h": hh, "margin": float(delta.value), "status": prob.status}


RANK_CUT = 1e-2


def ideal_from(Gh: np.ndarray, hh: np.ndarray, rel_cut: float = RANK_CUT) -> tuple[np.ndarray, np.ndarray]:
    """t = G^+ h with the pseudo-inverse cut at rel_cut of the top eigenvalue; also returns the
    projector onto the estimated range. The cut is 1e-2 (the prior's eigenvalue ratio is at
    least 0.04, so no true direction is cut): a smaller cut lets a tiny estimated eigenvalue
    of a singular metric blow the ideal up along the estimated kernel, and the small angle
    between the estimated and the true kernel then leaks that into the range error."""
    w, V = np.linalg.eigh(Gh)
    keep = w > rel_cut * w.max()
    Ginv = (V[:, keep] / w[keep]) @ V[:, keep].T
    P = V[:, keep] @ V[:, keep].T
    return Ginv @ (P @ hh), P


# ----------------------------------------------------------------------------- errors

def unit_trace(G: np.ndarray) -> np.ndarray:
    return G / np.trace(G)


def range_projector(G: np.ndarray, rank: int) -> np.ndarray:
    w, V = np.linalg.eigh(G)
    idx = np.argsort(w)[::-1][:rank]
    return V[:, idx] @ V[:, idx].T


def errors(G: np.ndarray, t: np.ndarray, rank: int, Gh: np.ndarray, hh: np.ndarray, m: int) -> dict:
    Gn, Ghn = unit_trace(G), unit_trace(Gh)
    g_rel = float(np.linalg.norm(Ghn - Gn) / np.linalg.norm(Gn))
    P = range_projector(G, rank)
    Ph = range_projector(Gh, rank)
    s = np.linalg.svd(P @ Ph, compute_uv=False)
    angle = float(np.degrees(np.arccos(np.clip(np.sort(s)[::-1][rank - 1] if rank > 0 else 1.0, -1, 1))))
    th, _ = ideal_from(Gh, hh)
    dt = th - t
    return {"g_rel_err": g_rel, "range_angle_deg": angle,
            "t_range_err": float(np.linalg.norm(P @ dt) / np.sqrt(m)),
            "t_kernel_err": float(np.linalg.norm((np.eye(m) - P) @ dt) / np.sqrt(m)) if rank < m else 0.0}


def chance_errors(G: np.ndarray, t: np.ndarray, rank: int, m: int, rng: np.random.Generator, n_draws: int = 64,
                  normal: np.ndarray | None = None) -> dict:
    """Errors of a guess drawn from the evaluator prior, the reference for 'no better than
    chance'. With a unit normal, also the chance error of the metric's entry along it."""
    rows = []
    for _ in range(n_draws):
        Gr, tr = make_evaluator(m, m, rng)
        e = errors(G, t, rank, Gr, Gr @ tr, m)
        if normal is not None:
            e["g_normal_abs_err"] = float(abs(normal @ unit_trace(Gr) @ normal - normal @ unit_trace(G) @ normal))
        rows.append(e)
    return {k: float(np.median([r[k] for r in rows])) for k in rows[0]}


# ----------------------------------------------------------------------------- cells

def run_cells(cfg: dict, seed: int, out_path: str) -> dict:
    rng = np.random.default_rng(seed)
    dims = [int(x) for x in cfg["dims"]]
    ladder_offsets = [int(x) for x in cfg["battery_size_offsets"]]
    n_ev = int(cfg["evaluators_per_cell"])
    share = float(cfg["indifference_share"])
    solver = cfg.get("solver")
    result = {"config": cfg, "seed": seed, "cells": [], "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    for m in dims:
        for rank in (m, m - 1):
            for eps_mode in ("zero", "share"):
                for kind in ("general", "subspace"):
                    offsets = ladder_offsets if kind == "general" else [max(ladder_offsets)]
                    for off in offsets:
                        n = m + off
                        if n < 2:
                            continue
                        rows = []
                        t0 = time.time()
                        for e in range(n_ev):
                            G, t = make_evaluator(m, rank, rng)
                            Y = battery(n, m, rng, subspace=(kind == "subspace"))
                            d = distances(Y, G, t)
                            eps = 0.0 if eps_mode == "zero" else threshold_for_indifference_share(d, share)
                            pairs = strict_pairs(d, eps)
                            if not pairs:
                                rows.append({"n_pairs": 0, "skipped": True}); continue
                            est = estimate(Y, pairs, solver)
                            err = errors(G, t, rank, est["G"], est["h"], m)
                            err.update({"n_pairs": len(pairs), "margin": est["margin"], "status": est["status"], "eps": eps})
                            normal_vec = None
                            if kind == "subspace":
                                # split the metric error into the affine span of the battery and its normal
                                c = Y.mean(axis=0)
                                B = np.linalg.svd(Y - c, full_matrices=True)[2].T   # columns: right singular vectors
                                span, normal = B[:, : m - 1], B[:, m - 1:]
                                normal_vec = normal[:, 0]
                                Gn, Ghn = unit_trace(G), unit_trace(est["G"])
                                Gs, Ghs = span.T @ Gn @ span, span.T @ Ghn @ span
                                err["g_span_rel_err"] = float(np.linalg.norm(Ghs / np.trace(Ghs) - Gs / np.trace(Gs)) / np.linalg.norm(Gs / np.trace(Gs)))
                                err["g_normal_abs_err"] = float(abs((normal.T @ Ghn @ normal)[0, 0] - (normal.T @ Gn @ normal)[0, 0]))
                            err["chance"] = chance_errors(G, t, rank, m, np.random.default_rng(seed + 977 * e + 13 * n + 7 * m), normal=normal_vec)
                            rows.append(err)
                        cell = {"m": m, "rank": rank, "eps_mode": eps_mode, "kind": kind, "n": n, "offset": off,
                                "n_evaluators": n_ev, "seconds": time.time() - t0, "rows": rows}
                        good = [r for r in rows if not r.get("skipped")]
                        summ = {}
                        for key in ("g_rel_err", "range_angle_deg", "t_range_err", "t_kernel_err", "g_span_rel_err", "g_normal_abs_err"):
                            vals = [r[key] for r in good if key in r]
                            if vals:
                                summ[key] = {"median": float(np.median(vals)), "p90": float(np.quantile(vals, 0.9))}
                        for key in ("g_rel_err", "t_range_err", "t_kernel_err", "g_normal_abs_err"):
                            vals = [r["chance"][key] for r in good if key in r["chance"]]
                            if vals:
                                summ["chance_" + key] = float(np.median(vals))
                        cell["summary"] = summ
                        result["cells"].append(cell)
                        print(json.dumps({"m": m, "rank": rank, "eps": eps_mode, "kind": kind, "n": n,
                                          **{k: round(v["median"], 4) for k, v in summ.items() if isinstance(v, dict)}}))
                        json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
    result["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1)
    return result


# ----------------------------------------------------------------------------- self test

def selftest() -> int:
    """Noiseless recovery from a rich battery in general position must be near exact; a battery
    in a proper affine subspace must leave the normal component of the metric unidentified
    while recovering the in-span block; a singular metric must leave the ideal's kernel
    component unidentified while recovering its range component."""
    import cvxpy  # noqa: F401
    rng = np.random.default_rng(0)
    fails = 0
    m = 3
    G, t = make_evaluator(m, m, rng)
    Y = battery(m + 40, m, rng)
    est = estimate(Y, strict_pairs(distances(Y, G, t), 0.0))
    e = errors(G, t, m, est["G"], est["h"], m)
    ch = chance_errors(G, t, m, m, np.random.default_rng(1))
    print("full rank, rich battery:", json.dumps({k: round(v, 4) for k, v in e.items()}), "chance", json.dumps({k: round(v, 3) for k, v in ch.items()}))
    # finite ordinal data identify slowly; the logic check is 'far better than chance'
    if e["g_rel_err"] > 0.25 * ch["g_rel_err"] or e["t_range_err"] > 0.5 * ch["t_range_err"]:
        print("FAIL rich-battery recovery not far better than chance"); fails += 1
    # singular metric: kernel component of the ideal is unidentified, range component is
    G2, t2 = make_evaluator(m, m - 1, rng)
    Y2 = battery(m + 40, m, rng)
    est2 = estimate(Y2, strict_pairs(distances(Y2, G2, t2), 0.0))
    e2 = errors(G2, t2, m - 1, est2["G"], est2["h"], m)
    ch2 = chance_errors(G2, t2, m - 1, m, np.random.default_rng(2))
    print("singular metric:", json.dumps({k: round(v, 4) for k, v in e2.items()}), "chance", json.dumps({k: round(v, 3) for k, v in ch2.items()}))
    if e2["g_rel_err"] > 0.25 * ch2["g_rel_err"] or e2["t_range_err"] > 0.5 * ch2["t_range_err"] or e2["range_angle_deg"] > 10.0:
        print("FAIL singular-metric recovery not far better than chance"); fails += 1
    if e2["t_kernel_err"] < 0.5 * ch2["t_kernel_err"]:
        print("FAIL the kernel component of the ideal should not be recoverable"); fails += 1
    # subspace battery: in-span block recovered, normal entry not
    Y3 = battery(m + 40, m, rng, subspace=True)
    est3 = estimate(Y3, strict_pairs(distances(Y3, G, t), 0.0))
    c = Y3.mean(axis=0); B = np.linalg.svd(Y3 - c, full_matrices=True)[2].T
    span = B[:, : m - 1]
    Gs, Ghs = span.T @ unit_trace(G) @ span, span.T @ unit_trace(est3["G"]) @ span
    span_err = float(np.linalg.norm(Ghs / np.trace(Ghs) - Gs / np.trace(Gs)) / np.linalg.norm(Gs / np.trace(Gs)))
    e3 = errors(G, t, m, est3["G"], est3["h"], m)
    print("subspace battery: in-span block error %.4f, full metric error %.4f (chance %.3f)" % (span_err, e3["g_rel_err"], ch["g_rel_err"]))
    if span_err > 0.25 * ch["g_rel_err"]:
        print("FAIL in-span recovery on a subspace battery"); fails += 1
    if e3["g_rel_err"] < 0.5 * ch["g_rel_err"]:
        print("FAIL the full metric should not be recoverable from a subspace battery"); fails += 1
    # below the design bound: m points in R^m
    Y4 = battery(m, m, rng)
    est4 = estimate(Y4, strict_pairs(distances(Y4, G, t), 0.0))
    e4 = errors(G, t, m, est4["G"], est4["h"], m)
    print("battery of m points:", json.dumps({k: round(v, 4) for k, v in e4.items()}))
    if e4["g_rel_err"] < 0.5 * ch["g_rel_err"]:
        print("FAIL recovery below the design bound"); fails += 1
    print("SELFTEST", "PASS" if fails == 0 else f"FAIL ({fails})")
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config"); ap.add_argument("--out", default="results.json")
    ap.add_argument("--seed-role", choices=["pilot", "run"], default="run")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    cfg = json.load(open(a.config, encoding="utf-8"))
    seed = int(cfg["seed_pilot"] if a.seed_role == "pilot" else cfg["seed_run"])
    run_cells(cfg, seed, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
