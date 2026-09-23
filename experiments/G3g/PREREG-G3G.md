# PREREG G3g: the same resolution law where the label is a human judgement

Status: DRAFT. Not sealed. The calibration seed is in the config, the test seed is not and is
drawn only after `predictions.json` is committed with its hash.

## Why this gate exists

G3c and G3e graded arithmetic worksheets. G3f graded summaries against a passage, which is a
harder judgement and answered the objection that the judge was doing the task exactly. Neither
answered the other half of it. In both families the campaign generated the text and defined the
quality, so a reader can say the method has only been shown to work where quality is a thing we
built rather than a thing a person decided.

G3g changes what quality MEANS rather than how hard it is to see.

The target here is not the quality of a book, which nobody knows and readers dispute. It is the
star rating that one particular reviewer gave, which is a recorded fact. That label is at once

* **exactly known**, because it is what a person did and not an estimate of anything,
* **a human judgement**, rendered by that person in their own prose, and
* **genuinely hard to recover**, because sarcasm, faint praise and mixed opinions are the norm.

There is no annotator-noise term because there is no second annotator to disagree. This is the
first family in the campaign where the quantity being predicted is a human decision and the
quantity is still exact, and asking a model what a reader thought is a deployed use of judges
rather than a proxy for one.

## What had been seen when this was written

G3c, G3d, G3e and G3f are graded and in the ledger. Their verdicts are not re-litigated here.

The G3g probe was run before this registration, on a probe seed no graded block uses, and its
numbers are in Section 6. Nothing else about G3g has been measured.

## 1. Claims under test

Each is G3c's claim, in G3c's words, on this family, graded per judge by `../G3c/judge_grade.py`,
unmodified.

**C1g (J1, GET-12a).** The accuracy curve of every read-out on the test block is predicted, at
every gap, by the judge's calibration block alone, inside the registered bars.

**C2g (J2, GET-12b).** The channel the judge uses predicts its curves better than a rival reading
the nominal scale at face value.

**C3g (J3, GET-12c).** The ordering of thresholds across read-outs is the ordering their symbol
budgets predict, with Kendall's tau at or above the bar and every threshold inside the registered
factor.

**C4g (J5, GET-12d).** The pairwise threshold sits at or above the floor the finest pointwise
read-out predicts. Recorded as AT FLOOR, COARSER or FINER; none is a failure of the theory.

A claim holds only if every graded judge passes it. A judge declared vacuous from its calibration
block is reported and not graded.

## 2. World, judges, elicitations

**Stimulus.** One Goodreads review of at least 400 and at most 3000 characters, drawn from the
balanced 200k sample at `/archive/results_aesthetics/bip_sample_200k.jsonl`, which holds exactly
40,000 reviews at each star rating. Quality is the rating its writer gave, mapped to an error
count `e = 5 - rating` so that `e` runs 0 to 4, `n_items = 4` and quality is `1 - e/4`. The block
builder's level loop and every estimator therefore carry over unchanged, and the gap ladder runs
1 to 4.

**Pool hygiene, decided before any block.** The pool is built in two passes. A review text that
appears under more than one rating has no well-defined label and is dropped. A text that repeats
under one rating is kept once. Each level's surviving texts are then split by index parity, and a
calibration block draws only from one half and a test block only from the other, so a review
cannot cross from calibration into test. Both properties are asserted by `g3g_stimuli.py
selftest`, which is what found them: the parity split alone left 176 reviews in both halves
because it partitions positions and the sample repeats texts. After deduplication the halves
share none. Levels retain roughly 24,600 to 27,100 reviews each, against blocks needing a few
hundred.

**Judges.** Pinned by what the service reports serving; the harness refuses a block if the served
string does not match.

| key | asked for | must be served as |
|---|---|---|
| `gemma31b` | `gemma` | `google/gemma-4-31B-it-qat-w4a16-ct` |
| `gemma12b` | `gemma4-12b` | `google/gemma-4-12B-it-qat-w4a16-ct` |

Two judges and one vendor. This gate buys a family and not breadth, and claims none.

**Elicitations.** G3c's six read-outs on three scales, unchanged, plus pairwise comparison in both
orders. The judge's scale need not match the five-level target; the channel maps one to the other
as it always has.

**Blocks.** Calibration: 168 reviews at each of the 5 levels, 840 in all. Test: 200 pairs at each
gap of 1, 2, 3 and 4.

## 3. Reading a served judge

As G3e and G3f. Twenty most probable tokens per position; the first-token distribution on the two
single-token scales; a digit tree above `tree_prune = 1e-4` on the 0 to 100 scale. Pruned mass,
mass outside the scale and mass on a non-digit first token are recorded per review.

## 4. Bars

**Every bar is G3c's, taken by reference and not refitted.** This needs saying carefully, because
the design changed and a reader is entitled to ask how a bar set on a different ladder can still
be the same bar. The six are not one object and do not have one provenance.

| bar | value | where it came from, per PREREG-G3C |
|---|---|---|
| `dev_max` | 0.14 | upper quantile of the null simulation |
| `z_max` | 4.55 | upper quantile of the null simulation |
| `threshold_factor` | 1.75 | upper quantile of the null simulation |
| `rank_agreement_min` | 0.86 | 1st percentile of the null |
| `vacuity_acc_min` | 0.9 | "written in this draft before any sizing run" |
| `vacuity_bits_min` | 1.0 | "set after the sizing calibrations were read" |

The last one was never a transferred null quantile in any gate. G3c set it by reading its own
pilot and disclosed doing so, and the paper repeats the disclosure. Setting it here from a G3g
pilot and disclosing it identically is therefore applying G3c's procedure, not weakening it. That
matters, because the probe shows every cell of this family at 0.78 to 0.91 bits: recovering a
stranger's rating carries irreducible ambiguity, so the extremes are not perfectly separable and
a bar of 1.0 bit would declare vacuous two judges that order those extremes at 0.97 to 1.00.

The four genuine null quantiles do transfer, and the design change pushes them in **opposite**
directions rather than uniformly loosening them. Relative to G3c this gate has 4 gaps instead of
7, so the family-wide maximum runs over 72 comparisons instead of 126, and 168 calibration
reviews per level instead of 40, so each level's channel is estimated about four times as
precisely. Both shrink the null spread of `dev_max` and of the studentised `z_max`, which makes
those two **conservative** here. Against that, thresholds estimated on four gaps are coarser than
on seven, which widens the null of `threshold_factor` and of the tau that `rank_agreement_min`
bounds, making those two **stricter** here. Two bars easier and two harder, none of them moved.

Because two of them are conservative, transferring alone would leave a reader unable to see by how
much. So a null simulation for THIS design is run on the pilot by the same procedure, and its
quantiles are reported beside the transferred bars **and not used to grade anything**. A reviewer
then sees exactly where each inherited bar sits against a design-matched one, and the leniency of
`dev_max` becomes a disclosed property rather than a discovery.

## 5. What falsifies

* C1g fails if any read-out of a graded judge misses `dev_max` or `z_max` at any gap.
* C2g fails if the nominal rival's squared error is below the measured channel's on any scale of
  any graded judge.
* C3g fails if tau is below the bar, or any threshold falls outside the factor, on any graded judge.
* The gate fails if any claim fails, and is VACUOUS if every judge is.

A judge is vacuous if, from its calibration block alone, it cannot order reviews four levels apart
with accuracy `vacuity_acc_min` on any scale, or carries less than `vacuity_bits_min` about
quality. Decided before the test seed is drawn.

## 6. Self-test and probe

**Stimulus self-test.** `g3g_stimuli.py selftest` builds 2,000 stimuli across the five levels,
checks none repeats and all sit in the length band, and asserts that the calibration and test
halves are disjoint both as defined and as drawn. It passes, and it is what found the two pool
defects recorded in Section 2.

**Probe**, 30 reviews at each of 5 levels on the probe seed, before this file was written:

| judge | scale | scores used | accuracy at a gap of 4 | bits about quality | unparsed |
|---|---|---|---|---|---|
| `gemma31b` | 1-5 | 5 | 0.998 | 0.776 | 0 |
| `gemma31b` | 0-9 | 10 | 0.998 | 0.859 | 0 |
| `gemma31b` | 0-100 | 17 | 0.999 | 0.816 | 0 |
| `gemma12b` | 1-5 | 5 | 0.999 | 0.852 | 0 |
| `gemma12b` | 0-9 | 10 | 0.970 | 0.825 | 0 |
| `gemma12b` | 0-100 | 20 | 1.000 | 0.911 | 0 |

Mean greedy score falls monotonically across all five levels on every scale for both judges. On
the 0 to 100 scale, `gemma31b` writes 17 of the 101 scores offered and `gemma12b` 20, so the
comparison against the nominal scale has room here as it did on the other families.

The probe does not decide anti-vacuity. That is decided from each judge's own calibration block by
the registered rule before its test seed is drawn. What the probe establishes is that the family is
worth a gate, what it costs, and that a bar of 1.0 bit cannot be the one applied.

## 7. Compute, and whose

No GPU of the authors'. Requests to NRP's managed LLM service at its published concurrency of
eight, judges run one after another. No pods are submitted and no GPU requested, so the cluster's
sizing and utilisation rules are not engaged. The service's latency is known to vary by two orders
of magnitude between hours, which withdrew a judge from G3f after sealing, so this gate registers
two judges and no more.

## 8. Known weaknesses

* Five levels, so the ladder has four gaps where the worksheet gates had seven, and thresholds are
  correspondingly coarser.
* Two judges, one vendor. No claim of breadth.
* One reviewer per review, so the label is exact but idiosyncratic. It is what that person did, not
  what a panel would have done, and nothing here says the two agree.
* Reviews are English-language Goodreads prose about books, which is one register.
* A judge may recognise a famous book and recall its reception rather than read the review. The
  label is the individual reviewer's rating, which recall cannot supply, but a recalled consensus
  could still bias a judge toward the crowd and away from this writer.

## 9. Sealing procedure

1. `g3g_config.json` carries the calibration seed and no test seed.
2. The pilot is run and the null simulation for this design computed from it.
3. This file is committed. Its git blob hash is recorded here and in the ledger.
4. Calibration blocks are run and `predictions.json` written and committed with its sha256.
5. Only then is the test seed drawn from a system random source and the test blocks run and graded.
