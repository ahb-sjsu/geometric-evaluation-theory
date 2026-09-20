# PREREG G9b: was the refutation projection, and what does the violation rate do as you read more of the space

Status: SEALED 2026-09-19 by the rename to `PREREG-G9B.md`, on the owner's instruction of the
same day; blob hash recorded in `CAMPAIGN.md`. Sections 2, 3 and 6 are filled from two committed
probes that opened the data only to count events. At the seal no ranking had been formed and no
violation computed in this action space at any dimension, including two, since the action space
differs from G9's. The analysis code is committed and passes its synthetic self-test on Atlas
(`g9b_hull_law.py --selftest`, run of 2026-09-19: zero violations from convex costs at two,
three and four coordinates, on 500, 496 and 390 testable menus).

## Why this gate exists

G9 graded the hull law on ten two-coordinate planes. Four passed, one was indeterminate, and one
refuted, with violations more common than chance on expected points added against first down
probability. A witness row, GET-12w, records that the cause is open.

Afterwards the measurement itself was examined. Projection preserves convex hull membership and
can create it, so reading a menu on two coordinates can only add violations, never remove them.
Measured on synthetic evaluators in G9's exact configuration, rankings from genuine convex
evaluators violate at 0.1506 when read on two of five coordinates, against a true rate of zero.
The refuting plane showed 0.3000, about twice that, so projection contributes and does not
obviously account for it.

The obvious remedy was to stop projecting, and probe 1 killed it. Even thirteen actions leave
three testable units in the full five-dimensional space, and seven actions leave none, though
seven clears Radon's bound of `d + 2`. The consequence coordinates are strongly dependent, so the
points lie near a low-dimensional curved set, and a point on a surface is almost never inside the
hull of other points on that surface.

So the question is not whether projection can be avoided. It is what the violation rate does as
less of it is applied, and whether the one refutation survives being read in more of the space.

## 1. Claims under test

**Primary, C-b1 (was the refutation projection?).** Let `S` be a set of consequence coordinates
containing both expected points added and first down probability. As coordinates are added to
`S`, the hull-law violation rate on `S` falls, and at the largest testable `S` it no longer
exceeds the shuffle null.

**Secondary, C-b2 (the inflation is general).** Averaged over all coordinate subsets of a given
size, the violation rate is non-increasing in the number of coordinates read.

C-b1 can lose in the way that matters. If the rate on supersets of that pair stays at or above
the null, the refutation is not an artifact of the plane and GET-12w stands as a live
counterexample rather than a measurement defect.

## 2. World

Source, exclusions, state cells and pressure strata are PREREG-G9.md Sections 2 and 3
unchanged, and the consequence map of its Section 3 unchanged, five coordinates estimated from
outcomes and standardised across cells.

One thing changes, the action space. G9 used four play calls. This gate uses thirteen, which is
what makes any dimension above two testable at all.

    run_middle
    run_left_end     run_left_tackle     run_left_guard
    run_right_end    run_right_tackle    run_right_guard
    pass_short_left  pass_short_middle   pass_short_right
    pass_deep_left   pass_deep_middle    pass_deep_right

Unit, testability, ranking and tie rule are G9's unchanged. A unit is an evaluator and a state
cell, the evaluator is a franchise pooled across the ten seasons, the ranking inside a cell is
revealed by choice share, equal counts are not strictly better either way, and a unit enters
only when every action is observed at least five times. Testability is G2's rule, applied in the
subset `S` under test: some action's point lies in the convex hull of the others.

Because the action space differs from G9's, no rate in this gate has been measured at any
dimension, including two.

## 3. Statistic

For each coordinate subset `S` with `|S|` from 2 to 5, the fraction of testable units whose
revealed ranking violates the hull law at least once in `S`, against the same fraction under
the null that the ranking is shuffled within the unit, 200 shuffles, and the permutation p.
Identical to G2's and G9's statistic, run through G2's checker, with the subset as the only new
argument.

Twenty-six subsets in all: ten pairs, ten triples, five quadruples, one quintuple.

## 4. Bars (frozen at seal)

**C-b1.** Over the chain of subsets containing both expected points added and first down
probability, one pair, three triples, three quadruples and one quintuple:

    PASS  the violation rate at the largest subset meeting the anti-vacuity floor is at or
          below its own shuffle null, AND the rate does not rise as coordinates are added,
          allowing one reversal of at most 0.02
    FAIL  the rate at that largest subset still exceeds its shuffle null

**C-b2.** The mean violation rate over subsets of size 3 is at most that over subsets of size 2,
and over size 4 at most that over size 3, each within a tolerance of 0.02. This carries a bar
but is secondary and its failure does not change C-b1's verdict.

**Anti-vacuity.** A subset is graded only with at least 50 testable units. The probe measured
199 at two coordinates, a mean of 193 at three and a mean of 93 at four, so the floor is
expected to bind only at five, where the probe measured 3 and where no verdict is therefore
expected. The floor is 50 rather than G2's 300 because this gate estimates rates and compares
them across subsets rather than grading one population against one bar, and because thirteen
actions at five observations each is a much stricter cell filter than four actions was.

**Not a bar.** Every subset's rate, null and permutation p is reported whether or not it is
graded.

## 5. What falsifies

C-b1 fails if the violation rate on the chain containing expected points added and first down
probability remains above its shuffle null at the largest subset that clears the floor. That
would establish the G9 refutation as a property of those decisions rather than of the plane
they were read on, and GET-12w would stand as a live counterexample to the hull law on a
population with a known consequence map.

## 6. Event-presence probes

**Probe 1, `g9b_probe.py`, `g9b_probe.json`.** Testability in the full five-dimensional space,
for thirteen, nine and seven actions: 3, 12 and 0 testable units. The design this gate was first
drafted around, to stop projecting altogether, is dead and the record says why.

**Probe 2, `g9b_probe2.py`, `g9b_probe2.json`.** The dimension ladder for the thirteen-action
space, and the shape of the consequence cloud.

| coordinates read | subsets | testable units, mean | max | cells, mean |
|---|---|---|---|---|
| 2 | 10 | 199.0 | 199 | 126.0 |
| 3 | 10 | 193.2 | 199 | 124.7 |
| 4 | 5 | 92.6 | 168 | 91.2 |
| 5 | 1 | 3.0 | 3 | 35.0 |

The consequence cloud carries 95 percent of its energy in four directions, with the five
singular shares 0.549, 0.232, 0.109, 0.069 and 0.041. It is genuinely four-dimensional, which is
why testability survives to four coordinates and collapses at five.

## 7. Confounds declared before sealing

1. The four confounds of PREREG-G9.md Section 8 carry over unchanged.
2. Subsets of different sizes are tested on different unit sets, because testability depends on
   the subset. A rate that falls with dimension may reflect which units remain testable rather
   than a change in behaviour. The per-subset unit counts are reported beside every rate so a
   reader can see this, and the shuffle null is computed on each subset's own units, which
   absorbs the composition change into the comparison.
3. Thirteen actions at five observations each is a strict filter, and it keeps 126 cells of the
   229 G9 worked with. The cells it keeps are the busy ones, and busy cells are not a random
   sample of game states.

## 8. Compute

Twenty-six exempt-class CPU cells on NRP through the burst flow, one per subset, sized from the
G9 measurement since the loader and the statistic are the same.
