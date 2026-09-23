# PREREG G3h: where the preference reverses, located

Status: DRAFT. Not sealed. Calibration seeds are in the configs; no test seed exists and one is
drawn only after each judge's `predictions.json` is committed with its hash.

## Why this gate exists

G3d established that a deliberation budget reverses a judge's preference and that the budget at
which it reverses is predicted from calibration cells in which evidence and cue never conflict.
It is the one result in the paper that a stationarity argument cannot reproduce, and it is also
the paper's least precise: the ladder was 0, 16, 64, 256, 512 and 1024 tokens, and the two rungs
either side of the crossing, 64 and 256, gave 39 and 41 of 80 pairs to the better worksheet,
less than half a standard error apart. The paper says so and says what would fix it, in
Section 5: "a ladder of 64, 96, 128, 160, 192 and 256 tokens would be needed to say where, and
that is the natural next registration." This is that registration.

It also rests on one judge. A second judge with the crossing predicted is the difference between
a curiosity and a law.

## What had been seen when this was written

G3d is graded: PASS, crossover predicted at 174 tokens and observed at 128, 0.37 noise units
against a bar of 2.576, additive prediction within 3.11 noise units against 3.341, and the
additive account beating both single-term rivals. All of that is in the ledger and is not
re-litigated. The G3h smoke test, four pairs at budgets 0 and 256 on the replicate judge, was
run to confirm the harness still executes on this hardware; it grades nothing and its record is
in Section 6.

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

**Budgets.** 64, 96, 128, 160, 192 and 256 reasoning tokens. Six rungs, as G3d had, so the
multiple-comparison correction in the bars is identical, but concentrated across the fourfold
span in which G3d's crossing fell rather than spread over four orders of magnitude.

**Judges.** Local weights, read directly, so the reasoning tokens and the forced-answer logits
are the judge's own rather than a served approximation.

| key | weights | revision | role |
|---|---|---|---|
| `qwen7b` | Qwen/Qwen2.5-7B-Instruct | a09a354 | G3d's judge, replicated on the finer ladder |
| `qwen14b` | Qwen/Qwen2.5-14B-Instruct | cf98f3b | second judge |

Two judges of one family. This gate buys precision and a replication, not vendor breadth.

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
* The gate fails if any claim fails. It is VACUOUS if every judge's calibration predicts no flip
  inside 64 to 256, which would itself be a finding, since G3d placed the flip there.

## 5. What this can and cannot show

If it passes on both judges, the crossing is located to a fraction of the fourfold gap G3d left,
on two judges, from cells in which cue and evidence never met. That is a quantitative prediction
of a qualitative reversal, and it is the strongest kind of evidence the paper has.

If `qwen14b` crosses at a different budget than `qwen7b`, that is expected and not a failure: the
claim is that each judge's own calibration predicts its own crossing, not that all judges cross
together.

What it cannot show: anything about served judges, whose reasoning tokens and letter logits the
gateway does not expose in this form; anything about a second cue; anything about a second gap.
Those are G3d's stated limits and remain so.

## 6. Self-test, smoke test and pilot

**Self-test.** G3d's `flip_selftest.py`, no GPU, on synthetic deliberators of known structure,
run unchanged against each G3h config before sealing.

**Smoke test.** Four pairs at budgets 0 and 256 on `qwen7b`, to confirm the harness executes on
this hardware with this ladder's top budget. Record: `[pending]`.

**Pilot.** Both blocks on each judge at the pilot seeds, to measure noise and cost. It may change
the number of pairs and nothing else, exactly as G3d's registration allows.

## 7. Compute, and whose

The authors' workstation, one 32 GB GPU, the second one being in use. G3d measured about 19
seconds per prompt at 1024 tokens on this card; the top of this ladder is 256, so the run is
cheaper per prompt by roughly the ratio of budgets. Threads pinned and niced, as G3d ran, to
stay inside the workstation's thermal envelope.

## 8. Sealing procedure

1. Each config carries its calibration seed and no test seed.
2. Self-test passes on each config; the smoke record is written into Section 6.
3. This file is committed and its git blob hash recorded here and in the ledger.
4. Calibration blocks are run and each judge's `predictions.json` committed with its sha256.
5. Only then is a test seed drawn from a system random source, per judge, and the test blocks
   run and graded.
