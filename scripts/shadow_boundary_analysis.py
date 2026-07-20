"""
scripts/shadow_boundary_analysis.py — SPRINT33-C Phase 1: Heading-only
Shadow Baseline.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module (scripts/ -> core/ is the only allowed
direction). Runs core.semantic_boundary_detector's dormant FeatureRegistry
against the 12-PDF Beta corpus in shadow mode (score computed, nothing
written back, no chunk/TSU changes) to answer one question: does the
promoted HeadingBoundaryFeature reproduce SPRINT32-F's HeadingAssembler
result (334 distinct headings matched across 11/12 documents), or did
promotion introduce a regression?

Candidate generation: core.text_normalizer.split_paragraphs() on each
document's already-extracted .md text (output/beta_validation_v5/*.md),
matching the resolution SPRINT33-B settled on (paragraph-level candidates,
not chunk-level) — so an exact 334 match is not expected, only the same
order of magnitude, since HeadingAssembler matched against chunk lines
(1200-char chunks split further into lines) while this scores whole
paragraphs.

Cursor management: HeadingBoundaryFeature.score() is intentionally
stateless (see core/semantic_boundary_detector.py docstring) — it does not
advance any cursor itself. This script owns that responsibility, exactly
as HeadingAssembler.assign()'s loop does, by calling the same
_first_contained/_normalize_for_matching primitives directly to find which
window offset matched and advancing its own cursor accordingly
(SPRINT33-C Preflight finding #2).

Usage:
    python scripts/shadow_boundary_analysis.py
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.extractors import collect_pdf_spans
from core.heading_provider import (
    PdfHeadingProvider,
    ProviderHeading,
    _first_contained,
    _normalize_for_matching,
)
from core.semantic_boundary_detector import (
    BoundaryContext,
    DEFAULT_THRESHOLD,
    get_registry,
    score_boundary,
)
from core.text_normalizer import split_paragraphs

RAW_DIR = Path(__file__).parent.parent / "data" / "beta_corpus"
MD_DIR = Path(__file__).parent.parent / "output" / "beta_validation_v5"

# Same window size HeadingAssembler uses (core/heading_provider.py) — kept
# identical here so cursor recovery behaves the same way in shadow mode.
_LOOKAHEAD_WINDOW = 5


@dataclass
class DocResult:
    name: str
    candidate_count: int
    matched_count: int
    total_headings: int


def _resolve_pdf(md_path: Path) -> Path:
    # The .md filename is sanitized (commas/colons/parens -> "_"); the
    # matching *_chunks_meta.json still carries the exact original PDF
    # filename in its "source" field, so resolve through that instead of
    # guessing from the sanitized stem.
    meta_path = md_path.with_name(md_path.stem + "_chunks_meta.json")
    source_name = json.loads(meta_path.read_text(encoding="utf-8"))["source"]
    for p in RAW_DIR.rglob("*.pdf"):
        if p.name == source_name:
            return p
    raise FileNotFoundError(source_name)


def _advance_cursor(cursor: int, headings: List[ProviderHeading], key: str) -> int:
    """Mirrors HeadingAssembler.assign()'s cursor-advance step (heading_
    provider.py:283-288): find the match offset within the lookahead
    window and, if found, move the cursor past it. Returns the unchanged
    cursor when nothing in the window matches."""
    window = [
        _normalize_for_matching(h.text)
        for h in headings[cursor : cursor + _LOOKAHEAD_WINDOW]
    ]
    offset = _first_contained(window, key)
    if offset is None:
        return cursor
    return cursor + offset + 1


def analyze_document(md_path: Path) -> DocResult:
    stub = md_path.stem.replace("_pdf", "")
    pdf_path = _resolve_pdf(md_path)

    spans = collect_pdf_spans(str(pdf_path))
    headings = PdfHeadingProvider(spans).headings()

    text = md_path.read_text(encoding="utf-8")
    candidates = split_paragraphs(text)

    registry = get_registry()
    cursor = 0
    matched = 0
    for i, candidate in enumerate(candidates):
        ctx = BoundaryContext(
            candidate_text=candidate,
            position=i,
            headings=headings,
            heading_cursor=cursor,
        )
        event = score_boundary(ctx, registry=registry)
        if event.is_boundary:
            matched += 1
            key = _normalize_for_matching(candidate)
            cursor = _advance_cursor(cursor, headings, key)

    return DocResult(
        name=stub,
        candidate_count=len(candidates),
        matched_count=matched,
        total_headings=len(headings),
    )


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    results = [analyze_document(p) for p in md_files]

    print(f"{'document':<40} {'candidates':>10} {'headings':>10} {'matched':>8}")
    total_matched = 0
    docs_with_match = 0
    for r in results:
        print(f"{r.name:<40} {r.candidate_count:>10} {r.total_headings:>10} {r.matched_count:>8}")
        total_matched += r.matched_count
        if r.matched_count > 0:
            docs_with_match += 1

    print()
    print(f"documents: {len(results)}")
    print(f"documents with >=1 match: {docs_with_match}")
    print(f"total matched (this run): {total_matched}")
    print(f"SPRINT32-F baseline: 334 distinct headings, 11/12 documents improved")
    print(f"threshold used: {DEFAULT_THRESHOLD}")


if __name__ == "__main__":
    main()
