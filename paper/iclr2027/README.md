# ICLR 2027 submission: The Indifference Threshold of a Language-Model Judge Tracks Its Symbol Budget

A nine-page compression of `../geometric-evaluation-theory.tex` around gate G3. The
original paper is untouched. This folder is the only place the ICLR version lives.

## Deadlines

| Item | When |
|---|---|
| Abstract registration | 2026-09-18, 11:59 PM AoE |
| Full paper | 2026-09-25, 11:59 PM AoE |
| Reviews released | 2026-11-05 |
| Author discussion | 2026-11-05 to 2026-11-18 |

Main text 9 pages at submission (10 at camera-ready). References, appendices, the
AI use statement, the ethics statement and the reproducibility statement do not count.
Double blind. The AI use statement is required.

## Files

| File | What |
|---|---|
| `iclr2027.tex` | the paper, anonymous, `\iclrfinalcopy` commented out |
| `refs.bib` | references, each checked against the publisher's record; `lee2025quant` pages carry a verify note |
| `iclr2027_conference.{sty,bst}`, `fancyhdr.sty`, `natbib.sty`, `math_commands.tex` | the official 2027 style files, unpacked from `iclr-2027-style-files.zip` on 2026-09-18 |
| `build/make_figures.py` | Figure 1 (registered thresholds against budget) from `experiments/G3/grade.json` |
| `build/channel_fit.py`, `build/channel_fit.json` | the grid-channel fit per cell (step, lapse, bootstrap intervals) and Figure 2 with the law overlaid, from `experiments/G3/results.json` |
| `figures/thresholds.*`, `figures/accuracy.*` | Figure 1 and Figure 2, PDF for LaTeX and 300 dpi PNG |
| `iclr2027-abstract.md` (parent folder) | the abstract as registered, with its caveats |

## Build

```
python build/make_figures.py
pdflatex iclr2027 && bibtex iclr2027 && pdflatex iclr2027 && pdflatex iclr2027
```

Every number in the text traces to `experiments/G3/grade.json` (thresholds, ratios, P1
to P3), `experiments/G3/results.json` (per-cell accuracy, Appendix C), `experiments/G2/results.json`
(hull law: 489 of 557 testable, 246 violated, 0.503 against a shuffle mean of 0.664,
200 shuffles) and `experiments/G5/grade.json` (12 of 12 cells).

## Revision record, 2026-09-18, external review

An external reader's notes were triaged against the sealed code and the Lean files.

| Point | Finding | Action |
|---|---|---|
| Theorem 3(c) false as stated | Correct. `lean/GET/UniquenessGeneral.lean` checks the whole-space case and says so; the open-set statement fails in rank 1 without coverage (Y=R, U=(1,2), x^2 vs (x+10)^2). | Restated: metric up to scale from any open set; ideal needs rank >= 2 or U meeting the minimizers. Elementary proof. Defect recorded in `CAMPAIGN.md` G1 row. Original paper left as the record. |
| Theorem 3(a) range condition not linear in (G, b) | Correct. | Restated with the PSD lift W = [[G, b/2],[b^T/2, gamma]]; PSD forces b in range(G). |
| The grid is not the theory's deterministic tolerance | Correct. | New Proposition 1 (grid channel): accuracy = min(1, gap/h) under uniform phase, alpha-threshold = alpha h. Fits every ladder point in every cell (max deviation 0.055 on 200 pairs). |
| 0.87 is an estimator artifact | Correct: log-gap interpolation between h/2 (acc 0.5) and h (acc 1) gives h * 2^-0.2 = 0.87 h. | Said so in Section 4; the reported quantity is now the fitted step. |
| No uncertainty on thresholds | Correct. | Parametric binomial bootstrap per cell (4000 draws). Paired bootstrap impossible: the record holds per-gap aggregates only. Said so. |
| P3 is a single gap decided by an ungraded cell | Correct. | Stated plainly; next gate adds gaps 30, 50, 100 and defines P3 on the largest graded threshold. |
| 4-bit as reliability vs resolution | Adopted. | Two-parameter fit: step 0.99 of set, lapse 0.031 [0.024, 0.038]. Abstract, results and scope rewritten around it. |
| Tokenization audit | Done on Atlas against the recorded revision: one token per digit and per decimal point. | Appendix B with token ids, parse rule, probe generation samples, and the record's limits (no per-pair generations, no early-stop counts). |
| Second model family | Not run. | Registered as the next gate in Scope; needs a registration, probe, pilot and about four GPU hours per model. |
| Move two supporting gates to the appendix | Adopted. | G5 stays in the main text; hull law and GQA regret in Appendix C. |
| Title too strong | Adopted. | "Tracks" for "Is". |

## OpenReview form fields (paste as-is)

These are form fields, not PDF content: the ICLR style file has no `\keywords` and ICLR does not
put a TL;DR in the paper, so changing them needs no rebuild.

**TL;DR** (249 characters, under the 250 limit)

> How finely a language-model judge can tell answers apart is predicted, and committed, before the
> test data exists, from the channel it writes rather than the scale it is offered, on two stimulus families, and a second
> budget reverses its preference.

**Keywords**

> LLM-as-a-judge, evaluation methodology, preregistration, discrimination threshold, semiorder,
> calibrated channel, stimulus family, reasoning budget, held-out prediction

Chosen for reviewer matching: the first four pull evaluation and benchmarking reviewers,
`semiorder` pulls someone who will check the theory, `reasoning budget` covers the second gate.
"quantization" was left out deliberately; the 4-bit result is real but that keyword attracts
efficiency reviewers, who are the wrong readers for this paper.

**Primary area** is the owner's call. Two fit: *foundation or frontier models, including LLMs*
matches the subject, *datasets and benchmarks* matches the contribution, which is an evaluation
protocol rather than a model. The second is the better match on contribution.

## Presentation pass (run before every upload)

- [x] Abstract narrative, no math (0 `$` in the abstract block)
- [x] Banned-word grep: only hits are the registered variable "gap"
- [x] No colored text, no em-dashes, no semicolons or colons in prose
- [x] Eaten-backslash checks (control characters, bare commands) clean
- [x] No undefined references
- [x] Every caption states what to notice
- [x] AI use statement, ethics statement, reproducibility statement present
- [x] Anonymous: no author name, no repository name, own work cited in third person
- [ ] Read-aloud pass for articles and grammar
- [x] Supplementary zip: `python build/make_supplementary.py`; every gate the paper reports with its sealed registration and hashes, configs, seeds, graded records including the score files, the Lean development, and `reproduce.ipynb`; names and paths redacted, `leaks after redaction: 0`
- [ ] Owner registers the abstract on OpenReview by the 18th and uploads the PDF and supplement by the 25th

## What the paper does not claim

One model, one numeric task, a known consequence map. The full-weight ladders are
nearly a tautology for a competent model and the registration says so; the weight-ladder
null and the well-separated ordering are the informative results. G4 and G4b are
reported as indeterminate. No claim about human evaluators.

## Pivot draft, 2026-09-19: `iclr2027-v2.tex`

The pivot the owner asked for: the main text is gate G3c (a judge's threshold predicted from
calibration before the test seed is drawn, on worksheet grading) and gate G3d (the deliberation
budget flip, with its crossover predicted), and the theory and the numeric-task gate G3 move to
Appendices A and B. `iclr2027.tex` is left as the G3 version. Every number that belongs to a
sealed result is a bold `[pending]` placeholder until the graded record exists; no pilot number is
written as a result. Filled with the sealed numbers on 2026-09-20: seven pages of main text plus references and
appendices, no undefined reference, no placeholder left. Figures come from the graded records
through `build/make_v2_figures.py`: Figure 1 the prediction against measurement, Figure 2 the
three regimes, Figure 3 the crossover. Tables 1 and 2 are the sealed thresholds and the flip
cells. Open before it can replace `iclr2027.tex`: the owner's read, one citation for reasoning
and judge bias, and the supplementary zip.

A `
ef` in the AI use statement had lost its backslash when this file was first assembled by
script and printed as literal text. It is repaired. Both checks from the paper skill now run
against the built source, the binary one for control bytes and the grep for commands missing a
backslash, including the partial forms a lost backslash leaves.

## Supplementary package

    python build/make_supplementary.py

Writes `supplementary/` and `iclr2027-supplementary.zip` (about 17 MB, 599 files). Both are
gitignored: the builder is the artifact that is kept, so the package can always be rebuilt from
the current records rather than drifting as a committed copy.

What goes in: every gate the paper reports, with its registration, configuration, seeds,
self-test and probe records, graded record and scripts; the Lean development with the axiom
audit; the protocol and the ledger; a commit list showing prediction committed before
measurement; and the scripts that build every figure and table.

Two hashes appear per registration and they are not meant to agree. The sealed blob is the git
blob hash recorded in the ledger before the run seed was drawn. The other is the sha256 of the
redacted file as shipped, which differs wherever a name or path was replaced.

The builder redacts author names, institutions, machine names, the cluster namespace, the
repository name and absolute paths, then re-scans everything it wrote, including inside gzipped
record files, and reports a leak count that must be zero. It excludes itself from the package,
since it names every string it redacts. LaTeX run logs are dropped rather than redacted.

The ANES 1972 corpus is not redistributed. Its files are listed with sizes and checksums so a
reader can confirm they obtained the same bytes.

Check before uploading: the last lines of the run must read `leaks after redaction: 0`.

## Two builds, one source (added 2026-09-21, revised)

The submission is the **cornerstone** build, which is what `iclr2027-v2.tex` produces by default:
23 pages, with the numbered sections ending on page 9 and the AI-use and reproducibility
statements running onto page 10, which ICLR excludes from the limit. It carries the
identification gate on synthetic evaluators and the two further sealed gates. A reviewer who read both scored this one an accept and the narrower
build a weak accept, so the wider paper is the one that goes in.

`iclr2027-v2-beachhead.tex` is a four-line wrapper that defines `\BEACHHEAD` and inputs the same
file, switching those sections off. 22 pages. Kept because it is free to keep and because the
narrower cut is the right shape for a shorter venue.

One source, so the two cannot drift. Every cross-reference into a cornerstone-only section is
wrapped in `\ifcornerstone` and reads "reported in the supplementary material" in the beachhead
build, so nothing looks hidden. Both builds must show zero undefined references.

    pdflatex iclr2027-v2 ; bibtex iclr2027-v2 ; pdflatex iclr2027-v2 ; pdflatex iclr2027-v2
    pdflatex iclr2027-v2-beachhead ; bibtex iclr2027-v2-beachhead ; pdflatex ... (twice)

Appendix G was condensed on the same review: the survey gate and the play-calling gate keep a
paragraph each with their numbers, and the attention-head gate is summarized to four sentences
with its loss measurements and perturbation run pushed to the supplement.

Note for editors: `\newif` must stay outside the `\ifdefined\BEACHHEAD` test. TeX counts `\if`
tokens while skipping a false branch, so a `\newif\ifcornerstone` inside one breaks the nesting
and silently swallows the rest of the document. A misplaced closing `\fi` does the same thing
quietly; check the page count and the undefined-reference count after any edit to those blocks.


## Revision record, 2026-09-22, second external review

An external reader's notes on the built `iclr2027-v2.pdf` were triaged against the sealed records
and the grading code. A second set of notes, machine-generated, turned out to be about
`iclr2027.pdf`, the G3 version, and every substantive point in it was already repaired in v2
(pseudo-metric in Definition 1, the workload measure for the rank cap, the root-mean-square
wording, the margin in Theorem 3(a), no `least-squares slope`, no self-citation). Nothing was
changed for it.

| Point | Finding | Action |
|---|---|---|
| Appendix D is stale, 15 cells and no Qwen3 | Correct. `experiments/G3c/budget_ladder.json` already held all 18 graded cells. | Table 4 regenerated with the three Qwen3 rows and the medians, prose corrected to 22 / 39 / 22 percent over 17 live cells of 18, and the rate beating the capacity in 12 of 18. |
| J2 compares the calibrated channel, not the codebook | Correct, and checkable in `judge_grade.py`, where `sse_effective` reads `readouts.argmax.acc`, the full conditional prediction. The 0.001 reported in Section 4 is the channel column of Table 4; the codebook-only predictor on that cell is 0.282. | Renamed through the abstract, introduction, Section 4, Scope and the practitioner's summary. Section 4 now says what each side of the registered comparison is and points to the ladder for which part predicts. The registration and its claim names are untouched. |
| The abstract says the whole pattern replicates | Correct, the read-out ordering failed on Gemma 4 31B. | Abstract now states that the prediction and the nominal-scale comparison replicate and the ordering does not, and the read-out sentence is qualified to five of the six graded judges. |
| Six independent judges | Correct, six configurations of five models, the 7B appearing twice. | Reworded in the introduction, Section 4 and Scope. |
| Quantization moves reliability and not resolution | Overstated for this task. The worksheet gate bounds the change at a factor of 1.75 with ratios up to 1.60, and the lapse result belongs to the numeric gate. | Heading and paragraph rewritten to claim the bound and to attribute the lapse to the numeric gate. |
| Practitioner rule 2, one forward pass | Correct. Only the single-token scales are free; the 0 to 100 scale needs the digit tree. | Rule 2 now separates the two cases. |
| Practitioner rule 3, unconditional | Correct. One judge, one cue, one forced-answer protocol. | Rule 3 restated as what a cap can do, with the scope of the evidence named. |
| The commit DAG proves precommitment | Fair. It proves artifact ancestry. | Section 4 now says the order is checkable in the artifact and that it is the repository's own history, not a third-party timestamp. |
| A quantizer is not globally a fixed-threshold semiorder | Right in principle. Proposition 1(a) was already anchored to the position of the lower point and 1(b) already made the tolerance uniform, so the appendix was already correct. The exposed bridge was one sentence in Section 2. | Section 2 now says the tolerance is the distance to the next boundary, that a grid gives a semiorder at a known alignment rather than one shared threshold, and that a threshold read at accuracy 0.75 is a quantile of that tolerance. |
| Related work too thin | Correct. | Four works added, each verified against the arXiv record on 2026-09-22 and each distinguished. Non-transitivity of strict preference across models against intransitive indifference within one judge; calibration used to debias a reported score against calibration used to predict a held-out curve; item response theory fitting discrimination and thresholds to the responses they explain; the simplex view of judge confusion channels and its finding that fewer levels can rank better. |
| Stale supplementary navigation | Correct. | `MANIFEST.md` section and table numbers corrected in `build/make_supplementary.py`, `RESULTS-G3E-DRAFT.md` filled in from the graded record (verdict, Qwen3 row, the two unshown-mass numbers, the floor table), and the package rebuilt with `leaks after redaction: 0`. |

Two things found while doing this and not raised by either reader. The main text carried 27
colons and semicolons against the standing prose rule, including one in the abstract, and the
presentation checklist above had them marked clean; all 27 are removed. And the count of read-outs
at the ladder floor was written in an order that did not match the order the three judges are
introduced in; it now names each judge.

Both builds are clean after the pass. The cornerstone build is 24 pages with the numbered sections
ending on page 9 and the AI-use statement starting on page 10, and the beachhead build is 23. Zero
undefined references in both.

Still open: the owner's read of the changed passages, and the upload.


## Revision record, 2026-09-22, second pass on the same reader's notes

The reader's remaining blocker was that a grid is still not the claimed semiorder, and it was
right. The earlier repair said a grid gives "a semiorder at a known alignment", which is a
category error, since a semiorder is a relation on a set and an alignment fixes one comparison.

The correct statement, now in Section 2, in Proposition 1(a), in the discussion after it, and in
the Lean file's own docstrings: a grid coarsens the distance, so on a set of options it induces
the weak order of Theorem 2(a) on the quantized distance, whose indifference is transitive, and
against the true distance no single threshold represents it. Proposition 1(a) is a rule for one
comparison, that two options are distinguished when their difference reaches the distance from
the lower of them to the next boundary. A remark now carries the counterexample, unit bins with
0.1, 0.9 and 1.1, where one tolerance would have to be at least 0.8 and below 0.2 at once. The
ramp, the fitted step and every number are unaffected, since the quantity measured was always the
distribution of the tolerance.

Three other corrections.

The information rate is now called a proxy rather than the theory's rate budget. A rate has no
meaning without a source and a cost, so Definition 1 now makes a rate budget the triple
`(R, workload, distortion)`, matching what the rank cap already carried, and Appendix D says its
rung 2b has neither and is a summary of the measured channel rather than a code chosen to
minimise a distortion.

Appendix D had two orderings of the budget-only rungs reading as one. By median squared error the
positions win at 0.220 against the rate at 0.240. By median share of the distance closed the rate
wins at 39 percent against 22. Both are now stated, the disagreement is explained as a median of
ratios against a ratio of medians, and the script's rule that a cell counts only when capacity and
channel differ by more than 0.05 is disclosed. The claim that the unexplained remainder splits
into noise and placement is withdrawn, since those predictors are not nested.

The comparison with Lee et al. said they fit parameters to the responses those parameters explain.
They do not, they apply a calibration out of sample. The distinction is the target, an aggregate
score with an error bound against a discrimination curve committed before the test seed, and the
related-work paragraph now says that and no longer says everything twice.

Polish: `hidelinks` on hyperref, the API described as exposing the twenty most probable tokens at
each position, and the long-sheet probe now reports its 30 pairs per gap and the resulting
standard error of about 0.08.

Main text was 25 pages of PDF with the numbered sections running two lines onto page 10 after
these additions. Recovered by cutting real duplication rather than content: the non-monotone
budget axis stated three times, the bars simulation restated in Scope, the numeric gate's caveat
restated from Appendix C, an argumentative pair of sentences in the introduction, and the
related-work paragraph introducing Lee and Choi and then describing them again. Scope now ends on
page 9 and the AI-use statement starts on page 10.

One defect the style scan caught that the build did not. A `\ref` written through a shell heredoc
lost its backslash and its `r`, leaving `Section~` and a line beginning `ef{sec:flip}`, which
typesets as literal text and raises no undefined-reference warning because there is no reference
left to be undefined. This is the same failure the 2026-09-19 note records. Repaired, and the
scan for partial command forms is clean.

Both builds clean, zero undefined references, package rebuilt at `leaks after redaction: 0`.
