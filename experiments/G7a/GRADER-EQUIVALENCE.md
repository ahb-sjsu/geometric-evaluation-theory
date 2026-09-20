# G7a grader: a faster implementation, shown equivalent before any evaluation data

Recorded 2026-09-20, before any July label exists.

The grader at the sealed code commit aecf7d9 rebuilds its arrays from dictionaries on every
bootstrap draw. It is correct and slow. The replacement builds each arm's arrays once and resamples
players by index. No statistic, bar, seed or rule changes.

Evidence. Both graders were run with `--selftest` on Atlas, same seeds, three synthetic worlds
(exponents of minus one half, zero and minus one). The two outputs are identical byte for byte,
sha256 78d11d65a31a6a2e3cbcb53fc7f0eaf7ada454bb927084d4bdcc9cf8c1046ae8, including every
exponent, interval and ratio to the last printed digit.

| file | sha256 |
|---|---|
| sealed grader, commit aecf7d9 | f9978ba5a0564bde659c3320b6d4951364df1109f09a127f3c0e4ed887f0d285 |
| faster grader, this commit | 6f375bcef7c10dc322cd1561b08c0b78b73a090775aeafb140cb3147e28620b8 |

This is a change to code after the seal and is declared as one. The sealed grader stays on Atlas as
`g7a_grade_sealed.py`. If the two ever disagree on real labels, the sealed grader's verdict is the
verdict.
