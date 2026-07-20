"""
scripts/shadow_d5_metrics.py — SPRINT33-D Phase 3-A: D-5 Metrics Formal
Evaluation.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Computes the three independent axes
ADR-007 Amendment A defines, split by the two genre profiles Amendment A
formalizes, against the Beta corpus:

  Axis 1  Orphaned Boundary Recovery Rate  (Phase 1 methodology)
  Axis 2  Semantic Flush Ratio             (Phase 2-B methodology)
  Axis 3  Unsplittable Outlier Ratio       (Phase 2-A methodology)

Profile classification (Amendment A, provisional): a document is Profile
B ("High Back-matter Density") if any candidate exceeds
chunk_size * SAFETY_CAP_RATIO (1800 chars at the default 1200 chunk_size);
otherwise Profile A ("Low Back-matter Density").

Axis 2 is computed without re-implementing core.hierarchical_chunk_
builder's decision loop: a chunk's start offset that exactly matches a
semantic-boundary candidate offset was a semantic-triggered flush: any
other chunk start was a safety-cap (or end-of-document) flush. This is
possible because build_chunks() already returns each chunk's start
offset, sparing this script from duplicating the builder's control flow
(unlike the Phase 2-B Preflight's ad-hoc measurement, which did
duplicate it for a one-off check).

Usage:
    python scripts/shadow_d5_metrics.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import MD_DIR, _extract_body_text, _resolve_pdf
from shadow_boundary_delta import TOLERANCE, candidates_with_offsets, chunk_start_offsets, nearest_distance
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_MIN_CHUNK_SIZE
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider, ProviderHeading, _normalize_for_matching
from core.hierarchical_chunk_builder import SAFETY_CAP_RATIO, build_chunks, _advance_heading_cursor
from core.semantic_boundary_detector import BoundaryContext, get_registry, score_boundary
from core.text_normalizer import normalize_pipeline_text, split_sentences_mixed

SAFETY_CAP = int(DEFAULT_CHUNK_SIZE * SAFETY_CAP_RATIO)


@dataclass
class DocMetrics:
    name: str
    profile: str
    candidates: int
    boundaries: int
    orphaned_before: int
    recovered: int
    recovery_rate: float
    shadow_chunks: int
    semantic_flushes: int
    semantic_flush_ratio: float
    unsplittable_outliers: int
    unsplittable_outlier_ratio: float


def _boundary_offsets(headings: List[ProviderHeading], candidates: List[Tuple[str, int]]) -> List[int]:
    registry = get_registry()
    cursor = 0
    out = []
    for i, (text, offset) in enumerate(candidates):
        ctx = BoundaryContext(candidate_text=text, position=i, headings=headings, heading_cursor=cursor)
        event = score_boundary(ctx, registry=registry)
        if event.is_boundary:
            out.append(offset)
            key = _normalize_for_matching(text)
            cursor = _advance_heading_cursor(cursor, headings, key)
    return sorted(out)


def classify_profile(candidates: List[Tuple[str, int]]) -> str:
    return "B" if any(len(text) > SAFETY_CAP for text, _ in candidates) else "A"


def unsplittable_outliers(candidates: List[Tuple[str, int]]) -> int:
    count = 0
    for text, _ in candidates:
        if len(text) > SAFETY_CAP and len(split_sentences_mixed(text)) <= 1:
            count += 1
    return count


def analyze_document(md_path: Path, chunks_path: Path) -> DocMetrics:
    pdf_path = _resolve_pdf(md_path)
    spans = collect_pdf_spans(str(pdf_path))
    headings = PdfHeadingProvider(spans).headings()

    body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
    normalized = normalize_pipeline_text(body_text)
    candidates = candidates_with_offsets(normalized)

    boundary_offsets = _boundary_offsets(headings, candidates)
    existing_offsets = sorted(chunk_start_offsets(chunks_path, normalized))
    shadow_chunks = build_chunks(candidates, headings, DEFAULT_CHUNK_SIZE, DEFAULT_MIN_CHUNK_SIZE)
    shadow_offsets = sorted(o for _, o in shadow_chunks)
    boundary_offset_set = set(boundary_offsets)

    orphaned_before = [b for b in boundary_offsets if nearest_distance(b, existing_offsets) > TOLERANCE]
    recovered = [b for b in orphaned_before if nearest_distance(b, shadow_offsets) <= TOLERANCE]

    semantic_flushes = sum(1 for o in shadow_offsets if o in boundary_offset_set)

    outliers = unsplittable_outliers(candidates)

    return DocMetrics(
        name=md_path.stem.replace("_pdf", ""),
        profile=classify_profile(candidates),
        candidates=len(candidates),
        boundaries=len(boundary_offsets),
        orphaned_before=len(orphaned_before),
        recovered=len(recovered),
        recovery_rate=len(recovered) / len(orphaned_before) if orphaned_before else 0.0,
        shadow_chunks=len(shadow_chunks),
        semantic_flushes=semantic_flushes,
        semantic_flush_ratio=semantic_flushes / len(shadow_chunks) if shadow_chunks else 0.0,
        unsplittable_outliers=outliers,
        unsplittable_outlier_ratio=outliers / len(candidates) if candidates else 0.0,
    )


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    results: List[DocMetrics] = []
    for md_path in md_files:
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        if not chunks_path.exists():
            continue
        results.append(analyze_document(md_path, chunks_path))

    print(
        f"{'document':<40} {'profile':>7} {'recovery':>9} "
        f"{'semantic':>9} {'outlier':>8}"
    )
    for r in results:
        print(
            f"{r.name:<40} {r.profile:>7} {100*r.recovery_rate:>8.1f}% "
            f"{100*r.semantic_flush_ratio:>8.1f}% {100*r.unsplittable_outlier_ratio:>7.1f}%"
        )

    for profile in ("A", "B"):
        subset = [r for r in results if r.profile == profile]
        if not subset:
            continue
        tot_orphaned = sum(r.orphaned_before for r in subset)
        tot_recovered = sum(r.recovered for r in subset)
        tot_chunks = sum(r.shadow_chunks for r in subset)
        tot_semantic = sum(r.semantic_flushes for r in subset)
        tot_candidates = sum(r.candidates for r in subset)
        tot_outliers = sum(r.unsplittable_outliers for r in subset)
        print()
        print(f"=== Profile {profile} aggregate ({len(subset)} docs) ===")
        print(f"  Axis 1 recovery rate:        {tot_recovered}/{tot_orphaned} = "
              f"{100*tot_recovered/tot_orphaned if tot_orphaned else 0:.1f}%")
        print(f"  Axis 2 semantic flush ratio: {tot_semantic}/{tot_chunks} = "
              f"{100*tot_semantic/tot_chunks if tot_chunks else 0:.1f}%")
        print(f"  Axis 3 unsplittable outlier: {tot_outliers}/{tot_candidates} = "
              f"{100*tot_outliers/tot_candidates if tot_candidates else 0:.1f}%")


if __name__ == "__main__":
    main()
