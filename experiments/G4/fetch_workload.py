"""Fetch the fixed public-domain workload text and record its hash.

    python fetch_workload.py

Downloads Project Gutenberg ebook 1342 (Pride and Prejudice, public domain), strips the
Gutenberg header up to the first chapter heading, writes `workload.txt`, and prints its
SHA-256, which is written into PREREG-G4 at sealing. The probe truncates to the first
`n_tokens` tokens of the model's tokenizer, so only the opening of the book is used.
"""
import hashlib
import urllib.request

URL = "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"

raw = urllib.request.urlopen(URL, timeout=60).read().decode("utf-8", errors="replace")
start = raw.find("Chapter I")
if start < 0:
    start = raw.find("CHAPTER I")
text = raw[start:] if start >= 0 else raw
text = text[:200_000]
open("workload.txt", "w", encoding="utf-8").write(text)
print("workload.txt", len(text), "chars, sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
