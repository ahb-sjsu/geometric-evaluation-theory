# PREREG G2: the hull law on ANES candidate placements

Status: SEALED 2026-09-07 by the rename to `PREREG-G2.md`; blob hash recorded in `CAMPAIGN.md`. The analysis
code is committed and passes its synthetic self-test on Atlas (`g2_hull_law.py --selftest`,
run of 2026-09-07, and again after the loader change recorded in Section 6). The 1972 data
file was downloaded by the owner on 2026-09-07 (`NES1972.dta` from the ICPSR 7010 Stata
release, SHA-256 a764e5779afe71d5..., gitignored). Sections 2, 3 and 7 were filled from the
codebook `nes1972.txt` and the placement-only probe before sealing; no thermometer value was
read by anything but the probe's menu-membership check described in Section 7.

## 1. Claim under test

GET-12 (paper prediction (iv), Theorem 3(b), Lean `GET.HullLaw.hull_law`). For an evaluator
whose cost is any convex function of a consequence it places itself, no action is ranked
strictly below every action whose consequences surround it. Operationally, for respondent `r`,
candidate `a`, respondent-placed position `y_a` on the chosen issue scales, and feeling
thermometer `T(a)`,

    a is a violation for r  iff  y_a lies in the convex hull of { y_s : T(s) > T(a) }.

The equivalence with the paper's form is proved in the docstring of `g2_hull_law.py`.

## 2. World

Primary: ANES 1972 Time Series Study (ICPSR 7010), post-election wave. The draft expected many
named candidates to be placed on the issue scales; the codebook shows that in 1972 only three
politicians (Nixon, McGovern, Wallace) and the two parties were placed by respondents, while
the other named candidates (Humphrey, Muskie, Kennedy, Chisholm, and the rest) carry
thermometers only. The menu is therefore five objects, Nixon, McGovern, Wallace, the
Democratic party, the Republican party, exactly the object set of the cumulative-file
secondary world plus Wallace. Four post-election scales carry all five objects, all on Form II
of the post-election questionnaire: liberal-conservative (also asked on Form I),
government guaranteed jobs and standard of living, tax rate increase, and urban unrest.
The primary pair is liberal-conservative with guaranteed jobs, the same two scales as the
secondary world. The other five pairs of those four scales are replication pairs, run after
the primary with the same code, bars, seed and null, and all six reported whatever they show.
No pair is chosen from ratings. Higher-dimensional menus (three or four scales) are not
registered: five points in three or more dimensions are almost always in convex position, so
the law would be empty there.
Secondary (run only if the primary is executed, as a replication across years): the ANES
Time Series Cumulative Data File, four-object menu per respondent-year, Democratic candidate,
Republican candidate, Democratic party, Republican party, on the scales that carry all four
placements, with the four thermometers.

The consequence map is the respondent's own placement of each object on each chosen scale
(the respondent's belief about consequences, which is the evaluator's `C(a,X)` under its own
`mu`). The evaluator is the respondent. The action set is the candidate menu. The rating is the
thermometer. No self-placement is used, because the hull law does not involve the ideal.

## 3. Variable mapping (filled from the codebook `nes1972.txt`, ICPSR 7010, 2026-09-07)

All variables are post-election questions. Placements (7-point scales, codes 1 to 7 valid,
0 inapplicable, 8 don't know, 9 not ascertained or inapplicable):

| Object | liberal-conservative J8/J11 | guaranteed jobs J4 | tax rate | urban unrest | thermometer |
|---|---|---|---|---|---|
| Nixon | V720653 | V720614 | V720662 | V720671 | V720702 (K1B) |
| McGovern | V720654 | V720615 | V720663 | V720672 | V720703 (K1C) |
| Wallace | V720655 | V720616 | V720664 | V720673 | V720701 (K1A) |
| Democratic party | V720656 | V720617 | V720665 | V720674 | V720719 (K2P, Democrats) |
| Republican party | V720657 | V720618 | V720666 | V720675 | V720721 (K2R, Republicans) |

Thermometers: 00 to 96 degrees as given, 97 means 97 to 100, 98 don't know, 99 not
ascertained or inapplicable; valid range 0 to 97 with 98 and 99 missing. The party
thermometers are the group thermometers for Democrats and Republicans, the same source the
cumulative file uses for its early-year party thermometers. Respondent id V720002. The 1972
file has no weight variable, so weights are 1. No row filter: a respondent enters through
having the placements, which restricts the sample to Form II post-election respondents by
construction. `prereg_config.json` is the primary pair; `prereg_config_1972_<a>_<b>.json`
are the five replication pairs.

The draft's instructions, kept for the record:

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
- Loader change before sealing, 2026-09-07: the draft loader used one missing-code set for
  placements and thermometers, which would have discarded true thermometer scores of 0, 8 and
  9. The config now carries `thermometer_missing_codes` (98, 99) separately from the placement
  codes (0, 8, 9). The self-test was rerun and passes.

## 7. Event-presence probe (standing rule)

Before sealing, run `g2_hull_law.py --probe` on the data. The probe uses placements only for
its statistic; it reads whether a thermometer is present, because an object enters a
respondent's menu only with a valid rating, but never a rating's value. It reports the
number with at least four complete objects, the number testable, and the distribution of
menu sizes, and writes `probe.json`, committed beside the seal. If the testable count is
below 300 the registration is revised before sealing and the revision is recorded.

Probe record, run on Atlas 2026-09-07 with `/home/claude/env/bin/python3` (scipy 1.17.1,
pandas 3.0.2, numpy 2.2.6):

| Pair | respondents with a menu | testable | menu of 4 / of 5 |
|---|---|---|---|
| liberal-conservative, guaranteed jobs (primary) | 557 | 489 | 130 / 427 |
| liberal-conservative, tax rate | 504 | 447 | 121 / 383 |
| liberal-conservative, urban unrest | 571 | 519 | 114 / 457 |
| guaranteed jobs, tax rate | 546 | 492 | 141 / 405 |
| guaranteed jobs, urban unrest | 603 | 553 | 152 / 451 |
| tax rate, urban unrest | 545 | 503 | 129 / 416 |

Anti-vacuity holds on the primary pair (489 against the bar of 300) and on every replication
pair.

## 8. Reporting

The result file `results.json` is committed as executed, whatever the verdict. The ledger row
GET-12 is graded `[demonstrated]` on pass, `[refuted]` on fail, `[vacuous]` on vacuity, and
`[exploratory]` on indeterminate, and the paper's Section 6 gains a sentence with the number.

## 9. Sealing procedure

1. Owner downloads the 1972 Time Series data and codebook from electionstudies.org
   (registration required) and places the data file under `experiments/G2/data/` (gitignored).
   Done 2026-09-07.
2. Fill Section 3 and `prereg_config.json` from the codebook only. Done 2026-09-07.
3. Run the probe (Section 7). Commit `probe.json`. Done 2026-09-07.
4. Rename this file to `PREREG-G2.md`, commit, and record its blob hash in `CAMPAIGN.md`.
5. Only then run `g2_hull_law.py --config prereg_config.json --data data/NES1972.dta --out
   results.json`, then the five replication configs to `results_1972_<a>_<b>.json`, on Atlas,
   and commit every result file as executed.
