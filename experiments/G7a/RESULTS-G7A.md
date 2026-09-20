# G7a results: the threshold against the clock, in the same chess players

Registration `PREREG-G7A.md`, blob ae29671c248dc6c979e8429016d8dc3c24d44098. Two claims. C1, the
indifference threshold falls as the clock rises with the player held fixed. C2, a posited bridge
(GET-18), that it falls as the inverse square root of the clock.

## July 2026: C1 INDETERMINATE, C2 INDETERMINATE

Graded 2026-09-20, `results/grade_2026-07.json`, sha256 `32e1b58f`. Neither claim passed and
neither failed. The gate did not resolve the question at this size.

| | value |
|---|---|
| exponent of the threshold against the clock | -0.047 |
| 95 percent interval, 1,000 draws resampling players | -0.332 to +0.195 |
| C1, needs the upper end below zero | INDETERMINATE, the interval straddles zero |
| C2, needs minus one half inside an interval no wider than 0.30 | INDETERMINATE, the interval is 0.527 wide |

Minus one half lies outside the interval. Under the sealed bar that is not a C2 failure, because the
width rule comes first: an interval this wide is declared unable to tell the bridge from its
neighbours. It is recorded here at full prominence all the same. The point estimate is near zero and
the bridge's value is outside the interval.

| clock, seconds | threshold at the clock | same players at 300 s | ratio | 95 percent interval | bridge predicts | positions, level and reference |
|---|---|---|---|---|---|---|
| 60 | 0.143 | 0.057 | 2.49 | 0.83 to 4.03 | 2.24 | 4,781 and 5,759 |
| 180 | 0.059 | 0.105 | 0.56 | 0.41 to 1.14 | 1.29 | 5,703 and 5,886 |
| 600 | 0.101 | 0.107 | 0.94 | 0.57 to 1.19 | 0.71 | 5,849 and 5,716 |
| 1,800 | 0.105 | 0.086 | 1.22 | 0.58 to 2.12 | 0.41 | 6,026 and 5,882 |

Thresholds are in win expectation, the gap between the two best moves at which the player picks the
better one three times in four.

**What passed.** All four levels cleared anti-vacuity, 4,781 positions in the smallest arm against a
floor of 3,000. All four cleared the engine-floor guard. The engine's own threshold, measured here
for the first time without the hash carry-over that spoiled the shakedown's figure, is 0.0143, and
the smallest human threshold is four times that. No level was excluded.

**What the table shows.** Bullet is where the bridge says it should be, 2.49 against 2.24. Nothing
else is. The 180 second ratio is on the wrong side of one, and the 1,800 second ratio is above one
where the bridge predicts 0.41. The ratios are not monotone in the clock. All four intervals contain one.

**Why it did not resolve.** The standard deviation of a log ratio is 0.18 to 0.42 with about 5,800
positions an arm. A ratio is known to a factor of about 1.4 to 2.3 either way, and the whole effect
the bridge predicts between neighbouring levels is a factor of 1.3 to 1.7. The anti-vacuity floor of
3,000 positions guaranteed that a threshold could be fitted. It did not guarantee that a ratio of
two thresholds could be told from one, and the registration should have sized for that. That is a
defect of the registration and is recorded as one.

**Read against the table written before the grade** (`../G7b/PLAN-AFTER-G7A.md`). The row is "C1 not
PASS": the instrument is the first suspect, no new gate is drafted, and the diagnosis comes first.
G7b stays a plan.

## Run record, July

| stage | where | count |
|---|---|---|
| positions drawn, eight arms | Atlas, one core, no engine | 853,189 |
| screen labels, 50,000 nodes | NRP, 96 jobs at 1 CPU and 512 Mi | 853,189, none lost, no job failed |
| sent to the deep pass, third-move gap at least 0.04 on the screen | Atlas | 147,467, 17.3 percent |
| deep labels, 1,000,000 nodes | NRP, 96 jobs | 147,467, none lost, no job failed |
| positions with a best move neither won nor lost | | 140,398 |

sha256 of the drawn positions `266a4d3f`, of the screen labels in shard order `22ae5d7c`, of the
deep labels `00b5f5cf`. Measured use on NRP was 0.96 to 1.06 CPU and 234 Mi a pod.

**Deviations, all declared before any label existed.** The grader was replaced by a faster one
whose self-test output is identical byte for byte to the sealed grader's (`GRADER-EQUIVALENCE.md`).
The engine work moved from Atlas to NRP, with labels shown identical across machines once the hash
is cleared per position. The staging script was rewritten during the run to resume and check byte
sizes. It moves files and touches no label.

**One file to ignore.** `grade_EMPTY_no_labels_atlas_script.json` on Atlas is the first run script
grading zero labels after its engine stages had been blocked. It carries no information.

## August 2026

Running. Same bars, same code. It is the same population a month later and not an independent world.
