"""NAE optional retrieval adapter (NAE-OPTIONAL-MODULE-PACKAGING-001).

`core/retrieval.py::RetrievalEngine`(ADR-001 유일 정본, "One Pipeline,
One Config, One Retrieval Engine, One Execution State")을 수정하지 않는다
— `RetrievalEngine`은 이 모듈을 import하지 않고, 이 모듈도 `RetrievalEngine`
을 import하지 않는다. 이 파일은 `nae_pd` module이 enabled일 때만 **호출하는
쪽**(예: 향후 UI 탭, 별도 스크립트)이 명시적으로 불러 쓰는 독립 adapter다.

DBMA Core retrieval 경로에 자동으로 끼워 넣지 않는다 — "명시적 module
boundary를 통해서만 접근"(지시서 §6) 원칙.

ADR-024 (NAE Production Retrieval Bridge) 구현: bridge_query()가
query_text → embedding → NAE Qdrant search → Citation 리스트의
전체 파이프라인을 책임진다.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import ollama

from core import module_registry

logger = logging.getLogger("nae.retrieval_adapter")

# ── ADR-024 §G: timeout / warn thresholds ──────────────────────────
_HARD_TIMEOUT_MS = 3_000  # hard timeout (milliseconds) — enforced at client level
_WARN_THRESHOLD_MS = 1_500  # warn threshold (milliseconds)


class NaePdModuleDisabledError(RuntimeError):
    pass


def _check_deadline(deadline: float) -> None:
    """deadline을 초과했으면 TimeoutError를 던진다."""
    remaining_ms = (deadline - time.monotonic()) * 1_000
    if remaining_ms <= 0:
        raise TimeoutError(
            f"[bridge_query] hard timeout exceeded ({-remaining_ms:.0f}ms overdue)"
        )


def search(query_vector: list[float], *, top_k: int = 10, limit_check: bool = True,
           remaining_timeout_s: float = 3.0) -> list[dict[str, Any]]:
    """`nae_pd` module이 비활성화 상태면 예외를 던진다 — DBMA Core
    retrieval 경로가 실수로 이 함수를 호출해도 NAE corpus/index에
    접근하지 않는다.

    NOTE: qdrant-client v0.13+에서 `client.search()` 메서드가 제거되어
    `client.query_points()`로 변경됨. 이는 ADR-024 §D(무수정)의 범위를
    벗어난 수정이지만, qdrant-client의 breaking change에 의한 필수 대응임.

    변경 사유:
      - qdrant-client 0.13.0+에서 `search()` 메서드가 deprecated 후 제거됨
      - `query_points(query=..., limit=..., with_payload=...)`가 공식 대체 API
      - 직접 확인: `dir(qdrant_client.QdrantClient)`에 `search` 없음, `query_points` 있음
    """
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError("nae_pd module is disabled — enable via `scripts/dbma_module.py enable nae_pd` first")

    from NAE.pipeline.index import qdrant_store, config as index_config

    client = qdrant_store.get_client()
    response = client.query_points(
        collection_name=index_config.COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
        timeout=max(1, int(remaining_timeout_s)),  # ADR-024 §G: 남은 deadline 기준 (최소 1초)
        with_payload=True,
    )
    return [{"tsu_id": h.payload.get("tsu_id"), "score": h.score, "payload": h.payload} for h in response.points]


# ── ADR-024 §C: NAE payload → Citation metadata mapping ────────────

def _map_nae_to_citation_metadata(hit: dict[str, Any]) -> dict[str, Any]:
    """NAE Qdrant hit payload를 CitationBuilder.build_citations()가
    기대하는 RankedCandidate.metadata dict로 변환한다.

    매핑 (ADR-024 §C 표 기준):
      tsu_id          → tsu_id            (직접)
      source_author   → author            (직접)
      retrieval_score → hit.score         (직접)
      source_type     → source_type       (직접)
      content_excerpt → source_text[:200] (직접)
      scripture_ref   → paragraph/sentence (CitationBuilder가 verse_mapping
                                      으로 처리 — 여기선 verse_mapping
                                      에 book_id/chapter/verse_start 채움)
      source_title    → f"{book} by {author}" (근사 합성)
      document_id     → work_id           (근사 대체)
      evidence_conf   → metadata_provenance (근사 대체)
      source_file     → source_id         (근사 대체)
      language        → source_text ASCII 판별 (근사 추론)
    """
    payload = hit["payload"]

    # scripture_reference용 verse_mapping — CitationBuilder가 이 구조를 읽음
    paragraph = payload.get("paragraph")
    sentence = payload.get("sentence")
    book = payload.get("book")
    verse_mapping: dict[str, Any] = {}
    if book and paragraph is not None:
        verse_mapping["book_id"] = str(book)
        verse_mapping["chapter"] = str(paragraph)
        verse_mapping["verse_start"] = str(sentence) if sentence is not None else "?"

    # source_title 합성 (NAE에는 title 필드가 없음)
    author = payload.get("author") or ""
    book_display = book or "Unknown Work"
    source_title = f"{book_display} by {author}" if author else str(book_display)

    # evidence_confidence 근사 — metadata_provenance 또는 overall_score
    provenance_raw = payload.get("metadata_provenance")
    if isinstance(provenance_raw, dict) and "confidence" in provenance_raw:
        evidence_confidence = provenance_raw["confidence"]
    else:
        # fallback: overall_score 또는 llm_score
        evidence_confidence = payload.get("overall_score") or payload.get("llm_score")

    # language 추론 — source_text가 ASCII면 "en", 아니면 "ko" 또는 "la" 등
    source_text = payload.get("source_text") or ""
    language = "en" if source_text and source_text.isascii() else None

    return {
        "tsu_id": payload.get("tsu_id"),
        "author": author,
        "book": book,
        "verse_mapping": verse_mapping,
        "title": source_title,
        "document_id": payload.get("work_id"),
        "provenance": {"confidence": evidence_confidence} if evidence_confidence is not None else {},
        "source_file": payload.get("source_id"),
        "language": language,
        "source_type": payload.get("source_type"),
        "content_excerpt": (payload.get("source_text") or "")[:200],
        # Canonical IDs (ADR-017 준수)
        "source_id": payload.get("source_id"),
        "work_id": payload.get("work_id"),
        "edition_id": payload.get("edition_id"),
        "metadata_provenance": provenance_raw,
    }


# ── ADR-024 §D: bridge_query() contract ────────────────────────────

def bridge_query(
    query_text: str,
    *,
    top_k: int = 10,
    limit_check: bool = True,
) -> list[Any]:
    """query_text(자연어) → embedding → NAE Qdrant search → Citation 리스트.

    module gate(limit_check)를 통과하지 못하면 NaePdModuleDisabledError.
    Qdrant/Ollama 장애 시 §G(fail-closed)에 따라 빈 리스트 반환, 예외를
    호출자까지 전파하지 않는다(단, module-disabled 예외는 예외로 남긴다).

    Returns:
        list[Citation] — core/retrieval.py::Citation 객체 리스트.
                          Qdrant 장애 시 [].
    """
    # §D: module gate
    if limit_check and not module_registry.is_enabled("nae_pd"):
        raise NaePdModuleDisabledError(
            "nae_pd module is disabled — enable via `scripts/dbma_module.py enable nae_pd` first"
        )

    # §G: hard timeout 시작 (클라이언트 레벨 timeout 적용)
    deadline = time.monotonic() + _HARD_TIMEOUT_MS / 1_000  # convert ms → s for monotonic addition

    # Ollama client with actual httpx timeout (not module-level ollama.embeddings())
    ollama_client = ollama.Client(timeout=_HARD_TIMEOUT_MS / 1_000)

    try:
        # 1. embedding (Ollama BGE-M3) — client-level timeout으로 실제 hang 차단
        _check_deadline(deadline)
        t0 = time.monotonic()
        vector = ollama_client.embeddings(model="bge-m3:latest", prompt=query_text)["embedding"]
        embed_ms = (time.monotonic() - t0) * 1_000

        # §G: hard timeout 체크 (embedding 후)
        _check_deadline(deadline)

        # §G: warn threshold 체크
        if embed_ms > _WARN_THRESHOLD_MS:
            logger.warning(
                "[bridge_query] embedding warn: %.0fms > %dms threshold",
                embed_ms, _WARN_THRESHOLD_MS,
            )

        # 2. NAE Qdrant search (read-only) — 남은 deadline 기준으로 timeout 계산
        remaining_s = max(0.5, deadline - time.monotonic())
        _check_deadline(deadline)
        t1 = time.monotonic()
        hits = search(vector, top_k=top_k, limit_check=False, remaining_timeout_s=remaining_s)
        search_ms = (time.monotonic() - t1) * 1_000

        # §G: hard timeout 체크 (search 후)
        _check_deadline(deadline)

        total_ms = embed_ms + search_ms
        if total_ms > _WARN_THRESHOLD_MS:
            logger.warning(
                "[bridge_query] total latency warn: %.0fms > %dms threshold",
                total_ms, _WARN_THRESHOLD_MS,
            )

        if not hits:
            return []

        # 3. NAE payload → RankedCandidate mapping (§C)
        from core.retrieval import CitationBuilder, RankedCandidate

        candidates: list[RankedCandidate] = []
        for h in hits:
            meta = _map_nae_to_citation_metadata(h)
            candidate = RankedCandidate(
                tsu_id=h["tsu_id"],
                content=meta.get("content_excerpt", ""),
                metadata=meta,
                vector_score=h["score"],
                bm25_score=0.0,
                theological_score=0.0,
                passage_score=0.0,
                final_score=h["score"],
                explanation=f"NAE Qdrant vector search (score={h['score']:.4f})",
            )
            candidates.append(candidate)

        # 4. CitationBuilder integration (§C) — 수정 없이 호출
        citations = CitationBuilder().build_citations(candidates)
        return citations

    except NaePdModuleDisabledError:
        raise  # 설정 오류 — 전파

    except Exception:  # Qdrant/Ollama 장애 — §G fail-closed
        logger.exception("[bridge_query] NAE retrieval failed (fail-closed)")
        return []
