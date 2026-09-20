#!/usr/bin/env python3
"""Why July did not resolve: a diagnosis of the reader, on July's graded labels.

EXPLORATORY. July is graded, so nothing here can be a test, and nothing here is
run on August, which is still to be graded by the sealed bars. The question is
where the spread of a threshold ratio comes from. Three candidates:

  free     the sealed reader: threshold, shape and lapse all free in each arm
  tied     shape and lapse fitted once per level on the two arms pooled, then
           only the threshold free in each arm
  band     no curve at all: the share of better-move choices among reader
           positions whose gap lies in a fixed band, level minus reference

For each, the point value per level and its spread over a bootstrap that
resamples players. If `tied` or `band` is several times tighter than `free`,
the sealed reader spent its positions on nuisance parameters. If all three are
equally loose, the positions are too few or too clustered and only more data
helps.

Also written: the empirical curve per arm, the share choosing the better move
by gap bin, so a reader of the record can see the data under the fits.
"""
import argparse
import glob
import json

import numpy as np
from scipy.optimize import minimize

import g7a_grade as G
import g7a_threshold as T

BAND = (0.03, 0.15)
BINS = [0.0, 0.01, 0.02, 0.04, 0.07, 0.10, 0.15, 0.25, 1.0]


def reader_view(arm, sel=None):
    g12, g23, ch = arm.g12, arm.g23, arm.ch
    if sel is not None:
        g12, g23, ch = g12[sel], g23[sel], ch[sel]
    keep = (ch <= 1) & (g23 >= T.THIRD_CUTOFF) & (g12 > 0)
    return g12[keep].astype(float), (ch[keep] == 0).astype(float)


def curve(g, y, le, lk, b):
    lam = 0.25 / (1 + np.exp(-b))
    p = 0.5 + (0.5 - lam) * (1 - np.exp(-(g / np.exp(le)) ** np.exp(lk)))
    return np.clip(p, 1e-9, 1 - 1e-9)


def nll(g, y, le, lk, b):
    p = curve(g, y, le, lk, b)
    return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))


def fit_free(g, y):
    best = min((minimize(lambda th: nll(g, y, *th), [np.log(q), 0.3, -2.0], method="Nelder-Mead",
                         options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-8})
                for q in np.quantile(g, [0.3, 0.5, 0.8])), key=lambda r: r.fun)
    return best.x


def fit_tied(g, y, lk, b):
    best = min((minimize(lambda th: nll(g, y, th[0], lk, b), [np.log(q)], method="Nelder-Mead",
                         options={"maxiter": 2000, "xatol": 1e-6, "fatol": 1e-8})
                for q in np.quantile(g, [0.3, 0.5, 0.8])), key=lambda r: r.fun)
    return best.x[0]


def eps_of(le, lk):
    return float(np.exp(le) * np.log(2.0) ** (1.0 / np.exp(lk)))


def band_share(g, y):
    m = (g >= BAND[0]) & (g < BAND[1])
    return float(y[m].mean()) if m.sum() else float("nan"), int(m.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--boot", type=int, default=100)
    a = ap.parse_args()

    rows = []
    for f in sorted(glob.glob(a.labels)):
        with open(f) as fh:
            rows.extend(json.loads(line) for line in fh)
    arms = {k: G.Arm(v) for k, v in G.split_arms(rows).items() if v}
    rng = np.random.default_rng(20260921)
    rec = {"exploratory": True, "month": "2026-07", "band": BAND, "boot": a.boot, "levels": {}}

    for L in G.LEVELS:
        if (L, "level") not in arms or (L, "ref") not in arms:
            continue
        lev, ref = arms[(L, "level")], arms[(L, "ref")]
        out = {"players_level": len(lev.players), "players_ref": len(ref.players)}
        views = {"level": reader_view(lev), "ref": reader_view(ref)}
        for side, (g, y) in views.items():
            le, lk, b = fit_free(g, y)
            counts, shares = [], []
            for lo, hi in zip(BINS[:-1], BINS[1:]):
                m = (g >= lo) & (g < hi)
                counts.append(int(m.sum()))
                shares.append(float(y[m].mean()) if m.sum() else None)
            out[side] = {"n_used": int(len(g)), "eps_free": eps_of(le, lk), "shape_k": float(np.exp(lk)),
                         "lapse": float(0.25 / (1 + np.exp(-b))), "share_better_overall": float(y.mean()),
                         "band_share": band_share(g, y)[0], "band_n": band_share(g, y)[1],
                         "bins": BINS, "bin_counts": counts, "bin_share_better": shares}
        # Nuisance parameters tied across the two arms of this level.
        gp = np.concatenate([views["level"][0], views["ref"][0]])
        yp = np.concatenate([views["level"][1], views["ref"][1]])
        _le, lk_t, b_t = fit_free(gp, yp)
        out["tied_shape_k"], out["tied_lapse"] = float(np.exp(lk_t)), float(0.25 / (1 + np.exp(-b_t)))
        e_l = eps_of(fit_tied(*views["level"], lk_t, b_t), lk_t)
        e_r = eps_of(fit_tied(*views["ref"], lk_t, b_t), lk_t)
        out["point"] = {"log_ratio_free": float(np.log(out["level"]["eps_free"] / out["ref"]["eps_free"])),
                        "log_ratio_tied": float(np.log(e_l / e_r)),
                        "band_diff": out["level"]["band_share"] - out["ref"]["band_share"]}

        free, tied, band = [], [], []
        for _ in range(a.boot):
            gl, yl = reader_view(lev, lev.draw(rng))
            gr, yr = reader_view(ref, ref.draw(rng))
            fl, fr = fit_free(gl, yl), fit_free(gr, yr)
            free.append(np.log(eps_of(fl[0], fl[1]) / eps_of(fr[0], fr[1])))
            tied.append(np.log(eps_of(fit_tied(gl, yl, lk_t, b_t), lk_t) / eps_of(fit_tied(gr, yr, lk_t, b_t), lk_t)))
            band.append(band_share(gl, yl)[0] - band_share(gr, yr)[0])
        out["spread"] = {"log_ratio_free_sd": float(np.std(free)), "log_ratio_tied_sd": float(np.std(tied)),
                         "band_diff_sd": float(np.std(band)),
                         "tied_ci": [float(x) for x in np.quantile(tied, [0.025, 0.975])],
                         "band_ci": [float(x) for x in np.quantile(band, [0.025, 0.975])]}
        out["predicted_log_ratio"] = float(-0.5 * np.log(L / G.REF))
        rec["levels"][str(L)] = out
        print(L, json.dumps(out["point"]), json.dumps(out["spread"]), flush=True)

    with open(a.out, "w") as f:
        json.dump(rec, f, indent=1)


if __name__ == "__main__":
    main()
