# PREREG G3g: the same resolution law where the label is a human judgement, at three input budgets

Status: SEALED 2026-09-23 at blob 3f90e5010498416c081237fc33f368ca5610c7b0 (commit a2c33b2). GRADED
2026-09-23, PASS. Two corrections after the seal, recorded at the end of Section 9. The calibration seed is in the
config, the test seed is drawn once, for every cell at once, only after every cell's
`predictions.json` is in a pushed commit with its hash.

## Why this gate exists

G3c and G3e graded arithmetic worksheets. G3f graded summaries against a passage, which is a
harder judgement and answered the objection that the judge was doing the task exactly. Neither
answered the other half of it. In both families the campaign generated the text and defined the
quality, so a reader can say the method has only been shown to work where quality is a thing we
built rather than a thing a person decided.

G3g changes what quality MEANS rather than how hard it is to see, and it does one more thing that
no earlier gate did. It puts a budget on the input.

The target is not the quality of a book, which nobody knows and readers dispute. It is the star
rating that one particular reviewer gave, which is a recorded fact. That label is at once

* **exactly known**, because it is what a person did and not an estimate of anything,
* **a human judgement**, rendered by that person in their own prose, and
* **genuinely hard to recover**, because sarcasm, faint praise and mixed opinions are the norm.

There is no annotator-noise term because there is no second annotator to disagree. This is the
first family in the campaign where the quantity being predicted is a human decision and the
quantity is still exact, and asking a model what a reader thought is a deployed use of judges
rather than a proxy for one.

The input budget is the theory's own construct, a length budget, applied to real prose. The
judge reads the first 200 characters of each review, or the first 400, or all of it, and the
label is never cut. The theory says resolution coarsens as the budget shrinks. Whether it does,
and whether each budget's calibration predicts that budget's test block, is what the ladder tests.

## What had been seen when this was written

G3c, G3d, G3e and G3f are graded and in the ledger. Their verdicts are not re-litigated here.

Three things about G3g were measured before this file was sealed, all on seeds no graded block
uses, and all are disclosed in Section 6.

1. A probe, 30 reviews per level on the probe seed, both judges, full length.
2. A pilot on one judge, `gemma31b`, both blocks at the pilot seeds, at full length and at 100,
   200 and 400 characters. It grades nothing. Its purpose was to measure noise and cost, to show
   whether thresholds move with the input budget, and to give each cell the population its
   design-matched null draws from.
3. Four null simulations, one per pilot cell, by G3c's procedure and code. They fix no bar. They
   are reported beside the transferred bars so a reader can see what each bar costs here.

The pilot decided two things recorded below and nothing else: the 100-character cell is dropped
from the ladder because the judge is vacuous there by the a-priori rule, and the read-out
ordering claim is reported and not graded on this family because the nulls show the instrument
cannot rank read-outs on a five-level scale at any budget.

## 1. Claims under test

Each of the first four is G3c's claim, in G3c's words, on this family, per cell, graded per judge
by `../G3c/judge_grade.py`, unmodified. The fifth is new and runs across cells.

**C1g (J1, GET-12a).** In every cell, the accuracy curve of every read-out on the test block is
predicted, at every gap, by the judge's calibration block in that cell alone, inside the
registered bars.

**C2g (J2, GET-12b).** In every cell, the channel the judge uses predicts its curves better than a
rival reading the nominal scale at face value.

**C3g (J3, GET-12c), reported and not graded.** The ordering of thresholds across read-outs is the
ordering their symbol budgets predict. Kendall's tau and the share of thresholds inside the
registered factor are computed and reported in every cell. No cell grades them, for the reason
given in Section 4 and decided before sealing: on a five-level scale a faithful judge fails the
transferred tau bar between 31 and 96 percent of the time.

**C4g (J5, GET-12d).** In every cell, the pairwise threshold sits at or above the floor the finest
pointwise read-out predicts. Recorded as AT FLOOR, COARSER or FINER; none is a failure.

**C5g, resolution is ordered by the input budget.** For every graded judge and on every scale,
the observed greedy threshold at 200 characters exceeds the observed greedy threshold at full
length, and the greedy thresholds predicted from calibration are non-increasing along the ladder
200, 400, full. The ends are graded on held-out data. The middle rung's place is graded on the
calibration predictions, which rest on 840 reviews per cell, because a rung 400 characters from
its neighbours can sit inside test noise of an observed threshold and a claim that noise decides
is not a claim.

A claim holds only if every graded judge passes it in every cell it is graded in. A judge declared
vacuous in a cell from its calibration block is reported and not graded in that cell. C5g is
graded for a judge only if it is graded in all three cells.

## 2. World, judges, elicitations

**Stimulus.** One Goodreads review of at least 400 and at most 3000 characters, drawn from the
balanced 200k sample at `/archive/results_aesthetics/bip_sample_200k.jsonl`, which holds exactly
40,000 reviews at each star rating. Quality is the rating its writer gave, mapped to an error
count `e = 5 - rating` so that `e` runs 0 to 4, `n_items = 4` and quality is `1 - e/4`. The block
builder's level loop and every estimator therefore carry over unchanged, and the gap ladder runs
1 to 4. In the pilot's blocks the median review is 786 characters long, the tenth percentile 458
and the ninetieth 1602, and two in a thousand are 400 characters or shorter.

**Input budget, the truncation ladder.** Three cells: `200`, `400` and `full`. In a cell of
budget L the judge is shown the first L characters of the review, cut back to the last space so
no word is split. The label is the reviewer's rating whatever the judge saw. One calibration seed
and one test seed serve every cell, so the three cells score the same reviews and the same test
pairs, cut to different lengths, and differ in nothing else. The config carries the ladder as
`truncation_ladder`. A fourth cell at 100 characters was piloted and is dropped, Section 6.

**Pool hygiene, decided before any block.** The pool is built in two passes. A review text that
appears under more than one rating has no well-defined label and is dropped. A text that repeats
under one rating is kept once. Each level's surviving texts are then split by index parity, and a
calibration block draws only from one half and a test block only from the other, so a review
cannot cross from calibration into test. Both properties are asserted by `g3g_stimuli.py
selftest`, which is what found them: the parity split alone left 176 reviews in both halves
because it partitions positions and the sample repeats texts. After deduplication the halves
share none. Levels retain roughly 24,600 to 27,100 reviews each, against blocks needing a few
hundred. The pilot drew from the same halves on its own seeds, so a pilot review can recur in the
registered blocks; nothing was graded on the pilot and the null draws its population from it,
which is what the null is for.

**Judges.** Pinned by what the service reports serving; the harness refuses a block if the served
string does not match.

| key | asked for | must be served as |
|---|---|---|
| `gemma31b` | `gemma` | `google/gemma-4-31B-it-qat-w4a16-ct` |
| `gemma12b` | `gemma4-12b` | `google/gemma-4-12B-it-qat-w4a16-ct` |

Two judges and one vendor. This gate buys a family and a budget ladder and not breadth, and
claims none.

**Elicitations.** G3c's six read-outs on three scales, unchanged, plus pairwise comparison in both
orders. The judge's scale need not match the five-level target; the channel maps one to the other
as it always has.

**Blocks.** Calibration: 168 reviews at each of the 5 levels, 840 in all, per cell. Test: 200
pairs at each gap of 1, 2, 3 and 4, per cell. Six calibration blocks and six test blocks in all.

## 3. Reading a served judge

As G3e and G3f. Twenty most probable tokens per position; the first-token distribution on the two
single-token scales; a digit tree above `tree_prune = 1e-4` on the 0 to 100 scale. Pruned mass,
mass outside the scale and mass on a non-digit first token are recorded per review. A review on
which no scale token is among the twenty visible is recorded as unparsed, with every read-out
missing, and counted; the pilot saw at most one per block of 1,600 above 100 characters.

## 4. Bars

**Five bars are G3c's, taken by reference and not refitted. The sixth is G3c's scaled by the
capacity of the quality scale, and disclosed.** The six are not one object and do not have one
provenance, and a reader is entitled to ask how a bar set on a different ladder can still be the
same bar, so each is stated with its origin.

| bar | value | where it came from, per PREREG-G3C |
|---|---|---|
| `dev_max` | 0.14 | upper quantile of the null simulation |
| `z_max` | 4.55 | upper quantile of the null simulation |
| `threshold_factor` | 1.75 | upper quantile of the null simulation |
| `rank_agreement_min` | 0.86 | 1st percentile of the null |
| `vacuity_acc_min` | 0.9 | "written in this draft before any sizing run" |
| `vacuity_bits_min` | 0.5 | G3c's 1.0 bit scaled by log2(5)/log2(21) = 0.53, rounded down |

**The bits bar.** G3c set its bits bar at one bit after its sizing calibrations were read, and
recorded that it "changes no judge's status, because the accuracy bar alone already decides every
judge seen". The bar was a reading of a 21-level scale, on which a judge can carry up to
log2(21) = 4.39 bits about quality. A five-level scale carries at most log2(5) = 2.32 bits, so
the same fraction of capacity is 0.53 bits, and the bar here is 0.5. It was set before sealing,
after the pilot was read, exactly as G3c set its own, and it is disclosed for the same reason. On
every pilot cell it agrees with the a-priori accuracy bar: the cells the accuracy bar admits
(full, 400, 200) carry 0.54 to 1.09 bits and the cell it rejects (100) carries 0.38 to 0.47. A
bar of 1.0 bit would have declared the 400 and 200 cells vacuous at 0.54 to 0.80 bits while the
judge orders reviews four levels apart in them at 0.90 to 0.95, which is the accuracy bar's own
test passed, and that is why 1.0 is not the bar applied. The choice is disclosed so a reader can
undo it: the record carries every cell's bits, and Section 6 shows what 1.0 would have done.

**The four null quantiles transfer, and the design change moves their cost in both directions.**
Relative to G3c this gate has 4 gaps instead of 7, so the family-wide maximum runs over 72
comparisons instead of 126, and 168 calibration reviews per level instead of 40. Thresholds read
on four gaps are coarser than on seven, and on a five-level scale most read-outs sit within a
level of each other. Rather than argue which way each bar moves, a null simulation for THIS
design was run on the pilot of each cell by G3c's procedure and code, `../G3c/null_bars.py`
unmodified, 1000 replicates per truncated cell and 500 at full length, and its quantiles are
reported here beside the transferred bars **and used to grade nothing**.

| cell | null q99 of dev | of z | of ratio | null q1 of tau | median tau | faithful judge fails tau 0.86 | fails transferred dev, z, ratio | fails any of the three |
|---|---|---|---|---|---|---|---|---|
| full | 0.110 | 6.69 | 1.34 | 0.314 | 0.706 | 96.2 % | 0.0, 5.8, 0.0 % | 5.8 % |
| 400 | 0.117 | 6.40 | 1.43 | 0.627 | 0.889 | 31.4 % | 0.0, 4.3, 0.0 % | 4.3 % |
| 200 | 0.126 | 5.22 | 1.50 | 0.627 | 0.850 | 55.9 % | 0.4, 3.8, 0.0 % | 4.2 % |
| 100, dropped | 0.158 | 4.85 | 1.85 | 0.555 | 0.778 | 87.7 % | 3.6, 1.6, 2.1 % | 5.6 % |

Records: `pilot_record/null/null_bars_<cell>.json` and `null_rows_<cell>.json`, where the
full-length cell is named `g3g`.

Three consequences, each decided here and not after the run.

* **`dev_max` and `threshold_factor` are lenient here** (a faithful judge never reaches 0.14 or
  1.75 in the three graded cells), **and `z_max` is stricter** (a faithful judge exceeds 4.55 in
  3.8 to 5.8 percent of replicates per cell, against 1.4 percent in G3c). So C1g under the
  transferred bars is a harder test than G3c set itself, and across two judges and three cells a
  pair of faithful judges fails C1g somewhere in at most about one run in four. The bars are not
  moved. The record reports, for every cell, the largest z beside both the transferred 4.55 and
  the design-matched 99th percentile, so a miss that lies inside the design-matched quantile is
  reported as exactly that, a miss against G3c's bar and not against one set for this design, and
  the claim's class is not raised by it.
* **`rank_agreement_min` cannot be tested on this family.** The median faithful tau is 0.71 to
  0.89 and the bar is 0.86, so C3g would fail a faithful judge in 31 to 96 percent of replicates
  depending on the cell. A gate that fails a faithful judge one time in three is not measuring
  the judge. C3g is therefore reported in every cell, with its tau and the share of thresholds
  inside the factor, and graded in none. The config records this as `c3g_graded_cells = []`.
  This is the same mechanism G3e found from the other side, read-outs piling onto the floor of
  the ladder, and here the floor is one level of a five-level scale: at full length 8 of the
  pilot judge's 18 read-outs sit there.
* **The 100-character cell is dropped.** The pilot judge's greedy accuracy at a gap of four is
  0.79 to 0.80 there, below the a-priori 0.9, so the registered rule would declare it vacuous
  from its calibration block, and registering a block known to be vacuous spends a shared service
  to record nothing. Its pilot and null are kept and reported.

## 5. What falsifies

* C1g fails if any read-out of a graded judge in any cell misses `dev_max` or `z_max` at any gap.
* C2g fails if the nominal rival's squared error is below the measured channel's on any scale of
  any graded judge in any cell.
* C5g fails if, for any graded judge on any scale, the observed greedy threshold at 200
  characters does not exceed the one at full length, or the predicted greedy thresholds are not
  non-increasing along 200, 400, full.
* The gate fails if C1g, C2g or C5g fails, and is VACUOUS if every judge is vacuous in every cell.
* C3g and C4g are reported and cannot fail the gate.

A judge is vacuous in a cell if, from its calibration block in that cell alone, it cannot order
reviews four levels apart with accuracy `vacuity_acc_min` on any scale, or carries less than
`vacuity_bits_min` about quality on every scale. Decided before the test seed is drawn.

## 6. Self-test, probe, pilot

**Stimulus self-test.** `g3g_stimuli.py selftest` builds 2,000 stimuli across the five levels,
checks none repeats and all sit in the length band, and asserts that the calibration and test
halves are disjoint both as defined and as drawn. It passes, and it is what found the two pool
defects recorded in Section 2.

**Probe**, 30 reviews at each of 5 levels on the probe seed, full length, before the pilot:

| judge | scale | scores used | accuracy at a gap of 4 | bits about quality | unparsed |
|---|---|---|---|---|---|
| `gemma31b` | 1-5 | 5 | 0.998 | 0.776 | 0 |
| `gemma31b` | 0-9 | 10 | 0.998 | 0.859 | 0 |
| `gemma31b` | 0-100 | 17 | 0.999 | 0.816 | 0 |
| `gemma12b` | 1-5 | 5 | 0.999 | 0.852 | 0 |
| `gemma12b` | 0-9 | 10 | 0.970 | 0.825 | 0 |
| `gemma12b` | 0-100 | 20 | 1.000 | 0.911 | 0 |

The probe's bits are read on 30 reviews per level and are biased low against the pilot's 168;
they are superseded by the pilot below and are kept because they were seen.

**Pilot**, `gemma31b` only, calibration and test on the pilot seeds, every cell. Computed by
`g3g_pilot_table.py` from G3c's grader and stored in `pilot_record/pilot_table.json`. PILOT
numbers on PILOT seeds, none a verdict.

| cell | greedy acc at gap 4 (1-5, 0-9, 0-100) | bits | greedy threshold pred / obs (1-5, 0-9, 0-100) | dev | z | tau | at floor |
|---|---|---|---|---|---|---|---|
| full | 0.970, 0.970, 0.970 | 0.99, 1.01, 1.09 | 1.43 / 1.45, 1.22 / 1.14, 1.00 / 1.00 | 0.031 | 1.21 | 0.752 | 8 of 18 |
| 400 | 0.942, 0.947, 0.952 | 0.71, 0.74, 0.80 | 1.67 / 1.66, 1.45 / 1.51, 1.30 / 1.44 | 0.064 | 1.91 | 0.928 | 3 of 18 |
| 200 | 0.914, 0.899, 0.922 | 0.54, 0.58, 0.62 | 1.95 / 1.77, 1.79 / 1.69, 1.70 / 1.63 | 0.061 | 1.85 | 0.882 | 0 of 18 |
| 100, dropped | 0.786, 0.794, 0.798 | 0.38, 0.40, 0.47 | 3.09 / 2.73, 3.04 / 2.79, 2.72 / 2.73 | 0.073 | 2.00 | 0.817 | 0 of 18 |

What the pilot shows and what it does not. Every cell's calibration predicted its test block
inside the transferred bars on this judge, at a fifth to half of `dev_max` and `z_max`. Every
greedy threshold, predicted and observed, falls as the budget grows, on every scale, which is
C5g's shape with margins of 0.3 to 0.6 levels between the ends against a threshold noise the
nulls put near 0.1. The channel beat the nominal rival in every cell. The pairwise elicitation
read AT FLOOR in every cell. The unparsed count was at most one review per block above 100
characters and four at 100. None of that is a verdict, and the second judge has no pilot; its
cells are graded by the same rule from its own calibration blocks. What 1.0 bit would have done
is in the third column: it would have refused the 400 and 200 cells that the accuracy bar admits.

## 7. Compute, and whose

No GPU of the authors'. Requests to NRP's managed LLM service at its published concurrency of
eight, blocks run one after another. No pods are submitted and no GPU requested, so the cluster's
sizing and utilisation rules are not engaged. The pilot measured a calibration block at about
four and a half minutes and a test block at about ten and a half on `gemma31b` at full length,
and less at shorter budgets, so the twelve blocks cost about an hour and a half of the service
at the latency seen. The service's latency is known to vary by two orders of magnitude between
hours, which withdrew a judge from G3f after sealing, so this gate registers two judges and no
more, and a judge withdrawn for cost is recorded as G3f recorded it.

## 8. Known weaknesses

* Five levels, so the ladder has four gaps where the worksheet gates had seven, thresholds are
  correspondingly coarser, and the read-out ordering claim cannot be graded at all (Section 4).
* The transferred `z_max` is stricter here than in the gate that set it, so the gate can fail on
  a faithful judge about one time in four across its six judge-cells. Section 4 says how such a
  miss is reported.
* Two judges, one vendor. No claim of breadth.
* One judge was piloted. The other's noise and cost are assumed to be similar.
* One reviewer per review, so the label is exact but idiosyncratic. It is what that person did,
  not what a panel would have done, and nothing here says the two agree.
* Reviews are English-language Goodreads prose about books, which is one register.
* A judge may recognise a famous book and recall its reception rather than read the review. The
  label is the individual reviewer's rating, which recall cannot supply, but a recalled consensus
  could still bias a judge toward the crowd and away from this writer.
* The budget ladder has three rungs. It can show that resolution is ordered by the input budget
  and cannot show the shape of the dependence.

## 9. Sealing procedure

1. `g3g_config.json` carries the calibration seed, the truncation ladder, the bars of Section 4
   and no test seed. `g3g_preflight.py` reads this file and refuses any block whose config
   disagrees with it.
2. This file is committed. Its git blob hash is recorded in the preflight and in the ledger.
3. The six calibration blocks are run, `g3g_predict.py` writes one `predictions.json` per cell
   and judge, and all six are committed with their sha256.
4. Only then is one test seed drawn by `g3g_draw_test_seed.py` from a system random source,
   which refuses unless every `predictions.json` is committed as it stands on disk. The seed is
   committed.
5. The six test blocks are run and graded by `g3g_grade.py`, which grades with G3c's code and
   refuses predictions the seed was not drawn against.

**Deviation recorded 2026-09-23, after sealing and before any test block.** A test seed was
drawn once before step 3 had completed. The six `predictions.json` had been written and staged,
the signing of their commit timed out on an expired passphrase cache, and the shell ran the draw
step regardless. `g3g_draw_test_seed.py` inherited G3e's check, which read the git index rather
than a commit, so "committed" was satisfied by `git add` alone and the script drew a seed. That
seed, 1008647962, was never used: no test block was built from it, it was removed from the config
with its `test_seed.json`, and the predictions it was pinned to are byte-identical to the ones
committed afterwards, whose sha256 values are in `predictions_summary.json`. The check now reads
HEAD, so a seed cannot be drawn against a prediction that is not in a commit, and the seed used
by this gate is the one drawn after the predictions commit was pushed. The order the gate claims,
prediction then seed, held in time on both draws; what failed was the public record between them,
and it is repaired by discarding the draw that lacked it.

**Second deviation recorded 2026-09-23, after grading.** The first run of `g3g_grade.py` over the
sealed test blocks returned C5g FAIL, and the record shows why: the script walked the ladder in
the config's order, full length first, and so tested the predicted greedy thresholds for
non-increase from full to 200 characters, the reverse of the claim as written in Section 1
("non-increasing along the ladder 200, 400, full"). The data satisfy the claim as written on
every scale of the graded judge, predicted 1.84, 1.58, 1.35 on the 1 to 5 scale, 1.68, 1.36,
1.13 on 0 to 9, and 1.60, 1.21, 1.00 on 0 to 100 along 200, 400, full, and the observed ends
1.82 against 1.43, 1.82 against 1.27, and 1.65 against 1.00. The orchestrator now walks the
ladder as Section 1 states it; G3c's grader, which computes every per-cell number, was not
touched; and the regrade returns C5g PASS. The first verdict file is superseded and the defect
is stated here so that the verdict cannot be read as a script that was fixed until it passed:
what was fixed is the direction of a comparison that the registration fixes in words.

**Record note, 2026-09-23.** The sha256 values pinned in `run_record/test_seed.json` and quoted in
`verdicts.json` are of the `predictions.json` files as they stood on the machine that drew the
seed, where they carried CRLF line endings. Git stores the canonical LF form, whose blob hash is
also pinned, and the supplementary package ships that form, whose sha256 differs. The grader and
the reproduction notebook accept the same content under either line-ending convention and
nothing else, and the notebook checks the pinned blob hash as well, which is independent of line
endings. The content pinned, committed, packaged and graded is one content.
