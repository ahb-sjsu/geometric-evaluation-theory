# G4: incompatibility regret of a shared key code

Gate G4 of `CAMPAIGN.md`. Registration is `PREREG-G4-DRAFT.md`, unsealed. Theory module
`g4_shared_code.py` passed its synthetic self-test on Atlas on 2026-09-07. The model probe
`g4_llama.py --probe` ran on Atlas the same day (`probe.log`, `probe.json`, the `.npy`
operators). Anti-vacuity at rank 16 failed, 4 of 16 cells against a bar of 12: each query
head reads a subspace of effective rank 3 to 8 and the three heads of a group largely
coincide, so a shared rank-16 code costs them only a few percent. The world is to be revised
before sealing (see the G4 record in `CAMPAIGN.md`). No losses were measured under any code.

## The experiment in one paragraph

In Llama-3.2-3B each KV head's keys are read by three query heads. Those three heads are
three evaluators sharing one representation. readscope recovers each head's read operator
from the head alone (two calls per input dimension per operating point); the keys' covariance
whitens the space; a shared code is a rank-k orthogonal projector in whitened coordinates
applied to every key of the cell. The theory predicts each head's loss under any such code,
says each head's own code has zero regret, says the compromise code (top-k eigenspace of the
summed read operators) attains a computable lower bound on the total regret, and says no code
beats that bound for everyone. The gate measures the heads' actual attention-distribution loss
under those codes and checks all four.

## Files

| File | What |
|---|---|
| `g4_shared_code.py` | formulas, code constructions, evaluation, synthetic self-test (`--selftest`) |
| `g4_llama.py` | model probe (`--probe`, read operators and anti-vacuity only) and sealed run (`--run`) |
| `fetch_workload.py` | fetches the fixed public-domain workload text and prints its hash |
| `prereg_config.json` | the world, protocol constants, and bars; revision and Atlas versions confirmed |
| `workload.txt` | the fixed workload (Gutenberg 1342, first 200000 characters), SHA-256 80fcc293... |
| `probe.json`, `probe.log`, `probe_*.npy` | the probe record: per-cell effective ranks, deficiency ratios, principal angles, and the whitened read operators and key covariances |
| `PREREG-G4-DRAFT.md` | the registration to seal |

## How the probe was run on Atlas (2026-09-07)

1. Confirm on Atlas: the cached model repository id and revision, the readscope version and
   the `jacobian_probe` signature, the transformers version and the rotary-embedding call.
   Write the versions into `prereg_config.json`. The two `CONFIRM` comments in `g4_llama.py`
   mark the lines that depend on them.
2. `python fetch_workload.py` on Atlas, commit `workload.txt`.
3. Probe, in a named screen session on GPU 1:
   `CUDA_VISIBLE_DEVICES=1 python g4_llama.py --probe --config prereg_config.json --out probe.json`
   Commit `probe.json` and the per-cell `.npy` operators. Check the anti-vacuity bar.
4. Seal per `PREREG-G4-DRAFT.md` Section 10, then `--run`, then commit `results.json`.
