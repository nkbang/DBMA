---
title: "ADR-020: NAE Incremental Ingestion Architecture v1"
category: architecture
based_on:
  - docs/architecture/ADR-013-NAE-Vector-Store.md
  - docs/architecture/ADR-014-NAE-Modern-Corpus-Layer.md
  - docs/architecture/ADR-015-NAE-Corpus-Ingestion-Standard.md
  - docs/NAE_CORPUS_INGESTION_STANDARD_v1.md
  - docs/NAE_TSU_4107_EXPANSION_STATE.md
created: 2026-08-11
scope: NAE/pipeline/ingest/, scripts/nae_incremental_ingest.py — 신규 실행 계층. 기존 corpus/review/embed/index 코드 무수정
---

# ADR-020: NAE Incremental Ingestion Architecture v1

| | |
|---|---|
| Status | Approved |
| Date | 2026-08-11 |
| Approved | 2026-08-11 (Rev. Bang 작업명령 승인) |
| Deciders | Rev. Bang, CUE |
| Supersedes | — (execution configuration, 기존 ADR과 충돌 없음) |
| Extends | ADR-013(NAE Vector Store), ADR-014/015(Ingestion Standard, 설계 단계) |
| Superseded by | — |

---

## 1. Context

Batch 24–36 Promotion(1,271건, commit `a330642`)과 BGE-M3 embedding(commit
`74b28d6`, Qdrant `nae_tsu_v1` 1,281 points)이 GREEN checkpoint(tag
`nae-batch24-36-green-checkpoint`)로 확정된 시점에서, Rev. Bang이 향후 신규
공공 신학 자료 추가 시 **기존 Production 3,319 verified TSU + 1,281
embedded vector를 전체 재처리하지 않고 증분 처리**할 수 있는 아키텍처를
요구했다.

Phase 1 READ-ONLY 감사 결과:

- `NAE_CORPUS_INGESTION_STANDARD_v1.md`(2026-08-02, 설계 단계·미구현)가
  정의하는 "Registration → Validation → ... → TSU" 파이프라인의 **앞단
  (신규 원문 발견/등록/OCR/최초 TSU 생성)은 아직 코드로 구현되어 있지
  않다.** 이번 ADR은 그 앞단을 새로 만들지 않는다.
- TSU 스키마에는 이미 identity 계층에 필요한 필드(`author_id`, `work_id`,
  `edition_id`, `source_id`/`source_identifier`)가 존재한다 — 새 필드
  추가 없이 재사용 가능.
- `NAE.pipeline.embed.client.embed_text()`는 이미 `content_hash` 파일명
  캐시로 재-embedding을 방지하지만, 캐시 파일의 `model`을 요청 model과
  대조하지 않는다 — model 교체 시 stale 캐시를 그대로 쓸 위험이 있었다.
- `NAE.pipeline.index.indexer.index_all()`은 corpus 전체(모든 identifier,
  모든 verified TSU)를 매번 재스캔·재embedding 판단하는 구조 — "새/변경만"
  개념이 없다. Batch 1–23의 2,038건이 Batch 24–36 Promotion 이후에도
  전혀 embedding되지 않은 채 남아있던 사실(Qdrant 10 points vs verified
  3,319건)이 이를 실측으로 뒷받침한다.

## 2. Decision

`NAE/pipeline/ingest/` 패키지를 신설해 **TSU 레코드가 이미 존재하는
시점부터**(identity 확정 이후) 증분 처리를 담당하게 한다:

```
NEW/CHANGED/UNCHANGED 판정(content hash)
        ↓
Processing State 추적(성공/실패 독립 보존)
        ↓
Incremental Embedding(model+dimension까지 확인하는 SKIP/EMBED)
        ↓
Incremental Indexing(Qdrant upsert-only, 기존 vector 보존)
        ↓
Production Manifest(경량 요약, 매 실행마다 generation 갱신)
```

`index_all()`은 코드를 수정하지 않고 그대로 유지하되, **역할을 정상 실행
경로에서 reconciliation/recovery/audit 전용으로 재정의**한다(문서 및
`NAE/pipeline/index/indexer.py` 모듈 docstring 참고 — 함수 시그니처
변경 없음, 새 호출자(CLI)가 이 함수를 정상 경로에 쓰지 않을 뿐).

## 3. Identity Model (Phase 2)

```
Author(author_id) → Work(work_id) → Edition(edition_id) → Source File(source_file_id) → TSU(tsu_id)
```

Batch 번호는 identity가 아니다 — `batch_manager.py`의 pool-front 슬라이스는
Promotion마다 재계산되는 processing unit일 뿐이므로, 같은 TSU가 다른 배치
번호를 가질 수 있다(`NAE/pipeline/ingest/identity.py`).

## 4. Content Hash / Idempotency (Phase 3)

기존 `NAE.pipeline.embed.hashing.tsu_hash()`(schema_version+claim+book+
page+scriptures)를 그대로 재사용한다 — 새 해시 알고리즘을 만들지 않는다.
`NAE/pipeline/ingest/content_hash.py`가 이 해시를 상태 저장소의 마지막
기록과 비교해 NEW/UNCHANGED/CHANGED로 분류한다.

## 5. Processing State (Phase 4)

`NAE/pipeline/ingest/state.py::ProcessingState` — `DISCOVERED` ~
`INDEXED` 정상 경로 9단계 + `VALIDATION_FAILED`/`HUMAN_REVIEW_REQUIRED`/
`EMBEDDING_FAILED`/`INDEX_FAILED` 4개 실패 상태. 상태 저장소는 Production
TSU 파일과 완전히 분리된 별도 JSON(`NAE/pipeline/ingest/state/
incremental_state.json`)이다 — Production 레코드 스키마에 필드를 추가하지
않는다. 실패한 레코드가 다른 레코드의 재처리를 유발하지 않는다(레코드별
독립 상태).

## 6. Incremental Embedding (Phase 5)

`NAE/pipeline/ingest/embedding.py`가 `embed_text()`의 content_hash 캐시
위에 model 일치 여부까지 확인하는 계층을 추가한다: 캐시가 있어도 캐시
파일에 기록된 `model`이 요청 `model`과 다르면 EMBED로 재분류한다. 현재
설정: `model=bge-m3:latest`, `dimension=1024`(변경 없음).

## 7. Incremental Indexing (Phase 6)

`NAE/pipeline/ingest/indexing.py`가 embedding까지 끝난 (record, vector)
쌍만 Qdrant에 upsert한다. Vector lifecycle: `ACTIVE`(신규 추가) /
`REPLACED`(같은 tsu_id point 재upsert) / `DELETED`(Production에서 사라진
tsu_id — 이번 v1은 자동 삭제하지 않고 후속 명시적 조치 대상으로만 정의).

## 8. `index_all()`의 역할 재정의 (Phase 9)

| | 정상 실행 경로 | Reconciliation/Recovery/Audit |
|---|---|---|
| 이전 | `index_all()` | — |
| 이후 | `scripts/nae_incremental_ingest.py`(NEW/CHANGED만 처리) | `index_all()`(corpus 전체 재스캔, 변경 없음) |

`index_all()` 함수 자체는 코드 변경 없이 그대로 남는다 — 이번 ADR은
"언제 쓰는가"만 재정의한다.

## 9. Checkpoint vs Production Manifest (Phase 10)

- **Historical checkpoint**(`NAE/review/human/checkpoints/*/`, 예:
  `nae-batch24-36-green-checkpoint`): 특정 작업 시점의 불변 snapshot(파일
  전체 사본). 한 번 만들면 다시 만들지 않는다.
- **Production Manifest**(`NAE/pipeline/ingest/manifest.py`,
  `NAE/pipeline/ingest/manifests/manifest_gen{NNNN}.json`): 현재 상태의
  경량 요약(카운트+해시, claim/source_text 본문 미포함). 매 incremental
  실행마다 새 generation으로 갱신 가능 — 전체 corpus를 복사하지 않는다.

## 10. CLI (Phase 11)

```
python scripts/nae_incremental_ingest.py --identifier <identifier> --dry-run   # 기본값, 아무것도 쓰지 않음
python scripts/nae_incremental_ingest.py --identifier <identifier> --apply     # 명시적으로만 실행
```

dry-run 출력은 `NEW/CHANGED/UNCHANGED/SKIP/EMBED/INDEX` 카운트를 포함한다.

## 11. 기존 Baseline (변경 금지, ADR-020이 고정)

```
Verified Production: 3,319 TSU (Batch 1-23: 2,038 + Batch 24-36: 1,271 + Pilot 001: 10)
Batch 24-36: 1,271 TSU, GATE=GREEN
BGE-M3 embedded: 1,281 vectors (Pilot 001 10 + Batch 24-36 1,271)
Deferred: Batch 1-23의 2,038건(embedding 미실행, 별도 후속 작업)
Qdrant nae_tsu_v1: 1,281 points, dimension=1024, distance=Cosine
Immutable checkpoint: nae-batch24-36-green-checkpoint (tag, commit dda0dab)
```

이 숫자들은 이번 아키텍처 구현의 편의를 위해 변경되지 않았다 — 모든 테스트는
격리된 fixture/fake client로 수행했다(§12).

## 12. Consequences

**긍정적**:
- 신규 자료 투입 시 기존 3,319건 재처리 없이 새/변경분만 처리 가능
- embedding 재계산을 model/dimension 변경 시에만 강제해 불필요한 Ollama
  호출 방지
- `index_all()`은 disaster recovery/reconciliation 용도로 보존되어 안전망
  기능 유지

**제약/후속 과제**:
- 신규 원문 발견→등록→OCR→최초 TSU 생성 파이프라인은 이번 ADR 범위 밖 —
  `NAE_CORPUS_INGESTION_STANDARD_v1.md`(설계 단계)가 구현되면 그 출력을
  이 패키지에 연결한다.
- `VectorLifecycle.DELETED`는 정의만 하고 자동 삭제 로직은 구현하지
  않았다 — Production에서 TSU가 제거되는 경우(현재 발생하지 않음)는 별도
  ADR/작업명령이 필요하다.
- Batch 1-23의 2,038건 embedding backlog는 이번 아키텍처로 처리 가능하지만
  실행은 별도 승인 대상이다(§11).

## 13. Compliance

- ADR-001(RetrievalEngine 유일 정본): 무영향 — 이 패키지는 Qdrant에만
  쓰고 `core/retrieval.py`를 호출하지 않는다.
- ADR-013(NAE Vector Store 분리): 무영향 — `NAE/pipeline/index/config.py`의
  `QDRANT_URL`/`COLLECTION_NAME`을 그대로 재사용, legacy `dbma_sermon`과
  분리 유지.
- Dataset Isolation Rule: 무영향 — `--dataset-path` 자동 추론을 하지
  않고, CLI가 `--identifier`를 명시적으로 요구한다(§2 절대 금지 "dataset
  path 자동 추론"과 일치).
