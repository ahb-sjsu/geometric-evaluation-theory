# G9 results, the hull law on NFL play calls, committed as executed

**Verdict: PASS on the primary plane. Across the six planes that carry bars, 4 pass, 1 is indeterminate and 1 refutes.** The gate as a whole does not pass. By the sealed sensitivity clause it grades INDETERMINATE, for the reason set out under that heading. Graded against PREREG-G9.md, blob f8a18aea4d82bded364b78a6da6c1a39f1fd9f51, sealed before any ranking was formed on real data. The statistic, the null and the tie rule are G2's, run through G2's own checker, so the difference between this and the 1972 survey is a difference between two populations and not between two pieces of code. Every number below is read from the cell records by `write_results_g9.py`.

## The primary plane

| quantity | value |
|---|---|
| plane | expected points added against turnover probability |
| units, evaluator by state cell | 962 |
| testable units | 402 |
| units violating the hull law at least once | 8 |
| observed violation rate | 0.0199 |
| shuffle null, mean and standard deviation | 0.2286 (0.0206) |
| permutation p | 0.0000 |
| distance below the null | 10.1 null standard deviations |
| verdict | **PASS** |

## Every plane at the sealed floor

| plane | testable | violating | observed | null (sd) | perm p | verdict |
|---|---|---|---|---|---|---|
| first down probability against clock stop | 307 | 0 | 0.0000 | 0.2356 (0.0243) | 0.0000 | PASS |
| turnover probability against risk | 517 | 9 | 0.0174 | 0.2315 (0.0183) | 0.0000 | PASS |
| expected points added against turnover probability (primary) | 402 | 8 | 0.0199 | 0.2286 (0.0206) | 0.0000 | PASS |
| expected points added against risk | 434 | 55 | 0.1267 | 0.2291 (0.0189) | 0.0000 | PASS |
| first down probability against risk | 399 | 78 | 0.1955 | 0.2256 (0.0201) | 0.0700 | INDETERMINATE |
| expected points added against first down probability | 450 | 135 | 0.3000 | 0.2211 (0.0173) | 1.0000 | FAIL |
| expected points added against clock stop | 277 | 0 | 0.0000 | 0.2327 (0.0252) | 0.0000 | no verdict, vacuous |
| risk against clock stop | 43 | 1 | 0.0233 | 0.2040 (0.0623) | 0.0000 | no verdict, vacuous |
| first down probability against turnover probability | 126 | 9 | 0.0714 | 0.2102 (0.0405) | 0.0000 | no verdict, vacuous |
| turnover probability against clock stop | 53 | 5 | 0.0943 | 0.2760 (0.0539) | 0.0000 | no verdict, vacuous |

The four planes carrying no verdict were declared vacuous in the registration before any number was seen, because each falls below the anti-vacuity bar of 300 testable units that this gate inherits from G2. Their rates are printed so the record is complete and they grade nothing.

## The registered sensitivity, a floor of ten, carrying no bar

| plane | testable | observed | null (sd) | perm p | verdict at the sealed floor |
|---|---|---|---|---|---|
| first down probability against clock stop | 184 | 0.0000 | 0.2393 (0.0311) | 0.0000 | PASS |
| turnover probability against risk | 265 | 0.0038 | 0.2367 (0.0261) | 0.0000 | PASS |
| expected points added against turnover probability | 184 | 0.0054 | 0.2299 (0.0327) | 0.0000 | PASS |
| expected points added against risk | 271 | 0.1476 | 0.2359 (0.0268) | 0.0050 | PASS |
| first down probability against risk | 187 | 0.2086 | 0.2339 (0.0315) | 0.2300 | INDETERMINATE |
| expected points added against first down probability | 211 | 0.3744 | 0.2249 (0.0280) | 1.0000 | FAIL |

The registration says a verdict that reverses between the two floors grades the gate INDETERMINATE regardless of which side the sealed floor falls on. It reverses on 1 of 6 planes.
- expected points added against risk, PASS at the sealed floor and INDETERMINATE at ten.

**A registration defect, recorded rather than resolved in the gate's favour.** The sealed sentence reads that a reversing verdict grades "the gate" INDETERMINATE, and it does not say whether that means the plane that reversed or every plane at once. Written before any number was seen, the ambiguity was invisible. Read after, one reading costs a single replication and the other costs the primary result, and choosing between them now is choosing a verdict. The stricter reading is taken here, so the gate is graded INDETERMINATE overall, and the defect is named so the next registration says which it means.

What the ambiguity does not touch. The primary plane does not reverse. It passes at the sealed floor at 0.0199 against a null of 0.2286, and at a floor of ten at 0.0054 against 0.2299, with a permutation p of zero at both. The headline claim stands under either reading.

## Reading

- **The hull law holds far more tightly here than in the survey.** G2 measured 0.503 of 489 testable respondents violating against a null of 0.664, and recorded that the law holds as a population tendency and fails as a deterministic statement for about half of them. On the primary plane here 8 of 402 testable units violate, a rate of 0.0199 against a null of 0.2286. The deterministic reading that ANES could not support survives on this world.
- **The consequence map was not placed by the evaluator.** That was G2's declared limit. Here the map is estimated from what happened after each call, pooled across every evaluator, which is the split GET's foundations require between what the world supplies and what the evaluator owns.
- **The observed rate sits below the measured noise of the ranking device.** The self-test put the device's manufactured-violation rate at 0.052 at this floor, on synthetic menus whose true rate was zero. The observed 0.0199 is lower than that, which says the real rate is near zero and that the synthetic geometries were harder than the ones football actually presents. It also means the declared bias cannot be what produced this verdict, since the bias only ever raises the observed rate.
- The confounds declared before sealing stand unchanged. The map is a conditional expectation over calls somebody chose to make and carries no causal reading, a cell pools states the bins do not separate, choice share reveals a ranking only to the extent the caller is choosing rather than mixing on purpose, and the franchise pools coaching staffs across ten seasons.

## The plane that refutes, and an explanation that did not survive

On expected points added against first down probability the law does not merely fail to clear its bar. It is violated more often than chance, 0.3000 against a null of 0.2211 in 450 testable units, with a permutation p of 1.0000, meaning every one of the 200 shuffles produced a rate at or below the observed one. That is a refutation on that plane and it is recorded at the same size as the passes.

An explanation offered after seeing it, and then tested. Expected points added and first down probability are close to redundant, so the four points lie near a line, and GET's own Theorem 3 says consequences on a line represent exactly the single-peaked orders, a stronger requirement that should produce more violations. The story is principled rather than invented for the occasion, and it is still post hoc, so it was checked against the other nine planes using probe 4's collinearity measure.

It does not survive. The rank correlation between how collinear a plane is and how often it is violated is -0.091 across the ten planes, which is nothing, and the most collinear plane of all has one of the lowest violation rates. The cause of this plane's failure is open, and no account of it is offered here.

- Nothing in the registration was changed after the seal. This document was written after grading and does not alter the verdict.
