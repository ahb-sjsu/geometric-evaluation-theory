# G4b: incompatibility regret of a shared key code, second-order world

Follow-up to G4 (`../G4/`). Same theorem, model, cells, consumers, workload and recovered read
operators; the measurement is redefined so that it is the quantity the theorem predicts. G4
coded all 1,024 keys to rank 2, 4 or 8 at once, which sits 20 to 330 times outside the
quadratic prediction. G4b perturbs one key at each probed operating point by `eps (I - Q) u`
with `u` isotropic in whitened coordinates, so the expected loss is exactly
`eps^2 tr(Pt_i (I - Q))` at second order, with an antithetic pair cancelling the third order
and common random numbers across codes so that regrets are estimated precisely. An `eps`
ladder 0.02 to 0.2 says where the second-order regime is, and the gate verdict is read at the
smallest `eps` where it holds.

Outcome. The regime is reached and the prediction is unbiased at the median (ratio 1.02 to 1.05 up to `eps` 0.1), but 64 draws per cell scatter the per-cell ratio by 20 percent, so the per-triple bar is missed and the sealed verdict is INDETERMINATE. Inside the quadratic regime the regret bars are theorems plus noise; the empirical content of the prediction there is the quadratic model with the recovered operator, which holds.

| File | What |
|---|---|
| `PREREG-G4B.md` | the sealed registration |
| `prereg_config.json` | world, ladder, codes, bars, gate rule |
| `g4b_llama.py` | the measurement (`--run`) and the self-test on a linear consumer through the real instrument (`--selftest`) |
| `g4b_grade.py` | applies the sealed rule at every `eps` and picks the gate verdict |
| `results.json`, `grade.json`, `run.log` | the sealed run as executed, 2026-09-08: INDETERMINATE (table and reading in `CAMPAIGN.md`) |
| `g4b_seedcheck.py`, `seedcheck.json`, `seedcheck.log` | exploratory, after the seal: five extreme cells with four fresh draw sets each, showing the per-cell offsets are draw noise |

Reads `../G4/probe_*.npy`, `../G4/workload.txt`, and imports `../G4/g4_shared_code.py`,
`../G4/g4_llama.py` (model loading and capture) and `../G4/g4_grade.py` (per-rank rule).
