"""
core/hierarchical_chunk_builder.py — Hierarchical Chunk Builder prototype
(SPRINT33-D Phase 1).

Dormant module — not imported by core/chunking_optimizer.py, core/
processing.py, or any production path. Prototype only: measures how much
improvement core.semantic_boundary_detector's dormant Boundary Score model
would give a chunker, without replacing the real one (Pre-SPRINT33-D
Preflight scope: "production chunker replacement" is explicitly excluded
from SPRINT33-D).

Decision rule ("hierarchical" — semantic-first, length-fallback):
  1. A buffer shorter than min_chunk_size never flushes, regardless of any
     semantic signal (mirrors chunking_optimizer.py's own MIN_CHUNK_CHARS
     floor — avoids fragment chunks).
  2. Once the buffer meets min_chunk_size, a candidate flagged as a
     boundary by core.semantic_boundary_detector.score_boundary() flushes
     the buffer BEFORE that candidate is appended — the semantic signal is
     the primary split decision.
  3. If no semantic boundary appears and the buffer exceeds a safety cap
     (chunk_size * SAFETY_CAP_RATIO, the same 1.5x soft cap
     chunking_optimizer.py already uses as its effective upper bound), the
     buffer is force-flushed regardless of signal — this is the
     length-based fallback layer, so a semantic-boundary-blind stretch of
     text (e.g. a document the heading detector fails on, per SPRINT32-F's
     known "2 Kings, Volume 13" case) still produces bounded chunks.

Heading cursor management mirrors scripts/shadow_boundary_analysis.py's
established pattern (SPRINT33-C Phase 6-A/6-B): the cursor advances only
when HeadingBoundaryFeature's own raw signal fires, independent of the
aggregate is_boundary decision — consuming a heading and deciding to cut
here are different questions. That helper cannot be imported from
scripts/ (core/ must not depend on scripts/), so the same small primitive
is reproduced here from core.heading_provider's exported matching
functions — no new detection logic, same pattern already duplicated once
in scripts/shadow_boundary_analysis.py.

Known limitations inherited from Pre-SPRINT33-D Preflight
(docs/SPRINT33-D-preflight-issues.md), NOT addressed here:
  - PageHeaderArtifact not implemented — running-header repeats in
    WBC-style commentary can still register as semantic boundaries.
  - TinyFragment x Heading is Won't-fix at this layer — roughly half of
    tiny heading-matched candidates are OCR noise, indistinguishable from
    genuine short headings by the current feature vector.

Overlap is deliberately NOT applied here (Preflight decision #3) — this
prototype compares boundary POSITIONS only; overlap is a later concern if
this is ever promoted toward production.
"""

from __future__ import annotations

from typing import List, Tuple

from core.heading_provider import (
    ProviderHeading,
    _first_contained,
    _normalize_for_matching,
)
from core.semantic_boundary_detector import (
    BoundaryContext,
    HeadingBoundaryFeature,
    get_registry,
    score_boundary,
)

SAFETY_CAP_RATIO = 1.5

# Same lookahead window HeadingAssembler/HeadingBoundaryFeature use
# (core/heading_provider.py, core/semantic_boundary_detector.py).
_LOOKAHEAD_WINDOW = 5

_heading_feature = HeadingBoundaryFeature()


def _advance_heading_cursor(cursor: int, headings: List[ProviderHeading], key: str) -> int:
    """Mirrors HeadingAssembler.assign()'s cursor-advance step and
    scripts/shadow_boundary_analysis.py::_advance_cursor exactly — kept as
    a small local copy since core/ cannot import scripts/."""
    window = [
        _normalize_for_matching(h.text)
        for h in headings[cursor : cursor + _LOOKAHEAD_WINDOW]
    ]
    offset = _first_contained(window, key)
    if offset is None:
        return cursor
    return cursor + offset + 1


def build_chunks(
    candidates: List[Tuple[str, int]],
    headings: List[ProviderHeading],
    chunk_size: int,
    min_chunk_size: int,
) -> List[Tuple[str, int]]:
    """Builds shadow chunks from (candidate_text, start_offset) pairs —
    offsets are the caller's responsibility (e.g.
    scripts/shadow_boundary_delta.py::candidates_with_offsets) so this
    function stays pure and doesn't re-derive positions via substring
    search. Returns (chunk_text, start_offset) pairs; start_offset is the
    offset of the first candidate folded into that chunk."""
    registry = get_registry()
    safety_cap = int(chunk_size * SAFETY_CAP_RATIO)

    buf: List[str] = []
    buf_start: int = 0
    buf_len = 0
    cursor = 0
    chunks: List[Tuple[str, int]] = []

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            chunks.append(("\n\n".join(buf).strip(), buf_start))
        buf = []
        buf_len = 0

    for i, (text, offset) in enumerate(candidates):
        ctx = BoundaryContext(
            candidate_text=text,
            position=i,
            headings=headings,
            heading_cursor=cursor,
            accumulated_length=buf_len,
            chunk_size=chunk_size,
            min_chunk_size=min_chunk_size,
        )
        event = score_boundary(ctx, registry=registry)

        if _heading_feature.score(ctx) > 0:
            key = _normalize_for_matching(text)
            cursor = _advance_heading_cursor(cursor, headings, key)

        if buf and event.is_boundary and buf_len >= min_chunk_size:
            flush()

        if not buf:
            buf_start = offset
        buf.append(text)
        buf_len += len(text) + 2  # +2 accounts for the "\n\n" join separator

        if buf_len > safety_cap:
            flush()

    flush()
    return chunks
