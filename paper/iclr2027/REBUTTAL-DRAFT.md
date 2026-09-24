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

**G3h, graded 2026-09-24, in the submission in Section 5 and Figure 3.** The crossing is now
located. On a second ladder built to bracket it (0, 16, 32, 48, 64, 96 tokens, same judge, fresh
seeds, G3d's bars unchanged) the calibration cells predicted the crossing at 72 tokens and the
sealed test block observed it at 57, 0.62 noise units against 2.576, with the bootstrap spread of
the comparison at 0.52 in log2 budget, a factor of 1.4 where G3d had 2.2. Additivity held at every
rung (largest 3.00 against 3.341) and the additive account beat both rivals by more than an order
of magnitude (1.7 against 64.4 and 16.4). Concede what the registration records: the first
draft's ladder of 64 to 256, the one the paper had named, was piloted and found the reversal
already at one half at 64 tokens, so the ladder was moved down before sealing, with the pilot
and its failed rival check kept in the registration; and the second judge named in that draft
was not run, its bf16 weights not fitting the one free card. One judge. Records and registration
in the supplement.

## 2. "Both stimulus families are synthetic"

**What the paper already says.** Scope names the limit: two families, neither prose, neither the
contested quality of an essay. The second family, summaries checked against a passage, is where
the judge does not do the task exactly, and the prediction held there inside bars set on
worksheets.

**G3g, graded 2026-09-23, in the submission as Appendix G and Table 7.** A third family answers
the half this leaves open. Reviews written by real readers, where the label is the star rating
that reader gave. It is a human judgement, in the writer's own prose, and it is still exactly
known, because it is what the person did and not an estimate of anything. The calibration
predicted the test block in all five graded cells inside G3c's bars, transferred unchanged:
deviations 0.035 to 0.084 against 0.14, noise units 2.45 to 3.08 against 4.55. The channel beat
the nominal scale in every cell.

And the family is where the theory's central claim is tested on human text for the first time: a
length budget on the input. The same reviews read to 200 characters, to 400, and whole. On
Gemma 4 31B the observed greedy threshold at 200 characters is 1.82, 1.82, 1.65 levels on the
three scales against 1.43, 1.27, 1.00 at full length, and the thresholds predicted from each
budget's own calibration fall along the ladder on every scale (1.84, 1.58, 1.35 on 1 to 5). The
claim was registered with both halves and both held. Concede in the same breath: it rests on
one judge, since Gemma 4 12B is vacuous at 200 characters by the registered rule (it orders
reviews four levels apart 0.76 to 0.80 of the time against 0.9), and the read-out ordering
statistic could not be graded on a five-level scale (the design-matched null fails a faithful
judge 31 to 96 percent of the time), so it is reported, at tau 0.64 to 0.90.

## 3. "The margins are thin"

**Concede, and say which ones.** `gemma31b` clears the rank bar by 0.009 and `gemma12b` sits at
88 percent of the deviation bar on the summaries family. The paper says both, in Appendix F. A
harder family held less comfortably; that is what one should expect and it is reported rather
than smoothed.

**G3g.** Largest deviation 0.084 against 0.14 and largest 3.08 noise units against 4.55, on a
design where the transferred noise-unit bar is stricter than in the gate that set it (false
alarm 3.8 to 5.8 percent per cell against 1.4), so these margins are not the null's. One cell of
six is vacuous, and the paper says so.

**G3h.** The additivity margin is thin at one rung, 3.00 against 3.341 in the reversal cell at
16 tokens; the crossing margin is wide, 0.62 against 2.576.

## 4. "One vendor on the new family"

**Concede.** G3f has two judges of one vendor and claims no breadth; breadth rests on G3c and G3e,
two vendors and three generations. The reason is measured and in the registration: the served
gateway's latency for the third judge collapsed by two orders of magnitude between probe and
block, with zero errors, and the run was withdrawn after sealing rather than left to consume a
shared service for four days.

**G3g.** Same two judges, same concession. Gemma 4 12B is graded at two of three input lengths
and vacuous at the third, so the budget claim rests on Gemma 4 31B alone.

## 5. "A registered claim failed"

**Yes, and it is the best thing in the paper.** C3e failed on `gemma31b` because seven read-outs
were pinned at the smallest gap the worksheets could express and tied read-outs cannot be
ranked. The mechanism was diagnosed from calibration blocks and recorded before the next seed was
drawn, and the predicted repair held on the sealed summaries block: two at the floor, tau 0.869.
That is what preregistration is for.

**G3g.** The same mechanism, from the other side. On five-level reviews the design-matched null
shows a faithful judge fails the transferred tau bar 96 percent of the time at full length and
31 to 56 percent at the shorter budgets, so the read-out ordering claim was declared not gradable
on this family before sealing, and is reported in every cell (tau 0.64 to 0.90, up to ten of
eighteen read-outs at the floor). The instrument's limit is stated as a limit, not discovered as
a failure. One correction is recorded in the registration after grading: the orchestrator first
walked the budget ladder in the reverse of the registered direction and reported the budget
claim as failed; the claim as written held on every scale, and the per-cell grader was never
touched. Say it before a reviewer finds it.

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
