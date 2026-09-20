# PREREG G3e: the same resolution law on judges of another family, read through a served API

Status: SEALED 2026-09-20 by the rename to `PREREG-G3E.md`, under the owner's instruction of
2026-09-20 to run this gate in this thread with elegance and rigor; blob hash recorded in
`CAMPAIGN.md`. At the seal no worksheet of either graded block had been shown to any judge.

## Why this gate exists

G3c measured a language-model judge's resolution and predicted it from the judge's own symbol
budget before measuring it. Its verdicts rest on three judges of one family, Qwen2.5 at 7B in two
precisions and at 14B, because the other two it registered failed anti-vacuity. An external reader
of the ICLR draft put it plainly: the main remaining risk is one model and one arithmetic task, and
the result becomes much harder to dismiss if a genuinely independent model and tokenizer behave the
way the theory says.

This gate is that second family. It changes the judge and nothing else. The worksheets, the blocks,
the read-outs, the estimator, the grader and every bar are G3c's, by reference to
`../G3c/PREREG-G3C.md` blob `e6bd3ef791ce9b96f68422d2df5cdd76e424adb4` and the code at the seal commit. What is new is who is being
read and how: three judges served by the National Research Platform's managed LLM API, two from
Google's Gemma 4 family at 4-bit QAT weights and one from Qwen3, none of which share weights,
tokenizer or serving stack with G3c's judges.

It also removes a second objection. G3c's judges ran on a card the authors control. These run on
someone else's, at weights the operator quantized, behind an API that shows only the twenty most
probable tokens. If the law survives that, it is not an artifact of how the authors load a model.

## What had been seen when this was written

The probe of Section 6, and nothing else. No worksheet of the calibration block and no worksheet of
the test block has been shown to any judge. The probe drew 42 worksheets from probe seed 20260920,
a seed no graded block uses, and its record is `probe/probe.json`.

The three judges were chosen from what the service offers, after the probe, on two stated grounds:
they answer with a score rather than with deliberation, and they clear anti-vacuity on the probe.
`gpt-oss` was tried and is excluded, because under both settings tried it answered with reasoning
and wrote no score in four tokens; that exclusion is recorded here rather than left silent, and it
is a limit of this gate, not of the theory.

## 1. Claims under test

Each is G3c's, unchanged, and is graded per judge by `../G3c/judge_grade.py`.

**C1e (J1, GET-12a).** The accuracy curve of every read-out on the test block is predicted, at every
gap of the ladder, by the codebook and the score distribution the judge showed on the calibration
block. Deviation no larger than `dev_max`, and in noise units no larger than `z_max`.

**C2e (J2, GET-12b).** The codebook the judge actually uses predicts its curves better than the
nominal scale it was offered. The scale is not the budget.

**C3e (J3, GET-12c).** The ordering of thresholds across read-outs is the ordering their symbol
budgets predict, with Kendall's tau at least `rank_agreement_min` and the expected-score and
eight-sample read-outs below the argmax.

**C4e (J5, GET-12d).** The pairwise threshold sits at or above the floor the judge's finest
pointwise read-out predicts, reported with its ratio. This claim has no failure and is reported
with its label.

**Not in scope.** GET-12e, that weights move reliability and not resolution, needs one model at two
precisions. The service serves each model at one precision, so this gate says nothing about it.

**What a pass would mean, stated before the run.** The resolution law is a property of judges and
not of Qwen2.5, of bfloat16, or of the authors' loader. What a failure would mean: the law is
narrower than G3c's record suggests, and the ICLR draft would say so with this gate's numbers beside
G3c's.

## 2. World, judges, elicitations

**Stimulus, blocks, read-outs.** G3c's, by reference. Worksheets of 20 single-digit
multiplications; calibration of 40 worksheets at each of 21 error counts; a test block of 200 pairs
at each gap of 1, 2, 3, 4, 6, 8 and 12; scales 1 to 5, 0 to 9 and 0 to 100; read-outs argmax,
expected score, and the mean of 1, 2, 4 and 8 samples drawn from the exact score distribution;
pairwise comparison in both orders with no deliberation.

**Judges.** Run in this order, which is fixed here so that no judge can be chosen after its result.

| key | asked for | must be served as |
|---|---|---|
| `gemma31b` | `gemma` | `google/gemma-4-31B-it-qat-w4a16-ct` |
| `gemma12b` | `gemma4-12b` | `google/gemma-4-12B-it-qat-w4a16-ct` |
| `qwen3_27b` | `qwen3-small` | `Qwen/Qwen3.8-27B` |

The served name is pinned from the first response of a block and every later response is checked
against it. A block served by another model stops there and is reported as not run.

**Deliberation is off.** Every request carries `chat_template_kwargs: {enable_thinking: false}`, and
`max_tokens` is 4 for a score and 1 for a continuation or a pairwise letter. G3c's judges were also
read with no deliberation. A judge that answers with reasoning anyway writes no parsable score, which
the record shows as an unparsed report rather than as a low score.

**Temperature.** Every request is made at temperature 0. The distribution read back is the
model's next-token distribution, which does not depend on the sampling temperature of the request;
samples are then drawn from it exactly, as in G3c.

## 3. Reading a served judge

`api_judge.py` at the seal commit, self-tested by `api_selftest.py` (Section 6). A served model
gives the text it wrote and, per position, the twenty most probable tokens with their log
probabilities. Three consequences are registered here because they are limits of this reading and
not of the judge.

**The wall.** What the twenty visible probabilities leave short of one is exactly the mass the
server did not show. It is recorded per worksheet as `unseen_mass`, and on the 0 to 100 scale
carried through the tree as `tree_unseen_bound`. On the probe it never exceeded 0.0016.

**The tree.** The 0 to 100 distribution is G3c's digit tree walked over the API: a live digit prefix
is sent back as the start of the assistant's turn and the next position's top twenty give each next
digit, with the remainder booked as stopping. A token that is a run of digits extends the prefix by
that run, so a tokenizer that writes a whole score as one token is read correctly; the self-test
checks that against a server built to do it.

**The prune.** G3c prunes prefixes below 1e-5, where a whole frontier is one batch on a local GPU.
Over an API every prefix is a request, so this gate prunes below **1e-4**, and the pruned mass is
recorded per worksheet. Measured on the probe, that choice costs 39 percent fewer requests for
`qwen3_27b` and 43 percent fewer for `gemma31b`, and leaves a pruned mass of at most 0.0013 and
0.00044 respectively, which is below the mass the twenty-token wall already hides. The pruning is
therefore not the binding limit on the reading, and that is the reason it was set here rather than
at G3c's value. A sweep over 1e-4, 1e-3 and 1e-2 is in `probe/`; at 1e-2 the pruned mass reaches
0.060 and the choice would have bound.

## 4. Bars (frozen at seal)

G3c's, unchanged and copied into `g3e_config.json`: `dev_max` 0.14, `z_max` 4.55,
`threshold_factor` 1.75, `rank_agreement_min` 0.86, `vacuity_acc_min` 0.9, `vacuity_bits_min` 1.0.
They were set from a null simulation on G3c's pilot and nothing here re-fits them. Using another
gate's bars is the point: a bar moved for a new judge is not a bar.

**Anti-vacuity.** A judge that cannot order worksheets twelve errors apart with accuracy 0.9 on
some scale, or that carries less than one bit about quality, is declared VACUOUS from its
calibration block before its test block is drawn, and its curves are reported and not graded. The
gate is VACUOUS if every judge is.

**Verdicts.** Each judge is graded on its own. C1e holds if J1 passes for every judge that is not
vacuous, and likewise C2e and C3e. With k judges graded the chance that at least one faithful judge
fails J1 or J3 is at most 3.3k percent, which is G3c's bound and is loose here for the same reason:
the two Gemma judges are a size ladder in one family and are far from independent.

## 5. What falsifies

C1e fails if a graded judge's test curves leave the band its calibration predicted. C2e fails if the
nominal scale predicts a graded judge's curves as well as its effective codebook. C3e fails if the
observed ordering of thresholds across read-outs is not the predicted one. Any failure is recorded
in the ledger, the campaign and the paper at the size of a pass, beside G3c's verdicts and not in
place of them.

## 6. Self-test and probe

**Self-test of the reader, 14 checks, PASS, no network** (`api_selftest.py`, record
`selftest/api_selftest.json`). A fake server of known structure answers the same requests the real
one does. Checked: the vector read back on a single-token scale is the server's to 1e-6 and the
greedy text is its argmax; the 0 to 100 distribution is the server's to 1e-6 when nothing is pruned
and nothing falls outside the visible twenty; a server whose tokenizer writes a whole score as one
token is read correctly; the reported unseen bound covers the mass actually lost when the wall is
lowered to six tokens, and again for a grouping tokenizer behind the twenty-token wall; what is
pruned is reported and the vector still sums to one; a server that changes model mid-block stops the
run, and so does a served name other than the registered one; a second pass over a cache sends no
request and returns the same records; and a synthetic judge behind the fake server, read through
G3c's harness and graded by G3c's grader, predicts its own test block, meets anti-vacuity, and puts
its expected-score threshold below its argmax threshold.

**Probe, 2026-09-20** (`g3e_probe.py`, record `probe/probe.json`, 42 worksheets at seven error
counts from probe seed 20260920, 4,263 requests in total). Event presence, not a test.

| judge | scores in use, 1-5 / 0-9 / 0-100 | accuracy at a gap of 12 | mass on the codebook | largest unseen mass |
|---|---|---|---|---|
| `gemma31b` | 5 / 10 / 13 | 1.00 on every scale | 0.9999 | 0.00072 |
| `gemma12b` | 4 / 8 / 12 | 0.96, 0.99, 1.00 | 0.9999 | 0.00018 |
| `qwen3_27b` | 5 / 9 / 10 | 1.00 on every scale | 0.947 to 0.996 | 0.0016 |

All three clear the anti-vacuity bar of 0.9 on the probe, so none is expected to come out vacuous,
and the gate is not expected to be empty. On the 0 to 100 scale all three use ten to thirteen of the
101 scores they are offered, which is the phenomenon C2e is about, seen here before the gate is run
and in a family G3c never touched. The pairwise prompt is readable: both answer letters are among
the visible tokens for every judge, and order-averaged accuracy at the largest gap is 1.00, with a
first-position preference of 1.00 that the order average cancels by design.

Nothing in this table is a verdict. It is measured on 42 worksheets from a seed no graded block
uses, and it reports the judges' greedy scores only.

## 7. Compute, and whose

No GPU of the authors'. The engine work is the service's, on hardware the National Research Platform
operates, under its fair-use policy: eight concurrent requests for these models, and 200,000 output
tokens per minute per token and model. This gate uses the published concurrency and no more, and
emits one to four output tokens per request, which is three orders of magnitude below the token
limit. Measured on the probe and scaled to the sealed design, the run is about 41,000 requests for
`gemma31b`, 64,000 for `gemma12b` and 139,000 for `qwen3_27b`, each request about 400 input tokens,
with the digit tree's repeated prefixes served by the provider's prefix cache. Atlas runs one core
to drive it. A judge whose run cannot be completed is reported as not run, in the order of Section 2,
so that nothing is chosen after the fact.

## 8. Known weaknesses

* One stimulus family still. This gate widens the judges, not the task. Arithmetic worksheets give
  an exact quality scale, and a judge's resolution on them need not transfer to prose.
* The weights are the operator's and the service may change them. The served name is pinned per
  block and checked on every response, which detects a change between blocks but not a silent
  requantization under the same name.
* Two of the three judges are a size ladder in one family, so the three are not three independent
  draws.
* Every judge here is quantized by the operator, and no bfloat16 counterpart is served, so the
  precision claim is out of scope and the resolution measured is the resolution of a quantized
  judge.
* `gpt-oss`, the one model offered whose tokenizer groups digits, could not be read without
  deliberation and is excluded. The reader handles a grouping tokenizer and the self-test proves it,
  but this gate does not exercise that on a real model.
* The reading is through a cache. A run resumed from the cache checks the served name against what
  the cache recorded, not against the service.

## Registration defect, recorded 2026-09-20T21:50Z

At the seal, `g3e_config.json` carried `tree_prune` 1e-5, G3c's value, while Section 3 of this file
registered 1e-4 and gave the measurement that justified it. The two disagreed. It was found when the
calibration run printed the config's value at start-up, thirty seconds in, before any worksheet of
any graded block had been scored. The run was stopped, its partial record deleted, the config
corrected to the registered 1e-4, and the correction committed before the block was started again.

The registration is the authority. Nothing here was chosen after seeing a result: the value 1e-4 and
the reason for it are in the sealed text at blob `4c0b1cb1a4f3705e7700a237cd09c1715838e36a`. The
defect is that a constant was written twice and checked once, and the repair is a preflight in the
runner that refuses to start a block unless the config matches this file: `g3e_preflight.py`,
which reads the prune, every bar, the judges and their order out of this text by name, checks the
rest of the design against G3c's own config, and refuses a test block while no test seed exists.
It was checked against the defect it was written for and three neighbours of it, and refuses all
four.

## 9. Sealing procedure

1. Self-test and probe first, both committed with their records.
2. Rename this file to `PREREG-G3E.md`, commit, record the blob hash in `CAMPAIGN.md`.
3. Run the calibration block for each judge, in the order of Section 2. Write `predictions.json`
   per judge with `judge_grade.py predict`, commit it with its sha256.
4. Only after that commit is pushed, draw the test seed with `secrets.randbits(32)`, commit it into
   `g3e_config.json`, then run the test block and grade.
5. Every number in any write-up names its file and commit.
