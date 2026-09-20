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
- [ ] Supplementary zip: the four registrations with hashes, configs, seeds, logs, graded records, grading scripts, with repository and author names removed
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

A `ef` in the AI use statement had lost its backslash when this file was first assembled by
script and printed as literal text. It is repaired. Both checks from the paper skill now run
against the built source, the binary one for control bytes and the grep for commands missing a
backslash, including the partial forms a lost backslash leaves.
