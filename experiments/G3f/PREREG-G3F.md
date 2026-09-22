# PREREG G3f: the same resolution law on a second stimulus family

Status: DRAFT. Not sealed. The calibration seed is in the config, the test seed is not and is
drawn only after `predictions.json` is committed with its hash.

## Why this gate exists

Every gate so far has graded one stimulus family. G3c measured five judge configurations on
worksheets of twenty single-digit multiplications and G3e measured three more, served by a public
API, on the same worksheets. Six graded configurations, one task.

That task was chosen because its quality scale is exact, and the choice was stated plainly. It has
a cost that no amount of further judges pays off: the judge does the arithmetic exactly, so the
grid on what it reads and writes is the whole story, and a reader can fairly say the method has
only been shown to work where the underlying judgement is trivial. An external reader of the ICLR
draft said exactly that.

G3f changes the stimulus family and nothing else. The blocks, the scales, the read-outs, the
estimator, the grading code and the bars are G3c's, taken by reference. If the prediction holds
here it holds on a task the judge does not do exactly, and the claim stops being about arithmetic.

## What had been seen when this was written

G3c and G3e are graded and their verdicts are in the record. G3c passed its three claims on three
graded configurations. G3e passed the prediction and the codebook comparison on three more and
failed the read-out ordering on `gemma31b`, whose seven read-outs at the ladder floor could not be
ranked. Those outcomes are known and are not re-litigated here.

The G3f probe was run before this registration was written, on a probe seed no graded block uses.
Its numbers are in Section 6. Nothing else about G3f has been measured.

## 1. Claims under test

Each is G3c's claim, in G3c's words, on the new family. Each is graded per judge by
`../G3c/judge_grade.py`, unmodified.

**C1f (J1, GET-12a).** The accuracy curve of every read-out on the test block is predicted, at
every gap, by the judge's calibration block alone, inside the registered bars.

**C2f (J2, GET-12b).** The channel the judge actually uses, its conditional score distribution
measured on the calibration block, predicts its curves better than a rival that reads the nominal
scale at face value.

**C3f (J3, GET-12c).** The ordering of thresholds across read-outs is the ordering their symbol
budgets predict, with Kendall's tau at or above the bar and every threshold inside the registered
factor of its prediction.

**C4f (J5, GET-12d).** The pairwise threshold sits at or above the floor the judge's finest
pointwise read-out predicts. Recorded as AT FLOOR, COARSER or FINER; none of the three is a
failure of the theory.

A claim holds only if every graded judge passes it. A judge declared vacuous from its calibration
block is reported and not graded.

## 2. World, judges, elicitations

**Stimulus.** A passage of twenty numbered facts and a summary restating them in twenty numbered
statements, of which `e` are unsupported. Quality is `1 - e/20`, the same scale G3c used for `e`
wrong answers out of twenty, so the gap ladder and every estimator transfer without change.

Both texts are rendered from one structured record of twenty facts, each a template with one slot
value. An unsupported statement is one whose slot was replaced by a different value of the same
kind. `g3f_stimuli.verify_record` checks, for every stimulus generated, that each perturbed value
differs from the truth and appears nowhere in the passage as a substring, and that no unperturbed
value was altered. A statement is therefore unsupported if and only if it was perturbed, and the
count is exact with no annotator.

The substring condition is not decoration. The self-test found on its first run that `tin` is a
substring of `printing`, so a summary whose medal was struck in the wrong metal had that metal
sitting in the passage inside another word. Checking values would not have caught it.

**Judges.** The three G3e judges, unchanged, pinned by what the service reports serving. The
harness refuses the block if the served string does not match.

| key | asked for | must be served as |
|---|---|---|
| `gemma31b` | `gemma` | `google/gemma-4-31B-it-qat-w4a16-ct` |
| `gemma12b` | `gemma4-12b` | `google/gemma-4-12B-it-qat-w4a16-ct` |
| `qwen3_27b` | `qwen3-small` | `Qwen/Qwen3.8-27B` |

Three aliases on this gateway resolve to the same 12B weights, so the alias is not the identity
and `served_as` is what is registered.

**Elicitations.** G3c's six read-outs on three scales, unchanged: the greedy score, the expected
score under the judge's own distribution, and the mean of 1, 2, 4 and 8 samples drawn from it, on
1 to 5, 0 to 9 and 0 to 100. Plus pairwise comparison in both orders.

**Blocks.** Calibration: 40 stimuli at each of the 21 error counts, 840 in all. Test: 200 pairs at
each gap of 1, 2, 3, 4, 6, 8 and 12, the better summary's error count uniform on what the gap
allows.

## 3. Reading a served judge

As G3e. The service exposes the twenty most probable tokens at each position. On the two
single-token scales the vector is the first-token distribution restricted to the codebook. On the
0 to 100 scale a score spans up to three digit tokens and the vector is built by a digit tree,
every prefix above `tree_prune = 1e-4` extended by one cached step. Pruned mass, mass outside the
scale and mass on a non-digit first token are recorded per stimulus.

## 4. Bars, frozen at seal

Taken from G3c by reference and **not re-fitted for this family**. A bar moved for a new task is
not a bar, and the whole value of this gate is that the bars were set on a different stimulus
family by a null simulation on a judge of a third family.

| bar | value |
|---|---|
| `dev_max` | 0.14 |
| `z_max` | 4.55 |
| `threshold_factor` | 1.75 |
| `rank_agreement_min` | 0.86 |
| `vacuity_acc_min` | 0.9 |
| `vacuity_bits_min` | 1.0 |

Source: G3c `pilot_record/null/bars_null.json`, 1000 null replicates.

## 5. What falsifies

* C1f fails if any read-out of a graded judge misses `dev_max` or `z_max` at any gap.
* C2f fails if the nominal rival's squared error is below the measured channel's on any scale of
  any graded judge.
* C3f fails if Kendall's tau is below the bar, or any threshold falls outside the factor, on any
  graded judge.
* The gate fails if any claim fails. It is VACUOUS if every judge is vacuous.

A judge is vacuous if, from its calibration block alone, it cannot order stimuli twelve errors
apart with accuracy `vacuity_acc_min` on any scale, or carries under `vacuity_bits_min` about
quality. This is decided before the test seed is drawn.

## 6. Self-test and probe

**Stimulus self-test.** `g3f_stimuli.py selftest` generates 840 stimuli over the full error
ladder, verifies every one against the property the quality scale rests on, and checks for
duplicates and line counts. It passes.

**Harness self-test.** The synthetic judges of G3c, run through this gate's stimuli. The synthetic
judge reads the error count from the stimulus registry rather than re-deriving it from the text,
which is the one change a summary forces and which leaves it exactly as faithful as it was.

**Probe.** Run before this registration was written, on the probe seed, six stimuli at each of the
levels 0, 2, 5, 8, 12, 16 and 20.

<!-- PROBE TABLE: filled from probe/ before sealing -->

## 7. Compute, and whose

No GPU of the authors'. Requests to NRP's managed LLM service at its published concurrency of
eight, one to four output tokens each, driven from Atlas at the lowest priority. No pods are
submitted and no GPU is requested, so the cluster's pod sizing and utilization rules are not
engaged.

## 8. Known weaknesses

* One stimulus family is replaced by a second, not by many. Two families are not a demonstration
  that the method is family-independent.
* The facts are templated and synthetic. The judgement is harder than arithmetic but it is still
  a fact-matching task, not the contested quality of prose.
* The same three judges as G3e, so the judges are not an independent draw from anything.
* Quality is a count of unsupported statements and treats all of them as equal, which the score a
  judge writes need not.

## 9. Sealing procedure

1. `g3f_config.json` carries the calibration seed and no test seed.
2. This file is committed. Its git blob hash is recorded here and in the ledger.
3. Calibration blocks are run and `predictions.json` is written and committed with its sha256.
4. Only then is the test seed drawn from a system random source, written to `test_seed.json`, and
   the test blocks run and graded by the registered script.
