# PREREG G3 (DRAFT, NOT SEALED): the indifference threshold tracks the resolution budget

Status: draft. Nothing here is a registered claim until Section 9 is executed.

## 1. Claim under test

GET-11 (paper prediction (i), Theorem 2(b)). For a fixed world and evaluator the
just-noticeable difference of the induced semiorder is the resolution budget: coarsening the
resolution at which the evaluator resolves consequences enlarges the threshold, and the
ordering of pairs separated by more than the largest threshold does not change. The claim is
measured on an evaluator the theory did not build, a language-model judge, under two budgets
the experimenter sets independently: the precision at which consequences are rendered to the
judge, and the precision of the judge's own weights.

## 2. World

Judge. `Qwen/Qwen2.5-7B-Instruct` from the HuggingFace cache on Atlas (revision recorded in
`prereg_config.json` at sealing), loaded on GPU 1 in bfloat16, in 8-bit, and in 4-bit NF4
through bitsandbytes (versions recorded at sealing). The judge is shown, in its chat template,
a target value and two options and asked which option is closer to the target, answering with
one letter. Its preference for the first-shown option is the sigmoid of the difference of the
two answer letters' next-token logits. Every pair is shown in both orders and the pair's
preference for the closer option is the mean of the two readings, which cancels a position
bias exactly to first order.

Consequences. The target is 100. An option is a number in (100, 150]; its consequence is its
distance from the target, between 1 and 40. A pair is two options whose distances differ by a
gap on the ladder 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10. 200 pairs per gap, drawn
by seed. Both options lie above the target. The draft had them on either side with equal
probability, and the first probe (2026-09-08, `probe_two_sided.json`) was vacuous: accuracy
0.62 to 0.76 at every gap including 10, and a six-case diagnostic showed the judge choosing
the larger number in every straddling pair rather than the closer one. A judge that cannot do
the two-sided task has no threshold there to measure, so the world is the one-sided task,
where closer means smaller and the judge's resolution is what is at issue. The same probe
found the instrument reading space-prefixed answer tokens whose logits sat 25 to 30 below the
bare letters the chat template elicits; corrected, and the probe now records the judge's
greedy generations on sample pairs so the reading is auditable.

Budgets. Rendering precision: numbers shown with 0, 1, 2, or 3 decimals (the target rendered
at the same precision). At d decimals two options whose distances differ by less than the
rendering step 10^-d may render identically, which the record counts per gap. Weight
precision: bfloat16, 8-bit, 4-bit. The twelve cells are the product.

Seeds. A probe seed (full precision, 3 decimals only, to establish that the events exist), a
pilot seed whose only use is to fix the tolerances of Section 5, and a run seed with fresh
pairs.

## 3. Estimator

For each cell and gap the accuracy is the share of pairs whose averaged preference for the
closer option exceeds one half. The threshold of the cell is the gap at which the accuracy
first reaches the registered level 0.9, interpolated linearly in log gap between ladder points,
infinite if never reached and the smallest gap if reached there. The self-test (Section 7)
shows the estimator recovers the threshold of a scorer whose threshold is known by
construction.

## 4. What the theory predicts

The judge's threshold in a cell is the larger of the budget it was set and a floor that is the
judge's own resolution at full precision and full rendering. So: (i) along the rendering
ladder, at fixed weight precision, the threshold is non-increasing in the number of decimals
and, where the rendering step exceeds the floor, tracks the step; (ii) along the weight ladder,
at fixed rendering, the threshold is non-decreasing as bits are removed; (iii) pairs whose gap
exceeds twice the largest threshold on either ladder are ordered the same way in every cell.

## 5. Bars (tolerances FIXED FROM THE PILOT before sealing; see Section 7)

- Anti-vacuity. At full precision and 3 decimals, accuracy at gap 10 is at least 0.95 and at
  gap 0.005 at most 0.65, so a threshold exists inside the ladder; and the floor, the threshold
  in that cell, is at most 0.3, so the rendering ladder (steps 1, 0.1, 0.01, 0.001) has at least
  one step above the floor. If the floor is above 0.3 the rendering ladder is VACUOUS and the
  registration is revised to coarser steps before sealing.
- P1, rendering tracks budget. At each weight precision the threshold is non-increasing over 0,
  1, 2, 3 decimals within a tolerance factor TOL, and at every decimal count whose step exceeds
  the floor by a factor of at least 3 the threshold is within a factor TOL of the step.
- P2, weight precision. At 3 decimals the threshold is non-decreasing over bfloat16, 8-bit,
  4-bit within the factor TOL.
- P3, well-separated ordering. For every gap at least twice the largest threshold measured in
  any cell, accuracy is at least 0.95 in every cell.

Pass: P1 to P3 hold. Fail: a threshold that decreases when the budget is coarsened by more than
the factor TOL at any step of either ladder, or a well-separated gap at which some cell's
accuracy is below 0.8. Otherwise INDETERMINATE, which includes a floor so high that the weight
ladder cannot move it.

## 6. What falsifies

A threshold that does not move with resolution where the theory says it must, a threshold
that shrinks when resolution is coarsened, or a reordering of well-separated pairs.

## 7. Self-test, probe and pilot (before sealing)

Self-test: a synthetic scorer that rounds distances to a grid of step h and prefers the
smaller rounded distance has threshold h; the estimator must place the threshold between 0.8 h
and 2.5 h at h in 0.01, 0.1, 1 (a rounded-distance scorer decides every pair whose gap exceeds
h and about half of those below, so the 90 percent level sits between h and 2h). Result
recorded here before sealing.

Probe: the full-precision, 3-decimal cell on the probe seed, to check anti-vacuity. Recorded
as `probe.json`.

Pilot: every cell on the pilot seed. TOL is fixed as the largest ratio between a threshold and
its predicted value (the step where the step exceeds the floor by a factor 3, the previous
cell's threshold otherwise) observed in the pilot, rounded up to one decimal, and at least 1.5.
Recorded here with the pilot's thresholds.

## 8. Compute and thermal rule

GPU 1 only. Batches of 32 prompts. Twelve cells of 4,400 forward passes each. A named screen
session with a log.

## 9. Sealing procedure

1. Self-test, probe, pilot on Atlas; record their results in Section 7 and TOL in Section 5;
   write the model revision and library versions into `prereg_config.json`; commit
   `probe.json` and `pilot.json`.
2. Rename this file to `PREREG-G3.md`, commit, record its blob hash in `CAMPAIGN.md`.
3. Only then run `--seed-role run`, grade with `g3_grade.py`, commit `results.json` and
   `grade.json` as executed.
