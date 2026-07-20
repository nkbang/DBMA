"""
scripts/shadow_score_distribution.py — SPRINT33-C Phase 3: Feature Score
Distribution Collection.

Investigation/analysis only — shadow mode, no new feature, no threshold
change (per HQ Task Order scope). Reuses
scripts/shadow_boundary_analysis.py's candidate/heading resolution and
cursor-managed scoring traversal (resolve_headings_and_candidates,
iter_scored_candidates) unchanged, so this script cannot silently diverge
from Phase 1/2's baseline on what a "candidate" or a "match" is — it only
adds observation on top of the same traversal.

Measures (per HQ's Phase 3 spec):
  1. score histogram — distribution of BoundaryEvent.total_score across
     every candidate in the Beta corpus, at the current default registry
     (heading=100, paragraph=30, threshold=50).
  2. boundary density — matched/total ratio per document and aggregate.
  3. false positive proxy — candidates that crossed the threshold via a
     heading match but are implausibly long to actually BE a heading (a
     containment match can fire on a heading's text appearing anywhere
     inside a large paragraph, not just when the paragraph mostly IS the
     heading). There is no ground-truth boundary label in this corpus, so
     this is a heuristic flag for manual review, not a precision score.

Usage:
    python scripts/shadow_score_distribution.py
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import (
    MD_DIR,
    iter_scored_candidates,
    resolve_headings_and_candidates,
)

# A matched candidate longer than this is flagged as a suspicious match —
# real headings in this corpus run well under this (see docs/SPRINT33-C-
# phase3-score-distribution.md for the sampled distribution of matched
# candidate lengths). Heuristic only, not a hard rule.
_SUSPICIOUS_MATCH_CHAR_LEN = 300


@dataclass
class SuspiciousMatch:
    document: str
    position: int
    length: int
    total_score: float
    preview: str


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))

    score_histogram: Counter = Counter()
    matched_length_histogram: Counter = Counter()  # bucketed lengths of matched candidates
    doc_density: List[tuple] = []
    suspicious: List[SuspiciousMatch] = []

    total_candidates = 0
    total_matched = 0

    for md_path in md_files:
        stub = md_path.stem.replace("_pdf", "")
        headings, candidates = resolve_headings_and_candidates(md_path)

        doc_matched = 0
        for pos, candidate, event in iter_scored_candidates(headings, candidates):
            score_histogram[event.total_score] += 1
            if event.is_boundary:
                doc_matched += 1
                total_matched += 1
                length = len(candidate)
                bucket = (length // 50) * 50
                matched_length_histogram[bucket] += 1
                if length > _SUSPICIOUS_MATCH_CHAR_LEN:
                    preview = candidate[:80].replace("\n", " ")
                    suspicious.append(
                        SuspiciousMatch(stub, pos, length, event.total_score, preview)
                    )

        total_candidates += len(candidates)
        doc_density.append((stub, doc_matched, len(candidates)))

    print("=== Score Histogram (all candidates, all documents) ===")
    for score in sorted(score_histogram):
        count = score_histogram[score]
        pct = 100.0 * count / total_candidates
        print(f"  score={score:>6.1f}  count={count:>6}  ({pct:5.1f}%)")

    print()
    print("=== Boundary Density (matched / candidates) ===")
    for name, matched, count in doc_density:
        density = 100.0 * matched / count if count else 0.0
        print(f"  {name:<40} {matched:>6} / {count:<6} = {density:5.2f}%")
    agg_density = 100.0 * total_matched / total_candidates if total_candidates else 0.0
    print(f"  {'AGGREGATE':<40} {total_matched:>6} / {total_candidates:<6} = {agg_density:5.2f}%")

    print()
    print("=== Matched Candidate Length Distribution (char count, 50-char buckets) ===")
    for bucket in sorted(matched_length_histogram):
        count = matched_length_histogram[bucket]
        print(f"  [{bucket:>4}-{bucket + 49:>4}] count={count:>5}")

    print()
    print(f"=== Suspicious Matches (matched candidate > {_SUSPICIOUS_MATCH_CHAR_LEN} chars) ===")
    print(f"  count: {len(suspicious)} / {total_matched} matched ({100.0 * len(suspicious) / total_matched:.1f}%)" if total_matched else "  count: 0")
    for s in suspicious[:15]:
        print(f"  [{s.document}] pos={s.position} len={s.length} score={s.total_score} :: {s.preview}...")
    if len(suspicious) > 15:
        print(f"  ... and {len(suspicious) - 15} more")


if __name__ == "__main__":
    main()
