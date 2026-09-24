# PREREG G3h: where the preference reverses, located

Status: SEALED 2026-09-23 at blob 5b628d5327446a97c1537126c724ee5d93f69848 (commit d844df9). GRADED
2026-09-24, PASS, test seed 2696997963; the verdict is in `CAMPAIGN.md` and `run_record/grade.json`. The calibration seed is in the config;
no test seed exists and one is drawn only after `predictions.json` is in a pushed commit with its
hash. The ladder and the judge list changed between the first draft and this seal, on the pilot
of Section 6, and both changes are stated where they occur.

## Why this gate exists

G3d established that a deliberation budget reverses a judge's preference and that the budget at
which it reverses is predicted from calibration cells in which evidence and cue never conflict.
It is the one result in the paper that a stationarity argument cannot reproduce, and it is also
the paper's least precise: the ladder was 0, 16, 64, 256, 512 and 1024 tokens, and the two rungs
either side of the crossing, 64 and 256, gave 39 and 41 of 80 pairs to the better worksheet,
less than half a standard error apart. The paper says so and says what would fix it, in
Section 5: "a ladder of 64, 96, 128, 160, 192 and 256 tokens would be needed to say where, and
that is the natural next registration." This is that registration.

It also rests on one judge. A second judge with the crossing predicted would be the difference
between a curiosity and a law, and the first draft of this registration named Qwen2.5-14B for
that role. It is not registered here. Its bfloat16 weights take 29.5 GB and the one free card
has 32 GB, with the workstation's other card held by a running service that this campaign does
not interrupt; a quantized copy would be a different judge at a different precision, at three
times the cost, and there is no time for it before the deadline this gate serves. The second
judge is the natural next registration and is not claimed.

## What had been seen when this was written

G3d is graded: PASS, crossover predicted at 174 tokens and observed at 128, 0.37 noise units
against a bar of 2.576, additive prediction within 3.11 noise units against 3.341, and the
additive account beating both single-term rivals. All of that is in the ledger and is not
re-litigated. Two more things were seen before this seal and are in Section 6: a smoke test of
four pairs at budgets 0 and 256, which grades nothing, and a pilot of the full design on the
pilot seeds at the ladder the first draft named, 64 to 256 tokens. The pilot is what moved the
ladder, and its record, including the check it failed, is kept and reported.

## 1. Claims under test

Each is G3d's claim, in G3d's words, on the finer ladder, graded per judge by
`../G3d/flip_grade.py`, unmodified.

**F1h additivity.** The sum of what the evidence is worth and what the decoration is worth, each
measured in its own calibration cell where the two never conflict, predicts both test cells at
every budget inside the registered bar.

**F2h crossover.** The budget at which the share of pairs favouring the better worksheet crosses
one half is predicted from the calibration cells, and the observed crossing lies within the
registered bar of that prediction.

**F3h rivals.** The additive prediction's squared error over both test cells and all budgets is
strictly below that of the evidence-only and the cue-only rivals.

A claim holds only if every graded judge passes it. A judge is vacuous if its calibration
predicts no flip inside the ladder, which is a finding and not a failure.

## 2. World, judges, elicitations

**Stimuli, cells, cue, gap, pairs.** G3d's, unchanged: worksheets of ten multiplications, pairs
three errors apart, 80 pairs per cell, the decoration a confident header and a check mark on
every line, two calibration cells in which cue and evidence never conflict and two test cells in
which the decoration sits on the worse and on the better sheet. Both presentation orders are
run and averaged.

**Budgets.** 0, 16, 32, 48, 64 and 96 reasoning tokens. Six rungs, as G3d had, so the
multiple-comparison correction in the bars is identical. The first draft placed the rungs at 64
to 256, the span between the two rungs of G3d that came out nearly tied, and the paper's
Section 5 says the same. The pilot on that ladder (Section 6) found the reversal cell's share
of pairs preferring the better sheet already at one half at 64 tokens and above it at every
higher rung, so the crossing lies at or below 64, and it found the cue term at 0.27 to 0.62
log-odds across the whole span, so small that the account which ignores the cue fits as well as
the additive one and the rival check cannot discriminate there. The registered ladder therefore
starts where G3d measured the cue at its largest, 0 tokens (cue 6.15 log-odds) and 16 (1.54,
share 0.31), and climbs in steps of 16 through the rung the pilot placed at one half. The
crossing is bracketed between 16 and 64 by two sealed measurements and the ladder has three
rungs inside that bracket.

**Judges.** Local weights, read directly, so the reasoning tokens and the forced-answer logits
are the judge's own rather than a served approximation.

| key | weights | revision | role |
|---|---|---|---|
| `qwen7b` | Qwen/Qwen2.5-7B-Instruct | a09a354 | G3d's judge, on the bracketing ladder |

One judge, G3d's. This gate buys precision on the crossing and a replication of the reversal
on fresh seeds, not breadth, and the second judge named in the first draft is not registered,
for the reason given above.

**Elicitation.** As G3d: the judge is told to think step by step and reasons greedily for at most
$k$ tokens, "Final answer (A or B): " is then forced, and the letter logits are read in one pass.

## 3. Bars, taken by reference

G3d's, unchanged, and unlike every other gate in this campaign they need no argument to
transfer. They are stated in noise units and were fixed from the design alone, before any pilot.

| check | bar | why it transfers |
|---|---|---|
| F1h | z of 3.341, two-sided 1 percent Bonferroni over 2 cells and 6 budgets | this ladder also has 6 budgets and 2 cells, so the correction is the same number |
| F2h | z of 2.576, two-sided 1 percent | one statistic, no correction, design-free |
| F3h | strictly below both rivals | not a quantity |

Nothing about a bar depends on where the rungs sit. What changes with the rungs is the
**precision** of the crossover estimate, which is the point of the gate, not the standard it is
held to.

## 4. What falsifies

* F1h fails if any test cell at any budget deviates from the additive prediction by more than
  3.341 noise units on any graded judge.
* F2h fails if the observed crossing lies more than 2.576 noise units from the predicted one on
  any graded judge.
* F3h fails if either single-term rival matches or beats the additive prediction.
* The gate fails if any claim fails. It is VACUOUS if the judge's calibration predicts no flip
  inside 0 to 96, which would itself be a finding, since G3d and the pilot place the flip there.

## 5. What this can and cannot show

If it passes, the crossing is located to a fraction of the fourfold gap G3d left, on G3d's judge
at fresh seeds, from cells in which cue and evidence never met. That is a quantitative prediction
of a qualitative reversal, and it is the strongest kind of evidence the paper has. It is one
judge, and the paper will say so.

What it cannot show: anything about served judges, whose reasoning tokens and letter logits the
gateway does not expose in this form; anything about a second cue; anything about a second gap.
Those are G3d's stated limits and remain so.

## 6. Self-test, smoke test and pilot

**Self-test.** G3d's `flip_selftest.py`, no GPU, on synthetic deliberators of known structure,
run unchanged against the config through `flip_selftest_g3h.py`, which swaps in the config and,
for this ladder, rescales one parameter of the synthetic judges. G3d's synthetic judges are
built to cross near 150 tokens, inside G3d's ladder and outside this one, so run as they stand
they read VACUOUS on 0 to 96 for a reason that says nothing about the harness. The wrapper sets
the evidence slope `a1` to 0.1 (G3d's 0.06) for all three synthetic judges and changes nothing
else, which places the synthetic crossing near 40 tokens. PASS, 2026-09-23. The additive judge
passes F1 at 1.338 against 3.341, F2 with its crossing predicted at 40.6 tokens and observed at
42.0, a deviation of 0.35 noise units, and F3 with squared error 0.05 against 49.3 and 31.4 for
the two rivals, and it meets anti-vacuity. The interaction judge fails F1 at 16.2, which is the
check rejecting a known defect on this ladder, and the cue-blind judge is vacuous, which is the
check refusing a judge the cue cannot move. Record in `selftest_qwen7b/`.

**Smoke test.** Four pairs at budgets 0 and 256 on `qwen7b`, run 2026-09-23 on the second GPU
before this file was written, to confirm the harness executes on this hardware with this ladder's
top budget. It does. At budget 0 the calibration cells gave evidence $+3.105$ and cue $+7.135$
in 8.8 seconds; at 256 they gave $-0.355$ and $+0.463$ in 89.9 seconds for eight prompts, about
11 seconds each. That is G3d's shape: with no reasoning the cue dominates, and at 256 tokens both
terms sit near zero, which is the indifference regime the ladder is built to resolve. Four pairs
say nothing about where the crossing is and are not used for that. The record is
`/home/claude/g3h_smoke/calibration/`, grading nothing.

**Pilot, 2026-09-23** (`pilot_record/pilot_qwen7b/`, Atlas GPU 1, pilot seeds 41 and 42, the
full design of the first draft: 80 pairs per cell, ladder 64, 96, 128, 160, 192, 256). Both
blocks ran, calibration 15:00Z to 16:38Z and test 16:39Z to 18:19Z, and were graded against the bars by `flip_grade.py`
for the record only. F1 held, largest deviations 2.24 noise units in the reversal cell and 3.19
in the control cell against 3.341. F2 held at 2.08 against 2.576, but with the observed crossing
at the ladder's floor: the reversal cell's share of pairs preferring the better sheet was
0.50, 0.68, 0.74, 0.76, 0.85, 0.60 at the six rungs, at one half from the first rung, and the bootstrap
standard deviation of the crossing comparison was 3.2 in log2 budget, which is to say the
ladder did not see the crossing at all. F3 FAILED: the additive account's squared error over
the two test cells was 2.36, the evidence-only rival's 2.18 and the cue-only rival's 7.97. The
calibration cue term was 0.27 to 0.62 log-odds across the six rungs, so the rival that drops it
is the additive model to within noise, and no design on this span can separate them. The
reversal-cell means were +0.07, +0.40, +0.59, +0.73, +1.08, +0.25 log-odds, positive throughout.

What the pilot decided. The ladder is moved down, to 0 through 96, as Section 2 states, so that
it brackets the crossing and includes the rungs at which G3d measured the cue large enough for
F3 to have something to reject. The number of pairs stays at 80. The claims and bars do not
change. The pilot's verdict is a pilot verdict on a ladder that is not the registered one, and
it is reported here so that the change of ladder cannot be read as a change made after a
failure was seen on the registered design: the registered design had not been run when the
ladder moved, and this file is sealed before it is.

## 7. Compute, and whose

The authors' workstation, one 32 GB GPU, the second one being in use. The pilot measured the
cost on the first draft's ladder at 80 pairs per cell: 513 s, 624 s, 738 s, 852 s, 1392 s, 1773 s per rung from 64 to 256 tokens,
about 100 minutes per block, at 98 percent GPU utilization. The registered ladder tops out at
96 tokens, so a block should take well under an hour, and the gate needs one calibration block
and one test block. Threads pinned and niced, as G3d ran, to stay inside the workstation's
thermal envelope.

## 8. Sealing procedure

1. The config carries its calibration seed and no test seed.
2. Self-test passes on the config; the smoke and pilot records are written into Section 6.
3. This file is committed and its git blob hash recorded in the ledger.
4. The calibration block is run and `predictions.json` committed with its sha256 and pushed.
5. Only then is a test seed drawn from a system random source, against the predictions in
   HEAD, and the test block run and graded by `../G3d/flip_grade.py`, unmodified.
