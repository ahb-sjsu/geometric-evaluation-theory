# G3e results: G3c's resolution law on judges of another family, read through a served API

Registration `PREREG-G3E.md`, blob `4c0b1cb1a4f3705e7700a237cd09c1715838e36a`, sealed
2026-09-20T21:46:28Z. Graded 2026-09-21. The judge changes and nothing else: G3c's worksheets,
blocks, read-outs, grader and bars, by reference.

Three claims, each G3c's, each graded per judge by `../G3c/judge_grade.py`:

* **C1e (J1)** the calibration block predicts the test block's accuracy curves
* **C2e (J2)** the codebook the judge uses predicts them better than the nominal scale does
* **C3e (J3)** the ordering of thresholds across read-outs is the one their symbol budgets predict

## Verdict

GATE FAILS, on C3e alone. Graded 2026-09-21 on all three judges, test seed 3996926402.

| judge | served as | anti-vacuity | J1 | J2 | J3 | gate |
|---|---|---|---|---|---|---|
| `gemma31b` | google/gemma-4-31B-it-qat-w4a16-ct | met | PASS | PASS | FAIL | FAIL |
| `gemma12b` | google/gemma-4-12B-it-qat-w4a16-ct | met | PASS | PASS | PASS | PASS |
| `qwen3_27b` | Qwen/Qwen3.8-27B | met | PASS | PASS | PASS | PASS |

C1e PASS, C2e PASS, C3e FAIL. The registration holds each claim only if every graded judge passes
it, so one judge's miss on C3e carries the gate.

## What passed, and by how much

**C1e, the prediction, PASS on every graded judge.** Each judge's calibration block predicted the
accuracy of every read-out at every gap of a test block drawn from a seed that did not exist when
the prediction was written. Largest deviation 0.047 for `gemma31b` and 0.066 for `gemma12b`,
against a bar of 0.14; largest deviation in noise units 1.93 and 2.49 against a bar of 4.55. The
bars are G3c's, set from a null simulation on a judge of another family, and nothing here re-fit
them. `qwen3_27b` was the largest deviation of the three at 0.077, and 2.57 in noise units.

**C2e, the effective codebook, PASS on every graded judge, by two to three orders of magnitude.**
On the 0 to 100 scale the calibrated channel of the judge gives a squared error of 0.0001 for
`gemma31b`, 0.0064 for `gemma12b` and 0.0032 for `qwen3_27b`, against 0.061, 0.469 and 0.444 for the
nominal scale it was offered. The scale a judge is given is not the budget it spends. What is
compared here is the whole conditional distribution of the score given the quality and not the
codebook alone. `budget_ladder.py` separates the two and finds the codebook by itself closes a
minority of the distance.

The codebooks, on a scale offering 101 scores: 21 for `gemma31b`, 15 for `gemma12b`, 17 for
`qwen3_27b`. Both Gemma judges use only multiples of five and `qwen3_27b` does not. G3c's Qwen2.5 judges used nine and thirteen scores and did not
heap that way, so the heaping is a property of the judge and not of the method that reads it.

## What failed

**C3e, the ordering, FAILS, because one graded judge missed it.** `gemma12b` passed with Kendall's
tau 0.908 against a bar of 0.86, and so did `qwen3_27b` at 0.908. `gemma31b` returned 0.804 and
failed. The registration holds C3e
only if every graded judge passes, so the claim fails and the gate fails with it.

The thresholds themselves were not the problem. Every one of `gemma31b`'s eighteen read-outs landed
within the registered factor of its prediction, and most within 0.2 of a wrong answer:

| read-out | predicted | observed |
|---|---|---|
| 0-9, greedy score | 2.146 | 2.059 |
| 0-9, mean of 1 sample | 2.214 | 2.094 |
| 0-9, mean of 2 | 1.785 | 1.760 |
| 0-9, mean of 4 | 1.475 | 1.450 |
| 0-9, mean of 8 | 1.174 | 1.132 |
| 1-5, greedy score | 3.933 | 4.048 |
| 1-5, mean of 8 | 2.619 | 2.810 |

What failed is the rank statistic, and seven of that judge's eighteen read-outs have a predicted
threshold of exactly one wrong answer in twenty, which is the smallest gap the ladder contains. All
six read-outs of the 0 to 100 scale sit there. A judge finer than the instrument cannot be placed on
it, and read-outs tied at the floor cannot be ranked.

This is a reading of the miss and not a defence of it. The bar was fixed before the run, taken from
another gate's pilot, and this judge did not clear it.

## Where the ladder stops measuring, EXPLORATORY

Run after both gates were graded, on records that already existed, and it changes no verdict
(`ladder_floor_check.py`, `ladder_floor.json`).

| gate | judge | J3 | tau | read-outs at the floor |
|---|---|---|---|---|
| G3c | Qwen 14B | PASS | 0.948 | 0 of 18 |
| G3c | Qwen 7B | PASS | 0.876 | 0 of 18 |
| G3c | Qwen 7B at 4-bit | PASS | 0.908 | 0 of 18 |
| G3e | Gemma 12B | PASS | 0.908 | 0 of 18 |
| G3e | Gemma 31B | FAIL | 0.804 | 7 of 18 |
| G3e | Qwen3 27B | PASS | 0.908 | 1 of 18 |

Among the graded judges of both gates, two have any read-out at the floor. The one with seven of
them fails C3e and the one with a single read-out there passes, so a read-out at the floor is not by
itself fatal and a majority of them appears to be. None of G3c's judges has a single one. G3c built a ladder whose finest gap is one
wrong answer in twenty and every judge it ran sat above that; running the same instrument on a finer
judge found its ceiling. That is one case, not a demonstration, and the honest next step is a ladder
with gaps below one, which needs worksheets longer than twenty items.

## Reading a served judge, what it cost

The reader shows only the twenty most probable tokens per position. What they leave short of one is
the mass the server did not show, recorded per worksheet. Over the whole run it never exceeded
0.0039, and the digit tree's pruned mass never exceeded 0.0019, which is why the registration set
the prune where it did.

A defect of the reader was found and corrected during the run and is recorded in the registration:
it admitted Unicode number characters as digits, where G3c reads only the ten ASCII digits. A second
defect, a constant written twice and checked once, was found before any block was scored and is also
recorded there. The repair for the second is `g3e_preflight.py`, which reads the registration's own
text and refuses to start a block whose config disagrees with it.

## What this does and does not establish

The law is not a property of Qwen2.5, of bfloat16, or of the authors' loader. Three judges served by
a third party behind an API that shows twenty tokens, two of a second family at weights that party
quantized and one a newer generation of the first family, had their thresholds predicted before they
were measured and wrote far fewer distinct scores than the scale they were offered. What the gate did not establish is the read-out ordering across all judges, because
the instrument could not resolve the finest one.

Still one stimulus family. Still no bfloat16 counterpart, so nothing here speaks to the precision
claim. Two of the three judges are a size ladder in one family and are not independent draws.

## Compute

No GPU of the authors'. Requests to NRP's managed LLM service at its published concurrency of eight,
one to four output tokens each. Atlas ran one core at the lowest priority to drive it. Response
counts and timings are in `run_record/`.
