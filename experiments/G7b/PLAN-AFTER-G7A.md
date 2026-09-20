# Plan: the phase after G7a

Written 2026-09-20, while G7a's July run is in flight and before any of its thresholds exist. A
plan, not a registration. Nothing here is sealed and nothing here may be run on evaluation data
until its own registration is. It is written now on purpose: a preference about how to read a
result is worth more stated before the result than after.

## Where G7a stands

Sealed, `experiments/G7a/PREREG-G7A.md`, blob ae29671. July positions are being drawn on one Atlas
core. The engine work, about 160 core-hours, goes to NRP as exempt-class jobs. July is graded before
August is labelled. Two claims: C1, the threshold falls as the budget rises with the evaluator held
fixed, and C2, a posited bridge, that it falls as the inverse square root.

## What each G7a outcome means for what comes next

Stated before the grade so that the reading cannot be fitted to it.

| July grade | reading | next |
|---|---|---|
| C1 PASS, C2 PASS | the bridge holds across a thirty-fold range of format | test it where it is sharpest, a single halving, in G7b |
| C1 PASS, C2 FAIL, slope shallower at long budgets than at short | a skill floor. Deliberation noise falls with time and a resolution the player cannot buy does not, so `threshold^2 = floor^2 + c / time`. Minus one half at short budgets, flattening at long ones | register the floor model on July's levels as calibration and predict August and the berserk ratio from it, in G7b. This is a new claim with a parameter, not a rescue of C2, and C2's miss is recorded as a miss |
| C1 PASS, C2 FAIL, slope steeper or not monotone | the bridge is wrong in a way the floor does not explain | G7b still runs, as the cleaner measurement, with no exponent claimed in advance beyond C1 |
| C1 not PASS | either the instrument or the theory. The same players no more discriminating at thirty minutes than at one would surprise every chess player alive, so the instrument is the first suspect | no new gate. Diagnose the engine floor, premoves and the two-alternative restriction first |
| a level excluded by the engine floor or the anti-vacuity floor | the exponent rests on fewer levels | report, and size G7b so it cannot happen there |

## G7b, berserk: one halving, chosen inside one format

**Why it is the sharpest test available.** G7a compares the same players across formats, and its
first declared confound is that a player chooses when to play which format. In a Lichess arena a
player may halve their own clock for an extra tournament point. Same format, same pool, same
evening. It is recorded nowhere as a tag and is visible in the clock tags, where the berserker
starts on half the base time. A check on 256,292 games found 22,267 arena games, 4,029 with one
berserker and 422 with two.

**Predictions, parameter-free under the bridge.**

| arm | budget | predicted threshold ratio against the same player's plain arena games |
|---|---|---|
| the berserker | halved | 1.414 |
| the berserker's opponent | unchanged | 1.000 |

The second row is a placebo and it is the point of the design. The opponent's budget did not
change, so the bridge says their threshold does not either. If it rises too, the effect belongs to
the situation, a wilder game, an opponent taking risks, and not to the budget, and the first row
cannot be read as a budget effect whatever its value.

**Confounds to be declared.** Players berserk when they expect to win, so the berserker is on
average the stronger side and the games must be matched on rating edge. The extra point is paid only
for a win, so berserking shifts incentives toward risk as well as cutting time. Arena scoring
rewards streaks, which changes incentives again. In controls with an increment, berserk also removes
the increment, so the primary arms use controls without one. Plain pool games are not the reference,
plain ARENA games are, because arena play differs from pool play for reasons that have nothing to
do with the clock.

**Event presence.** `g7b_probe.py`, engine-free, running on August as this is written. Per time
control it counts the within-player cohort, players with at least m berserk and at least m plain
arena games at that control, the placebo cohort, and the mean rating edge of a berserker. The gate
is drafted only if both cohorts can put 3,000 positions into the reader at two controls or more.

**Event presence, August, 2026-09-20** (`g7b_probe_2026-08.json`, 91,741,946 games, no engine).
Present, by a wide margin, at four controls without an increment. Players with at least ten
berserk and at least ten plain arena games at the same control, then players with at least ten
games facing a berserker on a full clock:

| control | arena games | one berserker | within-player cohort, players, berserk games | placebo cohort, players, games | berserker's mean rating edge |
|---|---|---|---|---|---|
| 60+0 | 2,030,302 | 250,318 | 3,854, 182,389 | 5,966, 162,719 | +337 |
| 180+0 | 2,125,083 | 488,109 | 7,908, 438,171 | 11,705, 346,785 | +213 |
| 300+0 | 900,199 | 190,116 | 2,870, 121,299 | 4,486, 100,545 | +206 |
| 600+0 | 609,732 | 117,987 | 1,945, 75,280 | 2,445, 53,307 | +210 |

In G7a's shakedown 4.7 to 6.4 percent of labelled positions survived the reader's restrictions
(`shakedown_pass2.json`). At the lowest rate 3,000 needs about 64,000 positions, near 11,000 games
at six positions a game, and every cell above clears that several times over. The
rating edge is large, 200 to 340 points, which makes matching on it a requirement and not a
refinement: an unmatched comparison would read the berserker's opponents as weaker play. At 60+0
a berserker has thirty seconds, where premoves dominate, so 60+0 is a candidate for exclusion on
the same ground as ultrabullet. 
**Event presence, July, 2026-09-20** (`g7b_probe_2026-07.json`, 88,905,085 games). The same picture.
Within-player cohort, then placebo cohort, at ten games each: 180+0, 7,409 players with 411,759
berserk games and 11,031 players facing 323,001; 300+0, 2,868 with 119,443 and 4,405 facing 96,783;
600+0, 1,860 with 69,998 and 2,317 facing 51,069; 60+0, 2,966 with 157,597 and 4,830 facing
136,075. The berserker's mean rating edge is 209 to 312 points. Both months clear the condition for
drafting, 3,000 reader positions in both cohorts at two controls or more, at all four controls.
Drafting still waits on G7a's July grade, because the table above decides what G7b claims.

**Instrument.** G7a's, unchanged: same sampler logic, same labeller with the hash cleared per
position, same two-pass labelling, same reader, same grader with its ratio taken against one instead
of a power of the budget. No new instrument is a feature. A result that differs from G7a's then
differs because of the world.

## G7c, the shape of the budget, lower priority

About a quarter of games carry an increment. Two controls of equal estimated length and different
shape separate two readings of what the budget is. If the budget is the total, thresholds match. If
it is the time guaranteed per move, the increment control is finer late in the game. The probe lists
every control with its estimated length so that matched pairs can be found if they exist. It is not
drafted unless they do, and it waits on G7b because G7b's result says whether the instrument resolves
a ratio as small as this one would be.

## Considered and set aside

Ultrabullet, fifteen seconds, would stretch the range from thirty-fold to a hundred-and-twenty-fold,
but most of its moves are premoves and the limit is the hand. It maps where the bridge stops
applying and tests nothing about deliberation. Correspondence chess is the long end, but it has no
clock tags, allows opening books, and is a different task. The long end is better read from whether
G7a's 1,800-second level bends.

## Debts from G7a to pay inside this phase

1. The engine's own threshold has never been measured cleanly. The shakedown compared two node
   counts while the hash carried over between positions, so it mixed depth with queue position.
   G7a's grader measures it properly on the sealed run. Until then the figure of 0.02 is an upper
   bound.
2. PAID in the commit that added this plan. The bridge had no ledger row. It is a claim under test
   and is now GET-18, posited, with G7a as its gate.
3. The prior-art note is recon grade. Anything from it that reaches a paper owes a
   quote-verification sweep first.
4. The grader rebuilds arrays from dictionaries on every bootstrap draw. Correct and slow. Worth an
   hour before it is asked to run three gates.

## Compute, and whose electricity

Engine search goes to NRP, exempt class, one core and about half a gigabyte a job. Atlas does only
what has to read the 29 GB source files where they live, one core for a pass of twenty to ninety
minutes, plus grading. The files for July and August are already on disk, so this phase downloads
nothing. One streaming pass per month can serve G7b and G7c together.

| gate | positions, order of magnitude | NRP core-hours | Atlas core-hours |
|---|---|---|---|
| G7a August | 800,000 | 160 | 2 |
| G7b, two controls, three arms each, two months | 1,200,000 | 250 | 4 |
| G7c, if drafted | 400,000 | 80 | 2 |

## The ICLR paper

The full paper is due 2026-09-25 and its critical path is the G3c and G3d grades, not this. G7a is
the paper's own headline claim, threshold tracks budget, measured in people, which makes it a better
second world than the football gates now in the appendix. It enters the paper only if July and
August are both graded by 2026-09-23, at the size of its verdict whatever that is, in the appendix,
with the prior-art sweep done. Otherwise it waits for the next version. G7b is not a candidate for
this deadline.

## Order

1. G7a July grades. Read it against the table above, not against hope.
2. G7a August, same code, same commit. Results, campaign, ledger.
3. G7b probe counts in, both months. Draft, self-test the modified grader, seal, run on NRP.
4. G7c only if the probe finds matched pairs and G7b shows the instrument can resolve it.
