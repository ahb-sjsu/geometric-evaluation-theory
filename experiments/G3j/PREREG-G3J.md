# PREREG G3j: the reversal on a second vendor's judge, on the ladder its calibration placed

Status: DRAFT. Not sealed. The calibration seed is in the config; no test seed exists and one is
drawn only after `predictions.json` is in a pushed commit with its hash.

## Why this gate exists

G3i put G3d's reversal design in front of Google's Gemma 3 12B on a ladder of 0 to 192 reasoning
tokens and came out VACUOUS by its own rule: the sealed calibration predicts the decorated worse
sheet preferred at every rung, with the reversal cell's share of pairs preferring the better sheet
rising from 0.33 at 0 tokens to 0.47 at 192 and never reaching one half. The reversal regime is
therefore measured on a second vendor, and the crossing is placed, by that calibration, just above
192 tokens. This gate puts the rungs there. It is to G3i what G3h was to G3d: the same design on
the ladder the earlier gate's own record said was needed.

## What had been seen when this was written

G3d, G3h are PASS and G3i is VACUOUS, all in the ledger. G3i's sealed calibration block, at seed
20261001 on a Colab A100, is the record that places this ladder; its numbers are in Section 6. No
block of this gate has been run; there is no separate pilot, since G3i's calibration is the
measurement a pilot would provide and it is sealed rather than exploratory.

## 1. Claims under test

G3d's three claims, in G3d's words, graded by `../G3d/flip_grade.py`, unmodified: F1 additivity,
F2 crossover predicted, F3 the additive account beating both single-term rivals (statements in
`../G3h/PREREG-G3H.md` Section 1). The judge is VACUOUS if its calibration predicts no flip inside
the ladder, which would be a finding about how long this judge holds the cue, and the gate then
grades nothing.

## 2. World, judge, elicitation

**Stimuli, cells, cue, gap, pairs, judge, elicitation.** G3i's, unchanged: worksheets of ten
multiplications, pairs three errors apart, 80 pairs per cell, the decoration a confident header and
a check mark on every line, two calibration cells and two test cells, both presentation orders,
unsloth/gemma-3-12b-it at revision 9478e665381f42974aa06177b019352fb6291876 in bfloat16, the
judge's own chat template, "Final answer (A or B): " forced and the letter logits read in one pass.

**Budgets.** 0, 128, 192, 256, 320 and 384 reasoning tokens. Six rungs, so the multiple-comparison
correction in the bars is G3d's number. The anchor at 0 tokens, where the cue is largest, and the
two rungs G3i measured just below the crossing are kept; three rungs are added above it, at steps
of 64, to the double of the rung where G3i's calibration last saw the share below one half.

## 3. Bars, taken by reference

G3d's, unchanged, in noise units, fixed from the design alone before any pilot: F1 at z 3.341
(two-sided 1 percent Bonferroni over 2 cells and 6 budgets), F2 at z 2.576, F3 strictly below both
rivals.

## 4. What falsifies

As G3h Section 4. The gate is VACUOUS if the calibration predicts no flip inside 0 to 384, which
G3i's calibration makes unlikely but does not exclude.

## 5. What this can and cannot show

If it passes, the reversal, its additivity and the prediction of its crossing hold on two vendors'
judges, each predicted from its own calibration, and the second judge's crossing is located on a
ladder its own record set. What it cannot show: anything about a second cue, a second gap, or a
served judge.

## 6. Self-test and the record that placed the ladder

**Self-test.** G3d's `flip_selftest.py`, unchanged, through `flip_selftest_g3j.py`, with the
synthetic evidence slope at G3d's own 0.06, which places the synthetic crossing near 184 tokens,
inside this ladder. PASS, 2026-09-24: the additive judge's crossing predicted at 183.6 tokens and
observed at 208.0, 0.53 noise units. Record in `selftest_gemma12b/`.

**G3i's sealed calibration, 2026-09-24** (`../G3i/run_record/calibration/`, seed 20261001,
Colab A100 40 GB, 54 minutes), which is what places this ladder:

| tokens | 0 | 32 | 64 | 96 | 128 | 192 |
|---|---|---|---|---|---|---|
| evidence term, log-odds | 5.01 | 0.12 | 0.73 | 0.67 | 0.67 | 1.40 |
| cue term, log-odds | 6.77 | 0.59 | 2.02 | 1.45 | 1.60 | 1.04 |
| predicted reversal share | 0.329 | 0.314 | 0.263 | 0.348 | 0.312 | 0.468 |

The evidence term first exceeds the cue term at 192 tokens and the share is still below one half
there, so the crossing is above 192 and, on the trend of the last two rungs, not far above it. As
on Qwen2.5-7B, the evidence term is not monotone in the budget. The cost on the A100 was 0.3, 2.6,
4.8, 7.0, 12.2 and 26.7 minutes per rung.

## 7. Compute, and whose

A Colab Pro A100 40 GB, run by hand from `../G3i/colab/g3i_block.ipynb` with the gate set to G3j,
which clones the public repository at its head, fetches the weights from the ungated mirror at the
registered revision, runs one block with the harness unmodified and writes the record to Drive.
From G3i's timing the 256, 320 and 384 rungs cost about 45, 65 and 90 minutes, so a block is about
four hours, and the gate needs one calibration block and one test block. The workstation's card and
the cluster's larger pools remain the fallback.

## 8. Sealing procedure

1. The config carries the calibration seed and no test seed.
2. Self-test passes on the config; G3i's calibration is recorded in Section 6.
3. This file is committed and its git blob hash recorded in the ledger.
4. The calibration block is run and `predictions.json` committed with its sha256 and pushed.
5. Only then is the test seed drawn from a system random source, against the predictions in
   HEAD, and the test block run and graded by `../G3d/flip_grade.py`, unmodified.
