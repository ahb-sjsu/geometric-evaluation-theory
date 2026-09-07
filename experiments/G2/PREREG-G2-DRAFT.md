# PREREG G2 (DRAFT, NOT SEALED): the hull law on ANES candidate placements

Status: draft. Nothing here is a registered claim until Section 9 is executed. The analysis
code is committed and passes its synthetic self-test on Atlas (`g2_hull_law.py --selftest`,
run of 2026-09-07). The data file has not been downloaded and has not been opened.

## 1. Claim under test

GET-12 (paper prediction (iv), Theorem 3(b), Lean `GET.HullLaw.hull_law`). For an evaluator
whose cost is any convex function of a consequence it places itself, no action is ranked
strictly below every action whose consequences surround it. Operationally, for respondent `r`,
candidate `a`, respondent-placed position `y_a` on the chosen issue scales, and feeling
thermometer `T(a)`,

    a is a violation for r  iff  y_a lies in the convex hull of { y_s : T(s) > T(a) }.

The equivalence with the paper's form is proved in the docstring of `g2_hull_law.py`.

## 2. World

Primary: ANES 1972 Time Series Study (ICPSR 7010), the wave with the most candidates placed by
respondents on 7-point issue scales and rated on thermometers.
Secondary (run only if the primary is executed, as a replication across years): the ANES
Time Series Cumulative Data File, four-object menu per respondent-year, Democratic candidate,
Republican candidate, Democratic party, Republican party, on the scales that carry all four
placements, with the four thermometers.

The consequence map is the respondent's own placement of each object on each chosen scale
(the respondent's belief about consequences, which is the evaluator's `C(a,X)` under its own
`mu`). The evaluator is the respondent. The action set is the candidate menu. The rating is the
thermometer. No self-placement is used, because the hull law does not involve the ideal.

## 3. Variable mapping (TO BE FILLED FROM THE CODEBOOK BEFORE SEALING)

Filling this section requires only the codebook, not the data. The owner fills
`prereg_config.json` with, for the primary world:

- `scales`: the list of 7-point issue scales on which at least four candidates were placed
  (candidate names for the 1972 wave are read from the codebook; the expected set includes
  McGovern, Nixon, Wallace, Humphrey, Muskie, Kennedy, Chisholm, Lindsay, Jackson, Muskie,
  and Agnew on subsets of scales).
- `candidates`: for each candidate, the placement column per scale and the thermometer column.
- `missing_codes` and `valid_placement_values` (1 to 7), `thermometer_range` (0 to 97 or
  0 to 100 as the codebook states, with the codebook's missing codes excluded).
- `weight_column` if the wave carries a weight, else null.
- `id_column`.

Only candidates with a placement on every chosen scale and a thermometer enter a
respondent's menu. A respondent enters the analysis with at least `min_candidates = 4`
such candidates.

## 4. Statistic

Per respondent, `violated` is true if any candidate is a violation. `testable` is true if some
candidate's point lies in the convex hull of the other candidates' points ignoring ratings,
which is the anti-vacuity indicator: a respondent whose placements are in convex position
cannot violate the law under any rating.

    p_obs  = weighted share of testable respondents who violate
    p_null = mean over K = 200 shuffles of thermometers within respondent of the same share

Permutation p-value: fraction of shuffles whose rate is at most `p_obs`. Seed 20260907.

## 5. Bars

- Anti-vacuity: at least 300 testable respondents in the primary world. Below that the gate is
  VACUOUS, not passed and not failed.
- Pass: `p_obs <= p_null - 0.10` (absolute) and permutation p-value below 0.01.
- Fail (falsifies every convex metric of evaluation for this population as the theory reads
  it): `p_obs >= p_null - 0.02`.
- Between the two: INDETERMINATE, reported as such.

## 6. Ties and exclusions

- Thermometer ties are not strictly better. A candidate tied with `a` is not in `a`'s
  better set. This is conservative for the law.
- Placements are used at integer precision as recorded. Hull membership is decided by linear
  programming feasibility, so collinear and repeated placements are handled without a
  triangulation; a point on a segment between two better candidates counts as surrounded.
- Respondents with fewer than four complete candidates are excluded. Missing codes per the
  codebook are excluded per candidate, not per respondent.
- No other exclusion. No trimming of thermometers.

## 7. Event-presence probe (standing rule)

Before sealing, run `g2_hull_law.py --probe` on the data. The probe reads placements only,
never thermometers, and reports the number of respondents, the number with at least four
complete candidates, the number testable, and the distribution of menu sizes. It writes
`probe.json`, which is committed beside the seal. If the testable count is below 300 the
registration is revised (more scales, fewer required candidates) before sealing, and the
revision is recorded.

## 8. Reporting

The result file `results.json` is committed as executed, whatever the verdict. The ledger row
GET-12 is graded `[demonstrated]` on pass, `[refuted]` on fail, `[vacuous]` on vacuity, and
`[exploratory]` on indeterminate, and the paper's Section 6 gains a sentence with the number.

## 9. Sealing procedure

1. Owner downloads the 1972 Time Series data and codebook from electionstudies.org
   (registration required) and places the data file under `experiments/G2/data/` (gitignored).
2. Owner fills Section 3 and `prereg_config.json` from the codebook only.
3. Run the probe (Section 7). Commit `probe.json`.
4. Rename this file to `PREREG-G2.md`, commit, and record its blob hash in `CAMPAIGN.md`.
5. Only then run `g2_hull_law.py --config prereg_config.json --data ... --out results.json`.
