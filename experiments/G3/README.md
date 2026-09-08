# G3: the indifference threshold tracks the resolution budget

Gate G3 of `CAMPAIGN.md`. Registration `PREREG-G3-DRAFT.md`, to be sealed after the probe and
the pilot. The evaluator is a language-model judge the theory did not build
(Qwen2.5-7B-Instruct on Atlas), asked which of two numbers is closer to a target; the
consequence map is known exactly (distance to the target). Two resolution budgets are set
independently, the decimals the judge is shown and the judge's own weight precision (bf16,
8-bit, 4-bit), and the just-noticeable difference is measured as the gap at which the judge's
preference for the closer option reaches 90 percent accuracy. The theory predicts the
threshold tracks the budget until the judge's own floor and that well-separated pairs keep
their order.

| File | What |
|---|---|
| `g3_threshold.py` | pairs, the judge (bf16, 8-bit, 4-bit), the accuracy-by-gap measurement, the threshold estimator, self-test on a rounding scorer, probe, pilot, run |
| `g3_grade.py` | applies the sealed bars to `results.json` |
| `prereg_config.json` | judge, prompt, ladders, seeds |
| `PREREG-G3-DRAFT.md` | the registration |

Protocol. Self-test; probe (full precision, 3 decimals, probe seed) for anti-vacuity; pilot
(all twelve cells, pilot seed) to fix the tolerance; seal; run (run seed); grade.
