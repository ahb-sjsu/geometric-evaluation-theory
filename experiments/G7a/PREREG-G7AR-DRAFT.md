# PREREG G7a-r: the same gate read with shape and lapse tied, tested on August

Status: DRAFT. Sealed by the rename to `PREREG-G7AR.md` and the blob hash in `CAMPAIGN.md`.

## What had been seen when this was written

Everything about July. G7a's July run is graded, INDETERMINATE on both claims
(`RESULTS-G7A.md`), and a diagnosis run on its labels after the grade is the whole motive for this
registration. July is therefore calibration here and can test nothing.

About August, this. A header-only count of players and games, made before G7a was sealed. An
engine-free draw of August positions, started 2026-09-20T13:32Z under G7a's registration and still
running when this was written. No engine has been run on any August position. No screen label and no
deep label from August exists, and the record that shows it is the orchestrator's log on Atlas,
`run_2026-08/nrp_pipeline.log`, whose `[submit] screen` line must carry a time later than this
file's seal commit. If it does not, this registration is void and says so.

## Why this gate exists

G7a's reader fits a threshold, a shape and a lapse rate freely in each arm. On July the lapse swung
from arm to arm, 0.009 against 0.121 at 60 seconds, 0.114 against 0.000 at 180, and the threshold
moved to compensate. The log of a threshold ratio had a spread of 0.18 to 0.42, the exponent's
interval was 0.527 wide, and the gate could not decide. The anti-vacuity floor had been sized for
fitting a threshold and not for telling two thresholds apart.

Fitting one shape and one lapse per level, shared by a cohort's games at the level and the same
cohort's games at 300 seconds, cut that spread about threefold on July. Under that reading July's
ratios are monotone in the clock, in the direction G7a's C1 states, and about a quarter of the size
its C2 states. That was found by looking, after a grade. It is worth exactly one thing: a prediction
that can be sealed before the next month's labels exist.

## 1. Claims under test

**C1r.** With the player held fixed, the indifference threshold falls as the clock rises. This is
GET-11 in people, and it is G7a's C1 unchanged.

**C2r.** It falls as the inverse square root of the clock. This is GET-18, posited, and it is G7a's
C2 unchanged.

**What is expected, stated so that it can be wrong.** C1r passes and C2r fails, with an exponent
between -0.25 and -0.05. If that happens the bridge is refuted in this world at the size of a pass,
and the threshold tracking the budget survives with a much shallower law than the mean of
independent reads gives.

## 2. World, labels, statistic

G7a's, all of it, by reference to `PREREG-G7A.md` blob ae29671: Lichess rated games of August 2026,
the within-player cohorts at 60, 180, 600 and 1,800 seconds against the same players at 300, the
sampler, the two-pass Stockfish labelling with the hash cleared per position, the Lichess logistic as
consequence map, the two-alternative restriction with the third-move cutoff of 0.10, the player
bootstrap with 1,000 draws, the slope through the origin weighted by inverse bootstrap variance, the
engine-floor guard at three times the screen engine's threshold, and the anti-vacuity floor of 3,000
positions an arm. August's positions and labels are produced once, by G7a's run, and both readers
grade the same files.

**The one change.** For each level the reader fits four parameters jointly: a threshold for the
level's games, a threshold for the reference games, one shape and one lapse shared by both. The fit
is redone inside every bootstrap draw. Code `g7a_grade_tied.py` at the seal commit.

## 3. Bars (frozen at seal)

**C1r.** PASS if the upper end of the exponent's 95 percent interval is below -0.05. FAIL if the
lower end is above zero. INDETERMINATE otherwise. The margin of 0.05 is not taken from July. It is
the leak measured in the self-test below: a world with a flat threshold and a lapse rate falling
from 0.12 at one minute to 0.04 at thirty reads as -0.052.

**C2r.** PASS if minus one half lies inside the interval and the interval is no wider than 0.30.
FAIL if minus one half lies outside it and the interval is no wider than 0.30. INDETERMINATE if it
is wider. G7a's bar let an interval too wide to decide swallow a value that lay outside it, and July
showed what that costs, so here the width rule and the outside rule are both stated.

**Guards.** G7a's. Fewer than three levels entering makes the gate INDETERMINATE.

## 4. What falsifies

C1r fails if the interval lies above zero, and it does not pass if the fall is no larger than a
lapse gradient could leak. C2r fails if minus one half is outside a decisive interval. Either
failure is recorded in the ledger, the campaign and any paper at the size of a pass.

## 5. Self-test (2026-09-20, `g7a_grade_tied.py --selftest`, Atlas, log sha256 `bc4426dc`)

Synthetic cohorts of 300 players whose resolution follows a known law, 60 bootstrap draws.

| world | true exponent | read | interval | C1 | C2 |
|---|---|---|---|---|---|
| inverse root | -0.50 | -0.475 | -0.517 to -0.449 | PASS | PASS |
| shallow | -0.15 | -0.138 | -0.191 to -0.103 | PASS | FAIL |
| flat | 0.00 | +0.005 | -0.037 to +0.050 | not passed | FAIL |
| flat, lapse falling with the clock | 0.00 | -0.052 | -0.092 to +0.008 | not passed | FAIL |
| inverse root, lapse falling with the clock | -0.50 | -0.492 | -0.537 to -0.452 | PASS | PASS |

The self-test was graded with the upper end compared to zero. With the bar of this registration,
-0.05, the shallow world still passes C1r, -0.103, and no flat world does. The reader shrinks a true
exponent toward zero by five to eight percent in the worlds without a lapse gradient, which is small
against the distance between -0.5 and the expected value.

## 6. Known weaknesses

* The reader was chosen after seeing July, and July's pattern under it is what this registration
  predicts. August is the same population a month later, not an independent world, and many of the
  same players. A pass is a replication within one population and is reported as that.
* Tying assumes the same players lapse at the same rate at both clocks. The self-test measures what
  a lapse gradient leaks, for one gradient, and the bar is moved by that much. A steeper gradient
  would leak more. The shared lapse the reader fits per level is reported so a reader of the record
  can see whether it changes with the clock.
* G7a's declared confounds stand: players choose when to play which format, premoves at one minute,
  and time forfeits kept in the sample.
* G7a's own August verdict, under its sealed reader, is graded and reported beside this one with
  the same prominence. Two readers on one month is two looks, and the record shows both.

## 7. Reporting and compute

No new engine work. The grade is one core on Atlas for about an hour. Every number names its file
and commit.
