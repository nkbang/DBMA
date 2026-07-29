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

Level 3 (Hard Fallback, ADR-008 제안 2, 2026-07-22 구현): Level 1/2가
flush한 청크가 그래도 safety_cap을 넘는 경우(Axis 3 "unsplittable
outlier" — 문장/공백 경계가 거의 없는 색인·용어집류 콘텐츠에서 발생)
word-safe hard slice로 추가 분할한다. `_slice_preserving_words()`는
`core/chunking_optimizer.py::_slice_preserving_words()`와 동일한 알고리즘을
**독립적으로 재구현**한 것 — Amendment A 원칙(production의 private
함수를 직접 import하지 않음)을 지킨다. 이 계층에서 쪼개진 조각들은
모두 그 청크의 원래 buf_start를 그대로 공유한다(shadow 측정 목적상
정확한 조각별 오프셋 재계산은 하지 않음 — 이 프로토타입은 아직 실제
인용/오프셋을 생성하지 않는다).

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

import re
import statistics
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

# [ADR-008 §4, 2026-07-23] Signal-Profile threshold (ADR-007 Amendment A) —
# replaces the earlier provisional rule ("any single candidate exceeds
# chunk_size * SAFETY_CAP_RATIO"), which classified a whole document off one
# outlier candidate and had a documented boundary-case risk (Amendment-A.md
# §리스크). Median candidate length was validated against the full Beta
# corpus (12 documents, 2026-07-23 measurement) and cleanly separates the two
# profiles with no overlap: Profile A (Low Back-matter Density) 132~184
# chars, Profile B (High Back-matter Density, academic commentary) 269~856
# chars. 220 sits in the gap. (Two alternative signals — citation-parenthetical
# ratio and BIBLIOGRAPHY-classification ratio via core.noise_classifier —
# separated just as cleanly in the same measurement but were not chosen,
# since median length needs no additional per-candidate classification pass.)
MEDIAN_CANDIDATE_LENGTH_THRESHOLD = 220


def classify_document_profile(candidates: List[Tuple[str, int]]) -> str:
    """[ADR-008 §4] Returns "A" (Low Back-matter Density) or "B" (High Back-
    matter Density) per ADR-007 Amendment A's Signal-Profile calibration.
    Empty candidates -> "A" (no signal; a conservative default rather than
    raising, matching how build_chunks() itself never raises on empty
    input)."""
    if not candidates:
        return "A"
    median_length = statistics.median(len(text) for text, _ in candidates)
    return "B" if median_length > MEDIAN_CANDIDATE_LENGTH_THRESHOLD else "A"


def _slice_preserving_words(s: str, max_len: int) -> List[str]:
    """Level 3 Hard Fallback (ADR-008 제안 2) — word-safe hard slice.
    Independent reimplementation of core/chunking_optimizer.py's
    `_slice_preserving_words()` (same algorithm) — Amendment A forbids
    importing production's private functions, so this is duplicated
    rather than shared. Falls back to a true hard slice only if a single
    "word" (no whitespace at all — e.g. an unbroken Hebrew/Greek run)
    itself exceeds max_len."""
    tokens = re.split(r"(\s+)", s)
    pieces: List[str] = []
    buf = ""
    for tok in tokens:
        if len(buf) + len(tok) <= max_len:
            buf += tok
        else:
            if buf.strip():
                pieces.append(buf.strip())
            if len(tok) > max_len:
                for i in range(0, len(tok), max_len):
                    pieces.append(tok[i : i + max_len].strip())
                buf = ""
            else:
                buf = tok
    if buf.strip():
        pieces.append(buf.strip())
    return [p for p in pieces if p]


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

    # [Task Order 016 Phase 1] Profile A/B 분류 — 버퍼에 Profile B 동적
    # 임계값을 적용하기 위해 candidates를 받은 후 바로 1회 분류한다.
    document_profile = classify_document_profile(candidates)

    buf: List[str] = []
    buf_start: int = 0
    buf_len = 0
    cursor = 0
    chunks: List[Tuple[str, int]] = []

    def flush() -> None:
        nonlocal buf, buf_len
        if buf:
            joined = "\n\n".join(buf).strip()
            if len(joined) > safety_cap:
                # Level 3 Hard Fallback — Level 1(semantic)/Level 2(safety
                # cap) still produced an oversized chunk (Axis 3
                # unsplittable outlier: no sentence/whitespace boundary
                # inside the run to flush on earlier). Slice word-safe
                # rather than emit an unbounded chunk.
                for piece in _slice_preserving_words(joined, safety_cap):
                    chunks.append((piece, buf_start))
            else:
                chunks.append((joined, buf_start))
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
            # [ADR-008 제안 3] EmbeddingSimilarityBoundaryFeature용 — 현재
            # 버퍼의 마지막 후보. 버퍼가 비어 있으면(문서/청크 시작
            # 직후) 빈 문자열, feature는 0.0으로 폴백한다.
            previous_candidate_text=buf[-1] if buf else "",
            # [Task Order 016 Phase 1] Profile A/B 분류 결과 —
            # EmbeddingSimilarityBoundaryFeature가 동적 임계값에 사용
            document_profile=document_profile,
        )
        event = score_boundary(ctx, registry=registry, document_profile=document_profile)

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
