"""Figures for the ICLR 2027 paper, built from the graded G3 record.

Reads experiments/G3/results.json and grade.json only. Writes
figures/thresholds.pdf and figures/accuracy.pdf (plus PNG at 300 dpi).
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "experiments" / "G3"
OUT = Path(__file__).resolve().parents[1] / "figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.labelsize": 9,
                     "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8})

res = json.load(open(G3 / "results.json"))
grade = json.load(open(G3 / "grade.json"))
cells = res["cells"]
gaps = res["config"]["gap_ladder"]
thr = grade["thresholds"]

# afforded resolution by report length: one digit per token, two digits before the point
AFFORDED = {1: 10.0, 2: 1.0, 3: 1.0, 4: 0.1, 5: 0.01, 6: 0.001, 12: 0.001}


def fig_thresholds():
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    xs = [10.0 ** -d for d in range(4)]
    for prec, mk, lab in (("full", "o", "bfloat16"), ("int8", "s", "8-bit"), ("int4", "^", "4-bit")):
        ys = [thr[f"{prec}_{d}dec"] for d in range(4)]
        ax.plot(xs, ys, marker=mk, ms=5, mfc="none", ls="-", lw=0.8, label=f"rendering step, {lab}")
    ks = [2, 3, 4, 5, 6, 12]
    ax.plot([AFFORDED[k] for k in ks], [thr[f"full_3dec_{k}tok"] for k in ks], marker="D", ms=4, ls="--", lw=0.8,
            label="report length, bfloat16")
    lo, hi = 3e-4, 3.0
    ax.plot([lo, hi], [lo, hi], color="0.6", lw=0.6, ls=":", label="threshold = budget")
    ax.plot([lo, hi], [0.87 * lo, 0.87 * hi], color="0.3", lw=0.6, ls="-.", label="0.87 of budget")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("budget (rendering step, or report resolution)")
    ax.set_ylabel("threshold (gap at 90% accuracy)")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"thresholds.{ext}", dpi=300)
    plt.close(fig)


def curve(cell):
    return [cell["accuracy_by_gap"][str(g)]["accuracy"] for g in gaps]


def fig_accuracy():
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.6), sharey=True)
    ax = axes[0]
    for d, mk in zip(range(4), ("o", "s", "^", "D")):
        c = next(x for x in cells if x["weight_precision"] == "full" and x["decimals"] == d and x["report_tokens"] == 12)
        ax.plot(gaps, curve(c), marker=mk, ms=3.5, mfc="none", lw=0.8, label=f"{d} decimal{'s' if d != 1 else ''}")
    ax.axhline(0.9, color="0.6", lw=0.6, ls=":")
    ax.set_xscale("log"); ax.set_xlabel("gap between the two consequences"); ax.set_ylabel("accuracy")
    ax.set_title("rendering ladder, bfloat16, 12-token reports", fontsize=8)
    ax.legend(frameon=False, loc="lower right")
    ax = axes[1]
    for k, mk in zip((1, 2, 4, 5, 6), ("v", "o", "s", "^", "D")):
        c = next(x for x in cells if x["weight_precision"] == "full" and x["decimals"] == 3 and x["report_tokens"] == k)
        ax.plot(gaps, curve(c), marker=mk, ms=3.5, mfc="none", lw=0.8, label=f"{k} token{'s' if k > 1 else ''}")
    ax.axhline(0.9, color="0.6", lw=0.6, ls=":")
    ax.set_xscale("log"); ax.set_xlabel("gap between the two consequences")
    ax.set_title("report ladder, bfloat16, 3 decimals", fontsize=8)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"accuracy.{ext}", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    fig_thresholds()   # figures/accuracy.* is produced by channel_fit.py, which overlays the grid-channel law
    print("wrote", sorted(p.name for p in OUT.iterdir()))
