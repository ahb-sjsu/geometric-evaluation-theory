# G9b results, the hull law read on every subset of the consequence space

**Verdict: C-b1 PASS, C-b2 PASS.** Graded against PREREG-G9B.md, blob adb0ad4bf2dabefbbd4af615b107a2eb2f8fe1cd, sealed before any violation was computed in this action space. Twenty-six exempt-class CPU cells on NRP, all twenty-six records held. Of the twenty-six coordinate subsets, 0 sit above their shuffle null. Every number below is read from the cell records by `write_results_g9b.py`.

## The chain the gate was built for

Every subset holding both expected points added and first down probability, the pair G9 refuted on with four play calls.

| coordinates read | testable | violating | observed | null (sd) | perm p | graded |
|---|---|---|---|---|---|---|
| expected points, first down | 199 | 188 | 0.9447 | 0.9859 (0.0083) | 0.0000 | yes |
| expected points, first down, clock stop | 199 | 62 | 0.3116 | 0.5396 (0.0361) | 0.0000 | yes |
| expected points, first down, risk | 199 | 88 | 0.4422 | 0.7209 (0.0338) | 0.0000 | yes |
| expected points, first down, turnover | 199 | 89 | 0.4472 | 0.7183 (0.0331) | 0.0000 | yes |
| expected points, first down, risk, clock stop | 46 | 7 | 0.1522 | 0.2773 (0.0672) | 0.0300 | no, below the floor of 50 |
| expected points, first down, turnover, clock stop | 42 | 12 | 0.2857 | 0.3114 (0.0732) | 0.3950 | no, below the floor of 50 |
| expected points, first down, turnover, risk | 168 | 31 | 0.1845 | 0.3722 (0.0368) | 0.0000 | yes |
| expected points, first down, turnover, risk, clock stop | 3 | 0 | 0.0000 | 0.1700 (0.2186) | 0.5750 | no, below the floor of 50 |

The rate on the chain falls from 0.9447 at 2 coordinates, then 0.4003 at 3 coordinates, then 0.1845 at 4 coordinates. At the largest subset that clears the floor it is below its null. **The refutation does not reproduce at any dimension in this action space, including two.**

## The secondary claim, mean rate by coordinates read

| coordinates read | graded subsets | mean observed rate |
|---|---|---|
| 2 | 10 | 0.9141 |
| 3 | 10 | 0.4439 |
| 4 | 2 | 0.1391 |

Non-increasing at every step, which is what was registered.

## Every subset

| coordinates read | k | testable | observed | null | perm p |
|---|---|---|---|---|---|
| expected points, clock stop | 2 | 199 | 0.9296 | 0.9718 | 0.0000 |
| expected points, first down | 2 | 199 | 0.9447 | 0.9859 | 0.0000 |
| expected points, risk | 2 | 199 | 0.9497 | 0.9892 | 0.0000 |
| expected points, turnover | 2 | 199 | 0.9095 | 0.9877 | 0.0000 |
| first down, clock stop | 2 | 199 | 0.8995 | 0.9796 | 0.0000 |
| first down, risk | 2 | 199 | 0.9548 | 0.9846 | 0.0050 |
| first down, turnover | 2 | 199 | 0.8945 | 0.9814 | 0.0000 |
| risk, clock stop | 2 | 199 | 0.8643 | 0.9753 | 0.0000 |
| turnover, clock stop | 2 | 199 | 0.9146 | 0.9659 | 0.0000 |
| turnover, risk | 2 | 199 | 0.8794 | 0.9915 | 0.0000 |
| expected points, first down, clock stop | 3 | 199 | 0.3116 | 0.5396 | 0.0000 |
| expected points, first down, risk | 3 | 199 | 0.4422 | 0.7209 | 0.0000 |
| expected points, first down, turnover | 3 | 199 | 0.4472 | 0.7183 | 0.0000 |
| expected points, risk, clock stop | 3 | 180 | 0.4833 | 0.6108 | 0.0000 |
| expected points, turnover, clock stop | 3 | 199 | 0.4121 | 0.5768 | 0.0000 |
| expected points, turnover, risk | 3 | 199 | 0.5980 | 0.8155 | 0.0000 |
| first down, risk, clock stop | 3 | 179 | 0.3687 | 0.5113 | 0.0000 |
| first down, turnover, clock stop | 3 | 180 | 0.4667 | 0.5744 | 0.0000 |
| first down, turnover, risk | 3 | 199 | 0.4573 | 0.7103 | 0.0000 |
| turnover, risk, clock stop | 3 | 199 | 0.4523 | 0.6558 | 0.0000 |
| expected points, first down, risk, clock stop | 4 | 46 | 0.1522 | 0.2773 | 0.0300 |
| expected points, first down, turnover, clock stop | 4 | 42 | 0.2857 | 0.3114 | 0.3950 |
| expected points, first down, turnover, risk | 4 | 168 | 0.1845 | 0.3722 | 0.0000 |
| expected points, turnover, risk, clock stop | 4 | 160 | 0.0938 | 0.3283 | 0.0000 |
| first down, turnover, risk, clock stop | 4 | 47 | 0.1489 | 0.2748 | 0.0450 |
| expected points, first down, turnover, risk, clock stop | 5 | 3 | 0.0000 | 0.1700 | 0.5750 |

## Reading

- **The G9 refutation was a property of its reading and not of the decisions.** With thirteen play calls the same coordinate pair sits below its null, and stays below it at three and four coordinates. `ACTION-SPACE-CHARACTERIZATION.md` measures why: G9's four actions could only ever be read on a plane, and one standard error of sampling noise moves that plane's rate by more than its margin over the null.
- **This is a flip in the sense of Observation Theory, not an artifact.** Reading a subset of coordinates is a read operator, and the verdict is relative to it. What falls with the number of coordinates is the mismatch between the rank at which the analyst reads and the rank at which the evaluator ranks. The rate is an observability statistic.
- **At two coordinates the statistic is saturated.** Observed rates near 0.91 against nulls near 0.98, because a unit counts as violating if any of thirteen actions violates. The ordering against the null survives and the margin is compressed. The per-action aggregation in the characterization file reduces the scale and not the dependence.
- The floor of 50 testable units excludes two four-coordinate chain subsets at 46 and 42, and the single five-coordinate subset at 3. Their rates are printed and grade nothing.
- Nothing in the registration was changed after the seal.
