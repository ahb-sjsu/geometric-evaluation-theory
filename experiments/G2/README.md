# G2: the hull law on ANES candidate placements

Gate G2 of `CAMPAIGN.md`. Registration is `PREREG-G2.md`, SEALED 2026-09-07. The analysis code is
`g2_hull_law.py`, which passed its synthetic self-test on Atlas on 2026-09-07 (quadratic
evaluators produce zero violations on 286 of 300 testable synthetic respondents; random raters
match their own shuffle null; hand-built, collinear, and tie cases are detected).

## What the owner does before the gate can run

1. Download the data. ANES data are free but require a registered account at
   https://electionstudies.org. Primary world: the 1972 Time Series Study (ICPSR 7010), data
   plus codebook. Secondary world: the Time Series Cumulative Data File, data plus codebook.
   Place the data files under `experiments/G2/data/`, which is gitignored. Never commit them.
2. Fill `prereg_config.json` from the codebook only (copy `prereg_config.template.json`).
   For the 1972 wave the fields are the placement column of each candidate on each chosen
   7-point scale and each candidate's thermometer column. Choose scales on which at least four
   candidates were placed.
3. Run the probe, which reads placements and never ratings:
   `python g2_hull_law.py --config prereg_config.json --data data/<file> --probe --out probe.json`
   Commit `probe.json`.
4. Seal: rename `PREREG-G2-DRAFT.md` to `PREREG-G2.md`, commit, and write its blob hash into
   `CAMPAIGN.md` beside G2.
5. Run: `python g2_hull_law.py --config prereg_config.json --data data/<file> --out results.json`
   and commit `results.json` as executed.

Steps 3 and 5 run on Atlas under the program's compute rule, from
`/archive/ahb-sjsu/geometric-evaluation-theory/experiments/G2/`, with the data placed there.

## Variables known from the public cumulative-file codebook (ICPSR 8475 mirror)

Party placements, 7-point scales, Democratic and Republican party respectively:
liberal-conservative VCF0503 / VCF0504; government health insurance VCF0508 / VCF0509;
guaranteed jobs VCF0513 / VCF0514; aid to blacks VCF0517 / VCF0518; rights of the accused
VCF0524 / VCF0525; urban unrest VCF0528 / VCF0529; school busing VCF0533 / VCF0534; women's
equal role VCF0537 / VCF0538; government services and spending VCF0541 / VCF0542; cooperation
with the USSR VCF0545 / VCF0546; defense spending VCF0549 / VCF0550.
Candidate placements, 7-point scales, Democratic and Republican presidential candidate
respectively: liberal-conservative VCF9088 / VCF9096; guaranteed jobs VCF9087 / VCF9095;
aid to blacks VCF9084 / VCF9092; government health insurance VCF9085 / VCF9093; government
services and spending VCF9086 / VCF9094; women's equal role VCF9083 / VCF9091; cooperation
with the USSR VCF9082 / VCF9090; defense spending VCF9081 / VCF9089. The sitting president's
placements are VCF9073 to VCF9080 on the same scales.
Thermometers: Democratic presidential candidate VCF0424, Republican presidential candidate
VCF0426, president VCF0428, Democratic party VCF0218, Republican party VCF0224. Named
candidates of the 1970s carry their own thermometers (VCF0432 Humphrey, VCF0435 McGovern,
VCF0437 Muskie, VCF0439 Wallace, VCF0440 Agnew, VCF0442 Nixon, VCF0433 Kennedy, VCF0434
McCarthy), which is why the 1972 Time Series, where those candidates were also placed on the
scales, is the primary world. Its placement variable names come from its own codebook, which
the owner downloads with the data.
`prereg_config.cdf.json` is the filled secondary-world config: four objects (the two
candidates and the two parties) on the liberal-conservative and guaranteed-jobs scales, with
the president as a fifth object where present.

## Files

| File | What |
|---|---|
| `PREREG-G2.md` | the sealed registration |
| `g2_hull_law.py` | checker, population statistic, shuffle null, probe mode, self-test |
| `prereg_config.template.json` | the config to copy and fill from the codebook |
| `data/` | the owner's downloaded files, gitignored |
