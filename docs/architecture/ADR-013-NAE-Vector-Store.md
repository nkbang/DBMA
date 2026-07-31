---
title: "ADR-013: NAE Vector Store (Independent Qdrant Instance)"
category: architecture
based_on:
  - docs/architecture/ADR-003-Legacy-Vector-Store-Strategy.md
created: 2026-07-31
scope_modified: NAE/ (new subsystem), docs/architecture/ only
---

# ADR-013: NAE Vector Store (Independent Qdrant Instance)

| | |
|---|---|
| Status | Accepted |
| Date | 2026-07-31 |
| Deciders | 사용자 승인 (Phase 4 진행 승인 시) |
| Supersedes | — |
| Superseded by | — |

---

## Context

ADR-003은 다음을 확정했다:

> No production dependency may be added to Chroma/Qdrant without new ADR approval.

이 제약은 `core/retrieval.py::RetrievalEngine`의 production 검색 경로를 대상으로
한다 — RetrievalEngine은 TSU dataset + in-memory 유사도 검색을 사용하며,
Chroma `dbmar_docs`/Qdrant `dbma_sermon`은 legacy artifact로 보존만 된다.

NAE(신학 문헌 corpus builder, `NAE/` 하위)는 `core/`와 완전히 분리된 별도
서브시스템이다. Phase 4(BGE-M3 벡터 인덱싱)에서 TSU(Theological Semantic
Unit) 레코드를 임베딩하고 검색 가능한 형태로 저장할 필요가 발생했다.

---

## Decision

### 새 Qdrant 인스턴스 (기존 legacy와 완전 분리)

```
Container name:  nae_qdrant       (기존 legacy: dbma_qdrant, qdrant)
Ports:           7333 (REST), 7334 (gRPC)   (기존 legacy: 6333)
Docker volume:   nae_qdrant_storage         (기존 legacy: dbma_qdrant_storage)
Collection:      nae_tsu
```

기존 `dbma_qdrant`/`dbma_sermon` 컨테이너·볼륨·컬렉션은 이 작업 중 시작/조회/
수정하지 않았다 — ADR-003이 legacy artifact로 규정한 상태를 그대로 유지한다.

### Scope 제약

- `nae_qdrant`/`nae_tsu` 컬렉션은 `NAE/` 하위 파이프라인에서만 사용한다.
- `core/retrieval.py::RetrievalEngine`의 검색 경로에는 연결하지 않는다 —
  ADR-003의 migration policy를 그대로 준수한다.
- `qdrant-client`는 NAE 전용 의존성으로 `requirements.txt`에 추가한다.

---

## Consequences

- NAE corpus의 검색/벤치마크는 `nae_qdrant`(포트 7333)를 통해서만 이루어진다.
- DBMA 핵심 RAG(`RetrievalEngine`)의 production 경로·의존성에는 변화가 없다.
- 향후 NAE corpus를 `RetrievalEngine`의 production 경로에 통합하려면(예:
  Theology RAG Alpha 단계) 이 ADR을 개정하는 신규 ADR이 필요하다.

---

## Validation

```
docker ps --filter name=nae_qdrant
curl http://localhost:7333/collections
```
