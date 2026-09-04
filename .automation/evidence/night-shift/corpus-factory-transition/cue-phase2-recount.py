"""CUE independent reproduction of Phase 2 §6 upper-bound counts.
Read-only. Run: python3 cue-phase2-recount.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
canonical = json.load(
    open(ROOT / "NAE/corpus/canonical/Fuller_Complete_Works_Vol01/canonical.json")
)

sentences = []
for p in canonical.get("paragraphs", []):
    if p.get("type") != "prose":
        continue
    for s in p.get("sentences", []):
        t = s.get("text", "")
        if len(t) >= 25:
            sentences.append(t)

print("candidates(>=25 chars):", len(sentences))

PAGE_PATTERNS = [r"^p\.?\s*\d+", r"\b\d+\s*p\.?\b", r"^[IVXLC]+\.?\s*"]
page_hits = sum(1 for t in sentences if any(re.search(p, t) for p in PAGE_PATTERNS))
print("page-number pattern matches (doc claims 291):", page_hits)

lower_start = sum(1 for t in sentences if t and t[0].islower())
print("starts with lowercase char (doc claims 666):", lower_start)
