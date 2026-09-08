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
| `PREREG-G5.md` | the sealed registration; `pilot_ladder32.json` and `pilot.json` the two pilots that fixed its bars |

Protocol. `--selftest` on Atlas; `--seed-role pilot` (seed 20260908) to see the error scale and
fix the tolerances, recorded in the registration; seal; `--seed-role run` (seed 20260909,
fresh evaluators and batteries) graded by `g5_grade.py`.

Outcome, 2026-09-08. PASS in all 12 cells on the fresh seed (`results.json`, `grade.json`,
`run.log`; table and reading in `CAMPAIGN.md`). Metric and ideal recovered at the largest
batteries, error falling monotonically, nothing recovered at or below the design bound, off
the span of a subspace battery, or in a singular metric's kernel.
