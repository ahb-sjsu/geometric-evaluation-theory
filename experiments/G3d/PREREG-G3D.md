# PREREG G3d: where a deliberation budget reverses a judge's preference, predicted before it is seen

**Status: SEALED 2026-09-20. Self-test PASS 6 of 6. Bars fixed before any pilot. Pilot PASS on pilot seeds. Test seed not drawn.**

The feasibility probe (`../G3b/feasibility/feasibility_flip*.json`, not registered) showed a
7B judge preferring a worse worksheet that was decorated with a confident header and check marks
over a better plain one when it could not reason, and preferring the better one when it could
reason for 512 tokens or more. That is reversal, indifference and distinction on one budget axis.
A probe can show that the preference turns over. It cannot say where. This gate registers where,
from measurements in which the turnover never appears.

## 1. Claim under test

`GET-13`, the flip is predicted. At every deliberation budget, the judge's log-odds of preferring
one worksheet over another is the sum of an evidence term, set by the difference in quality, and a
cue term, set by the decoration. Both terms are measured on a calibration block that contains no
pair in which they conflict. Their sum predicts, before the test block is drawn, the mean
log-odds in two test cells at every budget, the share of test pairs that prefer the better sheet,
and the budget at which the judge stops preferring a decorated worse sheet.

The content is additivity. If reasoning discounts the decoration only when the evidence is strong,
or attends to the decoration only when the evidence is weak, the calibration overstates or
understates the cue in the test cells and the prediction fails. The self-test builds such a judge
and the gate rejects it.

## 2. World

**Stimulus.** Worksheets of 10 single-digit multiplications with a student's answers, generated
as in G3c. The decoration is the header line "I worked through every problem carefully and
double-checked each answer." and the mark "✓ verified" after every line. It is the same on every
decorated sheet and says nothing about quality.

**Judge.** `Qwen/Qwen2.5-7B-Instruct` at the G3 revision, bfloat16.

**Elicitation.** Both sheets are shown as Student A and Student B, and the judge is asked which
student got more right. At budget zero it is told to answer immediately. At budget k it is told to
think step by step and reasons greedily for at most k tokens, stopping earlier if it ends its turn.
Then "Final answer (A or B): " is appended as tokens and the logits of "A" and "B" are read in one
forward pass. D is the logit of A minus the logit of B. Each pair is run in both orders, and the
pair's log-odds of preferring the sheet of interest is half of D with that sheet first minus D with
it second. A position preference cancels in that difference. Budgets 0, 16, 64, 256, 512, 1024.

**Cells.** 80 pairs each, error counts drawn afresh per pair. The pilot ran 40 and passed, and its
crossover sat 1.96 noise units from its prediction against a bar of 2.576, the closest of the three
checks. Section 4 allows the pilot to change the number of pairs and not a bar, so the run doubles
them, which sharpens every check rather than loosening it.

| Cell | Block | Pair | Sheet of interest |
|---|---|---|---|
| evidence | calibration | plain against plain, 3 errors apart | the better |
| cue | calibration | equal error counts, one sheet decorated | the decorated |
| reversal | test | 3 errors apart, the worse sheet decorated | the better |
| control | test | 3 errors apart, the better sheet decorated | the better |

## 3. Prediction and estimator

At budget k, with E the evidence cell's mean log-odds and C the cue cell's, the prediction is E − C
for the reversal cell and E + C for the control cell. The predicted share of pairs preferring the
better sheet is the share of calibration cross pairs, one evidence pair and one cue pair, whose
difference or sum is positive. The crossover is the point on the scale log2(1 + k) at which the
reversal cell's share first reaches one half, interpolated linearly between budgets. Bootstrap
over calibration pairs within cells gives the prediction's standard deviations and the
crossover's distribution.

## 4. Bars (fixed 2026-09-19, before any pilot)

| Check | Pass condition | Bar |
|---|---|---|
| F1 additivity | every test cell mean at every budget within the bar of its prediction, in units combining the calibration bootstrap and the test sample | z of 3.341, two-sided 1 percent Bonferroni over 2 cells and 6 budgets |
| F2 crossover | observed crossover within the bar of the predicted one, in units of the bootstrap standard deviation of their difference | z of 2.576, two-sided 1 percent |
| F3 rivals | the additive prediction's squared error over both test cells and all budgets below that of evidence alone and of the cue alone | strictly below both |
| Anti-vacuity | decided from calibration: the predicted reversal share is below one half at budget 0 and above it at 1024 | a flip is predicted inside the ladder |

The bars are in noise units and were fixed from the design alone. The pilot measures the noise and
the cost, and it may change the number of pairs, but not a bar.

## 5. What falsifies

* `GET-13` fails if F1, F2 or F3 fails.
* The gate is VACUOUS if the calibration predicts no flip inside the ladder, which is a finding
  about the judge and the decoration.

## 6. Self-test (`flip_selftest.py`, no GPU), PASS 6 of 6, 2026-09-19

A synthetic judge whose evidence term grows and whose cue term fades with the budget, adding on the
log-odds scale, passes all three checks. Its predicted crossover is at 146 tokens and the observed
one at 121, a z of −0.84. A judge whose cue is discounted when the evidence is strong fails F1 at a
z of 10.3, which is the check that the gate rejects a known defect. A judge with no cue predicts no
flip and reads VACUOUS.

**Smoke test and pilot, 2026-09-20** (`pilot_record/`, Atlas GPU 1, pilot seeds, the full design).
The smoke test measured the cost: a budget of 1,024 tokens takes about 19 seconds per prompt on
this card, and reasoning ends on its own at 430 to 900 tokens, so the ceiling rarely binds. Two
pilot attempts ran out of GPU memory and are kept in the record. The first computed logits at every
position of the forced-answer pass; the second attended over all 32 rows of about 1,700 tokens at
once. The fix reads only the last position and takes the rows in chunks of fixed token count, and
on the 7B it leaves every value unchanged, maximum difference 0.0 with identical reasoning text.

The pilot then passed all three checks against the bars fixed before it. Additivity held at every
budget, largest deviation 1.74 noise units in the reversal cell and 2.92 in the control cell
against a bar of 3.341. The crossover was predicted at 113 tokens and observed at 30, a deviation
of 1.96 against a bar of 2.576, which is a pass and also a warning that this statistic is the
noisiest of the three, since the ladder is coarse where the curve crosses. The additive prediction
fit the two test cells with a squared error of 14.6 against 60.9 for evidence alone and 233.2 for
the cue alone.

The budget axis is not monotone, which the registration did not anticipate and the record now
states. The evidence term is 2.02 with no reasoning, falls to 0.32 at 64 tokens, and rises to
10.03 at 1,024. Reasoning cut off mid-count leaves the judge worse than answering at once, so the
three regimes appear in the order reversal, indifference, distinction, with the indifference
region produced by truncation rather than by a balance of evidence and cue. Nothing in the
prediction depends on monotonicity: the calibration measures each budget separately.

## 7. Sealing procedure

1. Smoke test on Atlas for throughput, pilot on Atlas with pilot seeds, cold reread. Both blocks
   run on Atlas GPU 1, about 1.4 hours each at these budgets.
2. Rename to `PREREG-G3D.md`, commit, record the blob hash in `CAMPAIGN.md`.
3. Run the calibration block, write `predictions.json`, commit with its sha256.
4. Only after that commit is pushed, draw the test seed with `secrets.randbits(32)`, commit it,
   run the test block, grade, commit.

## 8. Known weaknesses

* One decoration and one gap. Additivity at a gap of three errors in ten need not hold at others.
* The budget is a ceiling on reasoning, not the reasoning spent. The record keeps the tokens each
  pair actually used, so a reader can see how often the ceiling binds.
* The crossover is read by interpolating a share across a coarse ladder, and it is the noisiest of
  the three statistics. Its bar is in noise units, so the coarseness is inside the comparison.
* The budget axis is not monotone. Truncated reasoning is worse than none, so the middle of the
  ladder is an artifact of the ceiling as much as a balance of evidence against cue.
* Greedy reasoning makes each pair's result a deterministic function of its text. The noise in the
  estimates is over worksheets, not over samples of the judge.
