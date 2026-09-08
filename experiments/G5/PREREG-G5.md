# PREREG G5: identification of the metric and the ideal from choices

Status: SEALED 2026-09-08 by the rename to `PREREG-G5.md`; blob hash recorded in `CAMPAIGN.md`. This is the
synthetic stage of G5; the stages on the TCSS reference implementation and on human data are
not registered here.

## 1. Claim under test

GET-5 (paper Theorem 4, Lean `GET.UniquenessGeneral`). Two evaluations that induce the same
weak order on an open set have proportional metrics and ideals that differ only in the metric's
kernel. On a finite battery the choices reveal the feasible cone of the representation program
of Theorem 3(a), and the remark after Theorem 4 states the design bound: the consequences must
span the space affinely, at least m + 1 affinely independent points in R^m, or the metric's
action off their span and the ideal's component off it are not revealed. The claims measured:
(i) above the bound the estimator recovers the metric up to scale and the ideal up to the
kernel, with error falling as the battery grows; (ii) at or below the bound, and on any battery
inside a proper affine subspace, the unrevealed components are no better than chance while the
revealed ones are still recovered; (iii) for a singular metric the ideal's kernel component is
no better than chance while its range component is recovered.

## 2. World

Synthetic. Dimensions m in {2, 3, 4}. Metric G = V diag(lambda) V^T with V a random orthogonal
matrix and lambda log-uniform on [0.2, 5] on the first r entries, zero on the rest, r in
{m, m - 1}. Ideal t standard normal. Battery of n = m + offset consequences, offset in
{-1, 0, 1, 2, 4, 8, 16, 32}, standard normal in R^m (general position, so the design bound is
met exactly when offset >= 1), and a second battery kind of m + 32 consequences inside a random
affine subspace of dimension m - 1, which violates the bound at every size. Choices: for every
ordered pair, the strict preference a > b iff d(a) + eps < d(b) with d the pullback distance
sqrt((y - t)^T G (y - t)), at eps = 0 (weak order) and at the eps for which 20 percent of the
unordered pairs are indifferent (semiorder). Indifferent pairs are not used by the estimator.
40 evaluators per cell, each with its own metric, ideal and battery. Two seeds: a pilot seed
whose only use is to fix the tolerances of Section 5, and a run seed, both in
`prereg_config.json`.

## 3. Estimator

The max-margin point of the representation program: maximise delta over positive semidefinite
G and h in R^m with the Euclidean norm of (G, h) at most one, subject to Q(y_b) - Q(y_a) >= delta
for every revealed a > b, where Q(y) = y^T G y - 2 y^T h, so that h = G t. The constraints are
homogeneous in (G, h, delta), so a norm on the whole parameter fixes the scale as for a
max-margin separator. Two earlier drafts of this estimator were wrong and the self-test and a
stopped pilot found them: fixing tr G = 1 alone leaves the margin unbounded whenever the
revealed pairs leave a direction of h unconstrained, and adding a ball on h instead lets the
margin grow by pushing h to the ball's edge, which drags the ideal with it. Solved by cvxpy
1.9.2 with Clarabel, SCS as fallback. The metric is reported at unit trace. The ideal
is t = G^+ h with eigenvalues below 1e-2 of the top one treated as kernel (the prior's eigenvalue ratio is at least 0.04, so no true direction is cut; a smaller cut let a tiny estimated eigenvalue of a singular metric blow the ideal up along the estimated kernel, and the small angle between estimated and true kernel leaked that into the range error, which the self-test found), which fixes t up to the estimated kernel. Nothing about the truth enters the estimator.

## 4. Errors

Metric: relative Frobenius error between the unit-trace true and estimated metrics, and the
largest principal angle between the true range and the estimated top-r eigenspace. Ideal:
the norm of the component of t_hat - t in the true range, and in the true kernel, each divided
by sqrt(m). For the subspace battery, the metric error is also split into the in-span block
(relative error of the (m-1)-dimensional block, unit-trace normalised) and the normal entry.
Chance reference per evaluator: the median of the same errors over 64 guesses drawn from the
evaluator prior.

## 5. Bars (form and factors fixed from the pilot before sealing; see Section 7)

Each bar is a statement about a cell (m, rank, eps mode) through medians over its 40
evaluators, relative to each evaluator's own chance level, the median error of 64 guesses
drawn from the evaluator prior (Section 4). "Recovered" means a median at most 0.35 times
chance; "unrevealed" means a median at least 0.5 times chance. The largest battery is offset
64, n = m + 64. `g5_grade.py` applies the rule; the factors are in `prereg_config.json`.

- P1, recovery at the largest battery. Weak-order cells (eps = 0): the metric and the ideal's
  range component are both recovered. Semiorder cells: the metric is recovered and the ideal's
  range component converges, its median at the largest battery at most 0.5 times its median at
  offset 8.
- P2, monotone improvement. The median metric error is non-increasing over offsets 4, 8, 16,
  32, 64, allowing 5 percent for ties.
- P3, the cliff. At offsets -1 and 0 (n <= m) the metric is unrevealed in the median. The
  fraction of evaluators within a quarter of chance is reported and not graded: a battery of n
  points spans an affine subspace of dimension n - 1 and reveals nothing off it, which is the
  theorem's claim, but it can reveal the in-span part, so single evaluators may land near the
  truth. An offset in which fewer than 20 evaluators have any strict pair is reported and not
  graded (with two points and a semiorder threshold the single pair is indifferent).
- P4, the subspace battery. At m + 64 points inside a proper affine subspace, the in-span block
  of the metric is recovered and the entry along the normal is unrevealed (its chance level
  is the same entry of guesses from the prior).
- P5, the kernel. For rank m - 1 at the largest battery, the ideal's range component satisfies
  P1, its kernel component is unrevealed, and at most 20 percent of evaluators have kernel
  error within a quarter of chance.

Pass: P1 to P5 hold in every cell. Fail: in a weak-order cell at the largest battery the
metric's or the ideal's median exceeds 0.5 times chance (recovery does not happen where the
theorem says it must), or more than 30 percent of evaluators below the bound have metric error
within a quarter of chance (the bound is wrong), or more than 30 percent have the kernel
component within a quarter of chance (the kernel ambiguity is wrong). Otherwise INDETERMINATE,
which is what a semiorder cell whose ideal has not converged at 64 points above the dimension
produces, and is reported as a finite-battery limit rather than as a verdict on the theorem.

## 6. What falsifies

Recovery below the design bound, which would mean the bound is wrong; failure to recover above
it at the largest battery, which would mean the identification claim is wrong for finite
batteries in the way the theorem's remark rules out; or a recovered kernel component of the
ideal, which the theorem says the choices cannot reveal.

## 7. Pilot (before sealing)

`g5_identify.py --seed-role pilot` runs every cell with the pilot seed; the run uses the run
seed only, with fresh evaluators and batteries.

First pilot, ladder to offset 32 (`pilot_ladder32.json`, 104 cells, 2026-09-08). Its purpose
as first drafted was to fix absolute tolerances as the 90th percentile of the errors at offset
8. It showed that rule to be empty: at offset 8 the 90th percentiles were 1.04 for the metric
and 5.09 for the ideal, at or beyond chance, because identification from ordinal data is slow
(medians at offset 8 of 0.4 to 0.5 for the metric against chance of 0.5 to 0.8) and only
tightens at offsets 16 and 32 (weak-order medians at offset 32 of 0.01 to 0.08 for the metric,
0.00 to 0.25 for the ideal). It also showed the semiorder cells, which drop the 20 percent of
pairs closest in distance, converge markedly slower for the ideal, and that in four dimensions
at full rank the ideal's median had not started to fall by offset 32 (1.24 against 0.90 at
offset 8). Three things followed, all before sealing: the bars were restated on medians
relative to chance, as in Section 5, so that the same statement is meaningful in every cell;
the ladder was extended to offset 64 so that the largest battery is closer to the limit the
theorem speaks of; and the chance reference for the normal entry of the subspace battery was
added. The first pilot's other findings are the ones the bars now test: at n <= m no cell had
more than 5 percent of evaluators within a quarter of chance; the in-span block of the
subspace battery was recovered in every cell while the full metric stayed at chance; and for
singular metrics the kernel component's median was 0.8 to 1.5 times chance while the range
component was recovered.

Second pilot, ladder to offset 64 (`pilot.json`, `pilot.log`, 116 cells, Atlas 15:40 to 17:11
UTC 2026-09-08). Under the bars of Section 5 every one of the 12 cells passes. Its values, to be
compared with the run's: metric median over chance at offset 64 between 0.00 and 0.02 in the
weak-order cells and 0.05 to 0.24 in the semiorder cells; ideal range median over chance 0.00
to 0.02 (weak order) and 0.03 to 0.28 (semiorder), with the semiorder ideal's median at offset
64 between 0.08 and 0.29 of its median at offset 8; median metric error falling monotonically
over offsets 4 to 64 in every cell (for instance from 0.92 to 0.015 in four dimensions at full
rank with a weak order); at n <= m the median metric error 1.19 to 1.84 times chance in every
graded offset; on the subspace battery the in-span block at 0.00 to 0.19 of chance and the
normal entry at 0.61 to 2.72 times its chance; for singular metrics the kernel component at
0.67 to 1.12 times chance. Two things the second pilot changed before sealing, both recorded
here: the cliff bar's fraction clause was dropped (a two-point battery in two dimensions with a
rank-one metric reveals one bit about the metric's direction, and single evaluators landed
within a quarter of chance more often than the clause allowed, which the theorem does not
forbid), and offsets with fewer than 20 evaluators having any strict pair are not graded (one
such offset had a single evaluator, whose lone error had driven a verdict).

## 7a. Self-test record

`--selftest` on Atlas, 2026-09-08, cvxpy 1.9.2 with Clarabel: SELFTEST PASS. Rich battery in
general position, metric error 0.076 against chance 0.67 and ideal range error 0.54 against
chance 1.72; singular metric, metric error 0.010, range angle 3.0 degrees, ideal range error
0.027 against chance 0.87, kernel component 0.61 against chance 0.58; subspace battery, in-span
block error 0.044 with the full metric at 0.92 against chance 0.67; battery of m points, metric
error 1.52. Two earlier estimator drafts failed this test or a pilot and are described in
Section 3.

## 8. Sealing procedure

1. Self-test on Atlas (`--selftest`). Done, Section 7a.
2. Pilots on Atlas; fix the form and factors of the bars; commit `pilot_ladder32.json` and
   `pilot.json`. Done, Section 7.
3. Rename this file to `PREREG-G5.md`, commit, record its blob hash in `CAMPAIGN.md`.
4. Only then run `--seed-role run` (seed 20260909, fresh evaluators and batteries), grade with
   `g5_grade.py`, commit `results.json` and `grade.json` as executed.
