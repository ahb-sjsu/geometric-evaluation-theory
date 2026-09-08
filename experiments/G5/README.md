# G5: identification of the metric and the ideal from choices

Gate G5 of `CAMPAIGN.md`, synthetic stage. Registration `PREREG-G5-DRAFT.md`, to be sealed
after the pilot fixes the tolerances. The estimator is the semidefinite program of Theorem
3(a) with a margin, solved by cvxpy with Clarabel, and the quantity tested is Theorem 4: from
choices alone the metric is recovered up to scale and the ideal up to the metric's kernel,
provided the battery of consequences spans the space affinely, and not otherwise.

| File | What |
|---|---|
| `g5_identify.py` | world, estimator, errors, chance reference, pilot and run (`--seed-role`), self-test |
| `prereg_config.json` | dimensions, battery ladder, evaluator count, indifference share, seeds |
| `PREREG-G5-DRAFT.md` | the registration |

Protocol. `--selftest` on Atlas; `--seed-role pilot` (seed 20260908) to see the error scale and
fix the tolerances, recorded in the registration; seal; `--seed-role run` (seed 20260909,
fresh evaluators and batteries) graded by `g5_grade.py`.
