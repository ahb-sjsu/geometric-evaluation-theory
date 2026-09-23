#!/usr/bin/env python3
"""Scan the paper's LaTeX sources for the house prose standard: no semicolons, no colons in
prose, no em-dashes. Labels, refs, cites, URLs, graphics paths and inline math are stripped
before the check. Comments and the preamble are skipped. Exit 1 on any hit.

    python build/style_scan.py iclr2027-v2.tex appendix_family3.tex
"""
import io
import re
import sys

STRIP = re.compile(r"\\(?:ref|label|cite[pt]?|eqref|url|href|includegraphics|input|include)\{[^}]*\}|\$[^$]*\$")
HIT = re.compile(r"; |[A-Za-z0-9)]: |---|\u2014")
EXEMPT = ("Target: $\\{$target$\\}$. Value:",)  # quoted prompt text is data


def scan(path: str) -> list:
    lines = io.open(path, encoding="utf-8").read().split("\n")
    body_started = "\\begin{document}" not in "".join(lines)
    hits = []
    for i, l in enumerate(lines, 1):
        if "\\begin{document}" in l:
            body_started = True
            continue
        if not body_started or l.lstrip().startswith("%"):
            continue
        if any(e in l for e in EXEMPT):
            continue
        t = STRIP.sub("", l)
        if HIT.search(t):
            hits.append((i, t.strip()[:110]))
    return hits


def main() -> int:
    total = 0
    for path in sys.argv[1:]:
        hits = scan(path)
        total += len(hits)
        print("%s: %d" % (path, len(hits)))
        for i, t in hits:
            print("  %5d  %s" % (i, t))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
