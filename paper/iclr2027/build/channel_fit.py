"""Grid-channel fit for every G3 cell, with parametric bootstrap intervals.

Model. An evaluator that resolves exactly, behind a channel that rounds or truncates
both consequences to a grid of step h, with a lapse rate lam above resolution:
    accuracy(gap) = (1 - lam) * min(1, gap / h).
h is fitted by least squares through the origin on the ladder points with accuracy
below 0.9 (the linear region); lam is one minus the mean accuracy on points with
gap >= 2 h_set (the plateau). The registered threshold (0.9 level, log-gap
interpolation) is recomputed for comparison. Intervals are a parametric binomial
bootstrap per gap, n = 200, 4000 draws.

Reads experiments/G3/results.json. Writes build/channel_fit.json and
figures/accuracy.pdf/png with the channel prediction overlaid.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "experiments" / "G3"
HERE = Path(__file__).resolve().parents[1]
AFF = {1: 10.0, 2: 1.0, 3: 1.0, 4: 0.1, 5: 0.01, 6: 0.001, 12: 0.001}
LEVEL = 0.9
plt.rcParams.update({"font.family": "serif", "font.size": 9, "legend.fontsize": 7.5,
                     "xtick.labelsize": 8, "ytick.labelsize": 8})

res = json.load(open(G3 / "results.json"))
gaps = np.array(res["config"]["gap_ladder"])
n = res["config"]["n_pairs_per_gap"]
rng = np.random.default_rng(20260918)


def threshold(acc):
    for i in range(len(gaps)):
        if acc[i] >= LEVEL:
            if i == 0:
                return float(gaps[0])
            g0, g1 = np.log(gaps[i - 1]), np.log(gaps[i])
            return float(np.exp(g0 + (LEVEL - acc[i - 1]) / (acc[i] - acc[i - 1]) * (g1 - g0)))
    return float("inf")


def fit(acc, h_set):
    lin = acc < LEVEL
    lam = 1.0 - float(acc[gaps >= 2 * h_set].mean()) if (gaps >= 2 * h_set).any() else 0.0
    x, y = gaps[lin], acc[lin] / max(1e-9, 1 - lam)
    h = float(x @ x / (x @ y)) if (x @ y) > 0 else float("nan")
    return h, lam


def budget(c):
    h = 10.0 ** -c["decimals"] if c["report_tokens"] == 12 else AFF[c["report_tokens"]]
    return max(h, 0.001)


out = {}
for c in res["cells"]:
    h_set = budget(c)
    acc = np.array([c["accuracy_by_gap"][str(g)]["accuracy"] for g in gaps])
    h, lam = fit(acc, h_set)
    thr = threshold(acc)
    H, L, T = [], [], []
    for _ in range(4000):
        a = rng.binomial(n, np.clip(acc, 0, 1)) / n
        hb, lb = fit(a, h_set)
        H.append(hb); L.append(lb); T.append(threshold(a))
    ci = lambda v: [float(np.nanpercentile(v, 2.5)), float(np.nanpercentile(v, 97.5))]
    pred = (1 - lam) * np.minimum(1.0, gaps / h_set)
    key = f"{c['weight_precision']}_{c['decimals']}dec_{c['report_tokens']}tok"
    out[key] = {"weight_precision": c["weight_precision"], "decimals": c["decimals"], "report_tokens": c["report_tokens"],
                "budget": h_set, "h_hat": h, "h_ci": ci(H), "h_ratio": h / h_set,
                "lapse": lam, "lapse_ci": ci(L), "threshold_0.9": thr, "threshold_ci": ci(T),
                "max_abs_dev_from_channel": float(np.max(np.abs(acc - pred)))}
    print(f"{key:20s} set {h_set:<6g} h {h:.5f} [{out[key]['h_ci'][0]:.5f},{out[key]['h_ci'][1]:.5f}] ratio {h/h_set:.3f} "
          f"lapse {lam:.3f} [{out[key]['lapse_ci'][0]:.3f},{out[key]['lapse_ci'][1]:.3f}] thr {thr:.5f} dev {out[key]['max_abs_dev_from_channel']:.3f}")

json.dump({"model": "accuracy = (1 - lapse) * min(1, gap / h); h by least squares through the origin on points below 0.9; "
                    "lapse = 1 - mean accuracy at gap >= 2 h_set; parametric binomial bootstrap n=200, 4000 draws, seed 20260918",
           "source": "experiments/G3/results.json", "cells": out}, open(HERE / "build" / "channel_fit.json", "w"), indent=1)

# Figure 2 with the channel prediction overlaid
fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6), sharey=True)
fine = np.logspace(np.log10(gaps[0]), np.log10(gaps[-1]), 300)
ax = axes[0]
for d, mk in zip(range(4), ("o", "s", "^", "D")):
    c = next(x for x in res["cells"] if x["weight_precision"] == "full" and x["decimals"] == d and x["report_tokens"] == 12)
    acc = [c["accuracy_by_gap"][str(g)]["accuracy"] for g in gaps]
    line, = ax.plot(gaps, acc, marker=mk, ms=3.5, mfc="none", lw=0, label=f"{d} decimal{'s' if d != 1 else ''}")
    ax.plot(fine, np.minimum(1, fine / budget(c)), color=line.get_color(), lw=0.8, alpha=0.7)
ax.axhline(LEVEL, color="0.6", lw=0.6, ls=":")
ax.set_xscale("log"); ax.set_xlabel("gap between the two consequences"); ax.set_ylabel("accuracy")
ax.set_title("rendering ladder, bfloat16, 12-token reports", fontsize=8)
ax.legend(frameon=False, loc="lower right")
ax = axes[1]
for k, mk in zip((1, 2, 4, 5, 6), ("v", "o", "s", "^", "D")):
    c = next(x for x in res["cells"] if x["weight_precision"] == "full" and x["decimals"] == 3 and x["report_tokens"] == k)
    acc = [c["accuracy_by_gap"][str(g)]["accuracy"] for g in gaps]
    line, = ax.plot(gaps, acc, marker=mk, ms=3.5, mfc="none", lw=0, label=f"{k} token{'s' if k > 1 else ''}")
    ax.plot(fine, np.minimum(1, fine / budget(c)), color=line.get_color(), lw=0.8, alpha=0.7)
ax.axhline(LEVEL, color="0.6", lw=0.6, ls=":")
ax.set_xscale("log"); ax.set_xlabel("gap between the two consequences")
ax.set_title("report ladder, bfloat16, 3 decimals", fontsize=8)
ax.legend(frameon=False, loc="lower right")
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(HERE / "figures" / f"accuracy.{ext}", dpi=300)
print("wrote channel_fit.json and figures/accuracy.*")
