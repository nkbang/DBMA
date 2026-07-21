"""
scripts/shadow_chunk_overflow_audit.py — Preflight follow-up: measures how
often production chunking (core.chunking_optimizer.chunk_once, the exact
function core/processing.py calls) emits a chunk that exceeds chunk_size,
across the 12-document Beta corpus.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Does not reimplement chunk_once's
decision logic; calls it directly against each document's real body_text
(recovered the same way shadow_boundary_analysis.py does) so results
reflect production behavior exactly, not a re-derived approximation.

Background: docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md found
that split_sentences_mixed() never actually splits a paragraph (it keys
off "\n", which split_paragraphs() always strips), so any paragraph
routed through the "long paragraph" branch in
core.chunking_optimizer._split_by_paragraphs() either falls back to a
word-safe hard slice (bounded, chunk_size respected) or — for a plain
single-language paragraph — is appended whole via
_merge_sentence_fragments(), producing a chunk with no upper bound at
all. That Preflight confirmed the mechanism with synthetic text; this
script measures how often it actually fires on real documents.

Usage:
    python scripts/shadow_chunk_overflow_audit.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import MD_DIR, _extract_body_text
from core.chunking_optimizer import chunk_once
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

# Same 1.5x threshold chunking_optimizer.py itself uses to decide a
# paragraph is "long" (core/chunking_optimizer.py:303) — a chunk beyond
# this is not just "a bit over," it is in the regime the Preflight
# doc identified as unbounded.
OVERFLOW_RATIO = 1.5
OVERFLOW_CAP = int(DEFAULT_CHUNK_SIZE * OVERFLOW_RATIO)


@dataclass
class OverflowStats:
    total_chunks: int = 0
    over_target: int = 0          # len > chunk_size
    over_cap: int = 0             # len > chunk_size * 1.5 (likely defect B)
    max_len: int = 0
    over_cap_lens: List[int] = field(default_factory=list)

    @property
    def over_target_ratio(self) -> float:
        return self.over_target / self.total_chunks if self.total_chunks else 0.0

    @property
    def over_cap_ratio(self) -> float:
        return self.over_cap / self.total_chunks if self.total_chunks else 0.0


def chunk_size_violation_stats(
    chunks: List[str],
    chunk_size: int,
    overflow_ratio: float = OVERFLOW_RATIO,
) -> OverflowStats:
    """Pure function over an already-produced chunk list — kept separate
    from document I/O so it is unit-testable with synthetic chunk lists,
    matching the pattern shadow_d5_metrics.py / test_shadow_d5_metrics.py
    already established for this script family."""
    cap = int(chunk_size * overflow_ratio)
    stats = OverflowStats()
    for c in chunks:
        n = len(c)
        stats.total_chunks += 1
        stats.max_len = max(stats.max_len, n)
        if n > chunk_size:
            stats.over_target += 1
        if n > cap:
            stats.over_cap += 1
            stats.over_cap_lens.append(n)
    return stats


@dataclass
class DocAudit:
    name: str
    stats: OverflowStats


def audit_document(md_path: Path) -> DocAudit:
    stub = md_path.stem.replace("_pdf", "")
    text = md_path.read_text(encoding="utf-8")
    body_text = _extract_body_text(text)

    result = chunk_once(body_text, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
    stats = chunk_size_violation_stats(result.chunks, DEFAULT_CHUNK_SIZE)
    return DocAudit(name=stub, stats=stats)


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    audits = [audit_document(p) for p in md_files]

    print(f"chunk_size={DEFAULT_CHUNK_SIZE}  overflow_cap(1.5x)={OVERFLOW_CAP}")
    print()
    print(f"{'document':<40} {'chunks':>7} {'>target':>8} {'>1.5x cap':>10} {'max_len':>8}")

    total = OverflowStats()
    docs_with_overflow = 0
    for a in audits:
        s = a.stats
        print(f"{a.name:<40} {s.total_chunks:>7} {s.over_target:>8} {s.over_cap:>10} {s.max_len:>8}")
        total.total_chunks += s.total_chunks
        total.over_target += s.over_target
        total.over_cap += s.over_cap
        total.max_len = max(total.max_len, s.max_len)
        if s.over_cap > 0:
            docs_with_overflow += 1

    print()
    print(f"documents: {len(audits)}")
    print(f"documents with >=1 chunk over 1.5x cap: {docs_with_overflow}")
    print(f"total chunks: {total.total_chunks}")
    print(f"chunks over target ({DEFAULT_CHUNK_SIZE}): {total.over_target} "
          f"({total.over_target_ratio:.1%})")
    print(f"chunks over 1.5x cap ({OVERFLOW_CAP}, likely defect B): {total.over_cap} "
          f"({total.over_cap_ratio:.1%})")
    print(f"largest chunk observed: {total.max_len} chars "
          f"({total.max_len / DEFAULT_CHUNK_SIZE:.1f}x target)")


if __name__ == "__main__":
    main()
