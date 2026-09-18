# PREREG G3b: the grid-channel law and the resolution-reliability split, across model families, tokenizers and a harder consequence map

**Status: DRAFT, NOT SEALED. No probe, no pilot, no bar fixed, no seed drawn.**
Sealing is the rename to `PREREG-G3B.md`, the commit of that rename, and the recording of
its blob hash in `CAMPAIGN.md`, after the self-test, the probes and the pilot of Section 7.

This gate follows G3 (PASS 2026-09-09). It registers as predictions two things that G3's
record showed but did not register: the grid-channel law of accuracy against gap, and the
separation of resolution from reliability under weight quantization. It removes the two
weaknesses an external reader found in G3: P3 rested on a single gap chosen by an
ungraded cell, and the record held no per-pair outcomes. And it answers the scope
limitation of one model on one task with a second model family, a tokenizer whose report
grid differs from Qwen's, and a consequence map that is not literal subtraction.

## 1. Claims under test

`GET-11b`. For an evaluator that resolves its consequences exactly, a grid of step `h`
placed on the consequences it reads, or on the symbols it may write, makes its probability
of ordering a pair correctly equal to `min(1, gap/h)`, up to a lapse `lam` that does not
depend on the pair. The step fitted from the accuracy curve equals the step that was set,
within a registered factor, in every graded cell. (Paper Proposition 1.)

`GET-11c`. Reducing the precision of the evaluator's weights changes the lapse and not the
step. (The resolution-reliability split, seen once on Qwen2.5-7B-Instruct at 4-bit.)

`GET-11d`. The report-length grid is the resolution the tokenizer's symbols afford, so on
a tokenizer that groups digits the mapping from report length to step is the one that
tokenizer implies, and not Qwen's one-character-per-token mapping.

`GET-11e`. Pairs separated by at least twice the largest graded step are ordered alike in
every cell, on a ladder of well-separated gaps and not a single gap.

## 2. What is new against G3, and why

| G3 | G3b |
|---|---|
| Threshold at the 0.9 level by log-gap interpolation, whose value 0.87 h is an estimator constant | Fitted step `h_hat` by least squares of accuracy on gap through the origin over sub-ceiling points, and lapse `lam_hat` from the plateau, both with bootstrap intervals |
| P3 on the largest threshold in any cell, including the ungraded 1-token cell, leaving gap 20 as the only qualifying point | P3 on the largest graded step, with gaps 30, 50 and 100 added |
| Per-gap aggregates persisted | Every pair's two reports, raw generations, token counts and stop reason persisted (Rule 8) |
| One model, one task | Qwen2.5-7B-Instruct replicated, Gemma-3-4b-it added, a Llama-3 instruct model added if it can be obtained, and a two-dimensional distance task added |

## 3. World

### 3.1 Evaluators

* `Qwen/Qwen2.5-7B-Instruct` at the G3 revision, the replication arm.
* `google/gemma-3-4b-it` from the Atlas cache, a second family whose tokenizer emits one
  character per token for digits and the decimal point (checked 2026-09-18), so the
  report-length grid is the same function of `k` as Qwen's.
* Conditional: a Llama-3 instruct checkpoint (`meta-llama/Llama-3.2-3B-Instruct` or
  `meta-llama/Llama-3.1-8B-Instruct`), whose tokenizer groups up to three digits into one
  token (`10.123` tokenizes as `10`, `.`, `123`, checked 2026-09-18 on the base
  checkpoint). Its report grid is registered from its own tokenizer before the pilot: with
  two-digit distances, `k = 1` affords step 1, `k = 2` affords step 1 (the decimal point),
  `k = 3` affords step 0.001. The prediction is that its steps follow that mapping. This
  arm runs only if the checkpoint is present on Atlas before sealing, and the registration
  records whether it ran.

Each evaluator is a scorer with the G3 prompt, greedy decoding, report read as the first
number in the generation. Weight precisions bfloat16 and 4-bit NF4 for every model; 8-bit
for Qwen only, since G3 showed it identical to bfloat16.

### 3.2 Consequence maps

* Task A, the G3 task: target 100, option a number in [50, 150], consequence its distance
  from the target, in [10, 40].
* Task B, not literal subtraction: target `(100, 100)`, option a pair of numbers, each in
  [50, 150], consequence the Euclidean distance of the pair from the target, in [10, 40].
  The judge is shown both coordinates and asked how far the point is from the target. The
  arithmetic requires a square root, and the floor is expected to be higher; the
  anti-vacuity rule of Section 5 decides whether the ladders can be graded.

### 3.3 Pairs and ladder

Gap ladder 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20,
30, 50, 100. 200 pairs per gap drawn by seed, option positions continuous so the phase
relative to any grid is uniform. Distances kept in [10, 40] so that two digits precede the
decimal point; gaps of 30 and above are placed so both distances stay in range, which
bounds the largest gap at 30 for Task A as registered; 50 and 100 are run with the
distance range widened to [10, 140] and three digits before the point, in cells marked as
such, so that the report grid for those cells is registered separately.

### 3.4 Budgets

Rendering at 0, 1, 2, 3 decimals. Report length `k` in 1 to 6 and 12, with the afforded
step per model registered from its tokenizer in Section 3.1. Weight precision per model.
Cells: for each model, rendering by weight precision at full report; the report ladder at
3 decimals and bfloat16; Task B at bfloat16 on the rendering ladder only.

## 4. Estimator

For each cell, accuracy per gap as in G3 (ties and unparsable reports count against).

* `h_hat`: least squares of accuracy on gap through the origin over ladder points with
  accuracy below 0.9, divided by `(1 - lam_hat)`.
* `lam_hat`: one minus the mean accuracy at gaps of at least twice the set step.
* Intervals: a paired bootstrap over pairs, resampling the 200 pairs at each gap with
  replacement and refitting, 4000 draws, which the per-pair record now supports; the
  parametric binomial bootstrap of the G3 analysis is reported beside it.
* The G3 threshold statistic is computed and reported for continuity and not graded.
* `h_hat` and `lam_hat` for every cell are computed by `g3b_grade.py` against the sealed
  bars, and the code is self-tested on a synthetic rounding scorer with a known step and a
  known lapse before sealing.

## 5. Bars (FIXED FROM THE PILOT before sealing)

| Quantity | Bar | Fixed by |
|---|---|---|
| Anti-vacuity, per model and task | accuracy at gap 20 at least 0.95 at full precision; floor (fitted step at full weights, 3 decimals, full report) at most `[ ]` | pilot |
| `GET-11b`, step tracks grid | `h_hat / h_set` within a factor `[ ]` of 1 in every graded cell, with the interval containing `h_set` | pilot |
| `GET-11b`, law at every point | maximum absolute deviation of accuracy from `(1 - lam_hat) min(1, gap/h_set)` at most `[ ]` in every graded cell | pilot, in units of the binomial standard error at n = 200 |
| `GET-11c`, weights move the lapse only | at 4-bit, `h_hat` within the factor of its bfloat16 value; `lam_hat` reported with its interval and not graded, since a lapse of zero at 4-bit is not a failure | pilot |
| `GET-11d`, tokenizer grid | on the Llama arm, `h_hat` within the factor of the step its tokenizer affords at each `k`, and outside the factor of the Qwen mapping at `k = 1` and `k = 3` | tokenizer, before pilot |
| `GET-11e`, well-separated ordering | accuracy at least 0.95 at every gap of at least twice the largest graded step, in every cell, on at least three such gaps | ladder |
| Equivalence bound for "unchanged step" | `delta_min` factor `[ ]` | stated before the pilot is opened |

Pass, fail and indeterminate are defined per claim. A model whose floor exceeds the
anti-vacuity bar on a task has that task's ladders recorded as VACUOUS for that model and
not graded.

## 6. What falsifies

* An accuracy curve that is not `min(1, gap/h)` at the set step within the bar, in any
  graded cell, fails `GET-11b` for that evaluator.
* A 4-bit `h_hat` outside the factor of its bfloat16 value fails `GET-11c`.
* A Llama-arm step that follows Qwen's mapping rather than its own tokenizer's fails
  `GET-11d`.
* A well-separated gap below 0.95 in any cell fails `GET-11e`.

## 7. Self-test, probe and pilot (before sealing)

1. Self-test of `g3b_grade.py` on a synthetic rounding scorer at steps 0.01, 0.1, 1 with
   lapses 0, 0.03, 0.1: recover `h_hat` within 3 percent and `lam_hat` within 0.01, with
   the paired bootstrap covering the truth at the nominal rate. Persist the simulated pairs.
2. Tokenizer probe per model: the token identifiers of representative reports, recorded in
   the registration, from which the afforded step per `k` is fixed.
3. Probe per model and task on a probe seed at full precision: anti-vacuity, raw
   generations persisted, count of reports that stopped before the budget, count of
   unparsable reports.
4. Pilot on a pilot seed over every cell to fix the bars of Section 5.
5. Seal, then run on the run seed, then grade.

## 8. Compute and thermal rule

GPU 1 on Atlas, one model at a time, bfloat16 for the 7B and 4B models fits in 32 GB;
4-bit through bitsandbytes. About four hours per model at G3's rate of 200 pairs per gap
over 18 gaps and up to 16 cells; Task B doubles the option count. Nothing runs on the
laptop. Raw generations are written to `/archive` beside the results.

## 9. Sealing procedure

1. Obtain the Llama instruct checkpoint or record that it was not obtained.
2. Run items 1 to 4 of Section 7 and fill Section 5 with dated bars.
3. Rename to `PREREG-G3B.md`, commit, record the blob hash in `CAMPAIGN.md`.
4. Draw the run seed, run, grade with `g3b_grade.py`, commit `results.json`,
   `grade.json`, `run.log` and the per-pair record.

## 10. Reread record

Empty. A cold reread precedes the pilot.

## 11. Known weaknesses

* The grid-channel law at full weights on Task A is close to a tautology for a competent
  model, as G3 recorded. The load is carried by the 4-bit arm, the Llama tokenizer arm,
  and Task B.
* Task B's floor may exceed the anti-vacuity bar on a 4B model, in which case that arm
  is vacuous and says nothing.
* The Llama arm depends on a download that may not be available offline.
