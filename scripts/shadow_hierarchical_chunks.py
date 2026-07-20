"""
scripts/shadow_hierarchical_chunks.py — SPRINT33-D Phase 1: Hierarchical
Chunk Builder Prototype, shadow evaluation.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Runs core.hierarchical_chunk_builder
(dormant, SPRINT33-D Phase 1) against the Beta corpus in shadow mode
(nothing written to disk, no chunk/TSU changes) and measures the D-5
metric Phase 1 Preflight identified as the headline number: how many of
the semantic boundaries the EXISTING production chunker orphans (SPRINT33-C
Phase 6-B: 70.3% aggregate) does the new builder now honor.

Usage:
    python scripts/shadow_hierarchical_chunks.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import _advance_cursor
from shadow_boundary_delta import (
    TOLERANCE,
    candidates_with_offsets,
    chunk_start_offsets,
    nearest_distance,
)
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_MIN_CHUNK_SIZE
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider, _normalize_for_matching
from core.hierarchical_chunk_builder import build_chunks
from core.semantic_boundary_detector import BoundaryContext, get_registry, score_boundary
from core.text_normalizer import normalize_pipeline_text
from shadow_boundary_analysis import MD_DIR, _extract_body_text, _resolve_pdf


def _boundary_offsets(headings, candidates: List[Tuple[str, int]]) -> List[int]:
    registry = get_registry()
    cursor = 0
    out = []
    for i, (text, offset) in enumerate(candidates):
        ctx = BoundaryContext(candidate_text=text, position=i, headings=headings, heading_cursor=cursor)
        event = score_boundary(ctx, registry=registry)
        if event.is_boundary:
            out.append(offset)
            key = _normalize_for_matching(text)
            cursor = _advance_cursor(cursor, headings, key)
    return sorted(out)


def analyze_document(md_path: Path, chunks_path: Path, meta_path: Path):
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

    orphaned_before = [b for b in boundary_offsets if nearest_distance(b, existing_offsets) > TOLERANCE]
    recovered = [b for b in orphaned_before if nearest_distance(b, shadow_offsets) <= TOLERANCE]

    production_count = json.loads(meta_path.read_text(encoding="utf-8")).get("chunks", 0)
    lengths = [len(t) for t, _ in shadow_chunks]

    return {
        "production_chunks": production_count,
        "shadow_chunks": len(shadow_chunks),
        "shadow_len_min": min(lengths) if lengths else 0,
        "shadow_len_median": sorted(lengths)[len(lengths) // 2] if lengths else 0,
        "shadow_len_max": max(lengths) if lengths else 0,
        "boundaries": len(boundary_offsets),
        "orphaned_before": len(orphaned_before),
        "recovered": len(recovered),
        "recovery_rate": len(recovered) / len(orphaned_before) if orphaned_before else 0.0,
    }


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    print(
        f"{'document':<40} {'prod':>6} {'shadow':>7} "
        f"{'len(min/med/max)':>20} {'orphaned':>9} {'recovered':>10}"
    )
    tot_orphaned = tot_recovered = 0
    for md_path in md_files:
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        meta_path = md_path.with_name(md_path.stem + "_chunks_meta.json")
        if not chunks_path.exists() or not meta_path.exists():
            continue
        stub = md_path.stem.replace("_pdf", "")
        r = analyze_document(md_path, chunks_path, meta_path)
        lens = f"{r['shadow_len_min']}/{r['shadow_len_median']}/{r['shadow_len_max']}"
        print(
            f"{stub:<40} {r['production_chunks']:>6} {r['shadow_chunks']:>7} "
            f"{lens:>20} {r['orphaned_before']:>9} "
            f"{r['recovered']:>4}({100*r['recovery_rate']:>4.1f}%)"
        )
        tot_orphaned += r["orphaned_before"]
        tot_recovered += r["recovered"]

    print()
    rate = 100 * tot_recovered / tot_orphaned if tot_orphaned else 0.0
    print(f"AGGREGATE orphaned-boundary recovery: {tot_recovered}/{tot_orphaned} = {rate:.1f}%")


if __name__ == "__main__":
    main()
