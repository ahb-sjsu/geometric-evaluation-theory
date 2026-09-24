# PREREG G3i: the reversal on a second vendor's judge

Status: SEALED 2026-09-24 at blob c59d4f0a7ac46510cb02dffba408ae5c259986df (commit d0b73a4). **VACUOUS**, decided
2026-09-24 from the calibration block alone, before any test seed: the calibration predicts no crossing inside 0 to 192
tokens (Section 10). No test seed was drawn and no test block was run. The first draft of this
file named two judges on G3h's ladder; the pilot of Section 6 changed both the judge list and the
ladder before this seal, and both changes are stated where they occur.

## Why this gate exists

G3d showed that a deliberation budget reverses a judge's preference and that the budget at which
it reverses is predicted from cells in which evidence and cue never conflict. G3h located the
crossing on the same judge, to a factor of 1.4. Both rest on one judge, Qwen2.5-7B, and a reader
is entitled to ask whether the reversal, the additivity of evidence and cue, and the prediction of
the crossing are facts about that judge or about judges. This gate asks a judge from another
vendor, with nothing else changed but the rungs of the ladder, which are set where that judge's
own pilot says its crossing lies.

## What had been seen when this was written

G3d and G3h are graded, PASS, and in the ledger. Their designs and bars are inherited here
unchanged. Before this seal, two judges were smoke-tested and piloted on G3h's ladder of 0 to 96
tokens, at pilot seeds no graded block uses; the full record is in Section 6 and it decided what
follows.

* **Llama 3.1 8B is not registered.** On the pilot ladder neither the evidence nor the cue moves
  it: its calibration evidence term is 0.55 log-odds at 0 tokens and never above 0.26 after 16,
  its cue term at most 0.87, and the reversal cell's share of pairs preferring the better sheet
  sits between 0.26 and 0.61 with no trend. The registered rule would declare it VACUOUS from
  its calibration block, and it did on the pilot. It is reported as a judge the design cannot
  move, at either rung of the ladder, and not run further.
* **Gemma 3 12B is registered, on a higher ladder.** On the pilot ladder its cue term falls from
  6.56 log-odds at 0 tokens to 0.96 at 96 while its evidence term falls from 4.38 to 0.63, so the
  cue still exceeds the evidence at 96 and the calibration predicts no crossing inside 0 to 96;
  the pilot test block nonetheless crossed one half at its last rung. The crossing lies at or
  above 96 tokens, and the registered ladder is moved up to bracket it.

## 1. Claims under test

G3d's three claims, in G3d's words, graded by `../G3d/flip_grade.py`, unmodified: F1 additivity,
F2 crossover predicted, F3 the additive account beating both single-term rivals (statements in
`../G3h/PREREG-G3H.md` Section 1). The judge is VACUOUS if its calibration predicts no flip inside
the ladder, which is a finding and not a failure, and then the gate grades nothing.

## 2. World, judge, elicitation

**Stimuli, cells, cue, gap, pairs.** G3h's, unchanged: worksheets of ten multiplications, pairs
three errors apart, 80 pairs per cell, the decoration a confident header and a check mark on every
line, two calibration cells and two test cells, both presentation orders.

**Budgets.** 0, 32, 64, 96, 128 and 192 reasoning tokens. Six rungs, so the multiple-comparison
correction in the bars is G3d's number. The pilot on 0 to 96 (Section 6) placed this judge's
crossing at or above 96, so the ladder keeps the anchor at 0 where the cue is largest, keeps 32,
64 and 96 from the pilot, and adds 128 and 192 above.

**Judge.** Local weights, read directly, in bfloat16, from a mirror that carries no access gate so
that the record can be rebuilt by anyone.

| key | weights | revision | vendor |
|---|---|---|---|
| `gemma12b` | unsloth/gemma-3-12b-it | 9478e665381f42974aa06177b019352fb6291876 | Google |

The mirror is a byte-identical republication of Google's instruction-tuned weights at that
revision, without the license click-through the original requires. One judge, one new vendor.

**Elicitation.** As G3d: the judge is told to think step by step and reasons greedily for at most
$k$ tokens, "Final answer (A or B): " is then forced, and the letter logits are read in one pass.
The judge's own chat template is applied by the harness, as it was for Qwen.

## 3. Bars, taken by reference

G3d's, unchanged, in noise units, fixed from the design alone before any pilot: F1 at z 3.341
(two-sided 1 percent Bonferroni over 2 cells and 6 budgets), F2 at z 2.576, F3 strictly below
both rivals. Nothing about a bar depends on the judge or on where the rungs sit.

## 4. What falsifies

* F1 fails if any test cell at any budget deviates from the additive prediction by more than
  3.341 noise units.
* F2 fails if the observed crossing lies more than 2.576 noise units from the predicted one.
* F3 fails if either single-term rival matches or beats the additive prediction.
* The gate fails if any claim fails. It is VACUOUS if the calibration predicts no flip inside 0
  to 192, which the pilot makes unlikely but does not exclude.

## 5. What this can and cannot show

If it passes, the reversal, its additivity and the prediction of its crossing hold on two
vendors' judges, each predicted from its own calibration, and the crossing of the second is
located on a ladder set by its own pilot. Its crossing is expected above Qwen2.5-7B's, and that
is not a failure: the claim is that each judge's own calibration predicts its own crossing. What
it cannot show: anything about a second cue, a second gap, a served judge, or a judge the cue
cannot move, of which Llama 3.1 8B is now a recorded example.

## 6. Self-test, smoke tests and pilots

**Self-test.** G3d's `flip_selftest.py`, unchanged, through `flip_selftest_g3i.py`, with the
synthetic evidence slope rescaled to 0.1 as in G3h so that the synthetic crossing lies inside the
ladder. PASS on the registered config, 2026-09-24. Record in `selftest_gemma12b/`.

**Smoke tests, 2026-09-24** (`pilot_record/smoke_*`), four pairs at budgets 0 and 96 on each
judge, to confirm the harness executes each judge's chat template and reads its letter tokens on
this hardware. Both ran. Llama 3.1 8B gave evidence 0.49 and cue 0.35 log-odds at 0 tokens in 32
seconds; Gemma 3 12B gave 5.60 and 6.39 in 18 seconds and 0.75 and 1.11 at 96 tokens in 130
seconds. Four pairs decide nothing and were used for nothing else.

**Pilots, 2026-09-24** (`pilot_record/pilot_*`, GPU 1, pilot seeds 51 and 52, G3h's ladder of
0, 16, 32, 48, 64, 96, 80 pairs per cell), graded by `flip_grade.py` for the record only.

| judge | calibration evidence, 0 to 96 tokens | calibration cue | reversal share observed | pilot verdict |
|---|---|---|---|---|
| Llama 3.1 8B | 0.55, 0.24, 0.06, $-$0.42, 0.14, 0.26 | 0.46, 0.87, 0.02, 0.67, 0.18, 0.51 | 0.50, 0.26, 0.55, 0.42, 0.61, 0.38 | VACUOUS |
| Gemma 3 12B | 4.38, 2.18, 0.22, 1.52, 0.63, 0.63 | 6.56, 3.85, 0.41, 1.83, 1.47, 0.96 | 0.16, 0.25, 0.34, 0.38, 0.28, 0.54 | VACUOUS on this ladder |

Llama 3.1 8B: the cue never exceeds a log-odd and the evidence never exceeds half of one after
0 tokens, so no flip is predicted and none is seen; the control cell, where cue and evidence
agree, sits at about one log-odd throughout. A judge the design cannot move is outside the
gate's claims, and it is recorded here so the reader can see that a second vendor was tried and
what happened. Gemma 3 12B: the reversal cell's mean rises from $-2.75$ log-odds at 0 tokens to
$+0.10$ at 96, its observed share crosses one half between 64 and 96 tokens, and the calibration
predicts the crossing above the ladder because at 96 its cue term still exceeds its evidence
term. The cost was about 4.5 minutes per rung at 0 tokens rising to 35 minutes at 96 with a
batch of 8, so a block took two hours. What the pilot decided: the judge list and the ladder of
Section 2. The number of pairs stays at 80 and the bars do not change.

## 7. Compute, and whose

The authors' workstation, one 32 GB GPU, the second being in use. Gemma 3 12B in bfloat16 takes
24 GB, so batches are 8 up to 96 tokens, 6 at 128 and 4 at 192. From the pilot's timing, 35
minutes for the 96-token rung at a batch of 8, a block is about five hours, and the gate needs
one calibration block and one test block. The card is shared with other work on the workstation,
and the run starts only when it is free. Threads pinned
and niced, as G3d ran.

## 8. Sealing procedure

1. The config carries the calibration seed and no test seed.
2. Self-test passes on the config; the smoke and pilot records are in Section 6.
3. This file is committed and its git blob hash recorded in the ledger.
4. The calibration block is run and `predictions.json` committed with its sha256 and pushed.
5. Only then is the test seed drawn from a system random source, against the predictions in
   HEAD, and the test block run and graded by `../G3d/flip_grade.py`, unmodified.

## 10. Verdict, from the calibration block alone

The calibration block ran 2026-09-24 16:46 to 17:40 UTC on a Colab A100 40 GB, the workstation's
card being held by other work and the cluster's 32 GB and larger pools having no free card that
hour (Section 7 named the workstation; the change of machine changes no stimulus, seed, weight or
line of the harness, and the record carries the loaded revision). Record in `run_record/calibration/`,
predictions in `run_record/predictions.json`, sha256 5f9105359eda4560b9e4e7a0f8e03b7704ddd25e1b62a8ccbf11866702a9ffc9.

Along the ladder 0, 32, 64, 96, 128, 192 the evidence term is 5.01, 0.12, 0.73, 0.67, 0.67, 1.40 log-odds and the cue term is
6.77, 0.59, 2.02, 1.45, 1.60, 1.04, so the cue still matches the evidence at 192 tokens, and the additive prediction for the
reversal cell's share of pairs preferring the better sheet is 0.329, 0.314, 0.263, 0.348, 0.312, 0.468. It never reaches one half. By
Section 4 the judge is VACUOUS on this ladder: its calibration predicts no flip inside it. The
crossing lies above 192 tokens, close to it. No test seed is drawn, because there is nothing the
test block could grade.

What this says. On a second vendor's judge the reversal regime exists and is measured, the decorated
worse sheet preferred at every rung to 192 tokens, and the crossing is again a budget the
calibration places, only higher than this ladder reaches. The pilot on 0 to 96 (Section 6) had put
the crossing at or above 96 from a test block that crossed one half at its last rung; the sealed
calibration says that crossing was noise about one half (predicted 0.44 there) and the true crossing
is above 192. The next registration, G3j, places the rungs where this calibration says the crossing
is, exactly as G3h did after G3d.
