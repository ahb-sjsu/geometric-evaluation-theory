"""Figures for the ICLR paper from the graded records of G3c and G3d. Nothing is fitted here.

    python build/make_v2_figures.py

Figure 1, prediction before measurement. Left, the 7B judge's accuracy against the gap on the 0 to
100 scale, three read-outs, with the calibration's prediction drawn as a line and the sealed test
block as points. Right, every read-out of every graded judge, predicted threshold against observed,
54 points on the diagonal, with the nominal-scale rival's predictions shown where they fall.

Figure 2, the three regimes on one budget. The reversal cell's pair log-odds at three budgets,
from the sealed G3d test block, with the prediction from the calibration marked.

Figure 3, the crossover. The share of test pairs preferring the better worksheet against the
reasoning budget, the calibration's prediction, and the predicted and observed crossing points.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
ROOT = PAPER.parents[1]
G3C = ROOT / "experiments" / "G3c" / "run_record"
G3D = ROOT / "experiments" / "G3d" / "run_record" / "run"
FIG = PAPER / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "figure.dpi": 300, "savefig.bbox": "tight"})
GRADED = [("qwen7b__full", "Qwen 7B"), ("qwen7b__int4", "Qwen 7B 4-bit"), ("qwen14b__full", "Qwen 14B")]
VACUOUS = [("gemma4b__full", "Gemma 4B"), ("qwen1p5b__full", "Qwen 1.5B")]
READOUTS = [("argmax", "greedy score", "o"), ("expected", "expected score", "s"), ("mean_8", "mean of 8 samples", "^")]


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}")
    plt.close(fig)
    print("wrote", name)


def figure1():
    g = json.load(open(G3C / "grade_qwen7b__full.json"))
    p = json.load(open(G3C / "predictions_qwen7b__full.json"))
    gaps = p["gaps"]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.0, 2.9))
    key = "0-100"
    for name, label, marker in READOUTS:
        pred = np.array(p["scales"][key]["readouts"][name]["acc"])
        sd = np.array(p["scales"][key]["readouts"][name]["acc_sd"])
        obs = np.array(g["observed"]["scales"][key][name]["acc"])
        line, = ax.plot(gaps, pred, "-", lw=1.2, label=f"{label}, predicted")
        ax.fill_between(gaps, pred - 2 * sd, pred + 2 * sd, color=line.get_color(), alpha=0.15, lw=0)
        ax.plot(gaps, obs, marker, ms=4.5, mfc="none", color=line.get_color(), label=f"{label}, observed")
    ax.axhline(0.75, ls=":", c="k", lw=0.8)
    ax.set_xlabel("gap in wrong answers"); ax.set_ylabel("share of pairs ordered correctly")
    ax.set_title("Qwen 7B, scale 0 to 100", fontsize=9)
    ax.set_xticks(gaps); ax.set_ylim(0.45, 1.02); ax.legend(fontsize=6, loc="lower right", ncol=1)

    lim = [0.8, 20]
    for tag, label in GRADED:
        gg = json.load(open(G3C / f"grade_{tag}.json"))["verdicts"]["J1_prediction"]
        xs = [v["predicted_threshold"] for k, v in gg.items() if isinstance(v, dict)]
        ys = [v["observed_threshold"] for k, v in gg.items() if isinstance(v, dict)]
        keep = [(x, y) for x, y in zip(xs, ys) if np.isfinite(x) and np.isfinite(y)]
        bx.plot([x for x, _ in keep], [y for _, y in keep], "o", ms=4, mfc="none", label=label)
    rivals = []
    for tag, _ in GRADED:
        j2 = json.load(open(G3C / f"grade_{tag}.json"))["verdicts"]["J2_effective_vs_nominal"]
        for k, v in j2.items():
            if isinstance(v, dict):
                rivals.append((v["nominal_threshold"], v["observed_threshold"]))
    bx.plot([x for x, _ in rivals], [y for _, y in rivals], "x", ms=5, color="0.35",
            label="nominal scale, the rival")
    bx.plot(lim, lim, "k-", lw=0.8)
    bx.set_xscale("log"); bx.set_yscale("log"); bx.set_xlim(*lim); bx.set_ylim(*lim)
    bx.set_xlabel("predicted threshold (wrong answers)"); bx.set_ylabel("observed threshold")
    bx.set_title("every read-out of every graded judge", fontsize=9)
    bx.legend(fontsize=6, loc="upper left")
    save(fig, "v2_prediction")


def flip_rows():
    with gzip.open(G3D / "test" / "pairs.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def figure2():
    rows = flip_rows()
    pred = json.load(open(G3D / "predictions.json"))
    budgets = pred["budgets"]
    panels = [(0, "no reasoning: reversal"), (256, "reasoning cut off: indifference"),
              (1024, "reasoning completed: distinction")]
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.4), sharey=True)
    for ax, (k, title) in zip(axes, panels):
        L = np.array([r["L"] for r in rows if r["k"] == k and r["cell"] == "reversal"])
        i = budgets.index(k)
        ax.hist(L, bins=np.linspace(-12, 12, 25), color="0.7", edgecolor="0.3", lw=0.5)
        ax.axvline(0, c="k", lw=0.8)
        ax.axvline(pred["reversal"]["mean"][i], c="C0", lw=1.4, ls="--", label="predicted mean")
        ax.axvline(L.mean(), c="C3", lw=1.4, label="observed mean")
        ax.set_title(f"{title}\n{k} tokens", fontsize=8)
        if ax is axes[0]:
            ax.legend(fontsize=6, loc="upper left")
    axes[0].set_ylabel("pairs")
    fig.supxlabel("log-odds for the better worksheet", fontsize=9, y=-0.03)
    save(fig, "v2_regimes")


def figure3():
    pred = json.load(open(G3D / "predictions.json"))
    g = json.load(open(G3D / "grade.json"))
    budgets = np.array(pred["budgets"], float)
    x = np.log2(1 + budgets)
    fig, ax = plt.subplots(figsize=(4.4, 2.6))
    ax.plot(x, pred["reversal"]["share"], "-", lw=1.3, label="predicted")
    ax.plot(x, g["F2_crossover"]["observed_shares"], "o", ms=4.5, mfc="none", color="C3", label="observed")
    ax.axhline(0.5, ls=":", c="k", lw=0.8)
    for v, c, lab in ((g["F2_crossover"]["predicted_log2"], "C0", "predicted crossover"),
                      (g["F2_crossover"]["observed_log2"], "C3", "observed crossover")):
        ax.axvline(v, color=c, ls="--", lw=1.0)
        ax.annotate(f"{lab}\n{2 ** v - 1:.0f} tokens", (v, 0.08 if c == "C0" else 0.3), fontsize=6,
                    ha="right" if c == "C0" else "left", color=c)
    ax.set_xticks(x); ax.set_xticklabels([int(b) for b in budgets], fontsize=7)
    ax.set_xlabel("reasoning budget (tokens)"); ax.set_ylabel("share preferring the better sheet", fontsize=8)
    ax.legend(fontsize=6, loc="upper left")
    save(fig, "v2_crossover")


if __name__ == "__main__":
    figure1(); figure2(); figure3()
