# ICLR 2027 submission: The Indifference Threshold of a Language-Model Judge Is Its Symbol Budget

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
| `build/make_figures.py` | figures from `experiments/G3/results.json` and `grade.json` only |
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
