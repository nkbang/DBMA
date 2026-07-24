"""
scripts/shadow_d5_single_feature_ratio.py — D-5 Gate §3(b) measurement:
what fraction of detected boundaries were judged by exactly one
non-zero-weight feature (a false-positive risk signal per
ADR-007 §3(b))?

Diagnostic/analysis artifact only — NOT part of the production pipeline.
core/ must never import this module. Reuses the same corpus loop as
scripts/shadow_d5_metrics.py so results are directly comparable to the
already-confirmed Axis 1/2/3 numbers.

Usage:
    python scripts/shadow_d5_single_feature_ratio.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from shadow_boundary_analysis import MD_DIR, _extract_body_text, _resolve_pdf
from shadow_boundary_delta import candidates_with_offsets
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider, ProviderHeading, _normalize_for_matching
from core.hierarchical_chunk_builder import SAFETY_CAP_RATIO, _advance_heading_cursor
from core.semantic_boundary_detector import BoundaryContext, get_registry, score_boundary
from core.text_normalizer import normalize_pipeline_text
from core.config import DEFAULT_CHUNK_SIZE

SAFETY_CAP = int(DEFAULT_CHUNK_SIZE * SAFETY_CAP_RATIO)


def _boundary_feature_counts(
    headings: List[ProviderHeading], candidates: List[Tuple[str, int]]
) -> Tuple[int, int]:
    """Returns (total_boundaries, single_feature_boundaries)."""
    registry = get_registry()
    cursor = 0
    total = 0
    single = 0
    for i, (text, offset) in enumerate(candidates):
        ctx = BoundaryContext(candidate_text=text, position=i, headings=headings, heading_cursor=cursor)
        event = score_boundary(ctx, registry=registry)
        if event.is_boundary:
            total += 1
            nonzero = [v for v in event.features.values() if v != 0.0]
            if len(nonzero) == 1:
                single += 1
            key = _normalize_for_matching(text)
            cursor = _advance_heading_cursor(cursor, headings, key)
    return total, single


def classify_profile(candidates: List[Tuple[str, int]]) -> str:
    return "B" if any(len(text) > SAFETY_CAP for text, _ in candidates) else "A"


def main() -> None:
    md_files = sorted(MD_DIR.glob("*_pdf.md"))
    rows = []
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
        total, single = _boundary_feature_counts(headings, candidates)
        profile = classify_profile(candidates)
        rows.append((md_path.stem.replace("_pdf", ""), profile, total, single))

    print(f"{'document':<40} {'profile':>7} {'boundaries':>10} {'single-feature':>14} {'ratio':>7}")
    for name, profile, total, single in rows:
        ratio = single / total if total else 0.0
        print(f"{name:<40} {profile:>7} {total:>10} {single:>14} {100*ratio:>6.1f}%")

    for profile in ("A", "B"):
        subset = [r for r in rows if r[1] == profile]
        if not subset:
            continue
        tot = sum(r[2] for r in subset)
        sing = sum(r[3] for r in subset)
        print()
        print(f"=== Profile {profile} aggregate ({len(subset)} docs) ===")
        print(f"  single-feature-only ratio: {sing}/{tot} = {100*sing/tot if tot else 0:.1f}%")


if __name__ == "__main__":
    main()
