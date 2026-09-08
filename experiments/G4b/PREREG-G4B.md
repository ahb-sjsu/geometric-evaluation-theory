# PREREG G4b: incompatibility regret of a shared key code, second-order world

Status: SEALED 2026-09-08 by the rename to `PREREG-G4B.md`; blob hash recorded in `CAMPAIGN.md`. G4b is the
follow-up that G4's record in `CAMPAIGN.md` called for: the same theorem, cells, consumers,
workload and recovered operators, with the measurement redefined so that it is the object the
theorem predicts. Nothing from G4's `results.json` was used to choose anything below; the
choices follow from G4's record, which is public at commit dc14015.

## 1. Claim under test

GET-9 (paper Theorem 7, prediction (iii), Lean `GET.Incompatibility`), as in G4 Section 1.
In whitened coordinates the read distortion of consumer `i` under a rank-k code `Q` is
`tr(Pt_i (I - Q))`, its regret is `sum_{j<=k} lambda_j(Pt_i) - tr(Q Pt_i)`, the weighted total
regret of any shared code is at least the deficiency of the weighted sum, and the top-k
eigenspace of the weighted sum attains it.

## 2. World

Identical to G4 Section 2: `unsloth/Llama-3.2-3B` at revision d4446454, layers 8 and 16, the 8
KV heads, the 3 query heads of each group as consumers, `experiments/G4/workload.txt`
(SHA-256 80fcc293...), 1,024 tokens. The read operators are the ones G4's probe recovered and
committed, `experiments/G4/probe_L{8,16}_h{0..7}_Pt.npy` with their key covariances, at 64
operating points per cell with 160 directions and step 0.01 in whitened coordinates. G4b
recovers nothing; it reads those files. The run replays the probe's seeded sampling so that
the consumer (its 64 sampled query positions) and the 64 operating points are exactly the ones
each operator was recovered for.

## 3. Why G4 could not test the formula, and what changes

G4 coded all 1,024 keys of a cell to rank 2, 4 or 8 at once and compared the resulting attention
loss to `tr(Pt_i (I - Q))`. Three things separate those two quantities. The operator is the
Jacobian Gram of a one-key consumer, so the formula predicts the loss of perturbing one key; the
measurement perturbed every key, whose second-order losses add and whose cross terms are not in
any one-key operator. The operator's output is the square-root weights summed over the 64
sampled query positions, while G4's measured loss was the mean over those positions. And a
code that keeps 2 of 128 whitened directions moves every key by about 11 whitened units, far
outside the second-order regime, which is what the 20 to 330 times discrepancy and the 4 nats
of KL per query showed. G4b removes all three.

The measurement. At each operating point `j` of a cell, key `j` alone is replaced by
`S^{1/2} (z_j + delta)` with `delta = eps (I - Q) u`, `u` a standard normal vector in whitened
coordinates drawn once per operating point and shared by every code, rank and consumer at that
point (common random numbers). The loss of consumer `i` is the summed squared change of its
square-root attention weights over the sampled query positions, the same output the operator
was recovered from. The antithetic pair `+delta` and `-delta` is averaged, which cancels the
third-order term exactly. The measured loss at `eps` is that average over the 64 operating
points divided by `eps^2`.

The prediction. `E[delta delta^T] = eps^2 (I - Q)`, so at second order the expected loss is
`eps^2 tr(P_{i,j} (I - Q))` at point `j` and `eps^2 tr(Pt_i (I - Q))` averaged over the 64
points, with `Pt_i` the committed average operator. The prediction is therefore exactly the
theorem's read distortion, with no independence assumption between the local operator and the
perturbation, and the only gaps between prediction and measurement are the fourth and higher
order terms in `eps`, the Monte Carlo error of 64 draws, and any error in the recovered
operators.

The ladder. `eps` in {0.02, 0.05, 0.1, 0.2}; at rank 2 those move the key by about 0.22, 0.56,
1.1 and 2.2 whitened units. Rank ladder 2, 4, 8 as in G4, where the incompatibility is largest
(non-vacuous cells 13, 10, 9 of 16 from the committed operators). Random codes 16 per cell and
rank, seeded, instead of G4's 32, to hold the run near 1.5 million consumer calls.

## 4. Codes

As G4 Section 4 after its revision: the 3 own codes, the compromise, the key-PCA code (whitened
projector onto the image of the top-k eigenspace of the key covariance), and 16 seeded random
projectors. Equal weights.

## 5. Bars

Measured regret and measured weighted total regret are defined as in G4 Section 5 on the
`eps`-scaled measured losses. For each `eps` and each rank:

- P1, second-order validity. The relative error between measured and predicted loss is at
  most 0.25 for at least 80 percent of (cell, code, consumer) triples.
- P2, own codes are measured-best within 5 percent in at least 12 of 16 cells.
- P3, the compromise's measured total regret is within 25 percent of the deficiency bound in
  at least 80 percent of the non-vacuous cells.
- P4, no code's measured total regret is below the bound by more than 25 percent of it, in any
  cell.
- P5, the compromise has the smallest measured total regret of the non-own codes in at least
  80 percent of the non-vacuous cells.

Per `eps` and rank the verdict follows G4's rule (PASS when P1 to P5 hold; FAIL when P4 is
violated in any cell, or P3 or P5 fails in more than half the non-vacuous cells, while P1
holds; INDETERMINATE otherwise). The gate verdict is the per-`eps` gate verdict at the smallest
`eps` at which P1 holds at every rank. If P1 holds at no `eps`, the gate is INDETERMINATE and
the diagnosis below is reported: if the median ratio of measured to predicted loss is the same
at every `eps` and differs from one, the operators are wrong, not the model; if it moves with
`eps`, the second-order regime was not reached at any `eps` of the ladder.

Monte Carlo error. With one antithetic pair at each of 64 points, a loss is a 64-draw average
of a quadratic form of effective rank 3 to 8, so its relative standard error is about 8 to 12
percent, inside P1's 25 percent; regrets between overlapping codes share the same draws and
are far more precise, which is what P3 and P4 rest on. Random codes are noisier and lie far
from the bound.

## 6. What falsifies

At the smallest `eps` where P1 holds: a code whose measured total regret beats the bound
beyond tolerance, or a compromise that does not attain it in most non-vacuous cells, or own
codes that are not measured-best. Those are the theorem's three statements, each now on the
quantity the theorem is about.

## 7. Event-presence probe (standing rule)

The events are the G4 probe's: operators present in every cell, non-vacuous cells 13, 10, 9 of
16 at ranks 2, 4, 8 from the committed operators (`experiments/G4/probe.json` and the ladder
computation recorded in `CAMPAIGN.md` at dc14015). Anti-vacuity holds at rank 2. No new probe.

## 8. Self-test

`g4b_llama.py --selftest`, run on Atlas before sealing: a linear vector consumer with a known
covariance; the real instrument (`readscope.jacobian_probe`, 2d + 8 directions, step 0.01,
whitened coordinates) must recover the whitened operator to 1e-6, which fixes the scale of the
prediction on the build the G4 probe used; the measurement of this file at every `eps` must
match `eps^2 tr(Pt (I - Q))` within Monte Carlo error at 256 points, own codes must be
measured-best, the compromise must sit at the bound, no code may beat it, and the antithetic
pair must agree exactly on a linear consumer. Result, Atlas 2026-09-08, `/home/claude/env/bin/python3` with readscope 0.1.0 from `/home/claude/readscope` (the build the G4 probe used): SELFTEST PASS, instrument recovery within 1e-6, worst relative error of measured against predicted loss 0.119 over 21 codes, 3 consumers, 2 ranks and 2 values of eps at 256 points.

## 9. Sealing procedure

1. Run the self-test on Atlas; record the result in Section 8.
2. Rename this file to `PREREG-G4B.md`, commit, record its blob hash in `CAMPAIGN.md`.
3. Only then run `g4b_llama.py --run --config prereg_config.json --out results.json` on Atlas
   (GPU 1 for the forward pass, then CPU, at most 6 threads, in a named screen session with a
   log), `g4b_grade.py results.json --out grade.json`, and commit both as executed with every
   per-`eps` per-rank verdict.
