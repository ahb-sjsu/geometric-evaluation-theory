# Prior art for G7a, checked before the registration was drafted

One web pass, 2026-09-19. Recon grade: titles, venues and headline findings were read from
publisher pages and abstracts, and nothing here has had a quote-verification sweep. A paper that
cites any of this owes that sweep first. Written before the design was fixed, because three of
these findings changed it.

## What is already known

**The indifference threshold as a fitted parameter of a chess player.** Regan and Haworth,
"Intrinsic Chess Ratings", AAAI 2011. They model move choice as a function of the engine's
evaluation differences between the best move and the alternatives, with two skill parameters. One
is a *sensitivity* `s`, described as the player's ability to discriminate among moderately inferior
moves, and the other a *consistency* `c`. Both are fitted by regression against Elo. The
sensitivity is a discrimination threshold in everything but name, so **the idea that a chess player
has a measurable indifference threshold in evaluation space is theirs and not this gate's.** Their
games are tournament games at standard time controls, and the search found no fit across time
budgets.

**Blunders against time, skill and difficulty.** Anderson, Kleinberg and Mullainathan, "Assessing
Human Error Against a Benchmark of Perfection", KDD 2016 and ACM TKDD 11(4), 2017. Tablebase
positions give exact ground truth. Their finding is that the inherent difficulty of the position
predicts a blunder far better than skill or time remaining does. **Consequence for this gate: any
comparison across budgets that does not hold difficulty fixed is measuring the mix of positions.**
The design holds it fixed by conditioning on the engine's gap between the best and second-best
move, so that the same question is asked at every budget.

**Time spent is not a budget.** Sunde, Zegners and Strittmatter, "Speed and quality of complex
strategic decisions", PNAS, May 2026, with an earlier version as arXiv 2201.10808. About 3,600
over-the-board games by players rated 2500 and above, across classical, rapid and blitz. Faster
moves are associated with *better* moves, after accounting for complexity and time pressure, since
a long think marks a position the player finds hard. **Consequence: time spent on a move is
endogenous to the position and cannot serve as the budget.** The budget in this gate is the time
control, which is fixed before the first move and cannot depend on any position in the game.

**That faster time controls produce worse chess is common knowledge** and has been in the
literature at least since comparisons of rapid and classical play by grandmasters. The ordinal
claim, that a smaller time budget gives a larger threshold, would surprise nobody. A gate that
registered only that would be registering the known.

A lead, not a source. A ResearchGate preprint on decision-space entropy in 9,114 games reports the
exponent of average centipawn loss against Elo varying with time control. Unreviewed, not read
beyond its abstract, and about error against skill rather than threshold against budget.

## What is left to measure

1. The threshold as a **discrimination threshold in gap space**, the gap at which a player picks
   the better of the engine's top two moves at a registered rate, which is the same object the
   paper measures for a language-model judge.
2. A **functional form committed before measurement**. If deliberation time buys independent
   reads of the position, then the paper's own result for the mean of `n` sampled scores carries
   over and the threshold falls as the inverse square root of the budget. That bridge is posited
   and the registration labels it so. The exponent is fixed by the bridge and is not fitted.
3. **Prediction before measurement across time controls**: calibrate one constant on one time
   control, commit the thresholds the law gives at the others with their hash, and only then open
   them. That is the G3c protocol applied to people.
4. A **within-player** version, in which the evaluator is fixed and only the budget moves.

None of the four is in the work above as far as this pass could see. That is a statement about one
web pass and not about the literature.
