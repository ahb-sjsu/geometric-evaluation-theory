#!/usr/bin/env python3
"""G3f stimuli: a passage and a summary of it, with a known number of unsupported statements.

The point of the gate is that NOTHING changes from G3c and G3e except the stimulus family.
G3c graded worksheets of twenty multiplications, where quality is a count of arithmetic errors
and the judge can do the arithmetic exactly. Here quality is a count of statements in a summary
that the passage does not support, which is the thing an LLM judge is actually asked to do, and
which no judge does exactly.

Quality has to stay EXACTLY known or there is no threshold to measure. That is what this module
buys, and it buys it by generating the passage and the summary from the same structured record
rather than by writing either one:

  * A record is twenty facts. Each fact is a template plus one slot value drawn from a pool.
  * The passage states the twenty facts, one numbered sentence each.
  * The summary restates the same twenty facts in different wording, one numbered sentence each.
  * For e of them, chosen at random, the summary's slot carries a DIFFERENT value from the same
    pool. That statement then contradicts the passage on one word, and the passage states the
    right value explicitly.

So a summary statement is unsupported if and only if it was perturbed, e is known by
construction, and quality is 1 - e/N with no annotator and no judgement call. `verify_record`
checks that property directly rather than trusting the construction, and `selftest` drives it
over the whole error ladder.

Two properties the perturbation must have, both enforced and both checked:

  * the replacement differs from the true value, so the statement is really contradicted;
  * the replacement appears NOWHERE else in the passage, so nothing else in the passage can be
    read as supporting it. Without this a reader could defend a wrong year by pointing at a
    different sentence that happens to carry it, and the quality scale would stop being exact.

    python g3f_stimuli.py selftest
"""
from __future__ import annotations

import sys

import numpy as np

# --------------------------------------------------------------------------- pools
# Disjoint by type and large enough that a perturbation almost always finds a free value.
# Values are compared as rendered strings, so no pool may share a surface form with another.

CITIES = ["Aldermere", "Brackwell", "Corvane", "Dunmoor", "Eastharrow", "Fenwick", "Garrow",
          "Holloway", "Inverell", "Jarrow", "Kestrel Bay", "Lowmarsh", "Merrow", "Northgate",
          "Oakhaven", "Pellstone", "Quarry Hill", "Redmoor", "Stonebridge", "Thornwick",
          "Ullswater", "Vexley", "Westfold", "Yarrow"]

PEOPLE = ["Ambrose Teal", "Bridget Lyle", "Casper Nunn", "Delia Frost", "Emmett Roe",
          "Fiona Marsh", "Gideon Pike", "Hester Vale", "Ivo Sandler", "Juno Craddock",
          "Kit Ferrers", "Lena Ostrow", "Milo Haight", "Nadia Sperling", "Otto Bellamy",
          "Petra Quill", "Rufus Ander", "Saskia Doorn", "Tobias Wren", "Ursula Kemp"]

MATERIALS = ["basalt", "birch", "brass", "canvas", "cedar", "copper", "granite", "iron",
             "limestone", "marble", "oak", "pewter", "sandstone", "slate", "steel", "teak",
             "terracotta", "tin", "walnut", "zinc"]

FIELDS = ["botany", "cartography", "ceramics", "forestry", "glassmaking", "horology",
          "hydrology", "lexicography", "masonry", "metallurgy", "mycology", "ornithology",
          "printing", "seismology", "surveying", "textiles", "typography", "viticulture"]

# Templates: (passage sentence, summary sentence, slot kind). {v} is the slot.
TEMPLATES = [
    ("The society was founded in {v}.", "Its founding year was {v}.", "year"),
    ("Its first meeting hall was built of {v}.", "The original hall was made of {v}.", "material"),
    ("The charter was signed in {v}.", "{v} is where the charter was signed.", "city"),
    ("Its first president was {v}.", "{v} served as the first president.", "person"),
    ("The society admitted {v} members in its first year.", "It took in {v} members that first year.", "count"),
    ("Its library opened in {v}.", "The library began operating in {v}.", "year"),
    ("The library's shelves were cut from {v}.", "Its shelving was {v}.", "material"),
    ("A second branch opened at {v}.", "{v} received the second branch.", "city"),
    ("The branch was directed by {v}.", "{v} ran that branch.", "person"),
    ("It held {v} volumes at the time.", "The collection numbered {v} volumes then.", "count"),
    ("The society's journal first appeared in {v}.", "Its journal began publication in {v}.", "year"),
    ("The journal was printed on presses of {v}.", "Those presses were built from {v}.", "material"),
    ("Its editor was {v}.", "{v} edited the journal.", "person"),
    ("The journal reached {v} subscribers.", "It had {v} subscribers.", "count"),
    ("An annual prize in {v} was endowed.", "The endowed prize was for {v}.", "field"),
    ("The prize was first awarded in {v}.", "{v} was the year of the first award.", "year"),
    ("It went to a researcher from {v}.", "The first winner came from {v}.", "city"),
    ("The medal was struck in {v}.", "That medal was {v}.", "material"),
    ("The society's archive holds {v} letters.", "Its archive contains {v} letters.", "count"),
    ("Its current secretary is {v}.", "{v} is secretary today.", "person"),
]

N_TEMPLATES = len(TEMPLATES)


def _pool(kind: str, rng: np.random.Generator) -> str:
    if kind == "year":
        return str(int(rng.integers(1802, 1998)))
    if kind == "count":
        return str(int(rng.integers(12, 9000)))
    if kind == "city":
        return str(rng.choice(CITIES))
    if kind == "person":
        return str(rng.choice(PEOPLE))
    if kind == "material":
        return str(rng.choice(MATERIALS))
    if kind == "field":
        return str(rng.choice(FIELDS))
    raise ValueError(kind)


def make_record(rng: np.random.Generator, n_items: int) -> list:
    """n_items facts with distinct rendered values, so every value identifies its own fact."""
    if n_items > N_TEMPLATES:
        raise ValueError("only %d templates; asked for %d items" % (N_TEMPLATES, n_items))
    idx = rng.permutation(N_TEMPLATES)[:n_items]
    facts, used = [], set()
    for i in idx:
        p_t, s_t, kind = TEMPLATES[int(i)]
        for _ in range(500):
            v = _pool(kind, rng)
            if v not in used:
                break
        else:
            raise RuntimeError("pool exhausted for %s" % kind)
        used.add(v)
        facts.append({"passage": p_t, "summary": s_t, "kind": kind, "true": v, "shown": v,
                      "perturbed": False})
    return facts


def perturb(facts: list, e: int, rng: np.random.Generator) -> list:
    """Replace the slot in e of the facts with a value of the same kind that is different from
    the truth and absent from the whole passage. Both conditions are what makes the statement
    unambiguously unsupported.

    Absence is tested against the rendered passage as a SUBSTRING, not against the set of true
    values. The selftest found why on its first run: 'tin' is a substring of 'printing', so a
    summary saying the medal was struck in tin had its wrong value sitting in the passage in
    another word, and a reader could argue the passage half-supported it. A value set cannot see
    that and the rendered text can."""
    passage = "\n".join(f["passage"].format(v=f["true"]) for f in facts)
    if e:
        for i in rng.choice(len(facts), size=e, replace=False):
            f = facts[int(i)]
            for _ in range(500):
                v = _pool(f["kind"], rng)
                if v != f["true"] and v not in passage:
                    break
            else:
                raise RuntimeError("no free replacement for %s" % f["kind"])
            # A later perturbation must not reuse it either, so it joins the text being searched.
            passage = passage + "\n" + v
            f["shown"] = v
            f["perturbed"] = True
    return facts


def render(facts: list) -> tuple:
    passage = "\n".join("%d. %s" % (i + 1, f["passage"].format(v=f["true"]))
                        for i, f in enumerate(facts))
    summary = "\n".join("%d. %s" % (i + 1, f["summary"].format(v=f["shown"]))
                        for i, f in enumerate(facts))
    return passage, summary


def make_stimulus(rng: np.random.Generator, n_items: int, e: int) -> dict:
    """One passage and one summary of it with exactly e unsupported statements."""
    facts = perturb(make_record(rng, n_items), e, rng)
    passage, summary = render(facts)
    ok, why = verify_record(facts, passage)
    if not ok:
        raise RuntimeError("stimulus failed its own check: %s" % why)
    return {"e": int(e), "text": "PASSAGE\n%s\n\nSUMMARY\n%s" % (passage, summary),
            "passage": passage, "summary": summary,
            "unsupported": [i for i, f in enumerate(facts) if f["perturbed"]]}


def verify_record(facts: list, passage: str) -> tuple:
    """The property the quality scale rests on, checked rather than assumed.

    A summary statement is unsupported if and only if it was perturbed. That needs: every
    perturbed statement shows a value that differs from its fact's true value AND appears
    nowhere in the passage, and every unperturbed statement shows exactly the true value."""
    for i, f in enumerate(facts):
        if f["perturbed"]:
            if f["shown"] == f["true"]:
                return False, "fact %d perturbed to its own value" % i
            if f["shown"] in passage:
                return False, "fact %d shows %r which the passage contains" % (i, f["shown"])
        elif f["shown"] != f["true"]:
            return False, "fact %d altered without being marked" % i
    return True, "ok"


def selftest(n_items: int = 20, reps: int = 40) -> int:
    rng = np.random.default_rng(20260922)
    seen_texts = set()
    for e in range(n_items + 1):
        for _ in range(reps):
            s = make_stimulus(rng, n_items, e)
            if len(s["unsupported"]) != e:
                print("FAIL: asked for %d unsupported, got %d" % (e, len(s["unsupported"])))
                return 1
            if s["text"] in seen_texts:
                print("FAIL: duplicate stimulus at e=%d" % e)
                return 1
            seen_texts.add(s["text"])
            if s["passage"].count("\n") != n_items - 1 or s["summary"].count("\n") != n_items - 1:
                print("FAIL: wrong line count at e=%d" % e)
                return 1
    print("selftest ok: %d stimuli over e=0..%d, every one verified, no duplicates"
          % (len(seen_texts), n_items))
    lo = make_stimulus(np.random.default_rng(1), n_items, 0)
    hi = make_stimulus(np.random.default_rng(1), n_items, n_items)
    print("\nexample, e=0, quality 1.00:\n%s" % lo["text"][:320])
    print("\nexample, e=%d, quality 0.00, unsupported at %s" % (n_items, hi["unsupported"][:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(selftest() if len(sys.argv) > 1 and sys.argv[1] == "selftest" else selftest())
