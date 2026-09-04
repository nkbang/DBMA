# Phase 5.1 ADR Linkage — Read-only Forensic

## ADR-003 (DBMA Core Retrieval 보호)

```
$ grep -rn "core\.retrieval\|core/retrieval\|import chromadb\|from chromadb" NAE/
NAE/benchmark/evaluator.py:3:      (주석) "RetrievalEngine를 직접 호출하지 않음." — 설계 의도를 명시한 주석, import 아님
NAE/pipeline/index/config.py:6:    (주석) "core/retrieval.py::RetrievalEngine's production query path." — ADR-013 근거 설명 주석, import 아님
```

`core.retrieval` 실제 import 0건, `chromadb` import 0건. 두 매치 모두 코드가 아니라 설계
의도를 명시한 주석문이다.

**판정**: `core/retrieval.py`를 import·수정·직접 호출하지 않음 — source-level 확인.

## ADR-013 (NAE Vector Store 독립 운영)

```
$ docker ps --filter name=nae_qdrant --format "{{.Names}} {{.Ports}}"
nae_qdrant   0.0.0.0:7333->6333/tcp, 0.0.0.0:7334->6334/tcp

$ docker ps -a --filter name=dbma_qdrant --format "{{.Names}} {{.Status}}"
dbma_qdrant   Exited (143) 6 days ago

$ docker volume ls | grep qdrant
local     dbma_qdrant_storage
local     nae_qdrant_storage

$ curl -s http://localhost:7333/collections
{"result":{"collections":[{"name":"nae_tsu_v1"}]},"status":"ok"}
```

- 포트 분리 확인: NAE=7333/7334, legacy dbma_qdrant=6333(현재 정지 상태 — ADR-003이 규정한
  "보존된 legacy artifact" 상태와 일치, 실행 중일 필요 없음).
- 볼륨 분리 확인: `nae_qdrant_storage` ≠ `dbma_qdrant_storage`, 별도 named volume.
- 컬렉션 버저닝 확인: `nae_tsu_v1`(TSU_SCHEMA_VERSION 파생 명명 — `NAE/pipeline/tsu/config.py`
  `TSU_SCHEMA_VERSION = "1"`과 `NAE/pipeline/index/config.py`의 `COLLECTION_NAME = f"nae_tsu_v{TSU_SCHEMA_VERSION}"`
  일치 확인).

```
$ grep -n "VECTOR_SIZE" NAE/pipeline/index/config.py
25:VECTOR_SIZE = 1024  # bge-m3:latest

$ grep -n "EMBED_DIMENSION" NAE/pipeline/embed/config.py
12:EMBED_DIMENSION = 1024
```

**판정**: BGE-M3 embedding dimension(1024)과 Qdrant collection vector size(1024) 일치 확인.

## 종합 판정

| 항목 | 상태 |
|---|---|
| `core/retrieval.py` 미침범 | `VERIFIED` |
| Chroma persistence 미공유 | `VERIFIED` |
| NAE Qdrant host/port/volume/namespace 독립 | `VERIFIED` |
| Collection version / TSU schema version 명시 | `VERIFIED` |
| Docker Compose가 DBMA Core volume/path와 충돌 없음 | `VERIFIED` (별도 named volume) |
| `nae_tsu_v1` 버전 명명 실존 | `VERIFIED` |
| BGE-M3 dimension = Qdrant vector size | `VERIFIED` (1024 = 1024) |

이번 forensic review 범위 내에서 ADR-003, ADR-013 위반 증거는 발견되지 않았다. 단, 이는
Phase 5 인프라 코드(committed + uncommitted 포함) 전체에 대한 판정이며, 아직 존재하지 않는
Phase 5.2 Retriever 컴포넌트에 대해서는 해당하지 않는다(존재하지 않는 코드는 검증 대상이
될 수 없음).
