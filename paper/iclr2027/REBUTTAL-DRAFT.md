# Author response, draft skeleton

Written 2026-09-23, before submission, from the two external reviews already received and the
paper's own weaknesses list. Reviews are released 2026-11-05 and the discussion runs to
2026-11-18. Each objection below carries the answer the submitted paper already contains, then a
slot for what the rebuttal-window gates add. Slots marked `[G3g]` and `[G3h]` are filled only
from graded records, never from pilots.

The rule for the response itself: every sentence either points at a number in the paper or the
supplement, or concedes. No sentence argues for the merit of the work.

## 1. "The prediction is a plug-in consequence of stationarity"

**What the paper already says.** Section 1 concedes it outright: turning a measured channel into
a predicted curve is elementary once the channel is known. What it claims is not the formula.
It is that the prediction carried its bars before the data existed, held across six read-outs
and two stimulus families with those bars never refitted, failed where the instrument ran out of
resolution rather than at random, and extended to a reversal no plug-in produces.

**The sharpest single point.** The reversal (Section 5). Two influences are measured in blocks
where they never conflict, and their sum predicts both the sign of the preference and the budget
at which it flips. Stationarity says nothing about a flip.

`[G3h]` The crossing is now located on `qwen7b` to `[z]` noise units at `[k]` tokens, against
G3d's factor of two, and on a second judge, `qwen14b`, at `[k']`. Each judge's own calibration
predicts its own crossing. Records and registration in the supplement.

## 2. "Both stimulus families are synthetic"

**What the paper already says.** Scope names the limit: two families, neither prose, neither the
contested quality of an essay. The second family, summaries checked against a passage, is where
the judge does not do the task exactly, and the prediction held there inside bars set on
worksheets.

`[G3g]` A third family answers the half this leaves open. Reviews written by real readers, where
the label is the star rating that reader gave. It is a human judgement, in the writer's own
prose, and it is still exactly known, because it is what the person did and not an estimate of
anything. The calibration predicted the test block on `[n]` judges inside G3c's bars, transferred
unchanged: deviation `[dev]` against 0.14, `[z]` against 4.55.

`[G3g]` And the family is where the theory's central claim is tested on human text for the first
time: a length budget on the input. Reading the first 100 characters of a review instead of all
of it raised every threshold off the ladder floor, greedy `[3.09 / 3.04 / 2.72]` against
`[1.43 / 1.22 / 1.00]`, and the calibration at each budget predicted the test block at that
budget. `[table across 100, 200, 400, full]`.

## 3. "The margins are thin"

**Concede, and say which ones.** `gemma31b` clears the rank bar by 0.009 and `gemma12b` sits at
88 percent of the deviation bar on the summaries family. The paper says both, in Appendix F. A
harder family held less comfortably; that is what one should expect and it is reported rather
than smoothed.

`[G3g]` `[G3h]` Margins on the new gates, stated the same way whatever they are.

## 4. "One vendor on the new family"

**Concede.** G3f has two judges of one vendor and claims no breadth; breadth rests on G3c and G3e,
two vendors and three generations. The reason is measured and in the registration: the served
gateway's latency for the third judge collapsed by two orders of magnitude between probe and
block, with zero errors, and the run was withdrawn after sealing rather than left to consume a
shared service for four days.

`[G3g]` Same two judges, same concession, same reason.

## 5. "A registered claim failed"

**Yes, and it is the best thing in the paper.** C3e failed on `gemma31b` because seven read-outs
were pinned at the smallest gap the worksheets could express and tied read-outs cannot be
ranked. The mechanism was diagnosed from calibration blocks and recorded before the next seed was
drawn, and the predicted repair held on the sealed summaries block: two at the floor, tau 0.869.
That is what preregistration is for.

`[G3g]` The same mechanism, from the other side. On five-level reviews at full length the
design-matched null shows a faithful judge fails the transferred tau bar 96.2 percent of the
time, so the read-out ordering claim was declared untestable there before sealing, and tested
only at truncated budgets where thresholds sit above the floor. The instrument's limit is stated
as a limit, not discovered as a failure.

## 6. "The practitioner rules are not surprising"

**Partly concede.** Reading the expected score from the logits is G-Eval's. What is new is that
its effect on the threshold is predicted before it is measured, and that a hard token cap can
leave a reasoning judge worse than no reasoning, which is measured and not assumed. If a reviewer
wants a deployment-shaped demonstration, that is the one gap this response cannot close with a
sealed record, and it should say so rather than promise one.

## 7. Provenance, if asked

Registration sealed and pushed while no test seed existed; predictions committed and pushed; seed
drawn only then. The commit graph records the order, the prediction commits are ancestors of the
seed commit, and it is checkable against the public repository after deanonymisation. Not a
third-party timestamp, and the paper does not call it one. The notebook in the supplement
re-grades both served gates from the raw score records and reproduces every verdict.

## What must be true before any slot is filled

* The gate is sealed, its registration's blob is in the ledger, and the manifest reports it.
* Its verdict is graded by the registered script and its record ships with score files.
* `reproduce.ipynb` re-grades it and agrees.
* The number quoted is the one in `verdicts.json`, rounded the way the paper rounds.
