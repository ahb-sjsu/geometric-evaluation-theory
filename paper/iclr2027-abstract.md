# ICLR 2027 abstract registration, drafted 2026-09-18 from gate G3

Source of every number: `experiments/G3/grade.json` (gate PASS, sealed registration
`experiments/G3/PREREG-G3.md`, blob 53cb1a0022ae7334b33f683f1acae6f620969e4a, run on
Atlas 2026-09-09). Single author. Not registered, not submitted.

## Title

The Indifference Threshold of a Language-Model Judge Is Its Symbol Budget

## TL;DR

A preregistered test on a language-model judge finds its just-noticeable difference equal
to the resolution of the symbols it is shown and allowed to emit, unchanged within tolerance by 4-bit weight
quantization, as Geometric Evaluation Theory predicts.

## Abstract

An evaluator with finite resolution does not order every pair of options. Two options
whose consequences differ by less than the evaluator can resolve are indifferent, and the
induced preference is a semiorder rather than a weak order. Geometric Evaluation Theory
derives that structure from an evaluation object made of a consequence map, a metric with an
ideal point, and a resolution budget, and proves that the threshold of the semiorder equals
the budget rather than being a free parameter. We test that prediction on an evaluator the
theory did not build. A language-model judge, Qwen2.5-7B-Instruct, is asked to report how
far a number lies from a target, and its preference between two options is the order of its
reports. Three budgets are set independently and registered before the run. Coarsening the
numbers the judge is shown from three decimals to none raises its threshold from 0.0009 to
0.87, at 0.86 to 0.87 of the rendering step at every level. Limiting the judge's report to two through
six generated tokens sets the threshold at 0.87 of the resolution those symbols can express,
from 0.87 down to 0.0009. Quantizing the judge's weights from bfloat16 to 8 bits and to 4 bits
leaves every threshold unchanged within the registered tolerance. Pairs separated by more than twice the largest measured
threshold are ordered alike in every cell, with worst-case accuracy 0.985. The resolution of
the judge is the budget of symbols it is shown and allowed to emit, and not the precision of
its weights. The registration, its hash, and the graded record are public.

## Keywords

LLM-as-judge, evaluation, semiorder, resolution budget, preregistration, quantization

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
