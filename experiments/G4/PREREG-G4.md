# PREREG G4: incompatibility regret of a shared key code

Status: SEALED 2026-09-07 by the rename to `PREREG-G4.md`; blob hash recorded in `CAMPAIGN.md`. The theory module `g4_shared_code.py`
passed its synthetic self-test on Atlas on 2026-09-07 (linear consumers: measured loss within
0.7 percent of predicted distortion, own codes zero regret, compromise attains the bound, none
of 64 random codes beats it, and, after the revision below, the same three statements in
measured regrets). The model probe ran on Atlas on 2026-09-07 (`probe.json`, commit 5dbc942)
with the rank ladder 8, 16, 32, 64 and the anti-vacuity bar of that draft FAILED at rank 16,
4 of 16 cells against a bar of 12. Section 6a records the revision made in response, before
any loss under any code was measured. Everything else below is as drafted before the probe.

## 1. Claim under test

GET-9 (paper Theorem 7, prediction (iii), Lean `GET.Incompatibility`). Several evaluators
reading one rank-k representation each pay a regret relative to their own best rank-k
representation. In whitened coordinates the regret of consumer `i` under projector `Q` is
`sum_{j<=k} lambda_j(Pt_i) - tr(Q Pt_i)`, the weighted total regret of any shared projector is
at least the deficiency `sum_i w_i sum_{j<=k} lambda_j(Pt_i) - sum_{j<=k} lambda_j(sum_i w_i Pt_i)`,
and the top-k eigenspace of the weighted sum attains it. The read operator `Pt_i` is the
consumer's own geometry, recovered from the consumer alone.

## 2. World

Model: `unsloth/Llama-3.2-3B` from the HuggingFace cache on Atlas, the checkpoint every
observation-theory Gate-B harness used (revision recorded in `prereg_config.json` before
sealing), loaded in float32 on GPU 1 with attention recomputed in float64 numpy from the
captured post-rotary queries and keys. Layers 8 and 16, the cells of the program's rematch
probe; layers outside {4, 8, 16, 20} are unspent and available for an out-of-sample rerun.

Consumers and shared representation. The model uses grouped-query attention with 8 KV heads
and 24 query heads, so each KV head's keys are read by exactly 3 query heads. A cell is one
(layer, KV head); its shared representation is that KV head's key vectors (dimension 128); its
consumers are the 3 query heads of the group; N = 3, weights w_i = 1. There are 16 cells.

Workload. A fixed public-domain text committed as `workload.txt` (SHA-256 recorded at sealing),
truncated to the first 1,024 tokens of the model's tokenizer, run once with no sampling. The
keys and queries of the two layers after rotary embedding, at every position, are the
operating points and the query workload.

Consumer definition. For KV head h and query head g in its group, the consumer at key position
j maps a key vector `x` (replacing key j) to the vector of square roots of the attention
weights of every query position over all keys, concatenated over a fixed sample of 64 query
positions (seeded). Its squared output change under a key perturbation is half the summed
KL divergence of the attention distributions to second order, so the read operator recovered
from it predicts the KL loss up to that factor. Causal masking is respected: a query attends
only to keys at or before it.

## 3. Recovery protocol

`readscope.jacobian_probe` (readscope 0.1.0 as checked out on Atlas, whose signature is the one the probe calls) at each operating point (key position j, a seeded
sample of 64 positions per cell), with 160 unit-norm probe directions at d = 128, above the
instrument's recovery cliff at k = d, central differences (320 calls per operating point),
step h = 1e-2 in whitened units, and the identity output metric. This is the published Gate-B
protocol. The probe is run in whitened coordinates directly, so the recovered operator is
already `Pt_i = Sigma^{1/2} P_i Sigma^{1/2}`, with `Sigma` the covariance of that KV head's
keys over the workload plus 1e-6 I; the per-position operators are averaged over the sampled
positions (jacobian_probe averages, the Gate-B loop summed, and the difference matters when
operators are added across heads).

The operator is the Jacobian Gram of the square-root-attention output map, the softmax-weighted
object a finite-difference probe recovers. It is not the unweighted query covariance that
earlier gates graded against; calibration C-10 showed the two differ by about 0.3 in
subspace overlap, so this registration names the Jacobian Gram and grades nothing against
Q^T Q. Per cell the probe records readscope's effective rank of each operator and the
step-response convergence of `readscope.diagnostics.step_response` at h/2, h, 2h.

## 4. Codes

All codes are rank-k orthogonal projectors in whitened coordinates, applied to every key of
the cell as `xhat = Sigma^{1/2} Q Sigma^{-1/2} x`, with no quantization, so that the
representation class is exactly the theorem's. The compromise code, the top-k eigenspace of
the summed (equal-weight) operators of the three query heads, is exactly the per-KV-head read
subspace the program's live-decode harness already builds by summing the group's operators;
the theorem is what says that construction is total-regret optimal and what each head pays
for it. Rank ladder k in {2, 4, 8} (revised, Section 6a). Per cell and
rank: the 3 own-optimal codes, the compromise, the key-PCA code (the orthogonal projector in
whitened coordinates onto the image of the top-k eigenspace of Sigma, a code that knows the
keys and none of the readers), and 32 seeded random projectors.

## 5. Measurement

For each cell, rank, code, and consumer: the measured loss is the mean over the 64 sampled
query positions of the summed squared difference of square-root attention weights between
the original keys and the coded keys (all keys of the cell coded at once). The KL divergence
of the attention distributions is reported beside it. The predicted loss is
`tr(Pt_i (I - Q))`. Predicted regrets, weighted totals, and the deficiency bound follow
Section 1. The predicted regrets are consequences of the theorem and cannot contradict it, so
the bars are stated on measured regrets: consumer `i`'s measured regret under code `Q` is its
measured loss under `Q` minus its measured loss under its own code `own_i`, and the measured
weighted total regret of `Q` is the weight-sum of those. A cell is non-vacuous at rank k when
the deficiency bound exceeds 5 percent of the summed own-optimal predicted losses at that rank.

## 6. Predictions and bars

- P1, second-order validity. At every rank of the ladder, the relative error between measured
  loss and predicted loss is at most 0.25 for at least 80 percent of (cell, code, consumer)
  triples at that rank. At rank 2 the code discards 126 of 128 whitened directions, so this
  is where the quadratic model is most strained, and P1 is what says whether it survives.
- P2, own codes are measured-best. For each consumer, its measured loss under its own code is
  at most 1.05 times the smallest measured loss over every evaluated code, in at least 12 of
  16 cells at every rank.
- P3, compromise attains the bound. Over the non-vacuous cells at a rank, the measured
  weighted total regret of the compromise code is within 25 percent of the deficiency bound
  in at least 80 percent of them.
- P4, no code beats the bound. In no cell and at no rank does any evaluated code have a
  measured weighted total regret below the deficiency bound by more than 25 percent of the
  bound.
- P5, ordering without the quadratic model. Over the non-vacuous cells at a rank, the
  compromise code has the smallest measured weighted total regret of every evaluated code
  other than the three own codes in at least 80 percent of them. This is the theorem's
  ordering claim tested on measured losses alone.
- Anti-vacuity (from the probe, before sealing): the deficiency bound exceeds 5 percent of
  the summed own-optimal predicted losses in at least 12 of 16 cells at the smallest rank of
  the ladder, meaning the three query heads of a group read genuinely different geometries
  there. The count of non-vacuous cells at every rank is recorded before sealing.

Per rank: PASS when P1 to P5 all hold at that rank; FAIL when P4 is violated in any cell, or
P3 or P5 fails in more than half of the non-vacuous cells, while P1 holds; INDETERMINATE
otherwise, including every case in which P1 fails at that rank, because P3 and P4 compare a
measurement to a quadratic prediction. Gate: PASS when every rank passes; FAIL when any rank
fails; INDETERMINATE otherwise. Every per-rank verdict is reported.

## 6a. Revision after the probe (2026-09-07, before any loss was measured)

The probe (commit 5dbc942) found the read operators of effective rank 2.6 to 8.3 in 128
dimensions with the three heads of a group largely coincident, so the drafted ladder 8, 16,
32, 64 was vacuous at rank 16 (4 of 16 cells) and thin at rank 8 (9 of 16). The revision:

1. Rank ladder 2, 4, 8, chosen because the theorem's content, a positive regret that no
   shared code escapes, lives below the operators' effective rank. From the committed probe
   operators, the deficiency bound exceeds 5 percent of the summed own-optimal losses in 13
   of 16 cells at rank 2, 10 of 16 at rank 4, 9 of 16 at rank 8 (16 of 16 at rank 1, 4 of 16
   at rank 16). Anti-vacuity holds at the smallest rank, and P3 and P5 are graded over the
   non-vacuous cells at each rank, whose counts are the ones just stated.
2. P2 and P4 restated in measured regrets. As drafted they compared predicted regrets, which
   the theorem fixes, so they could not fail. `evaluate_codes` now records measured regrets,
   measured totals, and each consumer's excess of its own code over the measured best.
3. P5 added, the ordering claim on measured losses alone.
4. The key-PCA code as coded was the top-k eigenspace of the identity, an arbitrary
   coordinate projector mislabeled. It is now the whitened projector onto the image of the
   top-k eigenspace of Sigma.
5. P1 restated at every rank, with the per-rank verdict rule above.

Nothing about the consumers, the workload, the operators, the recovery protocol, the code
family's other members, the seeds, or the tolerances changed.

## 7. What falsifies

A shared code that beats the deficiency bound for every consumer, or measured regrets that do
not follow the eigenvalue formula beyond the tolerance while P1 holds.

## 8. Event-presence probe (standing rule)

`g4_llama.py --probe` recovers the read operators and the key covariances and writes
`probe.json` with, per cell: readscope's effective rank of each operator and its step-response
convergence, the effective rank and condition number of Sigma (anisotropy, which is why whitening is not optional), the
effective rank of each Pt_i, the principal angles between the three heads' top-16 eigenspaces,
and the deficiency bound at each rank relative to the summed own-optimal predicted losses. It
computes no measured loss under any code.

Probe record (Atlas, GPU 1, 2026-09-07 19:37 to 21:00 UTC, `probe.log`, commit 5dbc942):
key covariance effective rank 22 to 46, condition number 540 to 6800; read operators of
effective rank 2.6 to 8.3; deficiency bound over summed own-optimal losses at rank 16 between
0.014 and 0.056, median 0.037; non-vacuous cells (bound above 5 percent) 16, 13, 10, 9, 4 of
16 at ranks 1, 2, 4, 8, 16. The per-cell operators are `probe_L{8,16}_h{0..7}_Pt.npy` with
the covariances beside them, and the run reads them rather than probing again.

## 9. Compute and thermal rule

GPU 1 only (`CUDA_VISIBLE_DEVICES=1`), float32 attention math, batch of 64 queries, at most
20 CPU threads, run inside a named screen session with a log. The probe is 16 cells x 3
heads x 64 positions x 320 calls, each call one attention evaluation over 1,024 keys for 64 queries,
which is small.

## 10. Sealing procedure

1. Confirm the model repository id and revision and the readscope version on Atlas; write
   them into `prereg_config.json`. Commit `workload.txt` and its hash. Done 2026-09-07.
2. Run the probe on Atlas. Commit `probe.json`. If the anti-vacuity bar fails, revise the
   world and record the revision. Done 2026-09-07, revision in Section 6a.
3. Rename this file to `PREREG-G4.md`, commit, record its blob hash in `CAMPAIGN.md`.
4. Only then run `g4_llama.py --run --config prereg_config.json --out results.json` on Atlas
   and commit `results.json` as executed, with every per-rank verdict.
