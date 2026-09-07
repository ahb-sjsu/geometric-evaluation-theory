# Geometric Evaluation Theory (GET)

**Status (2026-09-07):** foundational paper at draft 0.2, every statement labeled proved, defined, posited, or open. No gate of the campaign has run. Nothing here is a measured claim.

An evaluator-relative theory of preference, value, and choice. An evaluator maps actions and states into a consequence space, measures consequences with a metric of its own from an ideal point of its own, and does so at a finite resolution. The distinctions it can make are derived first, and preference and choice are derived from those.

```
evaluator + metric + budget  ->  effective distinctions  ->  preference and choice
```

The primitive is the evaluation object

```
E = (X, A, C, G, B, K)
```

with states `X` (and the evaluator's belief on them), actions `A`, the evaluator `C : A x X -> Y` into a consequence space, the metric of evaluation `G` (a metric on `Y` together with an ideal point `t`), the resolution budget `B` (a rank cap, a length, or a rate), and the admissible set `K`, which may depend on the menu.

The foundational commitment is the split between what the world supplies, `(X, A, C)`, and what the evaluator owns, `(G, B, K)`. Without it every ordering is trivially an evaluation object. With it, representation and identification are theorems.

## What is proved in the paper

- Unbudgeted distinctions are an equivalence; a rank budget coarsens it; a length budget gives a tolerance that is transitive only under a stated condition.
- Preference is a weak order with utility equal to minus the distance to the ideal at zero threshold, and a Luce semiorder whose threshold is the budget otherwise. Satisficing is the length budget.
- For a fixed world, representability is a semidefinite feasibility problem; every representable preference obeys the hull law (no action is strictly worse than every action whose consequences surround it); affinely independent consequences represent every order; consequences on a line represent exactly the single-peaked orders.
- Uniqueness: from the order on an open set of consequences, the metric is identified up to a positive scale and the ideal up to the metric's null directions.
- Expected utility, mean-variance, additive multi-attribute value and its ideal-point ancestors (Coombs, spatial voting), the TCSS decision cost, satisficing, Dawid-Lauritzen decision geometry, and Nash equilibrium are special cases, each with its conditions.
- Four things a scalar utility does not provide: rank-budget preference reversal; shared grammar without shared standard (same standard iff ordinally equivalent distances); incompatibility of coupled evaluator geometries (a neutral shared representation exists iff a common leading eigenspace, otherwise the least regret is at the leading eigenspace of the influence-weighted sum); menu-dependent admissibility violates the weak axiom of revealed preference.

Open: a closed-form combinatorial characterization of representability. Not in the theory as written: loss aversion (needs an asymmetric metric), lexicographic priority as a metric.

## What it descends from

Observation Theory (`ahb-sjsu/geometric-observation`, encyclopedia at https://erisml.org/encyclopedia). An evaluator is an observer whose output is scored from an ideal point; the pullback theorem, the transfer regret, the blind probe, and the budget cliff transfer unchanged. The descriptive branch is the TCSS paper (`ahb-sjsu/erisml-lib`, `docs/papers/foundations/submission/ieee-tcss`), reproduced by `eris-econ`. The normative branch is the ethics stack in `erisml-lib`. The multi-agent branch is the behavioral game of the observer-representation draft.

## Layout

| Path | What |
|---|---|
| `paper/geometric-evaluation-theory.tex` | the foundational paper, draft 0.2 |
| `CAMPAIGN.md` | the gates that take the theory from stated to measured, with bars and what falsifies each |
| `PRIOR-ART.md` | the neighbors the theory sits beside and what it adds to each |
| `claims/LEDGER.md` | the claim ledger, one row per headline claim with its class |
| `PROTOCOL.md` | the registration discipline every gate follows |
| `lean/` | machine checks (gate G1, not started) |
| `experiments/` | one directory per gate, created when its registration is sealed |

## Build

```
cd paper && pdflatex geometric-evaluation-theory.tex && pdflatex geometric-evaluation-theory.tex
```

## Naming

GET, always spelled out at first use. GDT is a different object (Geometric Decision Theory, in `ahb-sjsu/geometric-economics`) and is never used for this theory. "The geometry of decision theory" is Dawid and Lauritzen (2005), a special case here.

## License

MIT.
