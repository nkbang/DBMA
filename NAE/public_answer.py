"""공개 자료 근거 답변 (ADR-036 방안 B, Proposed).

"내서재 공개 자료(Beta)" 패널이 가져온 문단 근거(`bridge_query_paragraphs`)만으로
**별도의** 답변을 생성한다. 내 서재 답변과 병합하지 않고(ADR-024 §B), 근거·인용·고지·
경고를 각각 따로 둔다. 이 모듈은 다음을 하지 않는다.

- 검색 엔진·랭킹 변경 (Retrieval Engine 무변경, ADR-001)
- 저장소 쓰기 — Qdrant 조회는 색인 범위 요약용 읽기 전용 scroll 1회뿐이고
  `dbma_qdrant`(6333)에는 접근하지 않는다 (ADR-013, ADR-024 §H)
- 새 스위치 추가 — 게이트는 `modules.nae_pd.enabled` 하나(호출부 UI가 확인, ADR-024 §F)
- `ui/pages/chat.py`의 `generate_answer` 경로 참조 — 그쪽은 브리지를 참조하지 않는다는
  `tests/test_nae_f6_chat_wiring.py::TestNoMergeIntoGeneration` 가드를 그대로 유지한다.

생성은 기존 `core.generation.GenerationService`를 그대로 재사용한다(근거 강제 지시문,
오염 문자 처리, ClaimGuard, FU-003 인용 검증기 포함) — 여기서는 근거 패키지만 만든다.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.retrieval import (
    CitationBuilder,
    ParsedQuery,
    PerformanceMetrics,
    RankedCandidate,
    ResponsePackage,
    _format_context_source_label,
)
from NAE.citation_disclosure import get_disclosure

logger = logging.getLogger("nae.public_answer")

# 생성 컨텍스트에 넣는 근거 문단 수 상한(고유 문단 기준). ADR-036 §3 "N은 구현 시 결정".
# 채팅의 기본 k(5)와 같은 값 — 32k 컨텍스트에서 문단(수백~수천 자) 5개는 여유가 있다.
MAX_EVIDENCE = 5
# 문단 하나가 비정상적으로 길 때 컨텍스트를 잠식하지 않도록 자르는 상한(자).
MAX_PARAGRAPH_CHARS = 3000

QUERY_ID = "nae-public-answer"

NO_EVIDENCE_TEXT = (
    "공개 자료에서 이 질문에 답할 근거를 찾지 못했습니다. "
    "이 답변은 검색된 공개 자료 문단에만 근거하므로, 근거가 없으면 답변을 만들지 않습니다."
)
SEARCH_FAILED_TEXT = (
    "공개 자료 검색이 실패해(시간 초과 또는 오류) 답변을 만들지 않았습니다. "
    "결과가 없다는 뜻이 아닙니다. 잠시 후 다시 검색해 주세요."
)


def _hit_key(hit: dict) -> tuple[Any, Any]:
    bib = hit.get("bibliography") or {}
    return (bib.get("identifier"), bib.get("paragraph_index"))


def select_evidence(hits: list[dict], max_items: int = MAX_EVIDENCE) -> list[dict]:
    """답변에 쓸 근거 히트를 고른다: 문단 본문이 있는 것만, 같은 문단(identifier+
    문단 번호)은 한 번만, 검색 순서를 유지해 상위 `max_items`개."""
    seen: set[tuple[Any, Any]] = set()
    chosen: list[dict] = []
    for hit in hits or []:
        if not isinstance(hit, dict):
            continue
        text = (hit.get("evidence_paragraph") or "").strip()
        if not text:
            continue
        key = _hit_key(hit)
        if key[0] is not None and key[1] is not None:
            if key in seen:
                continue
            seen.add(key)
        chosen.append(hit)
        if len(chosen) >= max_items:
            break
    return chosen


def _candidate_from_hit(hit: dict) -> RankedCandidate:
    bib = hit.get("bibliography") or {}
    work = bib.get("work")
    metadata = {
        "author": bib.get("author"),
        "title": work,
        "book": work,
        "source_file": bib.get("identifier"),
        "page": bib.get("page_start"),
        "paragraph": bib.get("paragraph_index"),
    }
    score = float(hit.get("retrieval_score") or 0.0)
    text = (hit.get("evidence_paragraph") or "").strip()[:MAX_PARAGRAPH_CHARS]
    return RankedCandidate(
        tsu_id=str(hit.get("tsu_id") or ""),
        content=text,
        metadata=metadata,
        vector_score=score,
        final_score=score,
        explanation=f"NAE Qdrant vector search (score={score:.4f})",
    )


def build_public_evidence_package(
    question: str, hits: list[dict], max_items: int = MAX_EVIDENCE
) -> ResponsePackage | None:
    """근거 히트로 `GenerationService`가 받는 `ResponsePackage`를 만든다.

    사용할 근거가 하나도 없으면 None — 호출자는 생성하지 않고 보류 문구를 보여준다
    (일반 지식만으로 답을 만들지 않는다는 ADR-036 수용 기준 AC-3).
    """
    chosen = select_evidence(hits, max_items)
    if not chosen:
        return None
    candidates = [_candidate_from_hit(h) for h in chosen]

    blocks: list[str] = []
    for c in candidates:
        label = _format_context_source_label(c.metadata)
        source_line = f"출처: {label}\n" if label else ""
        blocks.append(
            f'<context id="{c.tsu_id}" score="{c.final_score:.4f}">\n'
            f"{source_line}{c.content}\n</context>\n"
        )

    return ResponsePackage(
        query_id=QUERY_ID,
        question=question,
        candidates=candidates,
        top_k_results=candidates,
        performance_metrics=PerformanceMetrics(),
        parsed_query=ParsedQuery(original_query=question, intent="unknown"),
        llm_context_block="\n".join(blocks),
        citations=CitationBuilder().build_citations(candidates),
    )


def public_disclosures(hits: list[dict]) -> list[str]:
    """답변에 쓰인 근거 소스별 고지문(중복 제거). ADR-030 Amendment A §6 —
    `historical_witness` 자료를 인용하는 영역에는 소스에 맞는 고지가 있어야 한다."""
    out: list[str] = []
    for hit in hits:
        bib = hit.get("bibliography") or {}
        text = get_disclosure(
            hit.get("authority_class"),
            identifier=bib.get("identifier"),
            author=bib.get("author"),
            work=bib.get("work"),
        )
        if text and text not in out:
            out.append(text)
    return out


# ── 색인 범위 요약 ──────────────────────────────────────────────────────
# 답변이 "어느 자료를 검색했는지"를 항상 밝힌다(EUAT-03·04: 인덱스에 없는 자료를 물으면
# 사용자가 "자료에 없다"와 "검색 범위 밖"을 구분할 수 없었다). 하드코딩하지 않고
# 실제 인덱스에서 읽는다 — 재인덱싱으로 범위가 바뀌어도 문구가 맞는다.
_SCOPE_TTL_S = 600.0
_scope_cache: dict[str, Any] = {"at": 0.0, "value": None}


def _read_indexed_sources() -> list[str] | None:
    """`nae_tsu_v1`에 실제로 색인된 (저자 — 문헌) 목록. 읽기 전용 scroll. 실패하면 None."""
    try:
        from NAE.pipeline.index import config as index_config
        from NAE.pipeline.index import qdrant_store

        client = qdrant_store.get_client()
        seen: dict[str, None] = {}
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=index_config.COLLECTION_NAME,
                limit=1000,
                offset=offset,
                with_payload=["author", "book"],
                with_vectors=False,
            )
            for p in points:
                pl = p.payload or {}
                author = (pl.get("author") or "").strip()
                book = (pl.get("book") or "").strip()
                label = f"{author} — {book}" if author and book else (author or book)
                if label:
                    seen.setdefault(label, None)
            if offset is None:
                break
        return sorted(seen)
    except Exception:  # noqa: BLE001 — 표시용 부가 정보. 실패해도 답변 경로는 계속
        logger.warning("[public_answer] 색인 범위 조회 실패 — 범위 문구 생략", exc_info=True)
        return None


def indexed_sources(now: float | None = None) -> list[str] | None:
    """`_read_indexed_sources()` 결과를 10분간 캐시한다."""
    t = time.monotonic() if now is None else now
    if _scope_cache["value"] is not None and t - _scope_cache["at"] < _SCOPE_TTL_S:
        return _scope_cache["value"]
    value = _read_indexed_sources()
    if value is not None:
        _scope_cache["value"] = value
        _scope_cache["at"] = t
    return value


def scope_note(sources: list[str] | None) -> str | None:
    """검색 범위 문구. 범위를 알 수 없으면 None(거짓 문구를 만들지 않는다)."""
    if not sources:
        return None
    listed = "; ".join(sources)
    return (
        f"검색 범위: 공개 신학 자료 중 현재 색인된 자료 — {listed}. "
        "색인되지 않은 자료는 검색·인용되지 않으며, 이 경우 '자료에 없다'는 뜻이 아니라 "
        "'검색 범위 밖'입니다."
    )
