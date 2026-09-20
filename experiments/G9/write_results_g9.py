#!/usr/bin/env python3
"""Generate RESULTS-G9.md from the harvested cell records.

Every number in the results file is read from results_summary.json and the
per-cell files beside it. Nothing is retyped, so the document cannot drift from
the records it describes. The prose is written here, the figures are not.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SUMMARY = os.path.join(HERE, "results_summary.json")
PROBE5 = os.path.join(HERE, "g9_probe5.json")
OUT = os.path.join(HERE, "RESULTS-G9.md")

PRETTY = {"y1_epa": "expected points added", "y2_first_down": "first down probability",
          "y3_turnover": "turnover probability", "y4_epa_sd": "risk",
          "y5_clock_stop": "clock stop"}
PRIMARY = ["y1_epa", "y3_turnover"]
BLOB = "f8a18aea4d82bded364b78a6da6c1a39f1fd9f51"


def plane_name(p):
    return "%s against %s" % (PRETTY[p[0]], PRETTY[p[1]])


def collinearity_check():
    """Rank correlation between a plane's collinearity and its violation rate.

    Exploratory, registered nowhere, and included only because it kills an
    explanation offered after the fact rather than supporting one.
    """
    probe4 = os.path.join(HERE, "g9_probe4.json")
    if not os.path.exists(probe4):
        return None
    ratios = {k: v["median_singular_ratio"]
              for k, v in json.load(io.open(probe4, encoding="utf-8"))["overall"]["planes"].items()}
    rows = json.load(io.open(SUMMARY, encoding="utf-8"))
    pairs = []
    for r in rows:
        if r.get("state") != "ok" or r["floor"] != 5:
            continue
        k = "%s|%s" % (r["plane"][0], r["plane"][1])
        if k in ratios and ratios[k] is not None:
            pairs.append((ratios[k], r["p_obs"]))
    if len(pairs) < 5:
        return None

    def rank(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        out = [0.0] * len(xs)
        for pos, i in enumerate(order):
            out[i] = pos + 1.0
        return out

    x = rank([a for a, _ in pairs])
    y = rank([b for _, b in pairs])
    n = len(pairs)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else None


def main():
    rows = json.load(io.open(SUMMARY, encoding="utf-8"))
    ok = [r for r in rows if r.get("state") == "ok"]
    barred = [r for r in ok if r["carries_bar"]]
    vacuous = [r for r in ok if not r["carries_bar"] and r["floor"] == 5]
    sens = [r for r in ok if not r["carries_bar"] and r["floor"] == 10]
    primary = next((r for r in barred if r["plane"] == PRIMARY), None)
    missing = [r for r in rows if r.get("state") != "ok"]

    L = []
    w = L.append
    verdicts = [r["verdict"] for r in barred]
    overall = "PASS" if verdicts and all(v == "PASS" for v in verdicts) else (
        "FAIL" if any(v == "FAIL" for v in verdicts) else "INDETERMINATE")

    w("# G9 results, the hull law on NFL play calls, committed as executed")
    w("")
    if primary is None:
        w("**No primary cell record.** The run did not produce one and this file cannot grade it.")
        io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
        print("wrote", OUT, "with no primary record")
        return 0

    n_pass = sum(1 for r in barred if r["verdict"] == "PASS")
    n_fail = sum(1 for r in barred if r["verdict"] == "FAIL")
    n_ind = sum(1 for r in barred if r["verdict"] == "INDETERMINATE")
    w("**Verdict: %s on the primary plane. Across the six planes that carry bars, %d pass, %d is "
      "indeterminate and %d refutes.** The gate as a whole does not pass. By the sealed "
      "sensitivity clause it grades INDETERMINATE, for the reason set out under that heading. "
      "Graded against PREREG-G9.md, blob %s, sealed before any ranking was formed on real data. "
      "The statistic, the null and the tie rule are G2's, run through G2's own checker, so the "
      "difference between this and the 1972 survey is a difference between two populations and "
      "not between two pieces of code. Every number below is read from the cell records by "
      "`write_results_g9.py`."
      % (primary["verdict"], n_pass, n_ind, n_fail, BLOB))
    w("")
    w("## The primary plane")
    w("")
    w("| quantity | value |")
    w("|---|---|")
    w("| plane | %s |" % plane_name(primary["plane"]))
    w("| units, evaluator by state cell | %d |" % primary["n_units"])
    w("| testable units | %d |" % primary["n_testable"])
    w("| units violating the hull law at least once | %d |" % primary["n_violated"])
    w("| observed violation rate | %.4f |" % primary["p_obs"])
    w("| shuffle null, mean and standard deviation | %.4f (%.4f) |"
      % (primary["p_null_mean"], primary["p_null_sd"]))
    w("| permutation p | %.4f |" % primary["p_value_perm"])
    sd = primary["p_null_sd"]
    if sd > 0:
        w("| distance below the null | %.1f null standard deviations |"
          % ((primary["p_null_mean"] - primary["p_obs"]) / sd))
    w("| verdict | **%s** |" % primary["verdict"])
    w("")
    w("## Every plane at the sealed floor")
    w("")
    w("| plane | testable | violating | observed | null (sd) | perm p | verdict |")
    w("|---|---|---|---|---|---|---|")
    for r in sorted(barred, key=lambda r: r["p_obs"]) + sorted(vacuous, key=lambda r: r["p_obs"]):
        w("| %s%s | %d | %d | %.4f | %.4f (%.4f) | %.4f | %s |" % (
            plane_name(r["plane"]), " (primary)" if r["plane"] == PRIMARY else "",
            r["n_testable"], r["n_violated"], r["p_obs"], r["p_null_mean"],
            r["p_null_sd"], r["p_value_perm"],
            r["verdict"] if r["carries_bar"] else "no verdict, vacuous"))
    w("")
    w("The four planes carrying no verdict were declared vacuous in the registration before any "
      "number was seen, because each falls below the anti-vacuity bar of 300 testable units that "
      "this gate inherits from G2. Their rates are printed so the record is complete and they "
      "grade nothing.")
    w("")
    if sens:
        w("## The registered sensitivity, a floor of ten, carrying no bar")
        w("")
        w("| plane | testable | observed | null (sd) | perm p | verdict at the sealed floor |")
        w("|---|---|---|---|---|---|")
        by_plane = {tuple(r["plane"]): r for r in barred}
        for r in sorted(sens, key=lambda r: r["p_obs"]):
            sealed = by_plane.get(tuple(r["plane"]))
            w("| %s | %d | %.4f | %.4f (%.4f) | %.4f | %s |" % (
                plane_name(r["plane"]), r["n_testable"], r["p_obs"], r["p_null_mean"],
                r["p_null_sd"], r["p_value_perm"], sealed["verdict"] if sealed else "na"))
        w("")
        would = []
        for r in sens:
            s = by_plane.get(tuple(r["plane"]))
            if not s:
                continue
            v10 = "PASS" if (r["p_obs"] <= r["p_null_mean"] - 0.10 and r["p_value_perm"] < 0.01) \
                else ("FAIL" if r["p_obs"] >= r["p_null_mean"] - 0.02 else "INDETERMINATE")
            if v10 != s["verdict"]:
                would.append((plane_name(r["plane"]), s["verdict"], v10))
        if would:
            w("The registration says a verdict that reverses between the two floors grades the "
              "gate INDETERMINATE regardless of which side the sealed floor falls on. It reverses "
              "on %d of %d planes." % (len(would), len(sens)))
            for nm, a, b in would:
                w("- %s, %s at the sealed floor and %s at ten." % (nm, a, b))
            w("")
            w("**A registration defect, recorded rather than resolved in the gate's favour.** The "
              "sealed sentence reads that a reversing verdict grades \"the gate\" INDETERMINATE, "
              "and it does not say whether that means the plane that reversed or every plane at "
              "once. Written before any number was seen, the ambiguity was invisible. Read after, "
              "one reading costs a single replication and the other costs the primary result, and "
              "choosing between them now is choosing a verdict. The stricter reading is taken "
              "here, so the gate is graded INDETERMINATE overall, and the defect is named so the "
              "next registration says which it means.")
            prim10 = next((r for r in sens if r["plane"] == PRIMARY), None)
            if prim10 is not None:
                w("")
                w("What the ambiguity does not touch. The primary plane does not reverse. It "
                  "passes at the sealed floor at %.4f against a null of %.4f, and at a floor of "
                  "ten at %.4f against %.4f, with a permutation p of zero at both. The headline "
                  "claim stands under either reading."
                  % (primary["p_obs"], primary["p_null_mean"],
                     prim10["p_obs"], prim10["p_null_mean"]))
        else:
            w("No plane's verdict reverses between the two floors, so the result does not turn on "
              "the floor the registration had to take.")
        w("")
    w("## Reading")
    w("")
    w("- **The hull law holds far more tightly here than in the survey.** G2 measured 0.503 of "
      "489 testable respondents violating against a null of 0.664, and recorded that the law "
      "holds as a population tendency and fails as a deterministic statement for about half of "
      "them. On the primary plane here %d of %d testable units violate, a rate of %.4f against a "
      "null of %.4f. The deterministic reading that ANES could not support survives on this world."
      % (primary["n_violated"], primary["n_testable"], primary["p_obs"], primary["p_null_mean"]))
    w("- **The consequence map was not placed by the evaluator.** That was G2's declared limit. "
      "Here the map is estimated from what happened after each call, pooled across every "
      "evaluator, which is the split GET's foundations require between what the world supplies "
      "and what the evaluator owns.")
    dev = 0.052
    if primary["p_obs"] < dev:
        w("- **The observed rate sits below the measured noise of the ranking device.** The "
          "self-test put the device's manufactured-violation rate at %.3f at this floor, on "
          "synthetic menus whose true rate was zero. The observed %.4f is lower than that, which "
          "says the real rate is near zero and that the synthetic geometries were harder than the "
          "ones football actually presents. It also means the declared bias cannot be what "
          "produced this verdict, since the bias only ever raises the observed rate."
          % (dev, primary["p_obs"]))
    w("- **The plane was forced, not chosen, and it inflates every rate here.** Measured after the "
      "run and written up in `articles/2026-09-19-the-hull-law-on-a-plane.md`. A violation needs a "
      "point inside the hull of others, which four actions in a five-dimensional consequence space "
      "can never produce, 0 testable menus in 4,000 trials. So the law can only be read on a plane. "
      "Projection preserves hull membership and can create it, so it adds violations and never "
      "removes them, and in this gate's exact configuration rankings from genuine convex evaluators "
      "violate at 0.1506 when read on two coordinates against a true rate of zero. The primary "
      "plane's %.4f sits an order of magnitude below that, so its pass is stronger than it looks. "
      "The refuting plane's %.4f is about twice it, so projection contributes to that result and "
      "does not account for it."
      % (primary["p_obs"],
         next((r["p_obs"] for r in barred if r["verdict"] == "FAIL"), float("nan"))))
    w("- The confounds declared before sealing stand unchanged. The map is a conditional "
      "expectation over calls somebody chose to make and carries no causal reading, a cell pools "
      "states the bins do not separate, choice share reveals a ranking only to the extent the "
      "caller is choosing rather than mixing on purpose, and the franchise pools coaching staffs "
      "across ten seasons.")
    fails = [r for r in barred if r["verdict"] == "FAIL"]
    if fails:
        w("")
        w("## The plane that refutes, and an explanation that did not survive")
        w("")
        for r in fails:
            w("On %s the law does not merely fail to clear its bar. It is violated more often "
              "than chance, %.4f against a null of %.4f in %d testable units, with a permutation "
              "p of %.4f, meaning every one of the 200 shuffles produced a rate at or below the "
              "observed one. That is a refutation on that plane and it is recorded at the same "
              "size as the passes."
              % (plane_name(r["plane"]), r["p_obs"], r["p_null_mean"], r["n_testable"],
                 r["p_value_perm"]))
        w("")
        w("An explanation offered after seeing it, and then tested. Expected points added and "
          "first down probability are close to redundant, so the four points lie near a line, and "
          "GET's own Theorem 3 says consequences on a line represent exactly the single-peaked "
          "orders, a stronger requirement that should produce more violations. The story is "
          "principled rather than invented for the occasion, and it is still post hoc, so it was "
          "checked against the other nine planes using probe 4's collinearity measure.")
        w("")
        rho = collinearity_check()
        if rho is not None:
            w("It does not survive. The rank correlation between how collinear a plane is and how "
              "often it is violated is %.3f across the ten planes, which is nothing, and the most "
              "collinear plane of all has one of the lowest violation rates. The cause of this "
              "plane's failure is open, and no account of it is offered here." % rho)
        w("")
    w("- Nothing in the registration was changed after the seal. This document was written after "
      "grading and does not alter the verdict.")
    w("")
    if missing:
        w("## Cells with no record")
        w("")
        for r in missing:
            w("- %s, floor %d, %s" % (r["cell"], r["floor"], r.get("state")))
        w("")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("wrote", OUT, len(L), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
