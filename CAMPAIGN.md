# GET campaign: from stated to measured

Every gate below has a deliverable, a bar, a statement of what falsifies it, and a verdict. A gate runs only after its registration is sealed (hash committed before any data is touched, see `PROTOCOL.md`). A miss is recorded at the same prominence as a pass. No verdict below has been written yet.

Standing rule inherited from the observation-theory campaigns: every gate registration cites a committed probe verifying that the events it will count are present in every cell and member before the gate runs. Three gates in that program passed vacuously on empty cells before the rule was adopted.

| Gate | Title | Depends on | Status |
|---|---|---|---|
| G0 | Foundations frozen | none | DONE 2026-09-07 (paper 0.2, prior art, naming) |
| G1 | Machine-checked core | G0 | DONE 2026-09-07 (seven files, no sorry, standard axioms; Ky Fan taken as named hypotheses, not in Mathlib) |
| G2 | Hull law on a public dataset with a known consequence map | G0 | DONE, PASS 2026-09-07 (sealed `experiments/G2/PREREG-G2.md`, blob fd7cc9240c225452a72ca7c9908107fa69b66201; ANES 1972: violation rate 50 percent of 489 testable respondents against a shuffle null of 66 percent, permutation p below 0.005; all five replication pairs pass; the raw rate is half, so the law holds as a population tendency, not as a deterministic statement) |
| G3 | Threshold tracks budget, computational evaluator | G0, G1 | PENDING |
| G4 | Incompatibility regret on a shared code | G0 | SEALED 2026-09-07 (`experiments/G4/PREREG-G4.md`, blob 91c834f7b2bf211ade587458ce859bf48f8560d2; world revised after the probe to the rank ladder 2, 4, 8 with measured-regret bars, Section 6a of the registration; run pending) |
| G5 | Identification: recover metric and ideal from choices | G1 | PENDING |
| G6 | Menu-dependent admissibility and the weak axiom | G0 | PENDING |
| G7 | Human budget manipulation | G3, G5 | PENDING, needs IRB |
| G8 | Submission and archive | G1, G2, G4, and at least one of G3, G5, G6 | PENDING |

## G0. Foundations frozen

Deliverable. `paper/geometric-evaluation-theory.tex` at draft 0.2 with every statement labeled proved, defined, posited, or open; `PRIOR-ART.md`; the name fixed.
Bar. No theorem without a proof, no number without a source, no claim labeled measured.
Verdict. DONE. Commit of record is the first commit of this repository.

## G1. Machine-checked core

Deliverable. Lean 4 files under `lean/GET/` checking, in order of value: the semiorder theorem (a threshold representation is a semiorder, Theorem 2(b)); the hull law for convex costs (Theorem 4(b)); the tolerance-transitivity condition (Theorem 1(c)); the uniqueness theorem in dimension one (Theorem 5 restricted to a line), then in general; Ky Fan's equality case as used in the incompatibility theorem if Mathlib supports it, otherwise the theorem stated with Ky Fan as an axiom named as such.
Bar. Zero `sorry`. Each theorem's Lean name recorded in `claims/LEDGER.md` beside its row.
What falsifies. A theorem that cannot be closed as stated. The statement is then corrected in the paper before anything else proceeds.
Record, 2026-09-07. First pass built on Atlas at `/archive/ahb-sjsu/geometric-evaluation-theory/lean` against Mathlib v4.32.2 with the textbook formalization's packages. Checked: the semiorder theorem (both axioms, irreflexivity, transitivity, trichotomy, the zero-threshold weak order), the tolerance witness and the chain condition for transitivity, the hull law for every convex cost, one-dimensional uniqueness of the ideal with scale freedom, and the reversal example with the no-common-utility statement. One Mathlib name (`lt_or_le`) and one deprecated tactic (`push_neg`) had to be replaced; no statement changed. Second pass, same day. `GET/UniquenessGeneral.lean` checks Theorem 4 in general dimension for the same weak order on all of the space (each ideal in the other metric's kernel shift, proportional metrics with a positive constant, via restriction to lines and polarization); the open-set version of the paper is not checked. `GET/Incompatibility.lean` checks Theorem 7 with Ky Fan's maximum principle as the named hypotheses `KyFanBound` and `KyFanAttained`, since Mathlib has no Ky Fan: regret nonnegative, the weighted total regret bounded below by the deficiency of the weighted sum, the bound attained, zero total regret iff every regret zero, and strict positivity iff no regret-free shared representation. Not checked and not claimed checked: the semidefinite characterization and single-peakedness on a line of Theorem 3, and Ky Fan itself. Clean build at 64b69dd: 8663 jobs, zero warnings, no `sorry`, and all seventeen audited theorems depend only on `propext`, `Classical.choice`, and `Quot.sound`. Verdict. DONE for the deliverable as stated, with the two exclusions above recorded. Axiom audit in `lean/Axioms.lean`: the clean pass (commit 2b51dd9, 8661 jobs, zero warnings, no `sorry`) reports every audited theorem depending only on `propext`, `Classical.choice`, and `Quot.sound`.
Toolchain. The observation-data-mining formalization (`lean/DataMiningAsObservation`, built on Atlas under `~/dmo-lean`) is the template. Build on Atlas, never on the laptop.

## G2. Hull law on a public dataset with a known consequence map

The hull law (Theorem 4(b)) is the cheapest test of the theory. It needs a world whose consequence map is known and menus of at least three alternatives whose consequences are not collinear.
Candidate world. Spatial voting data with respondent-placed candidate positions on two or more issue scales and respondent rankings or thermometer ratings of four or more candidates (American National Election Studies waves with multi-candidate placements). The consequence map is the respondent's own placement of each candidate; the evaluator is the respondent.
Registration. Seal the wave, the issue scales, the candidate set, the ranking source, the tie rule, the exclusion rules, and the null before touching the file.
Statistic. The fraction of respondents whose ranking violates the hull law at least once, against the same fraction under the null that rankings are shuffled within respondent.
Bar. Violation rate below the null by a preregistered margin, with a preregistered minimum number of respondents whose candidate placements are in general position (anti-vacuity: collinear placements make the law empty, and the probe must show how many respondents have a genuinely two-dimensional menu).
What falsifies. Violation rate at or above the null. That would falsify every convex metric of evaluation for that population, not only the quadratic one.
Record, 2026-09-07. Data: ANES 1972 Time Series (ICPSR 7010) Stata release, downloaded by the owner, gitignored. The codebook shows only Nixon, McGovern, Wallace and the two parties placed on issue scales in 1972, so the menu is those five objects on the post-election Form II scales; the primary pair is liberal-conservative with guaranteed jobs, and the five other pairs of the four Form II scales are registered replications. Placement-only probe on Atlas: 557 respondents with a menu of at least four objects, 489 testable against the bar of 300 (`experiments/G2/probe.json`; replication pairs 447 to 553 testable). Loader fixed before sealing to keep thermometer scores of 0, 8 and 9 (separate `thermometer_missing_codes`). Sealed by renaming `PREREG-G2-DRAFT.md` to `PREREG-G2.md`, blob fd7cc9240c225452a72ca7c9908107fa69b66201.
Run, 2026-09-07 (Atlas, screen `get-g2`, 21:21 to 23:22 UTC, `experiments/G2/run.log`, code at 617271d, `/home/claude/env/bin/python3` with scipy 1.17.1, pandas 3.0.2, numpy 2.2.6). Result files committed as executed. Per pair: respondents with a menu, testable, violating at least once, observed share, shuffle-null share (mean and sd over 200 within-respondent shuffles), permutation p, verdict against the sealed bars (pass at observed at most null minus 0.10 and p below 0.01, fail at observed at least null minus 0.02).

| Pair | n | testable | violated | observed | null (sd) | perm p | verdict |
|---|---|---|---|---|---|---|---|
| liberal-conservative, guaranteed jobs (primary) | 557 | 489 | 246 | 0.503 | 0.664 (0.016) | 0 of 200 | PASS |
| liberal-conservative, tax rate | 504 | 447 | 252 | 0.564 | 0.672 (0.018) | 0 of 200 | PASS |
| liberal-conservative, urban unrest | 571 | 519 | 281 | 0.541 | 0.683 (0.016) | 0 of 200 | PASS |
| guaranteed jobs, tax rate | 546 | 492 | 299 | 0.608 | 0.717 (0.013) | 0 of 200 | PASS |
| guaranteed jobs, urban unrest | 603 | 553 | 315 | 0.570 | 0.711 (0.015) | 0 of 200 | PASS |
| tax rate, urban unrest | 545 | 503 | 315 | 0.626 | 0.742 (0.015) | 0 of 200 | PASS |

Verdict. PASS on the primary pair and on every replication pair, by the sealed bars. What the bars do not say, stated here because it matters more than the verdict: half of the testable respondents violate the law at least once. Theorem 3(b) is deterministic for a representable preference, so on this world the hull law holds as a population tendency, 10 to 16 points below the geometric base rate and 7 to 10 null standard deviations from it, and fails as a deterministic statement for about half the respondents. The two smallest margins (the tax-rate pairs, 0.108 and 0.109) sit just above the 0.10 bar. Placements are integers on 7-point scales and ratings are integers on a thermometer capped at 97, ties are counted as not strictly better, and no error model was registered, so no part of the half is attributed to rounding here. Ledger GET-12 graded `[demonstrated]` with this caveat adjacent. The cumulative-file secondary world (`prereg_config.cdf.json`) has not been run, the owner has not downloaded that file.

## G3. Threshold tracks budget, computational evaluator

Prediction (i) of the paper. The indifference threshold of the induced semiorder is the resolution budget.
World. A computational evaluator whose consequence map is known and whose resolution can be set, for example a language-model judge comparing two options whose consequences are rendered at a controlled numeric precision or a fixed context budget, or a quantized scorer with a settable bit width.
Registration. Seal the evaluator, the consequence space, the resolution ladder, the pair set, the estimator of the just-noticeable difference, and the bars.
Bar. The estimated threshold is monotone in the resolution ladder and the ordering of well-separated pairs (separated by more than the largest threshold) is unchanged across the ladder.
What falsifies. A threshold that does not move with resolution, or a reordering of well-separated pairs under a resolution change.

## G4. Incompatibility regret on a shared code

Prediction (iii). Several evaluators reading one rank-k representation each pay the regret of Theorem 6, and the influence-weighted compromise is the leading eigenspace of the weighted sum of their geometries.
World. Several attention heads or several downstream consumers reading one compressed key cache, where readscope recovers each consumer's read operator and turboquant-pro builds rank-k codes. This reuses the observation-theory instruments unchanged.
Registration. Seal the model, the heads, the rank ladder, the recovery protocol (the 2d calls-per-operating-point rule), the regret estimator, and the bars.
Bar. Measured per-head regret of the compromise code within a preregistered tolerance of the Ky Fan bound, and no shared code found that beats the bound for every head.
What falsifies. A shared code that beats the bound for every head, or measured regrets inconsistent with the eigenvalue formula beyond the tolerance.
Record, 2026-09-07. Theory module `experiments/G4/g4_shared_code.py` self-tested on Atlas. Event-presence probe `g4_llama.py --probe` run on Atlas on GPU 1 (screen `get-g4`, 19:37 to 21:00 UTC, log `experiments/G4/probe.log`, config commit e3d3cc2, code at ca687bb): Llama-3.2-3B revision d4446454, layers 8 and 16, all 8 KV heads, 1024 tokens of `workload.txt` (SHA-256 80fcc293...), 64 operating points per cell, 160 directions and 320 calls per point through readscope 0.1.0 as checked out on Atlas. Outputs committed: `probe.json` and the 32 files `probe_L{8,16}_h{0..7}_{Pt,Sigma}.npy`. Findings. Every query head's whitened read operator has effective rank between 2.6 and 8.3 in the 128-dimensional key space, while the key covariance has effective rank 22 to 46 and condition number 540 to 6800. The three heads of a group overlap heavily: the deficiency bound at rank 16 is between 1.4 and 5.6 percent of the summed own-optimal predicted losses, median 3.7 percent, and reaches the registered 5 percent anti-vacuity bar in 4 of 16 cells (bar 12). At rank 8 it reaches 5 percent in 9 of 16 cells, at rank 32 in none. Verdict. The registered world is VACUOUS at rank 16 as registered: a shared rank-16 key code costs the three heads of a group only a few percent over their own codes, because each head reads a subspace of dimension well under 16 and the three subspaces largely coincide. The theorem is not tested by this world at that rank. Per Section 6 of the draft registration the world is revised before sealing, not the bars after the fact. Options recorded for the owner: (a) a rank ladder below the operators' effective rank (2, 4, 8) where the deficiency is largest; (b) consumers from different layers or different KV groups reading one shared code (a cross-layer or cross-head shared code, as a KV-cache compressor actually imposes); (c) a different model with more query heads per KV group. Nothing measured under any code; `results.json` does not exist.
Revision and seal, 2026-09-07. The owner chose option (a). The ladder is 2, 4, 8; from the committed operators the deficiency bound exceeds 5 percent of the summed own-optimal losses in 13, 10 and 9 of 16 cells at those ranks (16 of 16 at rank 1). Reading the evaluator before sealing showed that bars P2 and P4 as drafted compared predicted regrets, which the theorem fixes, so they could not fail; both are restated on measured regrets, a fifth bar P5 tests the theorem's ordering on measured losses alone, P3 and P5 are graded over the non-vacuous cells at each rank, P1 is graded at every rank with a per-rank verdict rule, and the key-PCA code, which as coded was an arbitrary coordinate projector, is now the whitened projector onto the top-k eigenspace of the key covariance. All of it is in Section 6a of the registration and was made before any loss under any code was measured. `g4_grade.py` applies the verdict rule. Sealed by renaming `PREREG-G4-DRAFT.md` to `PREREG-G4.md`, blob 91c834f7b2bf211ade587458ce859bf48f8560d2.

## G5. Identification: recover metric and ideal from choices

Theorem 5 says what choices reveal. The learned-geometry protocol of the observer-representation draft says how to recover it.
World. Synthetic evaluators first (known G and t, choices generated by the semiorder at a known budget), then the TCSS reference implementation as an evaluator, then human data if G7 runs.
Registration. Seal the generator, the menu battery (at least d+1 affinely independent consequences per evaluator, the design bound of the uniqueness remark), the estimator, and the bars.
Bar. Recovered metric within a preregistered principal-angle tolerance of the truth up to scale, and recovered ideal within tolerance modulo the metric's kernel, at every point of the battery above the design bound, and failure below it (the cliff).
What falsifies. Recovery that succeeds below the design bound, which would mean the bound is wrong, or fails above it.

## G6. Menu-dependent admissibility and the weak axiom

Prediction (v). Where an obligation is created by the availability of an action, choice violates the weak axiom in the pattern of Theorem 7, and the violation disappears when the obligation-creating action is absent from every menu.
World. First an agent whose admissibility rule is written down (a rule-following language-model agent or a scripted agent), then a human choice experiment.
Registration. Seal the menus, the obligation rule, the choice elicitation, the count of violating triples, and the null.
Bar. The predicted violation pattern present at a preregistered rate in menus containing the obligation-creating action and absent in matched menus without it.
What falsifies. Violations at the same rate with and without the obligation-creating action.

## G7. Human budget manipulation

Predictions (i) and (ii) in humans. Time pressure, cognitive load, or a coarsened consequence display as the budget manipulation; a known consequence map by construction of the stimuli.
Requires an IRB protocol. Not before G3 has shown the effect in a computational evaluator and G5 has shown the estimator recovers a known geometry.

## G8. Submission and archive

Deliverable. The paper at 1.0 with the ledger rows of every gate that ran, a Zenodo record, the encyclopedia entry updated to cite the ledger, and a venue. Candidates are the Journal of Mathematical Psychology (semiorders, ideal-point models, identification) and Theory and Decision (foundations of evaluation).
Bar. Every headline claim in the paper resolves to a ledger row of class proved, demonstrated, or replicated, or is labeled posited or open in the text.
