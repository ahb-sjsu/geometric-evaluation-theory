"""Build the anonymised supplementary package for the ICLR submission.

Collects, for every gate the paper reports: the sealed registration and its hash, the
configuration, the seeds, the graded records, the self-tests and probes, and the scripts.
Adds the Lean development, the axiom audit, and the figure and table scripts.
Redacts every string that would identify the authors, their institution, or their machines.
Third-party corpora are not redistributed; their checksums are recorded instead.
"""
import hashlib
import io
import os
import re
import shutil
import zipfile

# Repository root, three levels up from paper/iclr2027/build/.
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")).replace("\\", "/")
OUT = os.path.join(SRC, "paper/iclr2027/supplementary")
ZIP = os.path.join(SRC, "paper/iclr2027/iclr2027-supplementary.zip")

GATES = [
    ("G3c", "Main gate 1: a judge's symbol budget predicts its resolution (Section 3, Table 1, Figure 1)"),
    ("G3d", "Main gate 2: where a deliberation budget reverses a judge's preference (Section 4, Figures 2 and 3, Table 3)"),
    ("G3e", "The same resolution law on judges of another family, through a served API (Section 5)"),
    ("G5", "Identification of the metric and the ideal from choices (Section 6)"),
    ("G3", "The numeric gate: the threshold tracks the resolution budget (Appendix on the numeric task)"),
    ("G3b", "A drafted extension of the grid-channel law across families and tokenizers. Never sealed, never run. No number in the paper rests on it"),
    ("G2", "Hull law on a public survey (Appendix on further gates)"),
    ("G9", "Hull law and the budget prediction on professional football play calls (Appendix on further gates)"),
    ("G9b", "The refutation projection and the violation rate against reading precision"),
    ("G4b", "Shared-representation bound on attention heads, indeterminate (Appendix on further gates)"),
    ("G7a", "The threshold against a time budget in chess, indeterminate, and the registration that refuted the inverse-square-root bridge"),
]

# Ordered: longer keys first so a substring never eats its container.
REDACTIONS = [
    ("/archive/ahb-sjsu/geometric-evaluation-theory", "/ANON/repo"),
    ("/archive/ahb-sjsu", "/ANON"),
    ("ahb-sjsu", "anon"),
    ("geometric-evaluation-theory", "repo"),
    ("ssu-atlas-ai", "anon-namespace"),
    ("/home/claude/.g7a_player_key", "$HOME/.player_key"),
    ("g7a_player_key", "player_key"),
    ("/home/ahbond", "$HOME"),
    ("/home/claude", "$HOME"),
    ("Atlas", "the workstation"),
    ("atlas", "workstation"),
    ("Erebus", "the resident agent"),
    ("erebus", "the resident agent"),
    ("SJSU", "the institution"),
    ("sjsu", "the institution"),
    ("San Jose State", "the institution"),
    ("SSU", "the second institution"),
    ("C:/Users/abptl", "$HOME"),
    ("C:\\Users\\abptl", "$HOME"),
    ("abptl", "anon"),
]

# LaTeX run logs carry local absolute paths and no information a reader needs.
# LaTeX run logs carry local paths. This builder names every string it redacts, so
# shipping it would undo the redaction; it stays in the repository instead.
SKIP_FILES = {"pass1.log", "pass2.log", "pass3.log", "pass4.log", "pass5.log", "bibtex.log",
              "make_supplementary.py"}

TEXT_EXT = {".md", ".py", ".json", ".sh", ".txt", ".log", ".yaml", ".yml", ".csv", ".lean", ".toml", ".sha256", ".jsonl", ".tex", ".cfg", ".ini"}
SKIP_DIRS = {"__pycache__", ".git", ".lake", ".mypy_cache"}
# Third-party corpora: checksummed, not shipped.
NO_REDISTRIBUTE = {
    "G2/data": "ANES 1972 Time Series Study. Available from the ANES after free registration.",
}
BINARY_EXT = {".dta", ".zip", ".pkl", ".npz", ".parquet", ".pdf", ".png"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def redact(text):
    n = 0
    for old, new in REDACTIONS:
        c = text.count(old)
        if c:
            text = text.replace(old, new)
            n += c
    return text, n


def copy_tree(src, dst, counters, withheld):
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, SRC).replace("\\", "/")
        if any(rel_dir == "experiments/" + k or rel_dir.startswith("experiments/" + k + "/")
               for k in NO_REDISTRIBUTE):
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                withheld.append((rel_dir + "/" + fn, os.path.getsize(p), sha256(p)))
            dirnames[:] = []
            continue
        for fn in sorted(filenames):
            if fn in SKIP_FILES:
                counters["skipped_log"] += 1
                continue
            src_p = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            # Relative to the repository root, never to the subtree being walked, or
            # every gate would land at the package root and overwrite the last one.
            out_p = os.path.join(dst, os.path.relpath(src_p, SRC))
            os.makedirs(os.path.dirname(out_p), exist_ok=True)
            if ext in TEXT_EXT:
                try:
                    text = io.open(src_p, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    shutil.copy2(src_p, out_p)
                    counters["binary"] += 1
                    continue
                text, n = redact(text)
                io.open(out_p, "w", encoding="utf-8", newline="\n").write(text)
                counters["text"] += 1
                counters["redactions"] += n
            elif ext in BINARY_EXT:
                counters["skipped_binary"] += 1
            else:
                shutil.copy2(src_p, out_p)
                counters["binary"] += 1


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    counters = {"text": 0, "binary": 0, "skipped_binary": 0, "skipped_log": 0, "redactions": 0}
    withheld = []
    lines = []

    lines.append("# Supplementary material\n")
    lines.append("Every gate the paper reports, with its sealed registration and that registration's\n"
                 "hash, its configuration, its seeds, its self-test and probe records, its graded\n"
                 "record, and the scripts that produced them. The Lean development and the axiom\n"
                 "audit follow, then the scripts that build every figure and table in the paper\n"
                 "from the graded records.\n")
    lines.append("Author names, institutions, machine names, repository names and absolute paths\n"
                 "have been replaced throughout, for double-blind review. The replacements are\n"
                 "listed in `REDACTIONS.md`. Nothing else was altered: the records are the sealed\n"
                 "ones.\n")
    # The protocol and the ledger. Both are redacted like everything else.
    campaign_raw = io.open(os.path.join(SRC, "CAMPAIGN.md"), encoding="utf-8").read()
    for fn in ("PROTOCOL.md", "CAMPAIGN.md"):
        text, n = redact(io.open(os.path.join(SRC, fn), encoding="utf-8").read())
        io.open(os.path.join(OUT, fn), "w", encoding="utf-8", newline="\n").write(text)
        counters["text"] += 1
        counters["redactions"] += n

    lines.append("\n## How a registration is sealed, and what its hash is\n")
    lines.append(
        "`PROTOCOL.md` states the discipline and `CAMPAIGN.md` is the ledger it writes into.\n"
        "A gate is sealed by renaming its draft registration to its final name, committing that\n"
        "rename, and recording the git blob hash of the committed file in the ledger. That blob\n"
        "hash is the seal: it fixes the registration's content before the run seed is drawn.\n")
    lines.append(
        "Two different hashes therefore appear below, and they are not meant to agree.\n"
        "The **sealed blob** is the git blob hash recorded in the ledger at sealing time, over the\n"
        "original file. The **copy in this package** is the sha256 of the redacted file shipped\n"
        "here, which differs from the original wherever a name or a path was replaced. The\n"
        "second lets a reviewer check that this package is internally consistent. The first is\n"
        "what ties the registration to a commit that predates the run, and it becomes checkable\n"
        "against the public repository when the submission is deanonymised.\n")
    lines.append("\n## Gates\n")

    blob_re = re.compile(r"blob\s+([0-9a-f]{40})")
    for gate, caption in GATES:
        gdir = os.path.join(SRC, "experiments", gate)
        if not os.path.isdir(gdir):
            continue
        copy_tree(gdir, OUT, counters, withheld)
        pregs = sorted(f for f in os.listdir(gdir) if f.upper().startswith("PREREG-"))
        lines.append("### %s\n" % gate)
        lines.append("%s\n" % caption)
        for pf in pregs:
            shipped = sha256(os.path.join(OUT, "experiments", gate, pf))
            # The ledger row that names this registration file carries its sealed blob.
            blob = ""
            for row in campaign_raw.splitlines():
                if pf in row:
                    m = blob_re.search(row)
                    if m:
                        blob = m.group(1)
                        break
            lines.append("- `experiments/%s/%s`" % (gate, pf))
            if blob:
                lines.append("  - sealed blob: `%s`" % blob)
            else:
                lines.append("  - not sealed. This is a draft registration that was never sealed, so it"
                             " has no blob in the ledger and no number in the paper rests on it. It is"
                             " included because the paper's account of what was planned and not run is"
                             " part of the record.")
            lines.append("  - copy in this package, sha256: `%s`" % shipped)
        lines.append("")

    # Lean development.
    copy_tree(os.path.join(SRC, "lean"), OUT, counters, withheld)
    lines.append("## Lean development\n")
    lines.append("`lean/` holds ten files and `lean/Axioms.lean`, which prints the axiom dependence of\n"
                 "every theorem in them. All thirty-four report exactly `[propext, Classical.choice,\n"
                 "Quot.sound]`, and no file contains `sorry`. The audit output is in\n"
                 "`lean/AXIOM-AUDIT.txt`.\n")

    # Figure and table scripts.
    copy_tree(os.path.join(SRC, "paper/iclr2027/build"), OUT, counters, withheld)
    lines.append("## Figures and tables\n")
    lines.append("`paper/iclr2027/build/` holds the scripts that read the graded records and emit every\n"
                 "figure and table. `channel_fit.py` produces Table 1 and is the estimator the paper\n"
                 "describes: the lapse first, accuracy corrected by one minus it, then the step as the\n"
                 "reciprocal of the least-squares slope through the origin.\n")

    if withheld:
        lines.append("\n## Data not redistributed\n")
        lines.append("These files are third-party corpora we are not licensed to redistribute. Their\n"
                     "checksums are given so a reader can confirm they obtained the same bytes.\n")
        for k, why in NO_REDISTRIBUTE.items():
            lines.append("\n**%s** -- %s\n" % (k, why))
        for rel, size, digest in withheld:
            lines.append("- `%s`  %d bytes  sha256 `%s`" % (rel, size, digest))
        lines.append("")

    # The commit order. The discipline's central claim is that a prediction was committed
    # before the measurement it predicts, so the order of commits is evidence and belongs here.
    import subprocess
    log = subprocess.run(
        ["git", "-C", SRC, "log", "--date=iso-strict", "--format=%h  %ad  %s",
         "--", "experiments", "lean", "CAMPAIGN.md", "PROTOCOL.md"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    clines = [
        "# Commit order\n",
        "Every commit touching a gate, the Lean development, the protocol or the ledger, newest\n"
        "first, with its short hash, its author date, and its subject. Author names and email\n"
        "addresses are omitted for double-blind review; the dates and the order are untouched.\n",
        "The discipline's claim is an ordering claim: a registration is committed before its run\n"
        "seed is drawn, and a block of predictions is committed with its sha256 before the test\n"
        "block is scored. That ordering is visible here, and is checkable against the public\n"
        "repository once the submission is deanonymised.\n",
        "```",
    ]
    body, nred = redact(log.stdout.strip())
    counters["redactions"] += nred
    clines.append(body)
    clines.append("```")
    io.open(os.path.join(OUT, "COMMITS.md"), "w", encoding="utf-8", newline="\n").write("\n".join(clines))
    counters["text"] += 1
    lines.append("\n## Commit order\n")
    lines.append("`COMMITS.md` lists every commit that touched a gate, the Lean development, the\n"
                 "protocol or the ledger, with its date and subject and without author names. It is\n"
                 "where the ordering of prediction before measurement can be read.\n")

    io.open(os.path.join(OUT, "MANIFEST.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    rlines = [
        "# Redactions\n",
        "Applied to every text file in this package, for double-blind review. The strings\n"
        "themselves are not listed here, since listing them would defeat the purpose. The\n"
        "categories and what replaced them are:\n",
        "| what was found | replaced with |",
        "| --- | --- |",
        "| author names and login names | `anon` |",
        "| institution names and acronyms | `the institution`, `the second institution` |",
        "| the repository name | `repo` |",
        "| the names of the authors' machines | `the workstation`, `the resident agent` |",
        "| the shared-cluster namespace | `anon-namespace` |",
        "| absolute home and archive paths | `$HOME`, `/ANON` |",
        "| the path of a keyed-hash secret, never its value | `$HOME/.player_key` |",
        "\nReplacement ran longest string first, so a shorter string inside a longer one never\n"
        "broke it. %d substitutions were made across %d text files. Six LaTeX run logs were\n"
        "dropped rather than redacted; they record local paths and nothing a reader needs.\n"
        "Nothing else was changed. Numbers, seeds, hashes and verdicts are the sealed ones.\n"
        % (counters["redactions"], counters["text"]),
        "\nThe player-hash key used in the chess gate is not in this package and never was in\n"
        "the repository. The registration says how it is generated and how to regenerate the\n"
        "same player pseudonyms from it.\n",
    ]
    io.open(os.path.join(OUT, "REDACTIONS.md"), "w", encoding="utf-8", newline="\n").write("\n".join(rlines))

    print("text files    %d" % counters["text"])
    print("copied binary %d" % counters["binary"])
    print("skipped binary %d" % counters["skipped_binary"])
    print("skipped logs   %d" % counters["skipped_log"])
    print("substitutions %d" % counters["redactions"])
    print("withheld      %d files" % len(withheld))
    return OUT


if __name__ == "__main__":
    out = main()
    # Post-check: nothing identifying survived.
    bad = re.compile(r"ahb-sjsu|geometric-evaluation-theory|Andrew\s+Bond|\bahbond\b|abptl|"
                     r"\bSJSU\b|\bAtlas\b|\bErebus\b|ssu-workstation-ai|ssu-atlas-ai", re.I)
    leaks = 0
    for dirpath, dirnames, filenames in os.walk(out):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                t = io.open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for m in bad.finditer(t):
                if leaks < 10:
                    print("LEAK %s :: %s" % (os.path.relpath(p, out), m.group(0)))
                leaks += 1
    print("leaks after redaction: %d" % leaks)

    zp = ZIP
    if os.path.exists(zp):
        os.remove(zp)
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for dirpath, dirnames, filenames in os.walk(out):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                p = os.path.join(dirpath, fn)
                z.write(p, os.path.relpath(p, out).replace("\\", "/"))
    print("zip %s  %.1f MB" % (zp, os.path.getsize(zp) / 1e6))
