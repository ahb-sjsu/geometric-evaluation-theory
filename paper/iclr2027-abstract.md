# ICLR 2027 abstract registration, drafted 2026-09-18 from gate G3

Source of every number: `experiments/G3/grade.json` (gate PASS, sealed registration
`experiments/G3/PREREG-G3.md`, blob 53cb1a0022ae7334b33f683f1acae6f620969e4a, run on
Atlas 2026-09-09). Single author. Not registered, not submitted.

## Title

The Indifference Threshold of a Language-Model Judge Tracks Its Symbol Budget

## TL;DR

A preregistered test on a language-model judge finds its accuracy at a gap equal to the gap
over the symbol grid step on either side of it, the law of an exact evaluator behind a
rounding channel, with 4-bit weights lowering reliability above resolution and not the
resolution, as Geometric Evaluation Theory predicts.

## Abstract

An evaluator with finite resolution does not order every pair of options. Two options whose
consequences differ by less than the evaluator can resolve are indifferent, and the induced
preference is a semiorder rather than a weak order. Geometric Evaluation Theory derives that
structure from an evaluation object made of a consequence map, a metric with an ideal point,
and a resolution budget, and proves that the threshold of the semiorder is set by the budget
rather than fitted. We test that prediction on an evaluator the theory did not build. A
language-model judge, Qwen2.5-7B-Instruct, is asked to report how far a number lies from a
target, and its preference between two options is the order of its reports. Three budgets
are set independently and registered before the run. When the numbers the judge is shown, or
the symbols it may emit, are placed on a grid, its accuracy at a gap equals the gap divided
by the grid step, capped at one, in every cell over four orders of magnitude of step. The
step fitted from the judge's accuracy curve matches the step that was set to within eight
percent in every graded cell, with a bootstrap interval that contains it. Quantizing the
judge's weights to 8 bits changes nothing, and quantizing to 4 bits leaves the fitted step
unchanged while adding a lapse of three percent above resolution. Resolution and
reliability are separate properties of a judge, the first set by the symbols on either side
of it and the second by its weights. The registration, its hash, and the graded record are
public.

## Keywords

LLM-as-judge, evaluation, semiorder, resolution budget, preregistration, quantization

## Revision 2026-09-18 after an external review

Title changed from "Is" to "Tracks". The 0.87 constant is the registered estimator's
log-interpolation on this ladder (h times 2^-0.2) and is no longer presented as a property
of the judge; the reported quantity is the grid step fitted from the accuracy curve with a
bootstrap interval (`paper/iclr2027/build/channel_fit.json`). The 4-bit result is stated as
reliability lowered, resolution unchanged.

## What the abstract does not say, for the full paper

- One model, one numeric task with a known consequence map. The registration itself
  records that at full weights the rendering and report ladders are nearly a tautology for a
  competent model, and that the weight ladder is where the prediction could fail. It did not.
- The companion gates the paper would carry as support are G2 (hull law on ANES 1972,
  PASS), G5 (metric and ideal recovered from choices, 12 of 12 synthetic cells, PASS), and
  G4 and G4b (incompatibility regret, INDETERMINATE), each at its recorded size.
- The campaign names the Journal of Mathematical Psychology and Theory and Decision as
  venues. Submitting to ICLR is a retargeting decision and G8 still lists its own conditions.
- ICLR format is nine pages. The foundational paper is sixteen pages in article format and
  would be compressed around the G3 result, with proofs in the appendix.
