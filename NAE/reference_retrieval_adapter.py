"""NAE reference corpus retrieval adapter (TSU-separated).

Provides `search_reference()` for querying the reference corpus
(`nae_ref_v1` collection) independently of the TSU pipeline.

Unlike `NAE/retrieval_adapter.py`, this module has NO `module_registry`
gate — it is always enabled because reference content is a "default
background knowledge" source, not an optional module.

Does NOT import `core.retrieval.RetrievalEngine` and is NOT imported by it.

SPRINT34-SMITH-PHASEB: Added timeout enforcement, exception categorization,
and deterministic return schema for fault isolation during Smith Bible
Dictionary integration.
"""
from __future__ import annotations

import logging
import hashlib
import re
import time
from typing import Any

import ollama

from NAE.pipeline.reference import config as ref_config

logger = logging.getLogger("nae.reference.retrieval_adapter")

# ── Timeout thresholds (seconds) ─────────────────────────────────────
_EMBEDDING_TIMEOUT_S = 5.0
_QDRANT_TIMEOUT_S = 5.0


class ReferenceRetrievalError(RuntimeError):
    """Base exception for reference retrieval failures."""
    pass


class EmbeddingTimeoutError(ReferenceRetrievalError):
    """Embedding step exceeded timeout."""
    pass


class QdrantConnectionError(ReferenceRetrievalError):
    """Qdrant connection/search failed."""
    pass


# ── 어휘(표제어·본문 단어) 검색 보강 ──────────────────────────────────────
# [2026-10-23] 의미(벡터) 검색만으로는 사전의 정답 항목이 상위에 오르지 않았다
# (실측: "계시록은 용의 정체를 어떻게 말하고 있나"에서 Smith의 [DRAGON] 항목 —
# "신약에서는 계시록에서만 '옛 뱀, 마귀, 사탄'에 쓰인다" — 이 빠지고 REVELATION OF
# ST. JOHN·EGYPT 항목이 잡혔다). 호출부가 lexical_terms를 주면 표제어/본문의 단어
# 일치로 매긴 순위와 벡터 순위를 RRF로 합친다. 컬렉션 본문은 프로세스당 한 번
# 읽어 메모리에 둔다(참고 컬렉션 합계 ~45k건).
_LEX_CACHE: dict[str, tuple[int, list[tuple[Any, dict, str, str]]]] = {}
_RRF_K = 60
_LEX_POOL = 20


def _lexical_rows(client, name: str) -> list[tuple[Any, dict, str, str]]:
    count = client.count(name, exact=False).count
    cached = _LEX_CACHE.get(name)
    if cached and cached[0] == count:
        return cached[1]
    rows: list[tuple[Any, dict, str, str]] = []
    offset = None
    while True:
        points, offset = client.scroll(
            name, limit=1000, offset=offset, with_payload=True, with_vectors=False
        )
        for p in points:
            payload = p.payload or {}
            text = str(payload.get("text", ""))
            heading = str(payload.get("heading_context", "")) or text[:80]
            rows.append((p.id, payload, heading.lower(), text.lower()))
        if offset is None:
            break
    _LEX_CACHE[name] = (count, rows)
    return rows


def _lexical_rank(rows, terms: list[str], limit: int) -> list[tuple[Any, dict]]:
    """표제어/본문 단어 일치 점수 순위. 드문 단어일수록 무겁게(IDF) — "revelation"처럼
    흔한 단어가 "dragon" 같은 핵심어를 묻어 버리지 않게 한다."""
    import math
    # "dragons"처럼 다른 용어를 포함하는 굴절형은 점수가 중복되지 않게 뺀다.
    base = [t for t in dict.fromkeys(terms) if not any(o != t and t.startswith(o) for o in terms)]
    n = max(1, len(rows))
    idf = {t: math.log(n / (1 + sum(1 for r in rows if t in r[3]))) for t in base}
    scored = []
    for pid, payload, heading, text in rows:
        s = 0.0
        for t in base:
            w = max(idf[t], 0.1)
            if t in heading:
                s += 3.0 * w
            if t in text:
                s += w * (1.0 + 0.3 * min(text.count(t), 5))
        if s > 0:
            scored.append((s, pid, payload))
    scored.sort(key=lambda x: -x[0])
    return [(pid, payload) for _s, pid, payload in scored[:limit]]


def _headword_hits(rows, terms: list[str], limit: int = 2) -> list[tuple[Any, dict]]:
    """질의어가 항목 표제어와 정확히 같은 청크(사전의 "DRAGON" 항목 등).

    사전 검색이라면 질문의 핵심어가 표제어인 항목은 반드시 보여야 한다. 표제어는 숫자·
    기호를 뺀 영문 철자로 비교한다("[316 DRAGON]" → "dragon"). 같은 표제어의 청크가
    여럿이면 질의어가 본문에 더 자주 나오는 것을 고른다.
    """
    base = [t for t in dict.fromkeys(terms) if not any(o != t and t.startswith(o) for o in terms)]
    found: list[tuple[int, Any, dict]] = []
    for pid, payload, heading, text in rows:
        key = re.sub(r"[^a-z]+", " ", heading).strip()
        for t in base:
            if key == t or key == t + "s":
                found.append((text.count(t), pid, payload))
                break
    found.sort(key=lambda x: -x[0])
    return [(pid, payload) for _c, pid, payload in found[:limit]]


class _Hit:
    """벡터/어휘 결과를 같은 모양(.payload, .score)으로 맞춘다."""
    def __init__(self, payload: dict, score: float) -> None:
        self.payload = payload
        self.score = score


def search_reference(
    query: str,
    top_k: int = 3,
    collection_names: list[str] | None = None,
    lexical_terms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search the reference corpus for the given query.

    Embeds `query` with bge-m3 and searches one or more Qdrant reference
    collections.  Returns the top-k most similar chunks overall (merged
    across collections and re-sorted by score when more than one is given).

    Fault isolation guarantees:
        - Embedding timeout → returns [] (never hangs)
        - Qdrant connection failure → returns [] (never raises)
        - Malformed response → returns [] (never crashes)
        - Deterministic return schema: always list[dict] with fixed keys

    Args:
        query: The search query text.
        top_k: Number of results to return (default 3).
        collection_names: Collections to search. Defaults to
            `[ref_config.REFERENCE_COLLECTION_NAME]` (Smith Bible
            Dictionary only) — existing callers see zero behavior change.
            Pass e.g. `list(ref_config.KNOWN_REFERENCE_COLLECTIONS)` to also
            search the Baptist commentary collection once it is populated.
        lexical_terms: Optional English words (소문자) for hybrid search — 표제어·
            본문 단어 일치 순위를 벡터 순위와 RRF로 합친다. None이면 기존과 동일.

    Returns:
        List of dicts with keys: text, source_id, volume, page_start,
        page_end, heading_context, chunk_index, content_type.
        Always returns a list — never raises an exception.
    """
    if not query or not query.strip():
        return []

    names = collection_names or [ref_config.REFERENCE_COLLECTION_NAME]

    # Embed the query with timeout
    content_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
    cached = _get_cached_embedding(content_hash)
    if cached is not None:
        query_vector = cached
    else:
        try:
            t0 = time.monotonic()
            client = ollama.Client(timeout=_EMBEDDING_TIMEOUT_S)
            result = client.embeddings(
                model=ref_config.DEFAULT_EMBED_MODEL,
                prompt=query,
            )
            elapsed_ms = (time.monotonic() - t0) * 1_000
            if elapsed_ms > _EMBEDDING_TIMEOUT_S * 800:
                logger.warning(
                    "[search_reference] embedding slow: %.0fms", elapsed_ms,
                )
            query_vector = result["embedding"]
            _save_cached_embedding(content_hash, query_vector)
        except TimeoutError as e:
            logger.error("[search_reference] embedding timeout (%.1fs): %s", _EMBEDDING_TIMEOUT_S, e)
            return []
        except ollama.ResponseError as e:
            logger.error("[search_reference] embedding API error: %s", e)
            return []
        except Exception as e:  # noqa: BLE001
            logger.error("[search_reference] embedding unexpected error: %s", e)
            return []

    # Search Qdrant with timeout — one or more collections, merged by score
    # [2026-10-23] 내장(로컬) 저장소가 준비돼 있으면 Docker 서버 없이 그것을 쓴다
    # (scripts/nae_reference_to_local.py). 로컬에 없는 컬렉션만 서버로 대체한다.
    from qdrant_client import QdrantClient
    from NAE import reference_local_store as local_store
    local = local_store.get_local_client()
    server = None

    scored_points = []
    for name in names:
        try:
            t0 = time.monotonic()
            if local is not None and local.collection_exists(name):
                results = local.query_points(
                    collection_name=name, query=query_vector, limit=top_k,
                )
            else:
                if server is None:
                    server = QdrantClient(url=ref_config.QDRANT_URL)
                results = server.query_points(
                    collection_name=name,
                    query=query_vector,
                    limit=top_k,
                    timeout=max(1, int(_QDRANT_TIMEOUT_S)),
                )
            elapsed_ms = (time.monotonic() - t0) * 1_000
            if elapsed_ms > _QDRANT_TIMEOUT_S * 800:
                logger.warning("[search_reference] Qdrant search slow (%s): %.0fms", name, elapsed_ms)
        except TimeoutError as e:
            logger.error("[search_reference] Qdrant timeout (%s, %.1fs): %s", name, _QDRANT_TIMEOUT_S, e)
            continue
        except ConnectionError as e:
            logger.error("[search_reference] Qdrant connection failed (%s): %s", name, e)
            continue
        except Exception as e:  # noqa: BLE001
            logger.error("[search_reference] Qdrant unexpected error (%s): %s", name, e)
            continue
        pts = list(results.points)
        if lexical_terms:
            try:
                lex_client = local if (local is not None and local.collection_exists(name)) else server
                lex = _lexical_rank(_lexical_rows(lex_client, name), lexical_terms, _LEX_POOL)
                pts = _fuse(pts, lex)
                # 표제어가 질의어와 정확히 같은 항목은 맨 앞에 둔다.
                head = _headword_hits(_lexical_rows(lex_client, name), lexical_terms)
                if head:
                    top = max((p.score for p in pts), default=0.0) + 1.0
                    seen = {id(p.payload) for p in pts}
                    pts = [_Hit(pl, top - i * 1e-3) for i, (_pid, pl) in enumerate(head)] + [
                        p for p in pts
                        if not any(p.payload is pl for _pid, pl in head)
                    ]
            except Exception as e:  # noqa: BLE001 — 어휘 보강 실패는 벡터 결과만 쓴다
                logger.warning("[search_reference] lexical boost failed (%s): %s", name, e)
        scored_points.extend(pts)

    if not scored_points:
        return []

    scored_points.sort(key=lambda p: p.score, reverse=True)

    # Format results — deterministic schema
    output = []
    for point in scored_points[:top_k]:
        payload = point.payload or {}
        output.append({
            "text": payload.get("text", ""),
            "source_id": payload.get("source_id", ""),
            "volume": payload.get("volume", ""),
            "page_start": payload.get("page_start"),
            "page_end": payload.get("page_end"),
            "heading_context": payload.get("heading_context", ""),
            "chunk_index": payload.get("chunk_index"),
            "content_type": payload.get("content_type", "reference_dictionary"),
        })

    logger.info(
        "[search_reference] query=%r collections=%s top_k=%d → %d results",
        query[:50], names, top_k, len(output),
    )
    return output


def _fuse(vector_points: list, lexical: list[tuple[Any, dict]]) -> list:
    """벡터 순위와 어휘 순위를 RRF로 합쳐 (.payload, .score) 목록으로 돌려준다."""
    fused: dict[Any, list] = {}
    for rank, p in enumerate(vector_points):
        fused[p.id] = [1.0 / (_RRF_K + rank), p.payload or {}]
    for rank, (pid, payload) in enumerate(lexical):
        if pid in fused:
            fused[pid][0] += 1.0 / (_RRF_K + rank)
        else:
            fused[pid] = [1.0 / (_RRF_K + rank), payload]
    return [_Hit(payload, score) for score, payload in fused.values()]


def _get_cached_embedding(content_hash: str) -> list[float] | None:
    """Get a cached embedding from the embed cache."""
    from NAE.pipeline.embed import client as embed_client
    return embed_client.get_cached(content_hash)


def _save_cached_embedding(
    content_hash: str, vector: list[float],
) -> None:
    """Save an embedding to the embed cache."""
    from NAE.pipeline.embed import client as embed_client
    from NAE.pipeline.reference import config as ref_config
    embed_client._save_cache(content_hash, vector, ref_config.DEFAULT_EMBED_MODEL)
