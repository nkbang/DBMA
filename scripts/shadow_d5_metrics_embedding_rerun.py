"""
scripts/shadow_d5_metrics_embedding_rerun.py — ADR-008 제안 3 (Embedding
Similarity Boundary Feature) 도입 후 Axis 1/2/3 재측정.

Diagnostic/analysis artifact only — NOT part of the production pipeline.
scripts/shadow_d5_metrics.py의 Phase 3-A 방법론을 그대로 재사용하되,
core.semantic_boundary_detector의 module-level registry singleton에 등록된
EmbeddingSimilarityBoundaryFeature의 embed_fn을 텍스트별 캐싱 래퍼로
교체해서 실행한다 — 캐싱 없이 그대로 돌리면 문서당 최대 9천 개
candidate가 경계 판정마다 이전/현재 후보를 각각 재임베딩해 실행이
비현실적으로 느려진다(같은 텍스트가 반복적으로 "이전 후보"로도, "현재
후보"로도 재사용되므로 캐싱은 순수 성능 최적화일 뿐 측정 결과에는
영향 없음).

Profile B(학력 밀도 낮은 학술 주석서 — ADR-008 §1이 "임베딩 feature 개선
필요"로 판정한 대상) 4개 문서로 범위를 좁혀 실행한다: 나머지 Profile A
8개 문서는 Axis 2가 이미 임계값을 충족한 상태라 이번 결정에 영향을
주지 않는다(ADR-008 §1 참고).

Usage:
    python scripts/shadow_d5_metrics_embedding_rerun.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_MIN_CHUNK_SIZE, EMBEDDING_SIMILARITY_WEIGHT
from core.embedder import get_embedder

_real_embed = get_embedder().embed
from core.heading_provider import ProviderHeading, _normalize_for_matching
from core.hierarchical_chunk_builder import SAFETY_CAP_RATIO, _advance_heading_cursor, build_chunks
from core.semantic_boundary_detector import (
    BoundaryContext,
    EmbeddingSimilarityBoundaryFeature,
    get_registry,
    score_boundary,
)

import shadow_d5_metrics as d5
from shadow_boundary_analysis import _extract_body_text, _resolve_pdf
from shadow_boundary_delta import TOLERANCE, candidates_with_offsets, chunk_start_offsets, nearest_distance
from core.extractors import collect_pdf_spans
from core.heading_provider import PdfHeadingProvider
from core.text_normalizer import normalize_pipeline_text


def _boundary_offsets_with_prev_text(headings, candidates):
    """[ADR-008 제안 3 재측정, 2026-07-21] shadow_d5_metrics.py의
    _boundary_offsets()는 BoundaryContext에 previous_candidate_text를
    채우지 않아 EmbeddingSimilarityBoundaryFeature가 이 경로에서는 항상
    0.0으로 죽는다(build_chunks() 내부는 정상 연결됨 — 측정 스크립트만의
    간극). Phase 3-A의 frozen 산출물(scripts/shadow_d5_metrics.py)은
    수정하지 않고, 이 재측정 스크립트 안에서만 buf[-1] 추적을
    build_chunks()와 동일한 방식으로 재현한다."""
    registry = get_registry()
    cursor = 0
    out = []
    buf: list[str] = []
    buf_len = 0
    safety_cap = int(DEFAULT_CHUNK_SIZE * SAFETY_CAP_RATIO)

    for i, (text, offset) in enumerate(candidates):
        ctx = BoundaryContext(
            candidate_text=text,
            position=i,
            headings=headings,
            heading_cursor=cursor,
            accumulated_length=buf_len,
            previous_candidate_text=buf[-1] if buf else "",
        )
        event = score_boundary(ctx, registry=registry)
        if event.is_boundary:
            out.append(offset)
            key = _normalize_for_matching(text)
            cursor = _advance_heading_cursor(cursor, headings, key)

        # buf 추적은 build_chunks()의 실제 흐름(경계 판정 시 flush,
        # min_chunk_size 미달이면 유지, safety_cap 초과 시 강제 flush)을
        # 그대로 재현 — previous_candidate_text가 build_chunks()와
        # 동일한 값이 되도록 하는 목적일 뿐, 여기서 청크를 만들지는 않음.
        if buf and event.is_boundary and buf_len >= DEFAULT_MIN_CHUNK_SIZE:
            buf = []
            buf_len = 0
        buf.append(text)
        buf_len += len(text) + 2
        if buf_len > safety_cap:
            buf = []
            buf_len = 0

    return sorted(out)


def _analyze_document_fixed(md_path, chunks_path):
    """d5.analyze_document()와 동일하지만 _boundary_offsets_with_prev_text
    를 사용 — 나머지(Axis3, shadow_chunks 등)는 원본 로직 그대로."""
    pdf_path = _resolve_pdf(md_path)
    spans = collect_pdf_spans(str(pdf_path))
    headings = PdfHeadingProvider(spans).headings()

    body_text = _extract_body_text(md_path.read_text(encoding="utf-8"))
    normalized = normalize_pipeline_text(body_text)
    candidates = candidates_with_offsets(normalized)

    boundary_offsets = _boundary_offsets_with_prev_text(headings, candidates)
    existing_offsets = sorted(chunk_start_offsets(chunks_path, normalized))
    shadow_chunks = build_chunks(candidates, headings, DEFAULT_CHUNK_SIZE, DEFAULT_MIN_CHUNK_SIZE)
    shadow_offsets = sorted(o for _, o in shadow_chunks)
    boundary_offset_set = set(boundary_offsets)

    orphaned_before = [b for b in boundary_offsets if nearest_distance(b, existing_offsets) > TOLERANCE]
    recovered = [b for b in orphaned_before if nearest_distance(b, shadow_offsets) <= TOLERANCE]
    semantic_flushes = sum(1 for o in shadow_offsets if o in boundary_offset_set)
    outliers = d5.unsplittable_outliers(candidates)

    return d5.DocMetrics(
        name=md_path.stem.replace("_pdf", ""),
        profile=d5.classify_profile(candidates),
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

PROFILE_B_DOC_STEMS = [
    "2 Chronicles_ Volume 15 _Word Biblical Commentary_ _Raymond B. Dillard__pdf",
    "2 Kings The Anchor Bible Commentary _Mordechai Cogan and Hayim Tadmor__pdf",
    "2 Kings The Power and the Fury _Dale Ralph Davis _Davis_ Dale Ralph__pdf",
    "2 Kings_ Volume 13 _David Allen Hubbard_ Glenn W. Barker etc.__pdf",
]


def _cached_embed():
    cache: dict[str, list] = {}

    def _embed(text: str):
        if text not in cache:
            cache[text] = _real_embed(text)
        return cache[text]

    return _embed


def main() -> None:
    registry = get_registry()
    registry.register(
        "embedding_similarity",
        EmbeddingSimilarityBoundaryFeature(embed_fn=_cached_embed()),
        weight=EMBEDDING_SIMILARITY_WEIGHT,
    )

    md_files = [d5.MD_DIR / f"{stem}.md" for stem in PROFILE_B_DOC_STEMS]
    results = []
    for md_path in md_files:
        if not md_path.exists():
            print(f"SKIP (not found): {md_path.name}")
            continue
        chunks_path = md_path.with_name(md_path.stem + "_chunks.txt")
        if not chunks_path.exists():
            print(f"SKIP (no chunks file): {md_path.name}")
            continue
        print(f"analyzing: {md_path.name} ...", flush=True)
        m = _analyze_document_fixed(md_path, chunks_path)
        results.append(m)
        print(
            f"  profile={m.profile} recovery={m.recovery_rate:.1%} "
            f"semantic_flush={m.semantic_flush_ratio:.1%} "
            f"outlier={m.unsplittable_outlier_ratio:.1%}",
            flush=True,
        )

    if not results:
        print("no Profile B documents found/measured")
        return

    total_recovered = sum(m.recovered for m in results)
    total_orphaned = sum(m.orphaned_before for m in results)
    total_flushes = sum(m.semantic_flushes for m in results)
    total_chunks = sum(m.shadow_chunks for m in results)
    total_outliers = sum(m.unsplittable_outliers for m in results)
    total_candidates = sum(m.candidates for m in results)

    print("\n=== Profile B 집계 (임베딩 feature 도입 후) ===")
    print(f"Axis 1 recovery:        {total_recovered}/{total_orphaned} = "
          f"{total_recovered / total_orphaned if total_orphaned else 0.0:.1%}")
    print(f"Axis 2 semantic flush:  {total_flushes}/{total_chunks} = "
          f"{total_flushes / total_chunks if total_chunks else 0.0:.1%}")
    print(f"Axis 3 outlier:         {total_outliers}/{total_candidates} = "
          f"{total_outliers / total_candidates if total_candidates else 0.0:.1%}")
    print("\n(Phase 3-A 이전 수치: Axis1=99.0%, Axis2=16.4%, Axis3=5.5%)")


if __name__ == "__main__":
    main()
