# NAE Batch 1–23 Backlog Embedding — 최종 종합 보고서

**작성일**: 2026-08-12
**대상**: Batch 1–23 BGE-M3 embedding/indexing backlog, 2,038건
**관련 커밋**: `413eb43`(ADR-020) → `7083c58`(Optional Module Packaging) → `cc78781`(버그 수정+실행) → `1e338af`(checkpoint) → `78f59ca`(evidence)
**최종 GATE**: **GREEN**

---

## 1. 배경

Batch 24–36 Promotion(1,271건, commit `a330642`) 이후, NAE Incremental Ingestion Architecture v1(ADR-020)을 통해 Qdrant `nae_tsu_v1`을 조회한 결과 벡터가 **10개(Pilot 001)뿐**임이 드러났다. 당시 `verified` TSU는 3,319건이었으므로, **Batch 1–23에서 이미 verified된 2,038건이 한 번도 embedding되지 않은 채 남아있었다**(Promotion과 embedding이 별개 단계라는 사실이 이 시점까지 인지되지 않았던 운영 공백).

```
verified 3,319
  - Batch 24-36 Promotion분 1,271 (이번 세션에서 embedding 완료)
  - Pilot 001 10 (이미 embedding됨)
  - Batch 1-23 backlog 2,038 (미embedding, 이번 보고서의 대상)
```

## 2. 작업 순서

```
ADR-020 Incremental Ingestion Architecture (GREEN, C1 3회 감사·정정)
  → 전체 회귀 2,118 passed(무제한 timeout) 완주
  → NAE Optional Module Packaging v1 (DBMA Core/NAE 경계 명문화)
  → Batch 1-23 backlog(2,038건) embedding 실행
  → 실행 중 버그 2건 발견·수정
  → 재실행 성공, 전체 회귀 2,120 passed 재확인
  → nae-batch1-23-backlog-embedding-checkpoint 생성
  → C1 독립 감사(GREEN/HOLD) → CUE 재확인(ID 단위) → CUE Evidence Package
```

## 3. 실행 내역

`scripts/nae_incremental_ingest.py --identifier <corpus> --apply`(ADR-020 incremental 경로, `index_all()` 미사용)를 Dagg → Hiscox 순서로 실행했다.

| Corpus | 대상 | 신규 embedding | 오류 |
|---|---|---|---|
| Dagg_Church_Order | 2,958건 verified 중 미embedding분 | 1,682 | 0 |
| Hiscox_Standard_Manual | 361건 verified 중 미embedding분 | 356 | 0 |
| **합계** | | **2,038** | **0** |

## 4. 실행 중 발견·수정한 버그 2건

두 버그 모두 **첫 실행 시도 중 실측으로 발견**되었으며, Production 데이터 오염 없이 즉시 원인 규명 후 수정했다.

### 4.1 Qdrant HTTP payload 크기 제한

Dagg 1,682건 벡터를 한 번의 `upsert()` 호출로 보내려다 36.4MB(제한 33.5MB)로 요청이 **원자적으로 거부**됨 — Qdrant는 1,281 그대로 유지, 부분 오염 없음. `NAE/pipeline/ingest/indexing.py`에 `UPSERT_BATCH_SIZE=100` 배치 처리를 추가해 해결.

### 4.2 SKIP 레코드의 vector 유실 (재시도 시 0건 색인)

1차 시도에서 embedding 자체(Ollama 호출 + 캐시 기록)는 전부 성공했으나 upsert만 실패했다. 재시도 시 모든 레코드가 캐시 hit(SKIP)으로 분류되는데, 기존 코드는 SKIP 레코드의 vector를 반환하지 않아 색인 단계가 이들을 아예 받지 못해 `indexed_count=0`이 반복되는 문제가 있었다. `NAE/pipeline/ingest/embedding.py`에서 SKIP이어도 `embed_client.get_cached()`로 vector를 채워 반환하도록 수정. 재발방지 회귀테스트(`TestEmbedSucceedsIndexFailsRetry`) 추가.

*(부수적으로, 두 버그 사이의 한 차례 실행에서 상태 저장소(`NAE/pipeline/ingest/state/incremental_state.json`, git 미추적 로컬 런타임 파일)가 "색인 안 됐는데 INDEXED로 기록"되는 오염이 발생 — 삭제 후 수정된 코드로 재생성해 해결. Production 파일에는 영향 없음.)*

## 5. 최종 검증 — 4개 층위

### 5.1 CUE 실측 (실행 직후)

```
Dagg: 1281 → 2963 (+1682)
Hiscox: 2963 → 3319 (+356)
Production TSU/exception_queue hash: 전 구간 무변경
전체 회귀: 2120 passed / 0 failed (2118+신규2)
Validator: source 89/0/0, authority 128/26/0
```

### 5.2 C1 독립 감사 (모델 `qwen3.6:35b-DBMAcode` 고정, 4차 시도 만에 방법론 정합)

```
Changeset cc78781/1e338af: VERIFIED
버그 수정 2건: PASS
Incremental tests: 25/25 passed
Qdrant points_count: 3,319 (직접 조회)
Verified Production TSU: 3,319 (직접 재계산)
Incremental delta: 1,281 + 2,038 = 3,319 — PASS
Target ID: target=2038 / missing=0 / duplicate=0 / unexpected=0
Checkpoint hash: 3/3 MATCH
Production mutation: 0
Source/Authority/Manifest Validator: FAIL=0 (3개 전부)
Full Regression: INCOMPLETE/TIMEOUT(30초 제한, 감사 도구 자체의 시간 제약)

FINAL GATE: GREEN / HOLD
```

### 5.3 CUE 독립 재확인 (C1 결과와 별도로, ID 집합 단위까지 심화 검증)

C1은 "개수가 2,038"까지 확인했으나, CUE는 한 단계 더 나아가 **Qdrant의 실제 point ID 3,319개를 전부 나열**하고, `output/final_human_review_candidate.json` + Pilot 10건으로 기존 1,281 ID 집합을 재구성해 다음을 증명했다:

```
기존 1,281개 ID: 전부 Qdrant에 여전히 존재(훼손·삭제 없음)
신규로 추가된 ID: 정확히 2,038개
1,281 + 2,038 = 3,319 (개수뿐 아니라 ID 단위로 일치)
```

이는 "총량만 우연히 맞고 중간에 다른 것이 섞였을 가능성"을 배제하는 검증이다.

### 5.4 CUE Evidence Package (commit `78f59ca`)

`output/batch1_23_backlog_embedding_evidence.json/md`(gitignore, 로컬 산출물) — 위 5.3의 계산을 재현 가능한 스크립트(`scripts/generate_backlog_embedding_evidence.py`)로 고정. 추가로 `index_all()`(`NAE/pipeline/index/indexer.py`) 코드가 Batch 24-36 checkpoint 이후 전혀 수정되지 않았음을 `git diff`로 확인 — 이번 작업이 순수하게 incremental 경로만 사용했음을 코드 레벨로 증명.

## 6. Full Regression 최종 상태

C1 감사에서는 도구 자체의 30초 제한으로 `INCOMPLETE`였으나, **CUE가 별도로 무제한 timeout으로 2회 완주**했다:
- ADR-020 완료 직후: 2,118 passed / 0 failed (165초)
- Backlog embedding 완료 직후: 2,120 passed / 0 failed (165초)

## 7. Immutable Checkpoint

```
checkpoint_id: NAE-BATCH1-23-BACKLOG-EMBEDDING-CHECKPOINT-001
경로: NAE/review/human/checkpoints/batch1_23_backlog_embedding_checkpoint/
git tag: nae-batch1-23-backlog-embedding-checkpoint (commit 1e338af)
Production Manifest generation: 2 (total_vectors=3319, corpus_hash 불변 — TSU 내용 자체는 무변경)
```

`NAE/corpus/tsu/` 바깥에 위치시켜 `indexer.index_all()`이 corpus identifier로 오인하지 않도록 했다(Batch 24 스냅샷 오염 사고 재발 방지 원칙 재적용).

## 8. 최종 판정

```
NAE BATCH 1-23 BACKLOG EMBEDDING — FINAL REPORT

Scope: 2,038 TSUs (Dagg 1,682 + Hiscox 356)
Embedding errors: 0
Bugs found and fixed during execution: 2 (Qdrant payload batching, SKIP-vector retry loss)

Qdrant nae_tsu_v1: 1,281 → 3,319 points
  - 기존 1,281 ID 전부 보존: PASS
  - 신규 ID 정확히 2,038: PASS
  - 1,281 + 2,038 = 3,319 (ID 단위 증명): PASS

Production mutation: 0 (TSU/decisions/exception_queue/checkpoint 전부)
Checkpoint integrity: PASS
Full Regression: PASS (2,120 passed / 0 failed, 무제한 timeout 2회 완주)
Validator: PASS (source 89/0/0, authority 128/26/0, manifest 128/10/0)
Reconciliation tests: 25/25 passed

Verification layers:
  1. CUE 실행 기록: PASS
  2. C1 독립 감사(모델 고정, 4차 정정 완료): GREEN/HOLD → HOLD 사유(regression timeout) CUE가 별도 해소
  3. CUE 독립 재확인(ID 집합 단위): PASS
  4. CUE Evidence Package: READ_ONLY_EVIDENCE_COMPLETE_PASS

FINAL GATE: GREEN
```

## 9. NAE 현재 전체 상태 (2026-08-12 기준)

```
Verified TSU: 3,319 (Dagg 2,958 + Hiscox 361)
Embedded/Indexed: 3,319 / 3,319 (100%)
Qdrant nae_tsu_v1: 3,319 points, dim=1024, distance=Cosine
Generated(미검토): 776 (Dagg 397 + Hiscox 379)
Rejected: 22
남은 embedding 작업: 없음
```

## 10. 다음 단계 (미착수, 별도 지시 필요)

- Generated 상태 776건(Dagg 397 + Hiscox 379)의 Human Review — 이번 작업 범위 밖
- NAE Optional Module(`nae_pd`) 실제 활성화 및 DBMA 배포 반영 여부 결정
- 신규 공공 신학 자료 ingestion (ADR-020 incremental 경로로 처리 가능, 실행은 별도 승인 필요)
