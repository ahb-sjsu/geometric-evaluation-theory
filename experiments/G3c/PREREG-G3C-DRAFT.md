# PREREG G3c: a judge's symbol budget predicts its resolution before the resolution is measured

**Status: DRAFT, NOT SEALED. Self-test passed 2026-09-18. Pilot running. No bar fixed, no run seed drawn.**
Sealing is the rename to `PREREG-G3C.md`, the commit of that rename, and the recording of its
blob hash in `CAMPAIGN.md`. The run then has two commits of its own, in this order and never
merged: the calibration block with `predictions.json` and its sha256, and only after that commit
the drawing of the test seed and the test block. The order of those two commits is the evidence
for the word "before" in the title.

G3 measured a judge's threshold on a numeric task and passed. An external review and the
record itself showed that result to be a calibration: on G3's sealed pairs the judge's accuracy
equals that of an exact evaluator behind the rounding channel to within 0.005 in seventeen of
eighteen cells. The judge does the subtraction exactly, so the grid is the whole story and the
prediction could hardly fail. G3c moves to a judgment the model cannot do exactly, grading a
student's worksheet, where the budget that matters is the one the judge actually spends.

## 1. Claims under test

`GET-12a`, prediction before measurement. For each rating scale and each read-out of the judge's
report, the accuracy with which the judge orders two worksheets whose error counts differ by a
gap is predicted from a calibration block alone, by the share of calibration cross pairs at that
gap that the same read-out orders correctly. The test block, on disjoint worksheets drawn from a
seed fixed after the predictions are committed, matches the prediction at every gap within
registered bars.

`GET-12b`, the effective budget and not the nominal one. The threshold under a rating scale is
set by the codebook the judge actually uses, measured on the calibration block, and not by the
number of levels the scale offers. The rival is an ideal judge that uses every level of the
nominal scale. On the 0 to 100 scale the rival predicts a threshold below one error in twenty.

`GET-12c`, a larger report budget lowers the threshold, by the predicted amount. Reading the
expected score from the probability vector over the codebook, and averaging n samples drawn at
temperature one, are reports of more symbols than one greedy integer. The calibration block
predicts each read-out's threshold, and the prediction is that the observed thresholds fall in the
predicted order and within a registered factor of the predicted values.

`GET-12d`, a question with both answers stated. Direct pairwise comparison has no report grid on
quality. If the judge's internal resolution is what limits it, the pairwise threshold sits at the
floor of the pointwise read-outs. The label AT FLOOR, COARSER or FINER is recorded against the
registered factor, and none of the three is a failure of the theory.

`GET-12e`, weights move reliability and not resolution (from G3's 4-bit cell). At 4-bit weights
the thresholds stay within the factor of their bfloat16 values, and the accuracy at the largest
gap is reported with its interval.

## 2. World

**Stimulus.** A worksheet of 20 single-digit multiplications with a student's answers, of which
`e` are wrong, `e` from 0 to 20. Quality is `1 - e/20` and is known exactly. Wrong answers differ
from the product by one of the operands, by ten, or by one or two.

**Judges.** `Qwen/Qwen2.5-7B-Instruct` at the G3 revision, bfloat16 and 4-bit NF4. A size ladder
in the same family, 1.5B and 14B, and a second family, `gemma-3-4b-it`, at bfloat16.

**Elicitations.** Scoring on three scales, 1 to 5, 0 to 9 and 0 to 100, with the prompt in
`prereg_config.json`. One forward pass per worksheet gives the greedy integer, the probability
vector over the codebook, and eight samples at temperature one drawn from that vector. On the two single-token scales the vector is the first-token distribution over the codebook. On the 0 to 100 scale a score takes up to three digit tokens, and the vector is computed exactly by a digit tree: one pass gives the first digit, and every digit prefix above a probability of 0.00001 is extended by one cached single-token step that gives each next digit and the probability of stopping, with the model's repetition penalty applied at every step as sampling applies it. The pruned mass, the mass on values outside the scale and the mass on a first token that is not a digit are recorded per worksheet. Every scale therefore has the expected-score read-out and exact samples, and no sample is generated.
Pairwise comparison of two worksheets, both orders, read from the answer-letter logits with no
deliberation; a pair counts as ordered correctly when the order-averaged preference for the
better sheet exceeds one half.

**Blocks.** Calibration: 40 worksheets at each of the 21 error counts, 840 in all. Test: 200 pairs
at each gap of 1, 2, 3, 4, 6, 8 and 12 errors, 2,800 fresh worksheets, the better sheet's error
count uniform on what the gap allows.

## 3. Estimator

A read-out maps a worksheet to a number, higher is better. A pair is ordered correctly when the
better sheet gets the strictly larger number, so ties and unparsable reports count against.

* Predicted accuracy at a gap: over calibration levels `e` and `e + gap`, the share of cross pairs
  ordered correctly, averaged over `e` with the test block's weights. Interval by a bootstrap over
  calibration worksheets within levels.
* Observed accuracy at a gap: the share of the 200 test pairs ordered correctly.
* Threshold: the smallest gap at which accuracy reaches 0.75, interpolated linearly between
  ladder gaps.
* Codebook: the distinct scores used, the entropy of the score distribution, and the mutual
  information in bits between score and error count.
* Nominal rival: a judge whose score is the rounded scale position of the true quality.
* Comparison in noise units: the deviation between observed and predicted accuracy divided by a
  standard error that does not collapse near one, a Laplace-shrunk binomial variance plus a floor
  of one over twice the pair count on the prediction's bootstrap deviation. The self-test found
  the uncorrected version scoring z of 5.9 for two misordered pairs in 200.

## 4. Bars (FIXED FROM THE PILOT before sealing)

| Quantity | Bar | Fixed by |
|---|---|---|
| `dev_max`, largest absolute deviation of observed from predicted accuracy | `[ ]` | pilot |
| `z_max`, largest deviation in noise units | `[ ]` | pilot, with the false-alarm rate over the number of cells stated |
| `threshold_factor`, observed over predicted threshold | `[ ]` | pilot |
| `rank_agreement_min`, Kendall tau between predicted and observed thresholds across read-outs | `[ ]` | pilot |
| Anti-vacuity: on at least one scale the argmax accuracy at gap 12 is at least 0.9 and the calibration information about quality is at least `[ ]` bits | `[ ]` | pilot |
| Rival margin: on 0 to 100 the rival's sum of squared errors exceeds the effective prediction's by a factor of at least `[ ]` | `[ ]` | stated before the pilot is read |

## 5. What falsifies

* `GET-12a` fails if any scale and read-out misses the bars: the calibration block did not predict
  the test block.
* `GET-12b` fails if the nominal rival fits the observed argmax curve at least as well as the
  effective prediction on any scale, or if the judge turns out to use the 0 to 100 scale at a
  resolution the rival predicts.
* `GET-12c` fails if thresholds do not fall in the predicted order, or fall outside the factor.
* `GET-12e` fails if a 4-bit threshold leaves the factor of its bfloat16 value.
* The gate is VACUOUS for a judge that fails anti-vacuity, which is a finding about that judge.

## 6. Self-test, probe and pilot

**Self-test, PASS 9 of 9, rerun 2026-09-19** (`judge_selftest.py`, no GPU). A synthetic judge that
perceives quality with noise and writes a heaped codebook passes 12a, 12b and 12c, with the
expected-score and eight-sample read-outs below the argmax. A judge whose perception noise
triples on the test block fails 12a at z of 27.7 against 2.5 for the faithful judge, which is the
check that the gate rejects a known defect. A judge that uses every nominal level does not beat
the rival, which is the check that 12b cannot pass by construction. The first run failed 12a on
the faithful judge for the variance collapse recorded in Section 3, and the repair was to the
noise units and not to the bar.

**Feasibility probe, 2026-09-18** (`../G3b/feasibility/`, not a registered stage). The 7B judge's
scores fall monotonically with the error count on every scale. It used 5, 8 and 10 distinct
scores on the 1 to 5, 1 to 10 and 0 to 100 scales. Pairwise accuracy with both orders was 0.67,
0.71 and 0.96 at gaps of 1, 2 and 4 errors in ten, with a first-position preference of 0.83 to
0.98.

**Pilot.** Pilot seeds, the 7B judge at bfloat16, the full design. It fixes every bar in Section 4.
Pilot data are not pooled with the run. Two attempts failed before it ran and are kept in the
record on Atlas. The first ran out of GPU memory generating sixteen samples for sixteen prompts at
once. The second was stopped after an hour because generated samples cost one full prompt pass
each. The fix draws samples from the recorded first-token distribution on the two single-token
scales and, on the 0 to 100 scale, from the exact digit-tree distribution.

**Pilot outcome, 2026-09-19** (`pilot_record/`, graded with `pilot_summary.py`). The calibration
predictions were written and hashed (sha256 `6ac1530d`) before the test block was scored. On all
eighteen read-outs, three scales times six, the observed accuracy stayed within 0.088 of the
prediction at every gap, the largest deviation in noise units was 2.88, and the nominal rival fit
60 to 200 times worse than the effective codebook. The judge used 5, 8 and 9 distinct scores on
the three scales. Kendall's tau between predicted and observed thresholds was 0.95. Pairwise
grading reached 0.75 at 2.9 errors, against a floor of 1.7 predicted from the expected score on
the 1 to 5 scale. Its first-position preference was 0.86, which the order-averaged preference
cancels by design.

Every observed threshold came out above its prediction, by 1 to 21 percent. The deviations sat
at gaps 2, 4 and 6 with one sign across every scale and read-out. Two checks placed this as
chance. Calibration and test worksheets at equal error counts got the same scores, with a
chi-square p of 0.63, 0.64 and 0.57 on the three scales, so the blocks are scored alike. And
because all eighteen read-outs grade the same 200 pairs per gap, one draw of pairs moves all of
them together. The bars in Section 4 are therefore set from a simulation that keeps that
dependence (`null_bars.py`). It redraws a calibration block and a test block from disjoint
halves of the pilot's worksheets and grades each replicate with the same code as the run.

**Sampling verification, 2026-09-19** (`verify/`). On a 42-worksheet block the 7B judge left no
report unparsable on any scale and put all first-token mass on the codebook. Scoring took 0.49,
0.48 and 4.5 seconds per worksheet on the 1 to 5, 0 to 9 and 0 to 100 scales. Real samples were
compared with the recorded distribution on six worksheets of the 0 to 9 scale, 256 draws each.
Five matched within the 95th percentile of multinomial noise and one did not, at 16 errors, a
distance of 0.105 against a bar of 0.073. The distribution did not depend on batch shape: it was
identical alone, in 32 copies and inside a padded mixed batch, which ruled out bfloat16 numerics.
Redrawn with 2,048 samples, that worksheet sat at 0.015 against a bar of 0.026, p of 0.36, and a
second worksheet at 0.014 against 0.027. The miss was chance at the smaller sample.

**Digit-tree verification, 2026-09-19** (`verify/verify_tree.json`). On six worksheets of the 0 to
100 scale, 1,024 real samples each matched the tree's distribution within multinomial noise in
all six, p from 0.21 to 0.95, with no unparsable or out-of-range draw and at most 0.00006 of the
mass pruned. Recomputing the tree's 37 largest probabilities by one uncached forward pass gave
differences of up to 24 percent. That is one bfloat16 rounding step of the logits, about 0.125 at
the logit sizes seen here, between the cached decoding path that sampling uses and an uncached
full pass. The judge's score distribution is therefore defined only to one bfloat16 step in its
logits, depending on the kernel path, and the tree reproduces the path that sampling takes. The
tree scores a worksheet in 1.16 seconds, against 4.5 for generating eight samples.

**Chunked digit tree for the 14B judge, 2026-09-19** (`verify/verify_tree_chunked.json`). The
pilot's sizing run of the 14B judge ran out of GPU memory at the second digit of the 0 to 100 tree.
Every live two-digit prefix carried its own copy of the prompt's cache, about 65 MB for a prompt
of 337 tokens, beside 27.5 GiB of weights on a 31.7 GiB card. With `tree_rows` set, the tree runs
the same single-token step on at most that many prefixes at a time and keeps the cache only of
prefixes that have children. Only the 14B uses it, at one prompt and eight rows. The whole-frontier
tree used by every other judge is unchanged. On 22 worksheets the 7B's chunked and whole-frontier
trees differed by at most 0.00005 in any probability, which is batch composition in bfloat16. The
14B's chunked tree matched brute force to a relative difference of at most 0.21, against 0.24 for
the 7B's verified tree, with the largest gap on a score of probability 0.07. It scores a worksheet
in 3.7 seconds at a peak of 29.5 GiB, and its pairwise pass at batch 2 peaks at 28.1 GiB.

## 7. Compute

The first pilot attempt showed generated sampling costs one prefill per sample, which is why samples are generated only where the scale needs more than one token. Run time per model and precision is measured by the pilot and recorded here before sealing. The sealed runs go to NRP Nautilus, on untainted V100-SXM2-32GB nodes, the pilot's hardware class. The pinned environment and the weights at the revisions in `prereg_config.json` are staged onto a shared volume by CPU-only jobs (`nrp/stage_models.py`, manifests with sha256 per file), so GPU pods install and download nothing. Each GPU job is sized from the meter record of a measured run of the same model and precision (`nrp/submit.py`), and a model never measured is refused. Raw generations, probability vectors and samples are
persisted per worksheet.

## 8. Sealing procedure

1. Pilot, fill Section 4 with dated bars, cold reread.
2. Rename to `PREREG-G3C.md`, commit, record the blob hash in `CAMPAIGN.md`.
3. Draw the calibration seed, run the calibration block, write `predictions.json`, commit both
   with the file's sha256 in the commit message.
4. Only then draw the test seed, run the test block, grade, commit.

## 9. Known weaknesses

* One stimulus family. Arithmetic worksheets give an exact quality scale, and a judge's resolution
  on them need not transfer to prose answers.
* The prediction in 12a assumes a worksheet's score depends on its error count and not on which
  items are wrong. The pilot reports the within-level score variance so that a reader can see how
  much of the noise that assumption absorbs.
* 12a on its own is a test of stationarity and exchangeability. The content is in 12b and 12c,
  where a named rival and a predicted ordering can each fail.

## 10. Companion probe: a deliberation budget reverses a preference

Not part of this gate, and to be registered separately. Two fixed worksheets, the better one
plain and the worse one decorated with a confident header and a check mark on every line. With
no reasoning tokens the 7B judge preferred the better sheet in 8 percent of 24 pairs, at 64 tokens
in 42 percent, and at 512 tokens in 88 percent, with first-position preference 0.57, 0.78 and
0.57. With the decoration moved to the better sheet it preferred that sheet in every pair at zero
tokens. That is the theory's three regimes on one budget axis, reversal, indifference and
distinction, at probe level (`../G3b/feasibility/feasibility_flip*.json`).
