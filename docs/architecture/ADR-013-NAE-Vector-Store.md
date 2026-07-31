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

- `nae_qdrant`/`nae_tsu_v*` 컬렉션은 `NAE/` 하위 파이프라인에서만 사용한다.
- `core/retrieval.py::RetrievalEngine`의 검색 경로에는 연결하지 않는다 —
  ADR-003의 migration policy를 그대로 준수한다.
- `qdrant-client`는 NAE 전용 의존성으로 `requirements.txt`에 추가한다.

### Collection 버저닝 정책 (Phase 3.5 Gate Review 반영, 2026-07-31)

컬렉션 이름은 `NAE.pipeline.tsu.config.TSU_SCHEMA_VERSION`에서 파생된다
(`nae_tsu_v{TSU_SCHEMA_VERSION}`, 현재 `nae_tsu_v1`). TSU 레코드 구조가
바뀔 때(필드 추가/제거/이름 변경) `TSU_SCHEMA_VERSION`을 올리면 자동으로
새 컬렉션(`nae_tsu_v2`)에 색인되며, 기존 컬렉션은 삭제하지 않고 그대로
남긴다 — 스키마가 섞인 payload가 한 컬렉션에 공존하는 것을 방지하고,
필요 시 이전 버전으로 rollback/audit이 가능하도록 한다.

동일한 이유로 embedding cache key(`NAE.pipeline.embed.hashing.tsu_hash`)에도
`schema_version`을 포함시켰다 — TSU 구조가 바뀌면 캐시도 자연히 무효화된다.

### 운영 (Docker Compose)

`NAE/docker-compose.yml`로 관리한다 (`restart: unless-stopped`, named volume
`nae_qdrant_storage`는 기존 볼륨을 그대로 재사용하도록 `external: true`로 선언):

```
cd NAE && docker compose up -d       # 시작
cd NAE && docker compose down        # 중지 (데이터는 볼륨에 유지)
cd NAE && docker compose logs -f     # 로그
```

---

## Consequences

- NAE corpus의 검색/벤치마크는 `nae_qdrant`(포트 7333)를 통해서만 이루어진다.
- DBMA 핵심 RAG(`RetrievalEngine`)의 production 경로·의존성에는 변화가 없다.
- 향후 NAE corpus를 `RetrievalEngine`의 production 경로에 통합하려면(예:
  Theology RAG Alpha 단계) 이 ADR을 개정하는 신규 ADR이 필요하다.
- ADR 번호 충돌 확인: 작성 시점 기준 `docs/architecture/`에 001–012(006 결번)까지
  존재, 013은 미사용 번호로 충돌 없음.

---

## Validation

```
docker ps --filter name=nae_qdrant
curl http://localhost:7333/collections
```
