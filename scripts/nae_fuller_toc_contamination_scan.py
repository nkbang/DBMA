#!/usr/bin/env python3
"""Reproducible scan for table-of-contents (TOC) paragraphs misclassified as
`type: "prose"` in a Fuller volume's canonical.json, cross-referenced against
that volume's tsu.json to flag any TSU claim generated from one.

Written per ADR-030 Amendment C §5 R3 (C1 Review — the original "6 found"
scan for Fuller_Complete_Works_Vol08 was not documented as reproducible).
See docs/architecture/ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001.md.

Usage:
    python3 scripts/nae_fuller_toc_contamination_scan.py [IDENTIFIER ...]

With no arguments, scans every Fuller_Complete_Works_VolNN identifier found
under NAE/corpus/canonical/. Exits non-zero only if a TOC-derived TSU is
found with review_status == "verified" (a human signed off on a claim this
scan flags as pattern-matching known contamination) — "generated" is just
the normal pre-review state (true of Vol.01-07 while on HOLD), not a
finding, and "rejected" means it was already caught and handled.

Known limitation: this is a per-paragraph text heuristic (front-matter
index range + short length + a leader-dash/page-number tail), not a
semantic parser. Of the six known Vol.08 cases it catches four
(TSU-0030341/0030342/0030345/0030346); TSU-0030343/TSU-0030344 sit in a
paragraph (index 34) whose own text has no number or dash — the fragment
that outed it as a TOC entry was in an adjacent paragraph. Catching those
requires reading neighbouring paragraphs together, which this scan does
not do. Treat a clean run as "no *additional* pattern-matching TOC
contamination found", not as a proof of zero contamination.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANONICAL_ROOT = REPO_ROOT / "NAE" / "corpus" / "canonical"
TSU_ROOT = REPO_ROOT / "NAE" / "corpus" / "tsu"

# A prose paragraph is a TOC-contamination candidate if BOTH hold:
#   1. it sits in the front-matter index range, where a scanned book's table
#      of contents actually lives (real narrative content is index 130+ in
#      the one incident on record) — a lone short paragraph with a stray
#      number deep in the body (e.g. a Bible reference typo) is not TOC
#      contamination, and restricting to front matter is what keeps this
#      scan's false-positive rate usable;
#   2. it is short (real TOC entries run a few dozen to a few hundred
#      characters, not the 1000+ of an ordinary narrative paragraph) AND
#      contains either a leader-dash+number tail or a bare 1-3 digit number
#      that is not part of a verse/chapter citation (e.g. "3:16").
# Calibrated against the six known Vol.08 cases (paragraphs 30/33/34/36/83,
# lengths 46-264 chars, all within the first ~90 paragraphs of the volume).
# See docs/architecture/ADR-030-AMENDMENT-C-CUE-FINAL-VERIFICATION-001.md.
FRONT_MATTER_PARAGRAPH_LIMIT = 130
MAX_TOC_PARAGRAPH_LEN = 350
DASH_LEADER_PATTERN = re.compile(r"-{2,}[^a-zA-Z\n]{0,12}\d")
BARE_PAGE_NUMBER_PATTERN = re.compile(r"(?<![\d:.])\b\d{1,3}\b(?!\s*:)")


def _is_toc_like(text: str, paragraph_index: int | None) -> bool:
    if paragraph_index is None or paragraph_index >= FRONT_MATTER_PARAGRAPH_LIMIT:
        return False
    if len(text) > MAX_TOC_PARAGRAPH_LEN:
        return False
    return bool(DASH_LEADER_PATTERN.search(text) or BARE_PAGE_NUMBER_PATTERN.search(text))


def find_fuller_identifiers() -> list[str]:
    if not CANONICAL_ROOT.exists():
        return []
    return sorted(
        p.name for p in CANONICAL_ROOT.iterdir()
        if p.is_dir() and p.name.startswith("Fuller_Complete_Works_Vol")
    )


def scan_identifier(identifier: str) -> dict:
    canonical_path = CANONICAL_ROOT / identifier / "canonical.json"
    tsu_path = TSU_ROOT / identifier / "tsu.json"

    if not canonical_path.exists():
        return {"identifier": identifier, "error": f"missing {canonical_path}"}

    canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
    tsu_records = json.loads(tsu_path.read_text(encoding="utf-8")) if tsu_path.exists() else []
    tsu_by_paragraph: dict[int, list[dict]] = {}
    for r in tsu_records:
        tsu_by_paragraph.setdefault(r.get("paragraph"), []).append(r)

    toc_like_paragraphs = []
    contaminated_tsu = []
    for paragraph in canonical.get("paragraphs", []):
        if paragraph.get("type") != "prose":
            continue
        text = paragraph.get("text", "")
        idx = paragraph.get("index")
        if not _is_toc_like(text, idx):
            continue
        toc_like_paragraphs.append(idx)
        for tsu in tsu_by_paragraph.get(idx, []):
            contaminated_tsu.append({
                "id": tsu.get("id"),
                "paragraph": idx,
                "review_status": tsu.get("review_status"),
                "claim": tsu.get("claim"),
            })

    return {
        "identifier": identifier,
        "toc_like_paragraph_count": len(toc_like_paragraphs),
        "toc_like_paragraphs": toc_like_paragraphs,
        "contaminated_tsu": contaminated_tsu,
    }


def main(argv: list[str]) -> int:
    identifiers = argv or find_fuller_identifiers()
    if not identifiers:
        print("no Fuller_Complete_Works_VolNN identifiers found under", CANONICAL_ROOT)
        return 1

    unresolved = False
    for identifier in identifiers:
        result = scan_identifier(identifier)
        if "error" in result:
            print(f"[{identifier}] SKIP — {result['error']}")
            continue

        print(f"[{identifier}] TOC-like prose paragraphs: {result['toc_like_paragraph_count']}")
        if not result["contaminated_tsu"]:
            print(f"[{identifier}] no TSU generated from a TOC-like paragraph")
            continue

        for tsu in result["contaminated_tsu"]:
            status = tsu["review_status"]
            # Only a TSU that a human has already signed off as "verified"
            # while still matching the TOC-like pattern is an actionable
            # miss. "generated" just means the volume hasn't been reviewed
            # yet (true for Vol.01-07, on HOLD) — that's not a scan failure,
            # it's the normal pre-review state.
            if status == "verified":
                flag = "MISSED"
                unresolved = True
            elif status == "rejected":
                flag = "OK"
            else:
                flag = "PENDING"
            print(f"  [{flag}] {tsu['id']} (paragraph {tsu['paragraph']}, "
                  f"review_status={status}): {tsu['claim'][:80]!r}")

    return 1 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
