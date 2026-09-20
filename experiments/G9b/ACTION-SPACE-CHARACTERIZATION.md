# Characterizing the action space, and where the hull-law violations actually live

Exploratory, registered nowhere, and a measurement of the instrument rather than a test of any
claim. Written 2026-09-19 from `action_space_surface.json` and `violation_vs_precision.json`,
produced by `characterize_action_space.py` and `violation_vs_precision.py` on Atlas.

## Why

G9 read the hull law with four play calls and found expected points added against first down
probability violating above its shuffle null, which is recorded as a refutation and a witness row,
GET-12w. G9b read the same coordinates with thirteen play calls and found the same pair below its
null. At most one of those can be a fact about coaches.

The action space is a parameter. G2 chose five candidates, G9 chose four play calls, G9b chose
thirteen, and none of the three characterized what that choice does to the statistic. This does.

## The design

Four action spaces forming a strict refinement chain, so a coarser menu is exactly a pooling of a
finer one and the comparison is never confounded by which plays are included.

Two aggregations, because the one G2 and G9 both used saturates. A unit counts as violating if
**any** action violates, so a menu of thirteen has thirteen chances to trip it.

    P_unit    fraction of testable units with at least one violation
    P_action  fraction of (unit, action) pairs that are violations

Crossed against reading two, three, four and five of the five consequence coordinates, averaged
over every coordinate subset of that size.

## The surface

| actions | coords read | testable units | P_unit | P_action | violations per unit |
|---|---|---|---|---|---|
| 4 | 2 | 301 | 0.0849 | 0.0212 | 0.08 |
| 4 | 3, 4, 5 | 0 | not testable | not testable | not testable |
| 7 | 2 | 495 | 0.5368 | 0.0950 | 0.67 |
| 7 | 3 | 256 | 0.1103 | 0.0171 | 0.12 |
| 7 | 4 | 38 | **0.0000** | 0.0000 | 0.00 |
| 9 | 2 | 237 | 0.2131 | 0.0255 | 0.23 |
| 9 | 3 | 158 | 0.0175 | 0.0019 | 0.02 |
| 9 | 4 | 46 | **0.0000** | 0.0000 | 0.00 |
| 9 | 5 | 12 | **0.0000** | 0.0000 | 0.00 |
| 13 | 2 | 199 | 0.9141 | 0.1507 | 1.96 |
| 13 | 3 | 193 | 0.4439 | 0.0399 | 0.52 |
| 13 | 4 | 93 | 0.1730 | 0.0133 | 0.17 |
| 13 | 5 | 3 | 0.0000 | 0.0000 | 0.00 |

The survey reproduces G9 where they overlap. Its four-action two-coordinate mean of 0.0849 is
exactly the mean of G9's ten sealed plane results.

## Four findings

**1. The violations live in the projections, and nowhere else.** In every action space the rate
falls monotonically as more coordinates are read, and at four coordinates it is zero at seven and
nine actions and 0.17 at thirteen. Read the consequence space at four or five coordinates and the
hull law is essentially never violated. Read it on a plane and it is violated constantly. That is
the shape of a measurement artifact and not the shape of a fact about coaching.

**2. G9's menu could only ever have been read on a plane.** Four actions are four points, and four
points in general position never put one inside the hull of the other three above two dimensions.
The gate was structurally confined to projections from the moment the action space was chosen, and
no amount of care in the rest of its design could have avoided it. The article on this should say
that rather than implying the plane was a convenience.

**3. The per-action aggregation does not rescue the comparison.** It was introduced because
P_unit obviously saturates, and it does reduce the scale, from 0.91 to 0.15 at thirteen actions on
a plane. It does not remove the dependence: P_action still moves by a factor of seven across
action spaces at fixed dimension. Both aggregations are strongly parameter-dependent, so neither
rate is interpretable without the action space and the reading dimension stated beside it.

**4. The action-count dependence is real but not monotone, and is partly composition.** At two
coordinates the rate runs 0.085, 0.537, 0.213, 0.914 for four, seven, nine and thirteen actions.
Nine is lower than seven. Menus with more actions also survive the five-observation floor in
different cells, so these rows are not computed on the same units, and the composition moves with
the parameter. What can be said is that the choice of menu moves the headline number by an order
of magnitude, and that no gate to date has reported it.

## The mechanism, measured

`violation_vs_precision.py` tested the obvious explanation, that finer menus mean fewer plays per
action, noisier consequence points, and points pulled toward the middle of a configuration where
they fall inside the hull.

On G9's four-action space and its refuting plane the statistic reproduces exactly, P_unit 0.3000.
Then:

- **Violating points sit at half the distance from the centre.** Mean distance from the
  configuration centroid is 0.415 for violating action points against 0.807 for non-violating
  ones. Being in the middle is what a violation is, geometrically.
- **Small samples are not the cause here.** Almost every action in the four-action space carries
  more than a hundred plays, and the violations occur in that bucket at 0.0763. The
  fewer-plays bucket contributes nothing. So for G9 the noise story fails on its own terms.
- **The statistic is nonetheless not robust to the noise that is present, and this is where the
  two G9 verdicts part company.** Every consequence point was jittered by its own measured
  standard error, forty times, and the rate recomputed.

| G9 plane | verdict | observed | null | margin | jitter moves it to | displacement |
|---|---|---|---|---|---|---|
| expected points, turnover (primary) | PASS | 0.0199 | 0.2286 | 0.2087 | 0.0256 (sd 0.0063) | 0.006 |
| expected points, first down (refutes) | FAIL | 0.3000 | 0.2211 | 0.0789 | 0.2112 (sd 0.0215) | 0.089 |

  The pass has a margin thirty times the displacement that sampling noise produces. The
  refutation has a margin smaller than it. One standard error of the noise actually present is
  enough to carry the refuting plane from above its null to below it, and nowhere near enough to
  disturb the primary result.

## What this does to G9

The refutation does not survive. It is a two-coordinate reading in the only dimension its action
space permitted, its rate goes to zero when more of the space is read in every menu that can be
read there, and one standard error of the sampling noise actually present moves it by more than
its whole margin over the null.

GET-12w should be revised from a live counterexample to a witness absorbed by the measurement,
in the way GET-9w was absorbed by the measurement definition in G4. That is a ledger change and it
belongs in a record that names this file.

## What this does to the hull law

It is better supported than any single gate showed. The law is a claim about the evaluator's own
consequence space. Read at four and five coordinates, across three independent action spaces and
several hundred testable units, the measured violation rate is zero.

## Correction the same day: this is a flip, and "artifact" was the wrong word

The owner's reading, and it is right. Everything above calls the two-coordinate result an
artifact of projection and the four-coordinate result the truth. Observation Theory says there is
no such asymmetry to appeal to.

Reading two of five consequence coordinates is an orthogonal projector of rank two. That is a read
operator, `P_C`, in exactly the sense of the flip paper (`geometric-observation`,
`paper/flip_paper_revtex.tex`), where distortion is `tr(P_C Sigma_delta)` and is relative to the
consumer who reads. The flip is two objects reversing order depending on whose read operator
scores them, and the paper's point is that neither ordering is the defective one. Each is correct
for its consumer.

That is the structure measured here. On expected points added against first down probability the
verdict is FAIL under the rank-two read operator and PASS under the rank-four one. The verdict is
read-operator-relative. Nothing was broken in either reading.

**The dimension ladder is a rank-budget ladder.** GET-1 says a rank budget coarsens the
distinctions an evaluator can make, and GET-7 says a change of rank budget reverses preference
between fixed actions. What this file calls projection is that budget, applied by the analyst
rather than by the coach. A verdict that reverses with rank is prediction (ii) appearing in the
observer, and it was filed above as a measurement defect.

What a violation actually detects. The ranking comes from the evaluator's own consequence space and
the geometry is read in the analyst's. A violation appears when the analyst's read operator has
lower rank than the evaluator's. So the violation rate as a function of coordinates read is not a
statistic about the hull law. It is an observability statistic, a measure of how much of the
evaluator's consequence space the analyst is failing to read, which places it beside GET-16 rather
than beside GET-12.

Read that way the surface says something it did not say before. Violations vanish at four
coordinates at seven and nine actions, and the consequence cloud carries 95 percent of its energy
in four directions. **The rank at which violations vanish estimates the effective rank of the
evaluator's consequence space from choices alone**, which is what a blind probe does. The two
fours are not independent, since both reflect the same cloud, and that is stated here so it is not
later mistaken for a convergence of separate measurements.

What stays true from the sections above. The refuting plane is still not robust to one standard
error of sampling noise, its margin of 0.079 against a displacement of 0.089, and that fragility is
a fact about the estimate regardless of how the reversal is interpreted. The flip reading explains
why the verdict moves with rank. It does not rescue a number whose own noise exceeds its margin.

**What this buys.** The budget arm of G9 was graded NOT MEASURABLE because the G5 estimator
recovers no metric from pooled choices. The vanishing rank is a second instrument for the same
quantity, and it works on this data. The budget prediction becomes: under time pressure the
evaluator's effective rank is lower, so violations vanish at a smaller number of coordinates in the
high-pressure stratum than in the low. That is measurable here and it is not measured here, because
it needs its own registration and because this file was written after seeing the surface.

## What any future hull-law gate must report

The action space, the reading dimension, both aggregations, and the testable-unit count, as
parameters of the statistic rather than as setup. A violation rate quoted without them is not a
number about a population.
