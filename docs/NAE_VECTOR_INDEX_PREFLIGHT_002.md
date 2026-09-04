# NAE Vector Index Preflight 002 — Pilot 001 Verified 10건 기준 재확인

**작성일:** 2026-08-09
**성격:** DESIGN + READ-ONLY AUDIT ONLY. **실제 Embedding/Qdrant 실행 없음.**
**Authority:** `docs/NAE_VECTOR_INDEX_PREFLIGHT_DESIGN_001.md`(1차, verified=0 시점),
`docs/NAE_VECTOR_PAYLOAD_CONTRACT_IMPLEMENTATION_REPORT_001.md`(Payload Contract),
`docs/NAE_PILOT_001_REMEDIATION_EXECUTION_REPORT_001.md`(verified 10건 확정)
**Git Commit/Push:** 미수행.

---

## 배경

1차 Preflight(`NAE_VECTOR_INDEX_PREFLIGHT_DESIGN_001.md`) 시점에는
`verified=0`이라 "Embedding 실행 조건 자체가 안 됨"으로 결론났다. 이후
Pilot 001 Human Review Gate가 완료되어 **verified 10건**이 실제로
존재하는 지금, 동일한 Preflight를 다시 수행해 실행 가능 여부를
재확인한다.

---

## Phase 1 — Review Gate 상태(재확인)

```
$ indexer.index_all(dry_run=True)
{'processed': 6, 'indexed': 10,
 'identifiers': [{'Hiscox_Standard_Manual': 5 indexed}, {'Dagg_Church_Order': 5 indexed}, ...]}
```

```
generated: 4107
verified:  10  (TSU-0000025/0000033/0000199/0000330/0000713/
                 0003524/0003525/0003647/0003661/0003893)
eligible:  10  (Review Gate 통과)
indexed:   0   (아직 실제 Embedding/Qdrant 실행 안 함, dry_run만 확인)
```

**우회 경로 없음**(기존 검증 유지) — `indexer.py`가 항상
`load_records_with_gate_summary()`를 거침.

---

## Phase 2 — Qdrant 컬렉션 상태(재확인)

```
$ client.get_collections() -> ['nae_tsu_v1']
$ client.get_collection('nae_tsu_v1').points_count -> 0
```

컬렉션은 이미 존재(1024차원, Cosine) — Pilot 001 전체 기간 동안
**한 번도 실제로 쓰기가 일어나지 않았다**(points_count=0 그대로).
`nae_qdrant`(포트 7333/7334) vs legacy `qdrant`(6333) 물리적 분리
재확인.

---

## Phase 3 — Payload Contract 실증 검증(10건 전수)

`qdrant_store.build_point()`를 dummy vector(`[0.0]*1024`, 실제 임베딩
아님)로 실제 verified 10건 전부에 대해 호출:

```
TSU-0000025 ~ TSU-0003893 (10건): payload_field_ok=True(전부)
review_status: verified(10/10)
tsu_access: full(10/10 — 전부 public_domain 자료)
metadata_schema_version: 1.1.0(10/10)
```

`load_records()`가 Review Gate를 거쳐 반환한 레코드만 사용했으므로
(=verified 10건만), payload 구성 자체가 실제 Qdrant/Embedding 클라이언트를
호출하지 않고도 10/10 정상 검증됨.

---

## Phase 4 — Embedding 설정 재확인

```
모델: bge-m3:latest — Ollama에 설치 확인됨(1.2GB)
캐시: NAE/corpus/embeddings/cache/ — 0개 파일(아직 미실행, 정상)
TSU ID -> Qdrant point ID 매핑: 10건 전부 충돌 없음
  (TSU-0000025->25, TSU-0000033->33, ..., TSU-0003893->3893)
```

이전 Preflight(001)에서 지적한 WARNING(model version pin 없음,
batch/timeout/retry 미문서화)은 그대로 유효 — 이번 재확인에서 해소되지
않았음을 재확인(변경 없음, 재차 WARNING으로 기록).

---

## Phase 5 — Architecture Boundary(재확인)

```
$ git diff --stat core/retrieval.py core/tsu_builder.py
(출력 없음 — 0줄 변경)
```

Pilot 001 전체 사이클(Migration → Payload Contract → Human Review Gate →
Promotion → Remediation) 동안 `core/retrieval.py`, `core/tsu_builder.py`
전부 무수정 유지.

---

## Phase 6 — Benchmark Readiness(1차 지적 사항 재확인)

1차 Preflight에서 지적한 대로, `NAE/benchmark/datasets/gold_benchmark_v1.jsonl`은
여전히 `TSU-ACT-*` 형식의 placeholder이며 실제 verified 10건(TSU-0000025
등 순차 ID 형식)과 호환되지 않는다 — **미해결, 재확인만**. 실제
Retrieval Benchmark를 실행하려면 이 10건(또는 향후 확장분) 기준
Gold Query Set을 사람이 새로 작성해야 한다.

---

## 완료 보고

```
STATUS: READY_FOR_INTERNAL_E2E(조건부) — Embedding 실행은 여전히 미실행

CURRENT STATE:
verified=10, eligible=10, indexed(실제 Qdrant)=0(points_count 0)
generated=4107(차단 유지)

PAYLOAD CONTRACT: 10/10 PASS(실 데이터 기준 재검증)

QDRANT: 컬렉션 존재, points_count=0(변경 없음), legacy와 물리적 분리 유지

EMBEDDING CONFIG: 모델 가용, 캐시 정상(0), point ID 충돌 없음

ARCHITECTURE BOUNDARY: PASS(core/retrieval.py, core/tsu_builder.py 무수정)

WARNING(이월, 미해결):
1. bge-m3:latest 모델 버전 고정(digest pin) 없음 — 재현성 리스크
2. batch/timeout/retry 정책 미문서화
3. Gold Benchmark 데이터셋이 실제 TSU ID 네임스페이스와 여전히 불일치 — 신규 작성 필요

BLOCKER:
0(verified 10건 존재, Payload Contract 검증 통과, Embedding 실행을 막는
기술적 조건 없음 — 실행은 별도 승인만 있으면 됨)

EMBEDDING: NOT EXECUTED
QDRANT: NOT EXECUTED(읽기 전용 조회만 수행)
GIT: NOT PERFORMED

NEXT STEP:
1. (승인 필요) verified 10건에 한해 실제 Embedding + Qdrant upsert 실행(dry_run=False)
2. Embedding 실행 후 별도 검증 Gate(points_count==10, payload 필드 재확인) 실행
3. Retrieval Benchmark는 Gold Query Set 신규 작성 후 별도 진행
```
