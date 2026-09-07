# PREREG G4 (DRAFT, NOT SEALED): incompatibility regret of a shared key code

Status: draft. Nothing here is a registered claim until Section 10 is executed. The theory
module `g4_shared_code.py` passed its synthetic self-test on Atlas on 2026-09-07 (linear
consumers: measured loss within 0.7 percent of predicted distortion, own codes zero regret,
compromise attains the bound, none of 64 random codes beats it). The model probe has not run.

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

`readscope.jacobian_probe` (readscope 0.2.0) at each operating point (key position j, a seeded
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
for it. Rank ladder k in {8, 16, 32, 64}. Per cell and
rank: the 3 own-optimal codes, the compromise, the key-PCA code (top-k eigenspace of Sigma,
mapped to whitened coordinates), and 32 seeded random projectors.

## 5. Measurement

For each cell, rank, code, and consumer: the measured loss is the mean over the 64 sampled
query positions of the summed squared difference of square-root attention weights between
the original keys and the coded keys (all keys of the cell coded at once). The KL divergence
of the attention distributions is reported beside it. The predicted loss is
`tr(Pt_i (I - Q))`. Regrets, weighted totals, and the deficiency bound follow Section 1.

## 6. Predictions and bars

- P1, second-order validity. For k >= 16, the relative error between measured loss and
  predicted loss is at most 0.25 for at least 80 percent of (cell, code, consumer) triples.
- P2, own codes. The measured regret of each consumer's own code is at most 5 percent of its
  own-optimal measured loss in at least 12 of 16 cells at every rank.
- P3, compromise. The measured weighted total regret of the compromise code is within 25
  percent of the deficiency bound in at least 12 of 16 cells at every rank.
- P4, no code beats the bound. In no cell and at no rank does any evaluated code have a
  measured weighted total regret below the deficiency bound by more than 25 percent of the
  bound.
- Anti-vacuity (from the probe, before sealing): the deficiency bound exceeds 5 percent of
  the summed own-optimal predicted losses in at least 12 of 16 cells at k = 16, meaning the
  three query heads of a group read genuinely different geometries. If not, the gate is
  VACUOUS for this model and the registration is revised to a world with more distinct
  consumers before sealing.

Pass: P1 to P4 all hold. Fail: P4 violated in any cell (a shared code better than the bound
for everyone), or P3 failing in more than 8 cells. Otherwise INDETERMINATE.

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

## 9. Compute and thermal rule

GPU 1 only (`CUDA_VISIBLE_DEVICES=1`), float32 attention math, batch of 64 queries, at most
20 CPU threads, run inside a named screen session with a log. The probe is 16 cells x 3
heads x 64 positions x 320 calls, each call one attention evaluation over 1,024 keys for 64 queries,
which is small.

## 10. Sealing procedure

1. Confirm the model repository id and revision and the readscope version on Atlas; write
   them into `prereg_config.json`. Commit `workload.txt` and its hash.
2. Run the probe on Atlas. Commit `probe.json`. If the anti-vacuity bar fails, revise the
   world and record the revision.
3. Rename this file to `PREREG-G4.md`, commit, record its blob hash in `CAMPAIGN.md`.
4. Only then run `g4_llama.py --run` and commit `results.json` as executed.
