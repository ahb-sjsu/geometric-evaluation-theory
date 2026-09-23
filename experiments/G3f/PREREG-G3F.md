# PREREG G3f: the same resolution law on a second stimulus family

Status: SEALED 2026-09-22. The blob hash of this file is recorded in the commit that seals it and in the ledger. The calibration seed is in the config, the test seed is not and is
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

**Judges.** The three G3e judges unchanged, and a fourth added here, each pinned by what the
service reports serving. The harness refuses the block if the served string does not match.

| key | asked for | must be served as | in G3e |
|---|---|---|---|
| `gemma31b` | `gemma` | `google/gemma-4-31B-it-qat-w4a16-ct` | yes |
| `gemma12b` | `gemma4-12b` | `google/gemma-4-12B-it-qat-w4a16-ct` | yes |

Three aliases on this gateway resolve to the same 12B weights, so the alias is not the identity
and `served_as` is what is registered. The aliases also changed between G3e and this gate while
the weights behind them did not, which is the same lesson from the other side.

`qwen3_flash` was registered as a third judge and is withdrawn after sealing, for the reason in Section 6c. This gate therefore grades two judges, both of them G3e's, and it has one vendor. It makes no claim of judge breadth. That claim rests on G3c and G3e, which between them graded two vendors across three model generations. What this gate varies is the stimulus family, and with both judges carried over from G3e it varies only that. It shares a vendor with `qwen3_27b` and
differs in weights, architecture and serving precision. It was added because a fourth readable
judge was available, and the gate says what it is rather than counting it as breadth it does not
buy. Its presence changes nothing else: it runs the same blocks, prompts, read-outs and bars, and
it is graded by the same rule as the other three.

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

| judge | scale | scores used | accuracy at a gap of 12 | bits about quality | largest unseen mass | requests per stimulus |
|---|---|---|---|---|---|---|
| `gemma31b` | 1-5 | 5 | 0.847 | 1.000 | 0.0001 | 1.0 |
| `gemma31b` | 0-9 | 8 | 1.000 | 1.000 | 0.00054 | 1.0 |
| `gemma31b` | 0-100 | 13 | 1.000 | 1.000 | 0.00048 | 11.8 |
| `gemma12b` | 1-5 | 5 | 1.000 | 1.000 | 7.1e-05 | 1.0 |
| `gemma12b` | 0-9 | 7 | 1.000 | 1.000 | 5.6e-05 | 1.0 |
| `gemma12b` | 0-100 | 12 | 1.000 | 1.000 | 4.4e-05 | 23.2 |
| `qwen3_flash` | 1-5 | 5 | 1.000 | 1.000 | 0.0046 | 1.0 |
| `qwen3_flash` | 0-9 | 8 | 1.000 | 1.000 | 0.0075 | 1.0 |
| `qwen3_flash` | 0-100 | 11 | 1.000 | 1.000 | 0.014 | 80.6 |

Pairwise, both orders, on the same probe stimuli:

| judge | order-averaged accuracy at a gap of 12 | first-position preference | unreadable |
|---|---|---|---|
| `gemma31b` | 1.000 | 1.00 | 0 |
| `gemma12b` | 1.000 | 1.00 | 0 |
| `qwen3_flash` | 1.000 | 1.00 | 0 |

* `gemma12b` would clear the anti-vacuity rule on the probe, on the 1-5 scale, with accuracy 1.000 at a gap of twelve and 1.000 bits.
* `gemma31b` would clear the anti-vacuity rule on the probe, on the 0-9 scale, with accuracy 1.000 at a gap of twelve and 1.000 bits.
* `qwen3_flash` would clear the anti-vacuity rule on the probe, on the 1-5 scale, with accuracy 1.000 at a gap of twelve and 1.000 bits.

The probe is not the calibration block and does not decide anti-vacuity. That is decided from each
judge's own calibration block, by the registered rule, before its test seed is drawn. What the
probe establishes is that the gate is worth running and what it will cost.

Two things the probe shows that the worksheet gates did not. The task is harder: `gemma31b` reaches
only 0.847 at a gap of twelve on the 1 to 5 scale and `qwen3_27b` 0.833, where on worksheets every
judge of G3e saturated at 1.00 on every scale. That headroom is what leaves a threshold to measure.
And both Gemma judges show a first-position preference of 1.00 in the pairwise elicitation, an
extreme position bias that the two-order average cancels by construction and that is recorded here
because it is a property of the judge on this family and not of the method.

## 6a. gpt-oss and two others were tested as further judges and cannot be read

NRP.ai recommends `gpt-oss` for reproducible research, and a judge from a third vendor would have
strengthened the gate. It was tested before sealing and it cannot serve under this
protocol, so it is not in it.

At `max_tokens = 1` with thinking disabled, `openai/gpt-oss-120b` returns the content
`<|channel|>`, a control token of its output format, and its top twenty tokens contain no digit at
all. Forcing the assistant turn, with an empty prefill and with a `Rating: ` prefix, returns the
same token and no digits, and `max_tokens = 8` returns no content. Every read-out in this gate is
a function of the first token's distribution over the scale, so a judge whose first token is
structural has nothing for the method to read. This is not the judge failing to discriminate,
which anti-vacuity would catch from a calibration block. It is the judge being unreadable, which
anti-vacuity would not catch, so it is recorded here instead.

Two other candidates were tested at the same time and fail the same way, on the same real G3f
stimulus and prompt. `Inferact/GLM-5.3-NVFP4` returns the token `Let`, beginning prose, with no
digit in its top twenty. `MiniMaxAI/MiniMax-M2.7` returns empty content, likewise with no digit.
Of the four candidates tried, only `Qwen/Qwen3.8-Flash-Next-FP8` answers with a digit, and it is
the one that was added.

That three of four current reasoning-tuned models cannot be scored this way is worth stating on
its own account. It is not a limitation of this gate so much as a property of the models: a judge
whose first emitted token is structural rather than an answer has no first-token distribution to
read, whatever its quality as a judge.

The exclusion is a fact about the served chat template rather than about the weights. A
self-hosted instance answering on a raw completion endpoint would carry no template and would very
likely be readable. That is a later gate, not this one.


## 6b. A judge dropped before sealing, on cost and not on results

`qwen3_27b`, one of G3e's three, is **not** in this gate. Its probe was stopped and it is excluded.

On the 0 to 100 scale its digit tree expands far past the other judges'. At the registered
`tree_prune` of 1e-4 it had issued 2,015 requests for 42 probe stimuli, about 48 per stimulus and
still running, against 11.8 for `gemma31b` and 23.2 for `gemma12b`. It is also the slowest of the
three per request. Carried to the registered block sizes that is of the order of five hours for
its calibration block on that scale alone and fifteen for its test block, which does not fit the
time this gate has.

The line this draws is one of degree and the registration should say so rather than imply a
difference in kind. `qwen3_flash`, which is kept, has the same digit tree behaviour at roughly
half the magnitude: 80.6 requests and 9.87 seconds per stimulus on the 0 to 100 scale, against
0.50 for `gemma31b` and 0.80 for `gemma12b`. It is kept because at that rate its calibration block
costs about 2.4 hours and fits inside the time this gate has, where `qwen3_27b` did not. Read the
drop as a budget decision with a threshold measured in hours, not as a finding about either judge.

The two ways to keep `qwen3_27b` were both worse than dropping it. Raising `tree_prune` for that judge
alone makes the reading protocol judge-dependent, which is the one thing this gate is built not to
do. Shrinking the test block makes G3c's bars stop applying, and those bars transferring unchanged
is the whole argument.

What matters for reading this later: the decision is made **before the registration is sealed, on
measured cost, with no graded result of any kind in existence for this judge on this family**. Its
partial probe record is kept in the supplement so the cost claim can be checked. It is not an
exclusion on results and nothing about it is known that could motivate one.

## Stimulus defect, corrected 2026-09-22T23:02Z, before any judge was contacted

The registration was sealed at blob `dd5dc2268cfb759404f0cb940107895b48968e1c`. Building the first
calibration block then failed, and the failure was a defect in `g3f_stimuli.py` rather than in
anything this file specifies.

Section 2 requires that a replacement value appear nowhere in the passage. `verify_record` enforced
that against the passage as rendered, with its `1.` to `20.` line numbers. `perturb`, which chooses
the replacement, searched the passage WITHOUT those numbers. A replacement equal to a line number,
`13` for a count, therefore passed the chooser and was rejected by the checker, and the generator
refused to emit the stimulus. The message was `fact 13 shows '13' which the passage contains`.

The property the registration states is the one `verify_record` enforces, so the specification was
right and the chooser was wrong. The fix makes both search the same rendered text through one
`render_passage` function. No pool, template, seed, block size, scale, read-out, estimator or bar
is touched, and the registration's Section 2 is unchanged because it already described the intended
behaviour.

Two things make this recordable rather than damaging. It was caught by the stimulus generator's own
per-stimulus check while constructing the block, which is what that check exists for. And it was
caught before any judge was contacted: `run_record` held no score file and no API cache entry when
the run died, verified and stated here so the claim can be checked.

The self-test is widened in the same change. It swept one seed and passed 840 stimuli; the
calibration seed hit the defect on its first block. It now sweeps seven seeds and 5,880 stimuli. One
seed is not coverage, and the old self-test would have missed this again.

The registration's blob after this correction is recorded in the sealing commit alongside the
original. Both are in the history, and the calibration block was built only after the correction.

## Config defect, corrected 2026-09-22T23:15Z, before any prediction was written

`g3f_config.json` was missing `dither_ladder`. Section 2 of this file states the read-outs as the
greedy score, the expected score, and the mean of 1, 2, 4 and 8 samples, and `dither_ladder` is
the key that realises the last four. The config was assembled from G3e's and the key was dropped.

The registration's specification was right and the config was incomplete, so Section 2 is
unchanged and the config now carries `[1, 2, 4, 8]`, which is G3c's value and G3e's.

The calibration blocks already computed are unaffected and are not re-run. `dither_ladder` is read
only in `judge_grade.readouts`, where it slices the `samples` array that the block already stores
in full at `n_samples = 8`. The runner never reads it. That was verified by inspection of both
modules rather than assumed, because the alternative would have meant discarding a completed block.

How it was found, and the part worth keeping. It was not found by a guard. It was found by
rehearsing the prediction step, read-only, against the first calibration block as soon as that
block existed, which is a habit rather than a check. G3e had already built
`g3e_preflight.py` for exactly this class of defect after its own `tree_prune` disagreement, and
that guard tests for `dither_ladder` by name. It is bound to G3e's registration and there was no
G3f equivalent, so it could not run here.

`g3f_preflight.py` now exists and is the artifact this defect leaves behind. It reads every
constant out of this file by name, refuses a block whose config disagrees, refuses a test block
while no test seed exists, and refuses any block whose registration blob is not the sealed one or
a correction recorded here. One check is inverted from G3e's: this gate's prompts MUST differ from
G3c's, since changing the stimulus family is the whole point, while everything else must not.

## 6c. A judge withdrawn AFTER sealing, on measured service latency

`qwen3_flash` is named in this registration and is not graded. This is a deviation from the sealed
registration and not a pre-seal decision, so it is recorded separately from Section 6b rather than
alongside it.

Its calibration block was started and abandoned. The gateway's latency for that model regressed by
roughly two orders of magnitude between its probe and its block, on a service we do not own and
did not change:

| when | measured |
|---|---|
| probe, 22:5x | about 10 requests per second, 0.111 s per stimulus on the 1 to 5 scale |
| block, 00:45 | 0.167 requests per second measured over 90 s; 0.20 requests per second over a fresh 24-request sample at the registered concurrency, median latency 42.95 s, **zero errors** |

Zero errors matters: no request failed and nothing was retried, so this is the service answering
slowly and not the client misbehaving. At that rate the 1 to 5 scale took 73 minutes for 840
requests, and the 0 to 100 scale would need about 67,700 requests, of the order of 112 hours for
the calibration block alone, against a deadline about 71 hours away. The run was stopped rather
than left to consume a shared research service for four days to no end. Its partial record, 914
cached requests and the completed 1 to 5 scale, is kept so the latency claim can be checked.

What this costs and what it does not. It is not an exclusion on results: no test block for this
judge exists, no seed had been drawn, and nothing about its accuracy on this family is known. It
does cost the gate its only non-Gemma judge, so G3f has one vendor and claims no breadth.

The design that remains is narrower and, on one axis, cleaner. Both surviving judges are G3e's,
graded there on worksheets with this protocol and these bars. G3f runs the same two judges, the
same blocks, the same read-outs, the same estimator and the same bars, and changes the stimulus
family. A third judge new to the campaign would have varied two things at once.

## 7. Compute, and whose

No GPU of the authors'. Requests to NRP's managed LLM service at its published concurrency of
eight, one to four output tokens each, driven from Atlas at the lowest priority, judges run one
after another so the service never sees more than that one concurrency. No pods are submitted and
no GPU is requested, so the cluster's pod sizing and utilization rules are not engaged.

The load this gate places on that service, from the probe's measured cost per stimulus:

| judge | calibration, 840 stimuli | test, 2800 stimuli |
|---|---|---|
| `gemma31b` | about 7 minutes | about 25 minutes |
| `gemma12b` | about 12 minutes | about 40 minutes |
| `qwen3_flash` | about 2.4 hours | about 8 hours |

Nearly all of it is the 0 to 100 scale, where a score spans up to three tokens and the digit tree
expands every prefix above the prune. The two single-token scales together cost under two minutes
per block per judge.

## 8. Known weaknesses

* One stimulus family is replaced by a second, not by many. Two families are not a demonstration
  that the method is family-independent.
* The facts are templated and synthetic. The judgement is harder than arithmetic but it is still
  a fact-matching task, not the contested quality of prose.
* Two of the three judges are G3e's, so they are not an independent draw from anything, and the
  third shares a vendor with a judge G3e graded. The stimulus family is what this gate varies.
* G3e graded three judges and this gate registered three, of which two were graded. Section 6c supersedes this line and records the withdrawal. The three registered are not the same three G3e graded. `qwen3_27b`
  is dropped for the reason in Section 6 and `qwen3_flash` is added, so the continuity with G3e is
  two judges, not three.
* Three candidates for a third vendor were tested and none could be read, so the gate has no
  vendor outside the two it already had. The measurements are in Section 6.
* Quality is a count of unsupported statements and treats all of them as equal, which the score a
  judge writes need not.

## 9. Sealing procedure

1. `g3f_config.json` carries the calibration seed and no test seed.
2. This file is committed. Its git blob hash is recorded here and in the ledger.
3. Calibration blocks are run and `predictions.json` is written and committed with its sha256.
4. Only then is the test seed drawn from a system random source, written to `test_seed.json`, and
   the test blocks run and graded by the registered script.
