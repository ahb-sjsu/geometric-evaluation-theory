# PREREG G7a: the indifference threshold tracks the time budget, in the same players across chess clocks

Status. DRAFT, not sealed. Every section is filled. No threshold has been fitted on any evaluation
month, and on the shakedown month none has been fitted outside the reference level. What has touched
the evaluation months is a header-only count of players and games and an engine-free draw of
positions from the first 1.4 percent of July to check the sampler's mechanics. Neither parses a
quality of any move. Sealing is by the rename to
`PREREG-G7A.md` with the blob hash recorded in `CAMPAIGN.md`.

## Why this gate exists

Prediction (i) of the paper, ledger row GET-11, says the indifference threshold tracks the
resolution budget. G3 demonstrated it on a language-model judge whose budget was set by the
experimenter. G7 would test it in people and has waited on an ethics protocol, because it would
manipulate them.

Public chess records carry a budget nobody administered. The players chose a time control before
the first move, the clock is recorded on every move, an engine supplies the value of every
alternative including the ones not played, and the same person can be found playing at several
budgets. This gate is the observational arm of G7.

Prior art is in `PRIOR-ART-G7A.md` and it took most of the novelty. Regan and Haworth already fit a
discrimination threshold per player, so the threshold is theirs. That fast chess is worse chess is
common knowledge, so the ordinal claim alone would register the known. What is left is a functional
form committed before measurement, read on the same players at different budgets.

## 1. Claims under test

**C1, the theory's own (GET-11, ordinal).** Holding the evaluator fixed, the indifference threshold
falls as the time budget rises.

**C2, a posited bridge, labelled as such.** The threshold falls as the inverse square root of the
budget. The paper shows that reading the mean of `n` sampled scores lowers a judge's threshold as
`n` to the minus one half. If deliberation time buys independent reads of a position at a constant
rate, the same exponent carries over to seconds. That "if" is the bridge. It is not a theorem of
the theory, and C2 failing would refute the bridge and leave C1 standing.

With the evaluator held fixed the bridge has no free parameter. It predicts the ratio of thresholds
between any two budgets outright, so there is nothing to calibrate and nothing to look at first.

| budget against 300 s | predicted threshold ratio |
|---|---|
| 60 s | 2.236 |
| 180 s | 1.291 |
| 600 s | 0.707 |
| 1,800 s | 0.408 |

Rival exponents, named so the result can be read against them. Zero, the threshold does not track
the budget. Minus one, the threshold is inversely proportional to it.

## 2. World

Source. The Lichess open database, standard rated games, CC0. July 2026 is the primary month and
August 2026 the replication. The files were fetched by their official torrents on 2026-09-20 and
their sha256 is recorded beside the cohort counts. June 2026 is the shakedown month and is never an
evaluation month.

Budget. The time control, fixed before the first move, which is what makes it exogenous to every
position in the game. Five exact controls, all without increment so the budget is unambiguous: 60,
180, 300, 600 and 1,800 seconds. 300 is the reference. The clock left at the moment of the move is
recorded and reported as a secondary variable. Time spent on the move is NOT a budget. Sunde,
Zegners and Strittmatter find faster moves are better moves among professionals, because a long
think marks a position the player finds hard, so time spent is endogenous to the position.

Evaluator, and why cohorts. Lichess keeps a rating per category, so a 1600 in bullet and a 1600 in
classical are different numbers from different pools and skill cannot be equated across budgets by
rating. Comparing whoever plays bullet with whoever plays classical would confound the budget with
who shows up. So for each level `L` other than the reference, the cohort is the players with at
least ten games at `L` and at least ten at 300 seconds inside the month. Thresholds are compared
within that cohort, at `L` and at the reference. The evaluator is held fixed and only the budget
moves.

Games. Both players human, rated 1200 to 2399 in that game's category, ended normally or on time.
Games lost on time are kept on purpose. They are far commoner at short budgets, and dropping them
would keep, at short budgets only, the games where clocks were managed well.

Games are taken by a keyed hash of the game identifier falling under a per-arm rate. The file is
chronological, so filling a quota would sample the first days of the month, and the hash spreads the
sample over all of it, reproducibly, owing nothing to what happened in the game. Rates are set from
the cohort counts so every arm aims at 100,000 positions.

Positions. Up to six per game, at plies 16 to 80, drawn by a generator seeded from the game's
identifier, where the mover belongs to the cohort and has at least three legal moves. Six and not
two because of the 1,800-second cohort, which holds about 25,000 games in a month and would fall
under the anti-vacuity floor at two. It is six for every arm so that the rule is one rule. The
bootstrap resamples players, so several positions from one game do not narrow an interval. The
sample is fixed before any engine runs.

An arm is a cohort read at one budget. A reference position can serve several cohorts, since one
player can be in several. It is labelled once and tagged with every arm it serves.

Usernames are replaced by a keyed hash. The key is held in a mode-600 file outside the repository.

## 3. Consequence map and labels

Stockfish 19, one thread, 64 MB hash, fixed node counts and never fixed time, so a label does not
depend on how busy the machine was. Three principal variations per position.

Values are centipawns from the mover's side, converted to an expected score by the logistic Lichess
publishes for games between humans, with constant 0.00368208. The engine's own win-draw-loss model
is not used. It describes engines playing engines, and the shakedown lost 62 percent of its
positions to it before the mistake was seen.

Two passes. A screen at 50,000 nodes passes any undecided position whose second-to-third gap is at
least 0.04. Those are labelled again at 1,000,000 nodes, and every inclusion decision below is made
on the deep labels alone. On the shakedown the screen recovered 95.6 percent of the positions the
deep labels call two-alternative while passing 20 percent of all positions.

A position enters the reader when, on the deep labels, the mover's best expected score is in
[0.10, 0.90], the second move is at least 0.10 above the third, and the human played one of the top
two.

## 4. Statistic

The reader is `g7a_threshold.py`. It fits a two-alternative psychometric curve with chance fixed at
one half, and the threshold is the gap at which the lapse-free curve reaches 75 percent.

For each level `L`, the ratio `R_L` is the cohort's threshold at `L` over the same cohort's
threshold at 300 seconds. The exponent is the slope of `ln R_L` on `ln(L / 300)` through the origin,
since the ratio is one at the reference by construction, weighted by the inverse bootstrap variance
of each `ln R_L`. Intervals are from 1,000 bootstrap draws that resample players, not positions.

## 5. Bars (frozen at seal)

**C1.** PASS if the upper end of the exponent's 95 percent interval is below zero. FAIL if the
interval lies above zero. INDETERMINATE otherwise.

**C2.** PASS if minus one half lies inside the 95 percent interval and the interval is no wider than
0.30. FAIL if minus one half lies outside it. INDETERMINATE if the interval is wider than 0.30, since
an interval that wide would contain the bridge and its neighbours alike.

**The engine floor.** The engine has a discrimination threshold of its own. On the shakedown, labels
at 50,000 and 200,000 nodes agree on the better of two moves 96 to 100 percent of the time above a
gap of 0.04 and as little as 53 percent below 0.01. Label noise near a human threshold inflates it,
and inflates small thresholds more than large ones, which drags the exponent toward zero. So the
reader is turned on the instrument: the screen engine is scored as if it were a player against the
deep labels, and its threshold is the floor. A level enters the exponent only if both of its
thresholds are at least three times the floor. If fewer than three of the four levels remain the
gate is INDETERMINATE.

**Anti-vacuity.** Each arm of each level, the cohort at `L` and the cohort at the reference, needs
at least 3,000 positions entering the reader. A level that misses is reported and left out.

**Replication.** August is graded by the same bars and reported beside July. It is the same
population a month later and not an independent world, and the record says so.

**Not a bar.** Every per-level ratio with its interval, the share of positions surviving each
restriction per level, the exponent refitted on the screen labels alone, the exponent with
zero-second moves removed, and the threshold against clock remaining within a level.

## 6. What falsifies

C1 fails if the same players are no less discriminating at 1,800 seconds than at 60. C2 fails if
the measured exponent's interval excludes minus one half, in which case deliberation time does not
buy independent reads at a constant rate and the bridge from the paper's sampling result to seconds
is wrong.

## 7. Event-presence probes and instrument tests

**Probe, `g7a_probe.py`.** First 1.5 GB of June 2026. 4,919,786 games in under two days, a clock tag
on every move of every one, 110,693 of 785,797 players in two or more main categories.

**Reader self-test, `g7a_threshold.py --selftest`.** Passed in both noise worlds after two readers
failed. Slope of reported against true threshold 0.984 Gaussian and 0.977 Gumbel. An inverse-root
world is read as -0.485 and -0.501, a flat world as -0.006 and +0.005, an inverse world as -0.980 and
-0.968. The residual attenuation of about 2 percent moves a true minus one half by about 0.01, which
is small against the interval width C2 allows and is not corrected for.

**Reader diagnoses, `g7a_reader_diagnosis.py` and `g7a_reader_diagnosis2.py`.** The first two
readers drifted because keeping top-two choices conditions on those two beating the rest. A reader
that fits no curve at all drifted the same way, and only in worlds with more than two moves. The
cutoff on the third move is the only fix that is right under both Gaussian and Gumbel noise.

**Shakedown, `g7a_shakedown.py`.** June only, and blind by construction: counts for every category,
a threshold for the reference category alone, and the script asserts as much. 21,000 positions, 72
percent undecided, 4.7 to 6.4 percent surviving every restriction, similar across categories.

**Cohort count, `g7a_cohort_probe.py`.** Header-only, on both evaluation months in full, 88,905,085
games in July and 91,741,946 in August. It parses no move and runs no engine. Players with at least
ten games at the level and at least ten at 300 seconds, and the player-games they hold.

| level | July players | July games at level | July games at 300 s | August players | August games at level |
|---|---|---|---|---|---|
| 60 s | 17,639 | 2,851,362 | 1,101,341 | 18,699 | 2,950,332 |
| 180 s | 34,840 | 4,601,917 | 2,649,333 | 35,645 | 4,804,746 |
| 600 s | 24,294 | 1,670,121 | 2,024,970 | 25,200 | 1,741,062 |
| 1,800 s | 754 | 24,819 | 57,741 | 819 | 26,643 |

File sha256. July `68738b1c448f051dc8d42db645d5b01749988a3bc1c24981adfe44ea92060dc7`, August
`6bf6fa8a5dee7bb81d1874ac312160060daf12f18a29dc2740a3bf6f5e5e6248`.

The 1,800-second cohort is the binding constraint and it set the six-positions rule in Section 2.
At the shakedown's survival share of about 5.5 percent, an arm of 100,000 positions puts about 5,500
into the reader against a floor of 3,000. The floor is expected to hold at every level and is not
expected to hold with much room at 1,800 seconds.

**Sampler check, `g7a_sample_cohort.py`.** Engine-free, on the first 1.4 percent of July. The eight
arms drew between 1,338 and 1,718 positions each, so the per-arm rates balance and extrapolate to
between 96,000 and 124,000 positions an arm over the month.

**Grader self-test, `g7a_grade.py --selftest`.** The bars themselves on synthetic cohorts whose law
is known. An inverse-root world must pass both claims, a flat world must not pass C1, and an inverse
world must pass C1 and fail C2. Its result is recorded in the seal commit, and the gate is not
sealed unless it passes.

## 8. Confounds declared before sealing

1. A player chooses when to play which time control. Someone who plays classical when rested and
   bullet when tired differs between budgets in more than the budget.
2. Positions differ by budget. Short games are wilder. Conditioning on the gap holds the difficulty
   of the question fixed and does not hold the kind of position fixed.
3. Premoves. At short budgets many moves are entered before the opponent has moved and are not
   decisions made on the clock in the same sense. They inflate the short-budget threshold, which
   pushes the exponent away from zero. Reported with zero-second moves removed, without a bar,
   because removing them conditions on time spent.
4. Engine label noise, which pushes the exponent toward zero, guarded in Section 5.
5. The consequence map is one logistic for all ratings from 1200 to 2399.
6. The cohort restriction keeps people who play several time controls, who are not a random sample
   of chess players.
7. The reader uses about one position in twenty. The two-alternative positions it keeps are
   disproportionately forcing ones.

## 9. Reporting and compute

Every number names its file and commit. A miss is recorded in the ledger, the campaign and any paper
at the size of a pass. The run persists raw centipawns for every labelled position, so any later
change of consequence map or cutoff is a recomputation and not a rerun.

Runs on Atlas, pinned to a fixed set of cores at the lowest priority. About 800,000 positions a
month, some 47 core-hours of screening and 116 of deep labelling. The work is CPU-bound engine
search, which is the kind of load the cluster rules favour, but the source files and the sampled
positions live on Atlas, so moving them buys nothing. July runs first and is graded before August is
labelled, and August is graded by the same code at the same commit.
