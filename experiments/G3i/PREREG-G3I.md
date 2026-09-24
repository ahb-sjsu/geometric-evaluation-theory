# PREREG G3i: the reversal on two other vendors' judges

Status: DRAFT. Not sealed. The calibration seed is in the configs; no test seed exists and one is
drawn, per judge, only after that judge's `predictions.json` is in a pushed commit with its hash.

## Why this gate exists

G3d showed that a deliberation budget reverses a judge's preference and that the budget at which
it reverses is predicted from cells in which evidence and cue never conflict. G3h located the
crossing on the same judge, to a factor of 1.4. Both rest on one judge, Qwen2.5-7B, and a reader
is entitled to ask whether the reversal, the additivity of evidence and cue, and the prediction of
the crossing are facts about that judge or about judges. This gate asks two judges from two other
vendors, with nothing else changed.

## What had been seen when this was written

G3d and G3h are graded, PASS, and in the ledger. Their designs and bars are inherited here
unchanged. Nothing had been measured on either judge named below when this file was drafted; the
smoke test and pilot that follow are recorded in Section 6 before the seal, and the seal is what
fixes this file.

## 1. Claims under test

G3d's three claims, in G3d's words, per judge, graded per judge by `../G3d/flip_grade.py`,
unmodified: F1 additivity, F2 crossover predicted, F3 the additive account beating both
single-term rivals (see `../G3h/PREREG-G3H.md` Section 1 for the statements). A claim holds only
if every graded judge passes it. A judge is VACUOUS if its calibration predicts no flip inside the
ladder, which is a finding about that judge and not a failure of the gate, and its record is
reported and not graded.

Different judges may cross at different budgets. The claim is that each judge's own calibration
predicts its own crossing, not that judges cross together.

## 2. World, judges, elicitations

**Stimuli, cells, cue, gap, pairs, budgets.** G3h's, unchanged: worksheets of ten multiplications,
pairs three errors apart, 80 pairs per cell, the decoration a confident header and a check mark on
every line, two calibration cells and two test cells, both presentation orders, and the ladder 0,
16, 32, 48, 64 and 96 reasoning tokens. Six rungs, so the multiple-comparison correction in the
bars is G3d's number.

**Judges.** Local weights, read directly, in bfloat16, from mirrors that carry no access gate so
that the record can be rebuilt by anyone.

| key | weights | revision | vendor |
|---|---|---|---|
| `llama8b` | unsloth/Llama-3.1-8B-Instruct | 4699cc75b550f9c6f3173fb80f4703b62d946aa5 | Meta |
| `gemma12b` | unsloth/gemma-3-12b-it | 9478e665381f42974aa06177b019352fb6291876 | Google |

The mirrors are byte-identical republications of Meta's and Google's instruction-tuned weights
by their revision, without the license click-through that the originals require. Two judges,
two vendors, each a third vendor relative to the paper's other reversal judge.

**Elicitation.** As G3d: the judge is told to think step by step and reasons greedily for at most
$k$ tokens, "Final answer (A or B): " is then forced, and the letter logits are read in one pass.
Each judge's own chat template is applied by the harness, as it was for Qwen.

## 3. Bars, taken by reference

G3d's, unchanged, in noise units, fixed from the design alone before any pilot: F1 at z 3.341
(two-sided 1 percent Bonferroni over 2 cells and 6 budgets), F2 at z 2.576, F3 strictly below
both rivals. Nothing about a bar depends on the judge.

## 4. What falsifies

As G3h Section 4, per judge. The gate fails if any claim fails on any graded judge, and is
VACUOUS if every judge is.

## 5. What this can and cannot show

If both pass, the reversal, its additivity and the prediction of its crossing hold on three
vendors' judges, each predicted from its own calibration. If one is vacuous, the gate says which
judge the cue cannot move at any rung, which is itself a fact worth the record, and the claim
rests on the other. What it cannot show: anything about a second cue, a second gap, or a served
judge.

## 6. Self-test, smoke test and pilot

**Self-test.** G3d's `flip_selftest.py`, unchanged, through `flip_selftest_g3i.py`, with the
synthetic evidence slope rescaled to 0.1 as in G3h so that the synthetic crossing lies inside
this ladder. PASS on both configs, 2026-09-24, identically, since the synthetic judges do not
depend on which weights the config names.

**Smoke test.** To be recorded before the seal: four pairs at budgets 0 and 96 on each judge, to
confirm the harness executes on this hardware with each judge's chat template and letter tokens,
and to measure the cost. Grades nothing.

**Pilot.** To be recorded before the seal: both blocks on each judge at the pilot seeds 51 and
52, graded by `flip_grade.py` for the record only. It may change the number of pairs and the
batch size and nothing else.

## 7. Compute, and whose

The authors' workstation, one 32 GB GPU, the second being in use. The 8B judge in bfloat16 takes
16 GB and runs at G3d's batch of 32; the 12B takes 24 GB and runs at a batch of 8, so it is the
slower of the two. Judges run one after another. Threads pinned and niced, as G3d ran.

## 8. Sealing procedure

1. Each config carries the calibration seed and no test seed.
2. Self-test passes on each config; the smoke and pilot records are written into Section 6.
3. This file is committed and its git blob hash recorded in the ledger.
4. Each judge's calibration block is run and its `predictions.json` committed with its sha256
   and pushed.
5. Only then is that judge's test seed drawn from a system random source, against the
   predictions in HEAD, and its test block run and graded by `../G3d/flip_grade.py`, unmodified.
