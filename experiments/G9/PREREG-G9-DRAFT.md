# PREREG G9: the hull law and the budget prediction on natural human decisions at scale

Status. DRAFT, not sealed. Sections 2, 3 and 7 are filled from three committed probes that
opened the data only to count events. No ranking, no hull violation and no statistic of any
hypothesis has been computed. One pre-seal probe is still outstanding and is named in
Section 7. Sealing is by the rename to `PREREG-G9.md` with the blob hash recorded in
`CAMPAIGN.md`, and is the owner's step.

Why this gate exists. G2 measured the hull law on 489 survey respondents and found it holds
as a population tendency and fails as a deterministic statement for about half of them. That
record carries two limits. The evaluator was asked to place the alternatives itself, so the
consequence map is a self-report, and the decision had no stakes. G7 would remove both by
manipulating a human budget directly, and it needs an IRB protocol that does not exist. This
gate takes the third road. It uses human decisions that were already made, at stakes the
decision-maker cared about, with a consequence map estimated from outcomes rather than from
any report, and it uses the game clock as a budget manipulation that nobody had to administer.

## 1. Claims under test

**Primary, GET-12 (paper prediction (iv), Theorem 3(b), Lean `GET.HullLaw.hull_law`).** For an
evaluator whose cost is any convex function of a consequence the world supplies, no action is
ranked strictly below every action whose consequences surround it. Operationally, for
evaluator `e`, state cell `c`, action `a`, consequence position `y_a` in the registered
two-coordinate consequence plane, and revealed rank `R(a)`,

    a is a violation for (e, c)  iff  y_a lies in the convex hull of { y_s : R(s) better than R(a) }.

This is the same operational form as G2 Section 1, with the respondent replaced by an
evaluator and the self-placed candidate position replaced by a consequence the world supplies.

**Secondary, GET-11 and GET-7 (prediction (i) and (ii), Theorem 2(b) and Theorem 5).** A
smaller resolution budget coarsens the distinctions an evaluator can make, which lowers the
effective rank of its metric and reverses preference between fixed actions. The game clock
supplies the budget manipulation without an experimenter.

A note on why the world and the evaluator split the way they do here. GET's foundational
commitment gives the world `(X, A, C)` and the evaluator `(G, B, K)`. The consequence map in
Section 3 is therefore estimated once, across all evaluators, and each evaluator is permitted
its own metric, budget and admissible set. An evaluator-specific consequence map would make
every ranking trivially representable, which is the failure the commitment exists to prevent.

## 2. World

Source. nflverse play-by-play releases, the public artifact behind nflfastR, seasons 2015
through 2024, regular season only. Files are the per-season parquet releases at
`github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_<season>.parquet`. The
sha256 of each file as fetched is recorded in `probe.json` at seal time and the files are
gitignored.

Evaluator. A team, pooled across the ten seasons. The probe in Section 7 measured all three
candidate definitions and this is the only one that carries a per-evaluator test at adequate
count. The franchise's coaching staff changes inside the window, so the pooled object is a
franchise tendency rather than one person, and that is stated wherever the result is stated.

Action space. Four play calls that the source records directly.

    run_inside    a run between the tackles
    run_outside   a run outside the tackles
    pass_short    a pass thrown short of the registered depth boundary
    pass_deep     a pass thrown beyond it

Downs one, two and three. Fourth down is excluded from the primary arm for the reason in
Section 7 and is retained as a separate record.

State cell. The menu is held fixed inside a cell defined by down, distance bin, field position
bin and score-differential bin, with the bin edges frozen here.

    ydstogo             (0, 3], (3, 6], (6, 10], (10, 100]
    yardline_100        (0, 20], (20, 50], (50, 80], (80, 100]
    score_differential  (-100, -8], (-8, -3], (-3, 3], (3, 8], (8, 100]

Budget stratum. High pressure is the final 240 seconds of either half, low pressure is the
rest. The threshold is frozen here and a sensitivity record at 180 and 300 seconds is reported
beside the result without carrying a bar.

## 3. Consequence map

Estimated from outcomes only. For each cell and action, the map is the mean over every play of
that action in that cell, pooled across all evaluators, of five coordinates.

    y1  expected points added
    y2  probability the play gains a first down
    y3  probability the play is a turnover, meaning an interception or a lost fumble
    y4  the standard deviation of expected points added, the risk coordinate
    y5  probability the play stops the clock

Nothing in this map reads which action was called by whom. It reads what happened after each
action was called.

Consequence plane. The hull law in five dimensions is close to vacuous, because a point lies in
the convex hull of three others with vanishing probability once the ambient dimension exceeds
two. G2 handled this by testing on pairs of issue scales. This gate does the same. The primary
plane is `(y1, y3)`, expected points added against turnover probability. Of the nine other pairs,
the five that clear the anti-vacuity floor in Section 6 are registered replications and each is
reported with its own verdict. The four that do not are named in Section 7 before sealing and are
reported with their counts and no verdict.

## 4. Revealed ranking

The source records the action taken and never records a ranking. The ranking is therefore
revealed by choice share inside a cell, which is a stochastic-choice device and is registered
as such. For evaluator `e` and cell `c`, the rank of action `a` is the descending order of the
count of `a` in that cell. A pair whose counts are equal is treated as not strictly better in
either direction, which matches G2's tie rule.

A unit `(e, c)` is testable only when every one of the four actions is observed at least five
times, so that a share is estimated from something rather than from nothing.

## 5. Statistic

Primary. The fraction of testable units whose revealed ranking violates the hull law at least
once, against the same fraction under the null that the ranking is shuffled within the unit.
The null draws 200 within-unit shuffles, as G2 did.

Secondary, the budget arm. The metric and ideal are recovered by the G5 identification
estimator separately in the low-pressure and high-pressure strata, and the reported statistics
are the effective rank of the recovered metric in each stratum, and the fraction of fixed action
pairs whose order reverses between strata. The low-pressure fit is written to file with its
sha256 before any high-pressure cell is opened, so the predicted reversal set is committed
before it is scored.

## 6. Bars

Primary, carried over from G2 so the two worlds are comparable without adjustment.

    PASS  observed violation rate at most the null rate minus 0.10, and permutation p below 0.01
    FAIL  observed violation rate at or above the null rate minus 0.02
    otherwise INDETERMINATE

Anti-vacuity, primary arm, applied per plane. At least 300 testable units on that plane, where
testable carries G2's meaning and not a weaker one. A unit is testable when some action's
consequence point lies in the convex hull of the other three, ignoring the ranking, because a
menu in convex position cannot violate the hull law under any ranking whatsoever. A plane below
the floor is reported as vacuous and carries no verdict. Probe 5 measured this and four of the
ten planes fall below it, which is recorded in Section 7 before sealing rather than discovered
after.

Secondary, the budget arm. Its statistic is not a hull count and its anti-vacuity floor is
therefore its own. At least 100 cells and 20,000 decisions in each pressure stratum, so that
the identification estimator has a battery on both sides.

    PASS  effective rank strictly lower under high pressure, and at least 60 percent of the
          reversals predicted from the committed low-pressure fit observed under high pressure
    FAIL  effective rank equal or higher under high pressure

What falsifies the primary claim. A violation rate at or above the shuffle null. That would
refute every convex metric of evaluation for these decision-makers, not only the quadratic one.

## 7. Event-presence probes

Three probes have run on Atlas and are committed beside this file. Each opened the data only to
count events.

**Probe 1, `g9_probe.py`, output `g9_probe.json`.** Fourth-down decisions, the design this gate
was first drafted around. Ten seasons give 35,406 decisions after the exclusions, but only 41
state cells carry all three of the go, field goal and punt actions at three or more
observations, and only 11 of those sit under time pressure. Against G2's 489 testable
respondents that is not a gate, so the fourth-down design was abandoned before anything was
sealed. The record is kept because the count is the reason.

**Probe 2, `g9_probe2.py`, output `g9_probe2.json`.** The play call one level down. 303,414
decisions, 229 cells, 201 of them carrying all four actions at five or more observations and
holding 297,201 decisions. Under high pressure 126 cells qualify and under low pressure 189.
Both sides of the budget manipulation are populated.

**Probe 3, `g9_probe3.py`, output `g9_probe3.json`.** Who the evaluator can be. Measured at
three definitions.

| evaluator | testable units, all four actions | evaluators reached | units under high pressure |
|---|---|---|---|
| league, pooled | 201 | 1 | 126 |
| team, pooled over ten seasons | 962 | 32 | 99 |
| team and season | 471 | 263 | 0 |

The primary arm takes the team definition, which gives 962 units across all 32 evaluators. The
budget arm cannot be run per evaluator at all, since the team definition leaves 99 high-pressure
units and the team-season definition leaves none. The budget arm is therefore registered at the
league evaluator, where 126 high-pressure cells survive, and that limitation is stated wherever
its result is stated rather than in a footnote.

**Probe 4, `g9_probe4.py`, output `g9_probe4.json`.** Whether the menus are genuinely two
dimensional, which is the anti-vacuity question G2's probe asked before that gate could be
sealed. The probe builds the consequence map of Section 3 and, for each cell and each of the
ten planes, takes the singular values of the four centred action points after each coordinate
is standardised across cells. A cell spans two dimensions when the ratio of the smaller
singular value to the larger exceeds the tolerance 0.05, frozen here.

| plane | cells in general position, of 201 | median singular ratio |
|---|---|---|
| expected points added, turnover probability (primary) | 188 | 0.235 |
| expected points added, first down probability | 185 | 0.173 |
| expected points added, risk | 190 | 0.241 |
| expected points added, clock stop | 194 | 0.230 |
| first down probability, turnover probability | 187 | 0.201 |
| first down probability, risk | 188 | 0.185 |
| first down probability, clock stop | 195 | 0.187 |
| turnover probability, risk | 174 | 0.116 |
| turnover probability, clock stop | 180 | 0.148 |
| risk, clock stop | 192 | 0.151 |

Every plane clears the floor. The weakest is turnover probability against risk, at 174 cells and
a median ratio of 0.116, which is expected, since a call that turns the ball over more often is
also the call whose outcome varies more, so those two coordinates are the closest to redundant
of the ten pairs. Under high pressure the ratios rise rather than fall, 0.266 against 0.233 on
the primary plane, so the menus do not flatten in the stratum where the budget arm needs them.

**Probe 5, `g9_probe5.py`, output `g9_probe5.json`.** Testable under G2's rule, which supersedes
probe 4's count for the purpose of the floor in Section 6. Probe 4 asked whether the four points
span two dimensions. That is the weaker question. G2 asked whether some point lies in the convex
hull of the others, because a menu in convex position cannot violate the law under any ranking,
and a gate that counted spanning menus as testable would report a floor it had not met. This
probe imports G2's own checker so both worlds are counted by identical code.

| plane | units testable, of 962 | cells testable, of 201 | above the floor of 300 |
|---|---|---|---|
| turnover probability, risk | 517 | 88 | yes |
| expected points added, first down probability | 450 | 84 | yes |
| expected points added, risk | 434 | 88 | yes |
| expected points added, turnover probability (primary) | 402 | 95 | yes |
| first down probability, risk | 399 | 89 | yes |
| first down probability, clock stop | 307 | 42 | yes |
| expected points added, clock stop | 277 | 37 | no |
| first down probability, turnover probability | 126 | 84 | no |
| turnover probability, clock stop | 53 | 65 | no |
| risk, clock stop | 43 | 28 | no |

The primary plane clears the floor at 402 units. Six of the ten planes clear it and are
registered replications. The remaining four are declared vacuous here, before sealing, and will
be reported with their counts and no verdict. Naming them now is the point of the probe, since a
plane demoted after the fact is a plane chosen after the fact.

The budget arm is measured against its own floor rather than this one. Both strata clear it, 189
cells and 240,237 decisions at low pressure against 126 cells and 50,143 at high. The hull
counts under pressure are small, 68 testable units at the best plane, which is why the budget
arm's statistic is the identification estimator on pooled choices and not a hull count.

**Outstanding before seal.** Nothing. The five probes fill Sections 2, 3 and 7 and every floor in
Section 6 is either met or its plane is declared vacuous in advance.

## 8. Confounds declared before sealing

1. The consequence map is estimated from plays that were chosen, so the outcome of a deep pass
   on third and short is conditioned on the situations in which somebody called it. The map is a
   conditional expectation and not a causal effect, and the hull law is a statement about the
   geometry the evaluator faces rather than about what would have happened under a different
   call. No causal claim is made from this map.
2. A cell pools states that differ in ways the bins do not capture, including personnel, weather
   and opponent. Pooling widens a cell and blunts the ranking rather than sharpening it, so it
   works against the primary claim rather than for it.
3. Choice share reveals a ranking only if the evaluator is choosing rather than randomizing on
   purpose. Play-calling has a genuine mixed-strategy motive, since a predictable caller is
   exploited. A deliberate mixture flattens shares toward equality, which makes ties more common
   and makes the ranking harder to establish, again against the claim.
4. The franchise pools coaching staffs across ten seasons, as Section 2 states.

## 9. Reporting

Every number in the result names its file and the commit that produced it. A miss is recorded
in `claims/LEDGER.md`, in `CAMPAIGN.md` and in the paper at the same size as a pass. The run
persists the per-unit record, meaning the counts, the consequence points, the revealed ranking
and the per-unit verdict, so that a miss can be diagnosed from its own file without a second
run.

## 10. Compute

The probes ran on Atlas. The sealed run goes to NRP through the existing burst flow, as
exempt-class cells at one CPU and two gigabytes, one cell per consequence plane and stratum.
The workload is small-matrix and would sit far below the 40 percent floor on a GPU, so it
requests none. Sizing is measured before submission rather than guessed, per the standing
cluster rules.
