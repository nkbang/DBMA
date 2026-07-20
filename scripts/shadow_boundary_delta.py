"""
scripts/shadow_boundary_delta.py — SPRINT33-C Phase 6-B: Shadow Boundary
Delta Measurement.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Implements the input schema designed
in Phase 6-A Preflight: compares the EXISTING production chunk boundary
set (core.chunking_optimizer's real output, already on disk in
output/beta_validation_v5/*_chunks.txt) against the CANDIDATE boundary set
the dormant Semantic Boundary Detector would produce, both resolved to
character offsets in the SAME coordinate space.

Coordinate space: core/chunking_optimizer.py:chunk_once() calls
`normalize_pipeline_text(raw_text)` before splitting (same function
core.text_normalizer.split_paragraphs() itself calls internally) — so
existing chunk starts and candidate starts are both offsets into
`normalize_pipeline_text(body_text)`, with no cross-space alignment needed
(Phase 6-A Preflight finding).

A chunk's END offset is deliberately NOT used as a boundary point:
DEFAULT_CHUNK_OVERLAP (120 chars, core/config.py) means consecutive chunks
share a tail, so only chunk START offsets are real split decisions.

Metrics (Phase 6-A Preflight §3, HQ-approved):
  A. confirmed rate    = existing chunk starts within TOLERANCE chars of
                          some semantic-boundary candidate / all chunk starts
  B. orphaned rate      = semantic-boundary candidates with no chunk start
                          within TOLERANCE chars / all semantic boundaries

Usage:
    python scripts/shadow_boundary_delta.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import (
    MD_DIR,
    _advance_cursor,
    _extract_body_text,
    _resolve_pdf,
)
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider, _normalize_for_matching
from core.semantic_boundary_detector import BoundaryContext, get_registry, score_boundary
from core.text_normalizer import normalize_pipeline_text

TOLERANCE = 50  # chars — HQ-approved in Phase 6-A Preflight


@dataclass
class OffsetCandidate:
    start: int
    text: str
    is_boundary: bool


def candidates_with_offsets(normalized: str) -> List[Tuple[str, int]]:
    """Mirrors core.text_normalizer.split_paragraphs()'s own split
    (`re.split(r"\\n\\n+", text)` then strip + drop-empty) but keeps each
    surviving paragraph's start offset in `normalized`, which split_
    paragraphs itself discards. Same regex, so the resulting text list is
    identical to what split_paragraphs(normalized) would return applied to
    already-normalized text (idempotent — normalize_pipeline_text does not
    change already-normalized text)."""
    seps = list(re.finditer(r"\n\n+", normalized))
    starts = [0] + [m.end() for m in seps]
    ends = [m.start() for m in seps] + [len(normalized)]
    out: List[Tuple[str, int]] = []
    for s, e in zip(starts, ends):
        raw = normalized[s:e]
        stripped = raw.strip()
        if not stripped:
            continue
        # leading-whitespace-adjusted start offset
        lead = len(raw) - len(raw.lstrip())
        out.append((stripped, s + lead))
    return out


def chunk_start_offsets(chunks_path: Path, normalized: str) -> List[int]:
    """Resolves each existing chunk's start offset in `normalized` via
    sequential substring search (same pattern HeadingAssembler uses for
    heading-to-chunk matching) — verified in Phase 6-A Preflight that
    chunk-leading text is found as a direct substring of the normalized
    body text."""
    raw = chunks_path.read_text(encoding="utf-8")
    parts = re.split(r"\n*\[chunk \d+\]\n", raw)
    texts = [p.strip() for p in parts if p.strip()]

    offsets: List[int] = []
    cursor = 0
    for text in texts:
        probe = text[:40]
        if not probe:
            continue
        idx = normalized.find(probe, max(0, cursor - TOLERANCE))
        if idx == -1:
            idx = normalized.find(probe)
        if idx != -1:
            offsets.append(idx)
            cursor = idx
    return offsets


def score_candidates(headings, candidates: List[str]) -> List[bool]:
    """Same cursor-managed scoring as shadow_boundary_analysis.iter_scored_
    candidates, inlined here since that function doesn't expose per-
    candidate is_boundary alongside externally-computed offsets."""
    registry = get_registry()
    cursor = 0
    flags = []
    for i, cand in enumerate(candidates):
        ctx = BoundaryContext(candidate_text=cand, position=i, headings=headings, heading_cursor=cursor)
        event = score_boundary(ctx, registry=registry)
        flags.append(event.is_boundary)
        if event.is_boundary:
            key = _normalize_for_matching(cand)
            cursor = _advance_cursor(cursor, headings, key)
    return flags


def nearest_distance(point: int, sorted_targets: List[int]) -> int:
    if not sorted_targets:
        return 10**9
    import bisect
    i = bisect.bisect_left(sorted_targets, point)
    candidates = []
    if i < len(sorted_targets):
        candidates.append(abs(sorted_targets[i] - point))
    if i > 0:
        candidates.append(abs(sorted_targets[i - 1] - point))
    return min(candidates)


def analyze_document(md_path: Path, chunks_path: Path):
    pdf_path = _resolve_pdf(md_path)
    spans = collect_pdf_spans(str(pdf_path))
    headings = PdfHeadingProvider(spans).headings()

    body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
    normalized = normalize_pipeline_text(body_text)

    cand_pairs = candidates_with_offsets(normalized)
    candidates = [t for t, _ in cand_pairs]
    offsets = [o for _, o in cand_pairs]
    flags = score_candidates(headings, candidates)

    boundary_offsets = sorted(o for o, f in zip(offsets, flags) if f)
    chunk_offsets = sorted(chunk_start_offsets(chunks_path, normalized))

    confirmed = sum(1 for c in chunk_offsets if nearest_distance(c, boundary_offsets) <= TOLERANCE)
    orphaned = sum(1 for b in boundary_offsets if nearest_distance(b, chunk_offsets) > TOLERANCE)

    return {
        "chunks": len(chunk_offsets),
        "boundaries": len(boundary_offsets),
        "confirmed": confirmed,
        "confirmed_rate": confirmed / len(chunk_offsets) if chunk_offsets else 0.0,
        "orphaned": orphaned,
        "orphaned_rate": orphaned / len(boundary_offsets) if boundary_offsets else 0.0,
    }


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    print(f"{'document':<40} {'chunks':>7} {'bounds':>7} {'confirmed':>10} {'orphaned':>9}")
    tot_chunks = tot_confirmed = tot_boundaries = tot_orphaned = 0
    for md_path in md_files:
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        if not chunks_path.exists():
            continue
        stub = md_path.stem.replace("_pdf", "")
        r = analyze_document(md_path, chunks_path)
        print(
            f"{stub:<40} {r['chunks']:>7} {r['boundaries']:>7} "
            f"{r['confirmed']:>5}({100*r['confirmed_rate']:>4.1f}%) "
            f"{r['orphaned']:>4}({100*r['orphaned_rate']:>4.1f}%)"
        )
        tot_chunks += r["chunks"]
        tot_confirmed += r["confirmed"]
        tot_boundaries += r["boundaries"]
        tot_orphaned += r["orphaned"]

    print()
    print(f"AGGREGATE confirmed rate: {tot_confirmed}/{tot_chunks} = {100*tot_confirmed/tot_chunks:.1f}%")
    print(f"AGGREGATE orphaned rate:  {tot_orphaned}/{tot_boundaries} = {100*tot_orphaned/tot_boundaries:.1f}%")
    print(f"tolerance: {TOLERANCE} chars")


if __name__ == "__main__":
    main()
