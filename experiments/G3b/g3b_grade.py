"""Grade a G3b run against the bars of PREREG-G3B, or report the pilot statistics that fix them.

Every quantity is derived from the persisted generations and the seed, never from a summary
written by the harness:

* pairs are regenerated from the config and the seed with the harness's own ``make_pairs``;
* a pair's preference in a report cell at budget k compares the numbers parsed from the two
  values' generations truncated to their first k tokens (the recorded prefixes);
* the reference evaluator computes the exact consequence of the rendered inputs, rounds it to
  three decimals, and floors it to the report grid of the model at budget k.

Per cell the accuracy curve is fitted by the grid-channel law with a floor and a plateau,

    acc(gap) = c0 + (c1 - c0) * min(1, gap / h),

by least squares over h on a log grid with (c0, c1) solved exactly at each h. ``h_hat`` is the
step, ``1 - c1`` the lapse. Intervals come from a paired bootstrap that resamples the pairs of
each gap with the same indices in every cell of a task, so ratios between cells (a 4-bit judge
against its bfloat16 self) carry the pairing.

    python g3b_grade.py RESULTS_DIR --pilot            statistics only, no verdicts
    python g3b_grade.py RESULTS_DIR --out grade.json   verdicts against the sealed bars
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g3b  # noqa: E402

REQUIRED_BARS = ("anti_vacuity_acc_gap20", "floor_max", "h_ratio_factor", "law_max_abs_dev",
                 "weights_step_factor", "delta_min_factor", "p3_min_acc", "p3_min_gaps")


# ----------------------------------------------------------------------------- fit

def fit_curves(acc: np.ndarray, gaps: np.ndarray, n_grid: int = 240, n_refine: int = 40) -> dict:
    """Least squares of acc[N, G] on c0 + (c1 - c0) min(1, gap/h). Returns arrays over N."""
    acc = np.atleast_2d(acc).astype(float)
    lo, hi = gaps.min() / 8.0, gaps.max() * 8.0

    def solve(hs):
        m = np.minimum(1.0, gaps[None, :] / hs[:, None])              # [H, G]
        X = np.stack([1.0 - m, m], axis=-1)                            # [H, G, 2]
        XtX = np.einsum("hgi,hgj->hij", X, X) + 1e-9 * np.eye(2)
        inv = np.linalg.inv(XtX)                                       # [H, 2, 2]
        Xty = np.einsum("hgi,ng->nhi", X, acc)                         # [N, H, 2]
        coef = np.einsum("hij,nhj->nhi", inv, Xty)                     # [N, H, 2]
        pred = np.einsum("hgi,nhi->nhg", X, coef)                      # [N, H, G]
        sse = ((pred - acc[:, None, :]) ** 2).sum(-1)                  # [N, H]
        return coef, sse

    hs = np.exp(np.linspace(np.log(lo), np.log(hi), n_grid))
    coef, sse = solve(hs)
    j = sse.argmin(1)
    step = np.log(hs[1] / hs[0])
    h_out = np.empty(acc.shape[0]); c0 = np.empty(acc.shape[0]); c1 = np.empty(acc.shape[0]); s_out = np.empty(acc.shape[0])
    for jj in np.unique(j):
        rows = np.where(j == jj)[0]
        fine = np.exp(np.linspace(np.log(hs[jj]) - 2 * step, np.log(hs[jj]) + 2 * step, n_refine))
        cf, sf = solve(fine)
        cf, sf = cf[rows], sf[rows]
        k = sf.argmin(1)
        h_out[rows] = fine[k]
        c0[rows] = cf[np.arange(len(rows)), k, 0]
        c1[rows] = cf[np.arange(len(rows)), k, 1]
        s_out[rows] = sf[np.arange(len(rows)), k]
    censored = np.where(h_out < gaps.min(), -1, np.where(h_out > gaps.max(), 1, 0))
    return {"h": h_out, "c0": c0, "c1": c1, "sse": s_out, "censored": censored}


def threshold_09(acc: np.ndarray, gaps: np.ndarray, level: float = 0.9) -> float:
    """G3's statistic, kept for continuity and not graded."""
    for i in range(len(gaps)):
        if acc[i] >= level:
            if i == 0:
                return float(gaps[0])
            if acc[i] == acc[i - 1]:
                return float(gaps[i])
            t = (level - acc[i - 1]) / (acc[i] - acc[i - 1])
            return float(np.exp(np.log(gaps[i - 1]) + t * (np.log(gaps[i]) - np.log(gaps[i - 1]))))
    return float("inf")


# ----------------------------------------------------------------------------- data

def load(results_dir: str, cfg_path: str | None = None) -> tuple[dict, dict]:
    d = Path(results_dir)
    res = json.load(open(d / "results.json"))
    cfg = json.load(open(cfg_path)) if cfg_path else res.get("config")
    if cfg is None:
        raise SystemExit("config not in results.json; pass --config")
    return res, cfg


def report_grid(cfg: dict, model_key: str) -> dict[int, float]:
    spec = g3b.model_specs(cfg)[model_key]
    budgets = [int(b) for b in cfg["report_token_budgets"]]
    grid = spec.get("report_grid")
    if grid:
        return {int(k): float(v) for k, v in grid.items()}
    split = g3b.split_group3 if spec.get("synthetic", {}).get("tokenizer") == "group3" else g3b.split_char
    return g3b.afforded_steps(split("27.375"), budgets)


def cell_views(res: dict, cfg: dict, results_dir: str) -> tuple[list[dict], dict]:
    """Expand generation cells into report cells (one per budget) with pair-level judge and
    reference preferences, in pair order."""
    budgets = [int(b) for b in cfg["report_token_budgets"]]
    seed = int(res["seed"])
    pairs = {t: g3b.make_pairs(cfg, t, seed) for t in sorted({c["task"] for c in res["cells"]})}
    views = []
    for c in res["cells"]:
        gens = {}
        with gzip.open(Path(results_dir) / c["gens_file"], "rt", encoding="utf-8") as f:
            for line in f:
                g = json.loads(line)
                gens[g["value"]] = g
        grid = report_grid(cfg, c["model"])
        char_grid = g3b.afforded_steps(g3b.split_char("27.375"), budgets)
        ps = pairs[c["task"]]
        tstr = c["target"]
        cs = [g3b.render_value(c["task"], p["close"], c["dec"]) for p in ps]
        fs = [g3b.render_value(c["task"], p["far"], c["dec"]) for p in ps]
        exact_c = np.array([round(g3b.consequence_of_rendered(c["task"], tstr, v) * 1000) for v in cs], dtype=np.int64)
        exact_f = np.array([round(g3b.consequence_of_rendered(c["task"], tstr, v) * 1000) for v in fs], dtype=np.int64)
        for k in budgets:
            a = np.array([g3b.parse_report(gens[v]["prefix"][str(k)]) for v in cs])
            b = np.array([g3b.parse_report(gens[v]["prefix"][str(k)]) for v in fs])
            pref = np.where(np.isnan(a) | np.isnan(b) | (a == b), 0.5, np.where(a < b, 1.0, 0.0))
            def reference(step):
                if not math.isfinite(step):
                    return np.full(len(ps), 0.5)
                S = max(1, int(round(step * 1000)))
                qa, qb = exact_c // S, exact_f // S
                return np.where(qa == qb, 0.5, np.where(qa < qb, 1.0, 0.0))
            step = grid[k]
            ref = reference(step)
            alt = reference(char_grid[k]) if char_grid.get(k) != step else None
            views.append({"gen_id": c["id"], "model": c["model"], "precision": c["precision"], "task": c["task"],
                          "dec": c["dec"], "k": k, "report_step": step,
                          "correct": pref > 0.5, "ref_correct": ref > 0.5,
                          "alt_correct": None if alt is None else alt > 0.5, "alt_step": char_grid.get(k),
                          "unparsed": int(np.isnan(a).sum() + np.isnan(b).sum()),
                          "stopped_early_share": float(np.mean([gens[v]["stopped_early"] for v in cs + fs]))})
    gap_of = {t: np.array([p["gap"] for p in ps]) for t, ps in pairs.items()}
    return views, gap_of


def classify(v: dict, cfg: dict) -> dict:
    """Which cells are registered, what grid is set on the consequence, and how they are graded."""
    full_k = int(cfg["full_report_tokens"])
    if v["task"] == "A" and v["k"] == full_k:
        return {"registered": True, "kind": "A_render", "h_set": max(10.0 ** -v["dec"], v["report_step"]), "h_graded": True}
    if v["task"] == "A" and v["precision"] == "full" and v["dec"] == 3:
        return {"registered": True, "kind": "A_report", "h_set": max(0.001, v["report_step"]), "h_graded": True}
    if v["task"] == "B" and v["precision"] == "full" and v["dec"] == 3:
        return {"registered": True, "kind": "B_report", "h_set": max(0.001, v["report_step"]), "h_graded": True}
    if v["task"] == "B" and v["precision"] == "full" and v["k"] == full_k:
        # the grid is on the coordinates, not on the distance; graded against the reference only
        return {"registered": True, "kind": "B_render", "h_set": 10.0 ** -v["dec"], "h_graded": True}
    return {"registered": False, "kind": "derived", "h_set": max(10.0 ** -v["dec"], v["report_step"]), "h_graded": False}


# ----------------------------------------------------------------------------- analysis

def analyse(res: dict, cfg: dict, results_dir: str, n_boot: int = 1000, seed: int = 20260918) -> dict:
    views, gap_of = cell_views(res, cfg, results_dir)
    gaps_all = np.array(sorted(float(g) for g in cfg["gap_ladder"]))
    n = int(cfg["n_pairs_per_gap"])
    full_k = int(cfg["full_report_tokens"])
    for v in views:
        v.update(classify(v, cfg))
        v["id"] = f"{v['gen_id']}__k{v['k']}"
        g = gap_of[v["task"]]
        v["acc"] = np.array([v["correct"][g == x].mean() for x in gaps_all])
        v["ref_acc"] = np.array([v["ref_correct"][g == x].mean() for x in gaps_all])
        v["alt_acc"] = None if v["alt_correct"] is None else np.array([v["alt_correct"][g == x].mean() for x in gaps_all])
    keep = [v for v in views if v["registered"]]
    # point fits: the judge, the reference evaluator on the same pairs, and where the model's
    # report grid differs from one character per token, the reference under that other grid
    F = fit_curves(np.stack([v["acc"] for v in keep]), gaps_all)
    R = fit_curves(np.stack([v["ref_acc"] for v in keep]), gaps_all)
    for i, v in enumerate(keep):
        v["h_ref"] = float(R["h"][i])
        v["h_alt"] = float(fit_curves(v["alt_acc"][None, :], gaps_all)["h"][0]) if v["alt_acc"] is not None else None
    for i, v in enumerate(keep):
        v["h_hat"], v["c0"], v["c1"], v["censored"] = float(F["h"][i]), float(F["c0"][i]), float(F["c1"][i]), int(F["censored"][i])
        v["lapse"] = 1.0 - v["c1"]
        v["threshold_09"] = threshold_09(v["acc"], gaps_all)
        hi_m = v["ref_acc"] >= 0.999; lo_m = v["ref_acc"] <= 0.001
        c1e = float(v["acc"][hi_m].mean()) if hi_m.any() else 1.0
        c0e = float(v["acc"][lo_m].mean()) if lo_m.any() else 0.0
        pred = c0e + (c1e - c0e) * v["ref_acc"]
        v["law_dev"] = float(np.max(np.abs(v["acc"] - pred)))
        v["law_dev_gap"] = float(gaps_all[int(np.argmax(np.abs(v["acc"] - pred)))])
    # paired bootstrap per task: the same resampled pair indices in every cell of the task
    rng = np.random.default_rng(seed)
    boot = {}
    for task in sorted({v["task"] for v in keep}):
        tv = [v for v in keep if v["task"] == task]
        g = gap_of[task]
        B_acc = np.empty((len(tv), n_boot, len(gaps_all)))
        B_ref = np.empty((len(tv), n_boot, len(gaps_all)))
        for gi, x in enumerate(gaps_all):
            idx_rows = np.where(g == x)[0]
            draw = rng.integers(0, len(idx_rows), size=(n_boot, len(idx_rows)))
            for ci, v in enumerate(tv):
                B_acc[ci, :, gi] = v["correct"][idx_rows][draw].mean(1)
                B_ref[ci, :, gi] = v["ref_correct"][idx_rows][draw].mean(1)

        def fit_all(arr):
            flat = arr.reshape(-1, len(gaps_all))
            hs, c1s = np.empty(flat.shape[0]), np.empty(flat.shape[0])
            for s in range(0, flat.shape[0], 4000):
                ff = fit_curves(flat[s:s + 4000], gaps_all)
                hs[s:s + 4000], c1s[s:s + 4000] = ff["h"], ff["c1"]
            return hs.reshape(len(tv), n_boot), c1s.reshape(len(tv), n_boot)

        hs, c1s = fit_all(B_acc)
        hr, _ = fit_all(B_ref)
        for ci, v in enumerate(tv):
            v["h_ci"] = [float(np.percentile(hs[ci], 2.5)), float(np.percentile(hs[ci], 97.5))]
            v["lapse_ci"] = [float(np.percentile(1 - c1s[ci], 2.5)), float(np.percentile(1 - c1s[ci], 97.5))]
            ratio = hs[ci] / hr[ci]
            v["ratio_ref_ci"] = [float(np.percentile(ratio, 2.5)), float(np.percentile(ratio, 97.5))]
            boot[v["id"]] = (hs[ci], 1 - c1s[ci])
    # floors per (model, task): the full-precision, 3-decimal, full-report cell
    floors = {}
    for v in keep:
        if v["precision"] == "full" and v["dec"] == 3 and v["k"] == full_k:
            fl = v["h_hat"] if v["censored"] >= 0 else float(gaps_all.min())
            floors[(v["model"], v["task"])] = {"floor": max(fl, float(gaps_all.min())),
                                               "acc_gap20": float(v["acc"][gaps_all == 20.0][0]) if 20.0 in gaps_all else None,
                                               "cell": v["id"]}
    for v in keep:
        fl = floors.get((v["model"], v["task"]), {}).get("floor", float(gaps_all.min()))
        scale = v["h_set"]
        v["above_floor"] = bool(scale >= 3.0 * fl) and v["id"] != floors.get((v["model"], v["task"]), {}).get("cell")
    return {"views": keep, "boot": boot, "floors": floors, "gaps": gaps_all, "n": n}


# ----------------------------------------------------------------------------- verdicts

def verdicts(A: dict, cfg: dict, bars: dict) -> dict:
    views, boot, floors, gaps = A["views"], A["boot"], A["floors"], A["gaps"]
    full_k = int(cfg["full_report_tokens"])
    char_grid = g3b.afforded_steps(g3b.split_char("27.375"), [int(b) for b in cfg["report_token_budgets"]])
    out = {"bars": bars, "anti_vacuity": {}, "GET-11b": {}, "GET-11c": {}, "GET-11d": {}, "GET-11e": {}}
    vacuous = set()
    for (m, t), f in floors.items():
        ok = (f["acc_gap20"] is not None and f["acc_gap20"] >= bars["anti_vacuity_acc_gap20"]
              and f["floor"] <= bars["floor_max"])
        out["anti_vacuity"][f"{m}/{t}"] = {**f, "holds": bool(ok)}
        if not ok:
            vacuous.add((m, t))
    Fh, law = bars["h_ratio_factor"], bars["law_max_abs_dev"]
    for (m, t) in floors:
        key = f"{m}/{t}"
        if (m, t) in vacuous:
            out["GET-11b"][key] = {"verdict": "VACUOUS"}
            continue
        cells = [v for v in views if v["model"] == m and v["task"] == t and v["above_floor"]
                 and (v["precision"] == "full" or v["kind"] == "A_render")]
        recs, fail, indet = {}, False, False
        for v in cells:
            r = {"kind": v["kind"], "law_dev": round(v["law_dev"], 4), "law_ok": v["law_dev"] <= law}
            if v["h_graded"]:
                # the judge's fitted step against the reference evaluator's fitted step on the same
                # pairs, with a paired interval; the nominal step is recorded beside it
                ratio = v["h_hat"] / v["h_ref"]
                r.update({"h_set": v["h_set"], "h_ref": v["h_ref"], "h_hat": v["h_hat"], "ratio_to_ref": round(ratio, 4),
                          "ratio_to_ref_ci": v["ratio_ref_ci"], "ratio_to_nominal": round(v["h_hat"] / v["h_set"], 4),
                          "ratio_ok": 1 / Fh <= ratio <= Fh,
                          "ci_contains_1": v["ratio_ref_ci"][0] <= 1.0 <= v["ratio_ref_ci"][1]})
                fail |= not r["ratio_ok"]
                indet |= r["ratio_ok"] and not r["ci_contains_1"]
            fail |= not r["law_ok"]
            recs[v["id"]] = r
        out["GET-11b"][key] = {"cells": recs, "n_cells": len(recs),
                               "verdict": "FAIL" if fail else ("INDETERMINATE" if indet or not recs else "PASS")}
    Fw, dmin = bars["weights_step_factor"], bars["delta_min_factor"]
    for m in sorted({v["model"] for v in views}):
        if (m, "A") in vacuous:
            out["GET-11c"][m] = {"verdict": "VACUOUS"}
            continue
        base = {v["dec"]: v for v in views if v["model"] == m and v["task"] == "A" and v["k"] == full_k
                and v["precision"] == "full"}
        recs, fail, all_equiv = {}, False, True
        for v in views:
            # the floor cell is included: G3's weight ladder was graded at the floor, and that is
            # where its 4-bit lapse appeared
            if v["model"] != m or v["task"] != "A" or v["k"] != full_k or v["precision"] == "full":
                continue
            b = base[v["dec"]]
            rb = boot[v["id"]][0] / boot[b["id"]][0]
            lb = boot[v["id"]][1] - boot[b["id"]][1]
            ratio = v["h_hat"] / b["h_hat"]
            ci = [float(np.percentile(rb, 2.5)), float(np.percentile(rb, 97.5))]
            equiv = 1 / dmin <= ci[0] and ci[1] <= dmin
            recs[v["id"]] = {"step_ratio_to_full": round(ratio, 4), "ratio_ci": ci, "equivalent": bool(equiv),
                             "lapse": round(v["lapse"], 4), "lapse_full": round(b["lapse"], 4),
                             "lapse_diff_ci": [float(np.percentile(lb, 2.5)), float(np.percentile(lb, 97.5))]}
            fail |= not (1 / Fw <= ratio <= Fw)
            all_equiv &= equiv
        out["GET-11c"][m] = {"cells": recs, "verdict": ("NOT RUN" if not recs else
                                                         "FAIL" if fail else "PASS" if all_equiv else "INDETERMINATE")}
    for m in sorted({v["model"] for v in views}):
        grid = report_grid(cfg, m)
        diff_k = [k for k in grid if math.isfinite(grid[k]) and grid[k] != char_grid.get(k)]
        if not diff_k:
            continue
        recs, ok_all = {}, True
        for v in views:
            if (v["model"] == m and v["kind"] in ("A_report", "B_report") and v["k"] in diff_k and v["above_floor"]
                    and v["h_alt"] is not None):
                # the judge against the reference under its own tokenizer's grid, and against the
                # reference under the one-character grid, both on the same pairs
                own = 1 / Fh <= v["h_hat"] / v["h_ref"] <= Fh
                away = not (1 / Fh <= v["h_hat"] / v["h_alt"] <= Fh)
                recs[v["id"]] = {"h_hat": v["h_hat"], "h_ref_own_grid": v["h_ref"], "h_ref_char_grid": v["h_alt"],
                                 "own_step": grid[v["k"]], "char_step": char_grid[v["k"]],
                                 "matches_own": own, "rejects_char": away}
                ok_all &= own and away
        out["GET-11d"][m] = {"cells": recs, "verdict": "NOT RUN" if not recs else ("PASS" if ok_all else "FAIL")}
    if not out["GET-11d"]:
        out["GET-11d"]["_"] = {"verdict": "NOT RUN", "reason": "no model with a report grid that differs from one character per token"}
    graded = [v for v in views if v["h_graded"] and v["above_floor"] and (v["model"], v["task"]) not in vacuous]
    p3a, fail_a = {}, False
    for v in graded:
        sel = gaps >= 2 * v["h_set"]
        if sel.any():
            worst = float(v["acc"][sel].min())
            p3a[v["id"]] = {"n_gaps": int(sel.sum()), "worst": worst, "holds": worst >= bars["p3_min_acc"]}
            fail_a |= worst < bars["p3_min_acc"]
    gstar = 2 * max((v["h_set"] for v in graded), default=float("inf"))
    sep = gaps[gaps >= gstar]
    worst_b = min((float(v["acc"][gaps >= gstar].min()) for v in graded), default=float("nan")) if len(sep) else float("nan")
    ok_b = len(sep) >= bars["p3_min_gaps"] and worst_b >= bars["p3_min_acc"]
    out["GET-11e"] = {"per_cell": p3a, "cross_cell": {"gap_min": gstar, "gaps": sep.tolist(), "worst": worst_b, "holds": bool(ok_b)},
                      "verdict": "PASS" if (not fail_a and ok_b) else "FAIL"}
    vs = [r["verdict"] for key in ("GET-11b", "GET-11c", "GET-11d") for r in out[key].values()] + [out["GET-11e"]["verdict"]]
    core = [x for x in vs if x not in ("NOT RUN", "VACUOUS")]
    out["gate"] = "FAIL" if "FAIL" in core else ("PASS" if core and all(x == "PASS" for x in core) else "INDETERMINATE")
    return out


def table(A: dict) -> list[dict]:
    rows = []
    for v in A["views"]:
        rows.append({"id": v["id"], "kind": v["kind"], "h_set": v["h_set"], "h_hat": round(v["h_hat"], 6),
                     "h_ref": round(v["h_ref"], 6), "ratio_to_ref": round(v["h_hat"] / v["h_ref"], 4),
                     "ratio_to_ref_ci": [round(x, 4) for x in v["ratio_ref_ci"]],
                     "ratio": round(v["h_hat"] / v["h_set"], 4) if v["h_set"] else None, "h_ci": [round(x, 6) for x in v["h_ci"]],
                     "lapse": round(v["lapse"], 4), "lapse_ci": [round(x, 4) for x in v["lapse_ci"]],
                     "c0": round(v["c0"], 4), "law_dev": round(v["law_dev"], 4), "law_dev_gap": v["law_dev_gap"],
                     "threshold_09": v["threshold_09"], "above_floor": v["above_floor"], "censored": v["censored"],
                     "unparsed": v["unparsed"], "stopped_early_share": round(v["stopped_early_share"], 3),
                     "acc": [round(float(x), 3) for x in v["acc"]]})
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--config")
    ap.add_argument("--pilot", action="store_true", help="statistics only; bars may be unset")
    ap.add_argument("--out", default=None)
    ap.add_argument("--boot", type=int, default=1000)
    a = ap.parse_args(argv)
    res, cfg = load(a.results_dir, a.config)
    A = analyse(res, cfg, a.results_dir, n_boot=a.boot)
    report = {"role": res.get("role"), "seed": res.get("seed"), "n_cells": len(A["views"]),
              "floors": {f"{m}/{t}": f for (m, t), f in A["floors"].items()}, "cells": table(A)}
    bars = cfg.get("bars", {})
    missing = [b for b in REQUIRED_BARS if bars.get(b) is None]
    if a.pilot:
        report["verdicts"] = None
        report["bars_unset"] = missing
    else:
        if missing:
            raise SystemExit(f"bars not fixed: {missing}; run with --pilot or fix them from the pilot first")
        report["verdicts"] = verdicts(A, cfg, bars)
        print("GATE", report["verdicts"]["gate"])
    out = a.out or str(Path(a.results_dir) / ("pilot_stats.json" if a.pilot else "grade.json"))
    json.dump(report, open(out, "w"), indent=1, default=float)
    for r in report["cells"]:
        print(f"{r['id']:34s} {r['kind']:9s} set {r['h_set']:<8g} ref {r['h_ref']:<10.5g} hat {r['h_hat']:<10.5g} to_ref {r['ratio_to_ref']!s:7s} "
              f"lapse {r['lapse']:.3f} law {r['law_dev']:.3f} {'' if r['above_floor'] else '(floor)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
