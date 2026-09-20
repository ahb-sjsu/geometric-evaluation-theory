# G9 secondary arm, the budget prediction, committed as executed

**Verdict: NOT MEASURABLE, the representation program is degenerate.** Graded against PREREG-G9.md Section 5 and 6, blob f8a18aea4d82bded364b78a6da6c1a39f1fd9f51. The arm asked whether a smaller resolution budget lowers the effective rank of the evaluator's metric, using the game clock as a manipulation nobody had to administer. It cannot be answered on this world by the registered instrument, for a reason that is itself a measurement.

## What happened

The identification estimator of G5 recovers a metric and an ideal point from revealed strict preferences by a max-margin program. Run on the league's choices it returns nothing. In both strata the best achievable margin is zero and every eigenvalue of the recovered metric is of order 1e-9, which is numerical dust rather than a metric.

| quantity | low pressure | high pressure |
|---|---|---|
| consequence points | 756 | 504 |
| revealed strict preferences | 1131 | 749 |
| max-margin achieved | 9.36e-09 | 9.41e-09 |
| top eigenvalue of the recovered metric | 1.86e-09 | 1.42e-09 |
| degenerate | True | True |

## The number that would have been reported without the guard

This is the part worth keeping. Read naively, the two fits say the effective rank falls from 2 under low pressure to 1 under high pressure, and that 50 of 93 committed reversal predictions are observed, a share of 0.538. A rank that falls is the arm's PASS condition and the share sits just under its 0.60 bar. Reported without the guard that would have read as the theory very nearly confirmed.

Every one of those numbers is computed on eigenvalues of order 1e-9. They are noise given a decimal point. The guard that refuses to grade a degenerate fit was written before these values were seen, after an earlier fit returned the same dust, and it is the only reason this record says NOT MEASURABLE instead of something flattering.

## Why the program is degenerate, measured rather than asserted

Protocol rule 8 requires a stage that detects unfitness to persist what it saw. Single cells were fitted first, then pools of growing size.

Of 25 single cells fitted, 25 are non-degenerate. One game state on its own is comfortably representable, which the theory requires, since four consequence points in general position represent every order.

| game states pooled | revealed preferences | max-margin | degenerate |
|---|---|---|---|
| 1 | 6 | 2.36 | no |
| 2 | 12 | 0.478 | no |
| 3 | 18 | 0.2 | no |
| 5 | 30 | 0.18 | no |
| 8 | 48 | 0.0766 | no |
| 12 | 72 | -5.88e-08 | yes |
| 20 | 120 | -1.69e-09 | yes |
| 35 | 210 | -2.12e-07 | yes |
| 60 | 359 | -3.54e-08 | yes |
| 100 | 597 | -4.05e-08 | yes |
| 150 | 897 | 3.88e-09 | yes |
| 189 | 1131 | 9.36e-09 | yes |

**One evaluator serves about 8 game states and fails by 12.** The margin falls from 2.36 on a single state through 0.0766 at eight, and collapses to zero at twelve. That is the measurement this arm actually produced: the coach's evaluator geometry is not fixed across the game, and it is not different at every snap either. It changes on a scale of roughly ten game states.

## Reading

- **The registered instrument assumes what this world denies.** The estimator recovers one metric and one ideal from a body of choices. A pressure stratum holds 189 game states, about twenty times more than one evaluator can cover, so there is no single metric per stratum to recover and therefore no pair of ranks to compare.
- **This is not evidence against the budget prediction.** It is a failure to construct the measurement, and the arm is a miss rather than a refutation. GET is not embarrassed by a state-dependent evaluator, since the budget and the admissible set are the evaluator's own and are permitted to move with the state. What fails is the assumption this arm's design quietly made, that they hold still across a stratum.
- **The rank statistic is also confounded with constraint count.** In the ladder the recovered rank rises from 1 at a single state to 3 at five states while the margin is falling, so rank tracks how many constraints the program carries as much as anything about a budget. A future design must match constraint counts between strata before comparing ranks at all.
- The eigenvalue cut used throughout is 0.15, calibrated against synthetic evaluators of known rank before either stratum was opened, and recorded in `rank_cut.json`. The registration named the statistic and not the cut, which is a defect of the registration.
- Nothing in the registration was changed after the seal. The low-pressure fit and its predicted reversal set were written and hashed before any high-pressure row was read, and the high stratum was opened only to complete the record once the verdict was already determined by the low fit.

## What would measure it

Fit pools of a fixed size that the ladder shows are representable, eight game states or fewer, many times in each stratum, and compare the distributions of recovered rank at matched pool size and matched constraint count. That is a different registration and it is not run here.
