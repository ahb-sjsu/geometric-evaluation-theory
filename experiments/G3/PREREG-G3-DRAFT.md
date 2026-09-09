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

Evaluator. `Qwen/Qwen2.5-7B-Instruct` from the HuggingFace cache on Atlas (revision recorded
in `prereg_config.json` at sealing), loaded on GPU 1 in bfloat16, in 8-bit, and in 4-bit NF4
through bitsandbytes (versions recorded at sealing). The model is a scorer: shown, in its chat
template, a target value and one value, it is asked how far the value is from the target and
answers with a number, read as the first number in its greedy generation of at most 12 tokens.
The induced preference between two options compares their reported distances; equal reports,
and any unparsable report, are indifference. This is the theory's evaluator, a map from a
consequence to a scalar cost whose order is the preference, and the model's own output
resolution and arithmetic are its floor.

Two earlier instruments were tried on the probe seed and are kept in the record. A pairwise
chooser asked which of two options is closer, read from the answer letters' next-token
logits, both orders shown. With options on either side of the target it was vacuous
(`probe_two_sided.json`: accuracy 0.62 to 0.76 at every gap including 10; a six-case
diagnostic showed the model choosing the larger number in every straddling pair; and the
instrument was reading space-prefixed letter tokens whose logits sat 25 to 30 below the bare
letters the chat template elicits). With options on one side and the reading corrected
(`probe_one_sided_chooser.json`) it reached 0.99 at gap 10 but 0.43 to 0.63 from gap 0.01 to
gap 2, a threshold of 7.5 against the 0.3 the anti-vacuity rule allows, because the chooser's
first-position preference holds the two-order average at one half until the gap is large. A
pairwise chooser measures its position bias before it measures a threshold, so it was replaced
by the scorer before any pilot.

Consequences. The target is 100. An option is a number in [50, 150]; its consequence is its
distance from the target, between 10 and 40, two digits before the decimal point so that a
report of a fixed length has a fixed resolution. A pair is two options whose distances differ
by a gap on the ladder 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5,
10, 20, each option on either side of the target with equal probability. 200 pairs per gap,
drawn by seed; each distinct rendered value is scored once per cell. The first scorer probe
(`probe_scorer_v1.json`, distances 1 to 40, gaps from 0.005) found reports exact to three
decimals and accuracy 1.0 at every gap, a floor below the ladder, which is why the ladder
now reaches 0.0005 and 20.

Budgets. Three, set independently. Rendering precision: numbers shown with 0, 1, 2, or 3
decimals (the target rendered at the same precision); at d decimals two options whose
distances differ by less than the rendering step 10^-d may render identically, which the
record counts per gap. Weight precision: bfloat16, 8-bit, 4-bit. Report length: the scorer's
answer limited to k generated tokens, k in 1, 2, 3, 4, 5, 6, 12; this tokenizer emits one
digit per token, so with two-digit distances a report of k tokens resolves 10 at k = 1, 1 at
k = 2 and 3 (the third character is the decimal point), 0.1 at k = 4, 0.01 at k = 5, 0.001 at
k = 6 and beyond. This is the theory's length budget taken literally: the evaluator may spend
k symbols on its cost, and the threshold should be the resolution those symbols afford.
Cells: rendering times weight precision at the full report length (twelve cells), and the
report ladder at three decimals and full weights (six more).

Seeds. A probe seed (full precision, 3 decimals only, to establish that the events exist), a
pilot seed whose only use is to fix the tolerances of Section 5, and a run seed with fresh
pairs.

## 3. Estimator

For each cell and gap the accuracy is the share of pairs whose preference for the closer
option exceeds one half, with ties and unparsable reports counting as one half, so that
indifference counts against. The threshold of the cell is the gap at which the accuracy
first reaches the registered level 0.9, interpolated linearly in log gap between ladder points,
infinite if never reached and the smallest gap if reached there. The self-test (Section 7)
shows the estimator recovers the threshold of a scorer whose threshold is known by
construction.

## 4. What the theory predicts

The scorer's threshold in a cell is the larger of the budget it was set and a floor that is
the scorer's own resolution at full weights, full rendering, and full report length. So: (i)
along the rendering ladder, at fixed weight precision, the threshold is non-increasing in the
number of decimals and, where the rendering step exceeds the floor, tracks the step; (ib)
along the report ladder the threshold is non-increasing in k and, where the afforded
resolution exceeds the floor, tracks it; (ii) along the weight ladder, at fixed rendering and
report length, the threshold is non-decreasing as bits are removed; (iii) pairs whose gap
exceeds twice the largest threshold in any cell are ordered the same way in every cell. At
full weights the rendering and report ladders test only that the scorer's arithmetic resolves
what it is shown and allowed to say, which a competent model makes nearly a tautology; the
weight ladder, and the rendering and report ladders at reduced weights if run, are where the
prediction can fail.

## 5. Bars (tolerances FIXED FROM THE PILOT before sealing; see Section 7)

- Anti-vacuity. At full weights, 3 decimals and full report length, accuracy at gap 20 is at
  least 0.95, and the floor, the threshold in that cell, is at most 0.3, so that at least two
  rendering steps and at least three report budgets exceed three times the floor. A floor at
  or below the smallest gap is recorded as censored at 0.0005 and counted as 0.0005 in the
  "exceeds the floor" tests. If the floor is above 0.3 the ladders are VACUOUS and the
  registration is revised before sealing.
- P1, rendering tracks budget. At each weight precision the threshold is non-increasing over 0,
  1, 2, 3 decimals within a tolerance factor TOL, and at every decimal count whose step exceeds
  the floor by a factor of at least 3 the threshold is within a factor TOL of the step.
- P1b, report length tracks budget. At full weights and 3 decimals the threshold is
  non-increasing over k = 1 to 12 within TOL, and at every k >= 2 whose afforded resolution
  exceeds the floor by a factor of at least 3 the threshold is within a factor TOL of that
  resolution. The k = 1 cell is reported and not graded (its resolution, 10, is at the edge of
  the gap ladder).
- P2, weight precision. At 3 decimals and full report length the threshold is non-decreasing
  over bfloat16, 8-bit, 4-bit within the factor TOL.
- P3, well-separated ordering. For every gap at least twice the largest threshold measured in
  any cell, accuracy is at least 0.95 in every cell.

Pass: P1, P1b, P2 and P3 hold, with TOL = 1.5 from the pilot. Fail: a threshold that decreases when the budget is coarsened by more than
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
h and about half of those below, so the 90 percent level sits near h). Result, Atlas
2026-09-08: SELFTEST PASS, thresholds 0.0088, 0.087, 0.87 at h = 0.01, 0.1, 1.

Probe: the full-weights, 3-decimal, full-report cell on the probe seed, to check anti-vacuity.
Recorded as `probe.json`; the earlier chooser probes and the first scorer probe are recorded
beside it under their own names. Result (`probe.json`, seed 20260910, Atlas 2026-09-09):
accuracy 1.00 at gap 20 and at every gap from 0.001 up, 0.495 at 0.0005 where 0.505 of pairs
render identically and tie, threshold 0.00087, no unparsable report; the generation sample
shows reports exact to three decimals. Anti-vacuity holds: the floor is 0.00087, below 0.3,
so three rendering steps and four report budgets exceed three times the floor. A first run of
this probe crashed in the generation-sample code on a cache key that had gained the report
budget; the sample code was fixed and the probe rerun after the pilot, whose cells it does not
touch.

Pilot: every cell on the pilot seed. TOL is fixed as the largest ratio, in either direction,
between a threshold and its predicted value (the rendering step or the afforded report
resolution where that exceeds three times the floor, the previous cell's threshold along a
ladder otherwise) observed in the pilot, rounded up to one decimal, and at least 1.5.

Pilot record (`pilot.json`, `pp.log`, seed 20260911, Atlas GPU 1, 2026-09-08 21:58 to
2026-09-09 03:36 UTC including a 68-minute pause by the host's thermal guardian, which stops
the heaviest CPU processes when a package reaches 82 degrees and was resumed with the
owner's consent; no cell was affected). Thresholds: rendering ladder at bf16 0.869, 0.0864,
0.00882, 0.00088 for 0, 1, 2, 3 decimals against steps 1, 0.1, 0.01, 0.001; identical at
8-bit; 0.869, 0.0864, 0.00882, 0.00091 at 4-bit, where accuracy at gap 20 was 0.98 rather than
1.00. Report ladder at bf16 and 3 decimals 8.98, 0.872, 0.877, 0.0875, 0.00873, 0.00088 for
k = 1 to 6 against afforded resolutions 10, 1, 1, 0.1, 0.01, 0.001. No unparsable report in
any cell. The largest ratio between a threshold and its prediction is 1.15 (every threshold
sits at 0.87 to 0.90 of its step, which is where the 90 percent level of a rounding scorer
falls, as the self-test showed), so TOL = 1.5, the registered minimum. The floor is censored
at 0.0005 at every weight precision: 8-bit and 4-bit weights do not act as a resolution budget
on this scorer at this task, which is a finding the run will test again on fresh pairs, and
which means P2 can hold only as an equality within TOL.

## 8. Compute and thermal rule

GPU 1 only. Batches of 32 prompts, greedy generation of at most 12 tokens (fewer on the report
ladder), each distinct rendered value scored once per cell (at most 6,000 per cell), eighteen
cells per seed. A named screen
session with a log.

## 9. Sealing procedure

1. Self-test, probe, pilot on Atlas; record their results in Section 7 and TOL in Section 5;
   write the model revision and library versions into `prereg_config.json`; commit
   `probe.json` and `pilot.json`.
2. Rename this file to `PREREG-G3.md`, commit, record its blob hash in `CAMPAIGN.md`.
3. Only then run `--seed-role run`, grade with `g3_grade.py`, commit `results.json` and
   `grade.json` as executed.
