"""
scripts/adr011_page_header_artifact_delta.py — ADR-011 제안4 §3: how many
boundary decisions change when PageHeaderArtifactFeature (registry_with_
page_header_artifact(), fed by a document-scoped RepetitionTracker) is
added on top of the default 6-feature registry, on Profile B.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. core.hierarchical_chunk_builder.
build_chunks() itself is untouched (still uses get_registry(), the
default 6-feature set) — this script only measures the boundary-event
delta, it does not change what production emits.

Usage:
    python scripts/adr011_page_header_artifact_delta.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import MD_DIR, _extract_body_text, _resolve_pdf
from shadow_boundary_delta import candidates_with_offsets
from core.config import DEFAULT_CHUNK_SIZE
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider, ProviderHeading, _normalize_for_matching
from core.hierarchical_chunk_builder import SAFETY_CAP_RATIO, _advance_heading_cursor
from core.repetition_detector import RepetitionTracker
from core.semantic_boundary_detector import (
    BoundaryContext,
    get_registry,
    registry_with_page_header_artifact,
    score_boundary,
)
from core.text_normalizer import normalize_pipeline_text

SAFETY_CAP = int(DEFAULT_CHUNK_SIZE * SAFETY_CAP_RATIO)


def classify_profile(candidates: List[Tuple[str, int]]) -> str:
    return "B" if any(len(text) > SAFETY_CAP for text, _ in candidates) else "A"


def _run(candidates, headings, registry, with_repetition: bool):
    cursor = 0
    tracker = RepetitionTracker() if with_repetition else None
    boundaries = []
    for i, (text, offset) in enumerate(candidates):
        signal = tracker.observe(text) if tracker is not None else None
        ctx = BoundaryContext(
            candidate_text=text, position=i, headings=headings, heading_cursor=cursor,
            repetition_signal=signal,
        )
        event = score_boundary(ctx, registry=registry)
        boundaries.append(event.is_boundary)
        if event.is_boundary:
            key = _normalize_for_matching(text)
            cursor = _advance_heading_cursor(cursor, headings, key)
    return boundaries


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    default_registry = get_registry()
    extended_registry = registry_with_page_header_artifact()

    tot_before = tot_after = tot_flipped_off = 0
    for md_path in md_files:
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        if not chunks_path.exists():
            continue
        pdf_path = _resolve_pdf(md_path)
        spans = collect_pdf_spans(str(pdf_path))
        headings = PdfHeadingProvider(spans).headings()
        body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
        normalized = normalize_pipeline_text(body_text)
        candidates = candidates_with_offsets(normalized)
        profile = classify_profile(candidates)
        if profile != "B":
            continue

        before = _run(candidates, headings, default_registry, with_repetition=False)
        after = _run(candidates, headings, extended_registry, with_repetition=True)

        n_before = sum(before)
        n_after = sum(after)
        flipped_off = sum(1 for b, a in zip(before, after) if b and not a)

        name = md_path.stem.replace("_pdf", "")
        print(f"{name:<50} boundaries_before={n_before:>5} boundaries_after={n_after:>5} flipped_to_non_boundary={flipped_off:>4}")

        tot_before += n_before
        tot_after += n_after
        tot_flipped_off += flipped_off

    print()
    print(f"Profile B total: boundaries_before={tot_before} boundaries_after={tot_after} flipped_to_non_boundary={tot_flipped_off}")


if __name__ == "__main__":
    main()
