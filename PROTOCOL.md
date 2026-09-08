# Protocol

The registration discipline of `ahb-sjsu/observation-theory-campaigns` and `ahb-sjsu/geometric-observation` applies unchanged. In brief.

1. Seal before run. A gate's registration (hypothesis, world, statistic, bars, exclusions, null) is committed and its hash recorded before any data is opened. The registration file is `experiments/<gate>/PREREG.md` and its hash is written into `CAMPAIGN.md` beside the gate.
2. Event presence first. Every registration cites a committed probe showing that the events the gate will count are present in every cell and member. A gate that could pass on empty cells is not sealed.
3. Misses at full prominence. A miss is recorded in `claims/LEDGER.md`, in `CAMPAIGN.md`, and in the paper at the same size as a pass. A rerun after a miss is a new registration that names the miss.
4. Numbers trace to artifacts. Every number in the paper names its file, line range, and commit. A number without a row is removed.
5. Compute where it belongs. Nothing runs on the laptop. Lean builds and experiments run on Atlas or on NRP through the existing burst flow, under the standing cluster rules.
6. Owner submits. The repository builds submission-ready files. The owner uploads, signs, and publishes.
7. Prose. No em dashes, colons, or semicolons in sentences. No sentence that argues for the work's merit. Every caveat sits beside the result it bounds.

## Discovery records (added 2026-09-08)

Two ledger classes beside the evidence classes, defined for the program in
`observation-theory-campaigns/encyclopedia/SCHEMA.md` and `standards/DPE-RECORDS.md` there:
`[witness]`, a row whose content is a reduced counterexample, the smallest admissible
transformation or the named cause that breaks a claim, and the component that absorbed it;
and `[revised]`, a row recording a commitment changed in response to a named witness. A
verdict of FAIL or INDETERMINATE is not complete until its witness row is written or the
record says what stopped the reduction, and a registration that supersedes another because
of a witness writes its `[revised]` row before it is sealed. The campaign's admissible
transformations are declared in the program's transformation registry,
`observation-theory-campaigns/claims/transformations/GET.toml`, whose tests the
encyclopedia entry prints as the theory's invariance envelope. The first rows of each class
are GET-9w and GET-9r.

