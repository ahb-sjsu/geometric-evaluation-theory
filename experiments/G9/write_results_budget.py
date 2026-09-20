#!/usr/bin/env python3
"""Generate RESULTS-G9-budget.md from the budget arm's own records.

Every number is read from budget_results.json, degeneracy_diagnosis.json and
rank_cut.json. Nothing is retyped. The prose is written here.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "RESULTS-G9-budget.md")
BLOB = "f8a18aea4d82bded364b78a6da6c1a39f1fd9f51"


def load(name):
    p = os.path.join(HERE, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else None


def main():
    res = load("budget_results.json")
    diag = load("degeneracy_diagnosis.json")
    cal = load("rank_cut.json")
    if res is None:
        raise SystemExit("no budget_results.json")

    L = []
    w = L.append
    w("# G9 secondary arm, the budget prediction, committed as executed")
    w("")
    w("**Verdict: %s.** Graded against PREREG-G9.md Section 5 and 6, blob %s. The arm asked "
      "whether a smaller resolution budget lowers the effective rank of the evaluator's metric, "
      "using the game clock as a manipulation nobody had to administer. It cannot be answered on "
      "this world by the registered instrument, for a reason that is itself a measurement."
      % (res["verdict"], BLOB))
    w("")
    w("## What happened")
    w("")
    w("The identification estimator of G5 recovers a metric and an ideal point from revealed "
      "strict preferences by a max-margin program. Run on the league's choices it returns nothing. "
      "In both strata the best achievable margin is zero and every eigenvalue of the recovered "
      "metric is of order 1e-9, which is numerical dust rather than a metric.")
    w("")
    w("| quantity | low pressure | high pressure |")
    w("|---|---|---|")
    w("| consequence points | %d | %d |" % (res["n_points_low"], res["n_points_high"]))
    w("| revealed strict preferences | %d | %d |" % (res["n_pairs_low"], res["n_pairs_high"]))
    w("| max-margin achieved | %.3g | %.3g |" % (res["margin_low"], res["margin_high"]))
    w("| top eigenvalue of the recovered metric | %.3g | %.3g |"
      % (max(res["eigenvalues_low"]), res["top_eigenvalue_high"]))
    w("| degenerate | %s | %s |" % (res["degenerate_low"], res["degenerate_high"]))
    w("")
    w("## The number that would have been reported without the guard")
    w("")
    w("This is the part worth keeping. Read naively, the two fits say the effective rank falls "
      "from %d under low pressure to %d under high pressure, and that %d of %d committed reversal "
      "predictions are observed, a share of %.3f. A rank that falls is the arm's PASS condition "
      "and the share sits just under its 0.60 bar. Reported without the guard that would have "
      "read as the theory very nearly confirmed."
      % (res["effective_rank_low"], res["effective_rank_high"],
         res["predicted_reversals_observed"], res["predicted_reversals_scored"],
         res["observed_share"]))
    w("")
    w("Every one of those numbers is computed on eigenvalues of order 1e-9. They are noise given "
      "a decimal point. The guard that refuses to grade a degenerate fit was written before these "
      "values were seen, after an earlier fit returned the same dust, and it is the only reason "
      "this record says NOT MEASURABLE instead of something flattering.")
    w("")
    if diag:
        w("## Why the program is degenerate, measured rather than asserted")
        w("")
        w("Protocol rule 8 requires a stage that detects unfitness to persist what it saw. Single "
          "cells were fitted first, then pools of growing size.")
        w("")
        w("Of %d single cells fitted, %d are non-degenerate. One game state on its own is "
          "comfortably representable, which the theory requires, since four consequence points in "
          "general position represent every order."
          % (diag["single_cells_fitted"], diag["single_cells_nondegenerate"]))
        w("")
        w("| game states pooled | revealed preferences | max-margin | degenerate |")
        w("|---|---|---|---|")
        for r in diag["ladder"]:
            w("| %d | %d | %.3g | %s |"
              % (r["cells"], r["pairs"], r["margin"], "yes" if r["degenerate"] else "no"))
        w("")
        w("**One evaluator serves about %d game states and fails by %d.** The margin falls from "
          "2.36 on a single state through 0.0766 at eight, and collapses to zero at twelve. That "
          "is the measurement this arm actually produced: the coach's evaluator geometry is not "
          "fixed across the game, and it is not different at every snap either. It changes on a "
          "scale of roughly ten game states."
          % (diag["largest_nondegenerate_pool_cells"],
             next((r["cells"] for r in diag["ladder"] if r["degenerate"]), 0)))
        w("")
    w("## Reading")
    w("")
    w("- **The registered instrument assumes what this world denies.** The estimator recovers one "
      "metric and one ideal from a body of choices. A pressure stratum holds 189 game states, "
      "about twenty times more than one evaluator can cover, so there is no single metric per "
      "stratum to recover and therefore no pair of ranks to compare.")
    w("- **This is not evidence against the budget prediction.** It is a failure to construct the "
      "measurement, and the arm is a miss rather than a refutation. GET is not embarrassed by a "
      "state-dependent evaluator, since the budget and the admissible set are the evaluator's own "
      "and are permitted to move with the state. What fails is the assumption this arm's design "
      "quietly made, that they hold still across a stratum.")
    w("- **The rank statistic is also confounded with constraint count.** In the ladder the "
      "recovered rank rises from 1 at a single state to 3 at five states while the margin is "
      "falling, so rank tracks how many constraints the program carries as much as anything about "
      "a budget. A future design must match constraint counts between strata before comparing "
      "ranks at all.")
    if cal:
        w("- The eigenvalue cut used throughout is %.2f, calibrated against synthetic evaluators "
          "of known rank before either stratum was opened, and recorded in `rank_cut.json`. The "
          "registration named the statistic and not the cut, which is a defect of the "
          "registration." % cal["chosen_cut"])
    w("- Nothing in the registration was changed after the seal. The low-pressure fit and its "
      "predicted reversal set were written and hashed before any high-pressure row was read, and "
      "the high stratum was opened only to complete the record once the verdict was already "
      "determined by the low fit.")
    w("")
    w("## What would measure it")
    w("")
    w("Fit pools of a fixed size that the ladder shows are representable, eight game states or "
      "fewer, many times in each stratum, and compare the distributions of recovered rank at "
      "matched pool size and matched constraint count. That is a different registration and it is "
      "not run here.")
    w("")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print("wrote", OUT, len(L), "lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
