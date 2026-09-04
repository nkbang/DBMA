# NAE Vector Index Preflight Design 001

**Project:** NAE-VECTOR-INDEX-PREFLIGHT-DESIGN-001
**작성일:** 2026-08-08
**성격:** DESIGN + READ-ONLY AUDIT ONLY. 실제 Embedding/Qdrant 실행 없음.
**Authority:** `docs/NAE_METADATA_SCHEMA_2_PRODUCTION_MIGRATION_REPORT_001.md`(Migration 완료, 4,117/4,117)
**Git Commit/Push:** 미수행.

---

## Phase 1 — Current Index Architecture Audit(Read-Only)

| 확인 항목 | 실측 결과 |
|---|---|
| 1. `NAE/pipeline/index/indexer.py` | `load_records_with_gate_summary()`(Review Gate 적용) → `index_identifier()`(embed+upsert) → `index_all()`(배치). `dry_run` 파라미터로 embedding/Qdrant 완전 우회 가능(기존 구현, 재확인) |
| 2. Review Gate wiring | `index_identifier()`는 항상 `load_records_with_gate_summary()`를 거치며, 이 함수는 항상 `review_gate.filter_embedding_eligible()`을 호출한다 — 저장소 전체에서 `tsu.json`/`tsu_verified.json`을 직접 읽어 인덱싱하는 별도 경로 없음(grep 확인) |
| 3. Embedding 호출 경로 | `qdrant_store.build_point()` 직전, `embed_client.embed_text(claim_text, content_hash=...)` — 캐시 hit 시 Ollama 호출 자체가 생략됨 |
| 4. Embedding model | `bge-m3:latest`(`NAE/pipeline/embed/config.py::DEFAULT_EMBED_MODEL`) |
| 5. Vector dimension | `1024`(`EMBED_DIMENSION`/`VECTOR_SIZE` 양쪽 일치 확인) |
| 6. Qdrant collection configuration | `nae_tsu_v{TSU_SCHEMA_VERSION}` = 현재 `nae_tsu_v1`, `Distance.COSINE`, size=1024 — 실측: `client.get_collection('nae_tsu_v1')`로 이미 생성되어 있음(points_count=**0**, 즉 아직 아무것도 색인되지 않은 빈 컬렉션) |
| 7. payload/metadata mapping | `qdrant_store.build_point()`가 현재 담는 필드: `tsu_id/book/author/identifier/source_identifier/doctrine/page/paragraph/sentence/claim/source_text/scriptures/citations/review_status/llm_score/parser_score/evidence_score/citation_score/overall_score/duplicate_of/tsu_schema_version/collector_version/canonical_version` — **Metadata Schema 1.1.0 필드(source_id/author_id/work_id/edition_id/volume_id/publication_year/source_type/copyright_status/usage_permission/access_control/tsu_access/metadata_schema_version/metadata_provenance/category(_status)/citation_policy(_status))는 하나도 포함되어 있지 않다**(§Phase6에서 GAP으로 상세 분석) |
| 8. dataset isolation | `QDRANT_URL="http://localhost:7333"`(전용 인스턴스, ADR-013), collection명이 TSU_SCHEMA_VERSION에서 파생 |
| 9. existing index/collection 존재 여부 | `nae_tsu_v1` 존재, **points_count=0**(Embedding 미실행 상태와 일치, 이상 없음) |
| 10. 기존 DBMA RetrievalEngine과의 경계 | ADR-013 §Decision: `core/retrieval.py::RetrievalEngine` 검색 경로에 연결되지 않음. Docker 레벨 실측: `nae_qdrant` 컨테이너(포트 7333/7334)와 legacy `qdrant` 컨테이너(6333)가 물리적으로 분리된 별도 컨테이너로 확인됨 |

**core/retrieval.py, core/tsu_builder.py, DBMA core pipeline, 기존 Retrieval architecture — 전부 무수정(읽기만 수행).**

---

## Phase 2 — Review Gate Verification(Dry-run, 4,117건)

```python
>>> review_status 분포: {'generated': 4117}
>>> indexer.index_all(dry_run=True)
{'processed': 4, 'indexed': 0, 'identifiers': [
    {'identifier': 'Hiscox_Standard_Manual', 'indexed': 0},
    {'identifier': 'Dagg_Church_Order', 'indexed': 0},
    {'identifier': '_migration_backup_20260808T130432', 'indexed': 0},
    {'identifier': '_backup_20260807T015632', 'indexed': 0},
]}
```

**요구된 기대값과 정확히 일치**:

```
generated = 4,117
verified  = 0
eligible(would_index) = 0
indexed = 0
```

현재 상태에서 실제 Embedding 대상은 **0건**이다. `_migration_backup_*`/
`_backup_*`는 백업 디렉토리가 `tsu_root.iterdir()`에 함께 잡힌 것일 뿐
(디렉토리 안에 `tsu.json`이 없어 자연히 `indexed=0`) — 실제 데이터
오염이 아님을 확인.

---

## Phase 3 — Index Eligibility Design

기존 `NAE/pipeline/tsu/review_gate.py`가 이미 아래 정책을 정확히
구현하고 있음을 재확인했다(신규 구현 불필요, 기존 설계 그대로 승인):

```
VALID_REVIEW_STATUSES      = {generated, reviewed, verified, rejected}
EMBEDDING_ELIGIBLE_STATUSES = {verified}   # 이것만 PASS

generated → BLOCK
reviewed  → BLOCK
rejected  → BLOCK
verified  → PASS(ELIGIBLE)
review_status 누락       → BLOCK(check_tsu_review_status가 None/누락을 명시적으로 BLOCK 처리)
review_status가 유효 집합 밖의 값(invalid) → BLOCK
```

**Review Gate 우회 경로 없음**: `NAE/pipeline/index/` 전체에서
`tsu.json`/`tsu_verified.json`을 직접 읽어 Qdrant에 넣는 코드는
`indexer.py`의 `load_records_with_gate_summary()` 외에 존재하지 않는다
(grep 실측, §Phase1 항목2).

**판정: 정책 설계 완료, 코드 변경 불필요(이미 구현되어 있음).**

---

## Phase 4 — Embedding Configuration Audit(설정 검증만, 미실행)

| 항목 | 값/상태 | 비고 |
|---|---|---|
| embedding model | `bge-m3:latest` | |
| model version | Ollama 태그 `latest`(고정 버전 pin 없음) | **WARNING** — 재현성 관점에서 모델 다이제스트 고정 필요성 검토 권고 |
| embedding dimension | 1024 | `EMBED_DIMENSION`=`VECTOR_SIZE` 일치 |
| normalization | 코드상 명시적 정규화 로직 없음(Ollama 반환 벡터 그대로 저장) | Qdrant `Distance.COSINE`이 저장 시점 정규화 여부와 무관하게 코사인 유사도 계산 — 기능상 문제 없음, 별도 정규화 불필요 |
| chunk/input policy | claim 단위(문장 재진술 텍스트) 1개 = embedding 1개, chunking 없음 | TSU 자체가 이미 문장 단위 claim이므로 별도 청킹 불필요 |
| batch size | **없음** — `for record in records:` 순차 처리, batch API 미사용 | **WARNING** — 4,117건 순차 처리 시 소요시간 추정 필요(§Phase8 참고) |
| timeout | **없음** — `ollama.embeddings()` 호출에 timeout 파라미터 미설정 | **WARNING**, TSU claim 추출(`claim.py`)과 동일한 설계 관례(관찰) |
| retry policy | **없음** — 실패 시 `embedding_errors` 카운트만 하고 스킵(fail-soft), 재시도 없음 | 의도된 설계(배치 전체가 죽지 않도록)로 보이나 명시적 문서화는 없음 |
| GPU/CPU configuration | Ollama 자체 스케줄링에 위임(`bge-m3:latest`), 코드 레벨 명시 설정 없음 | |
| cache policy | SHA256(schema_version+claim+book+page+scriptures) 해시 키 디스크 캐시(`NAE/corpus/embeddings/cache/`) — 동일 내용 재호출 방지 | 이미 구현·검증됨(Phase 3.5 duplicate 검사와 캐시 공유) |
| dataset identifier | 명시적 필드 없음 — `identifier`(TSU 파일 경로 기준)로 암묵적 구분 | |
| collection name | `nae_tsu_v1`(TSU_SCHEMA_VERSION 기반 자동 파생) | |

**NAE ↔ DBMA 네임스페이스 혼합 여부**: 혼합 없음. `NAE/pipeline/embed/config.py`의
캐시 경로(`NAE/corpus/embeddings/cache/`), Qdrant collection(`nae_tsu_v1`),
Qdrant instance(`nae_qdrant:7333`) 전부 `NAE/` 전용이며 DBMA legacy
(`chroma_db`, `dbma_qdrant`, `dbma_sermon`)와 물리적으로 분리(§Phase1
항목10 실측).

**기존 DBMA vector index — 변경/재구축 없음(이번 작업 전체가 조사만 수행).**

---

## Phase 5 — Qdrant Design Audit(설계 검증만, 미실행)

| 항목 | 현재 설계 | 판정 |
|---|---|---|
| 1. collection name | `nae_tsu_v1`(schema version 파생, 향후 스키마 변경 시 `nae_tsu_v2`로 자동 분리 — 기존 collection은 삭제하지 않고 보존하는 정책, ADR-013) | PASS |
| 2. vector dimension | 1024(bge-m3) | PASS |
| 3. distance metric | Cosine | PASS |
| 4. payload schema | 현재 구현 = 기존 20개 필드 기준 payload만(§Phase1 항목7) — **Metadata Schema 1.1.0 필드 미반영(GAP, §Phase6)** | **CONDITIONAL** |
| 5. NAE dataset isolation | `nae_qdrant`(7333/7334) vs legacy `qdrant`(6333) — Docker 컨테이너 레벨 분리 실측 확인 | PASS |
| 6. TSU ID uniqueness | `tsu_id_to_point_id()`가 `TSU-\d+` 패턴에서 정수만 추출해 Qdrant point ID로 사용 — Migration 후에도 `id` 필드(IMMUTABLE_FIELDS)는 변경되지 않았으므로 그대로 유효 | PASS |
| 7. source/work/edition identifiers | 이번 Migration으로 TSU 레코드 자체에는 이미 존재(`source_id/work_id/edition_id`) — 그러나 Qdrant payload에는 아직 반영 안 됨(§4와 동일 GAP) | **CONDITIONAL** |
| 8. metadata_schema_version | TSU 레코드에는 `"1.1.0"`으로 존재, payload에는 없음 | **CONDITIONAL**(GAP) |
| 9. review_status | payload에 이미 포함(`review_status`) — Embedding 시점에는 항상 `"verified"`만 들어오므로(Review Gate가 이미 걸러줌) payload 값도 항상 `verified`로 일관될 것 | PASS(설계상 일관성 보장됨) |
| 10. provenance fields | `metadata_provenance`(crosswalk_id 등) 미반영 | **CONDITIONAL**(GAP) |

**보장 사항 재확인**: NAE vector collection(`nae_tsu_v1`, `nae_qdrant:7333`)
≠ DBMA vector collection(`dbma_sermon`, `qdrant:6333`) — 컨테이너/포트/
컬렉션명 3중으로 분리되어 있음. `core/retrieval.py::RetrievalEngine`은
이번 조사에서 읽지도 않았고(무수정), ADR-013이 이미 "연결하지 않는다"를
Decision으로 명시.

---

## Phase 6 — Index Payload Contract(설계, 미실행)

### 6.1 현재 payload(구현됨, §Phase1 항목7과 동일)

```
tsu_id, book, author, identifier, source_identifier, doctrine, page,
paragraph, sentence, claim, source_text, scriptures, citations,
review_status, llm_score, parser_score, evidence_score, citation_score,
overall_score, duplicate_of, tsu_schema_version, collector_version,
canonical_version
```

### 6.2 제안 — 추가되어야 할 Metadata Layer 필드(설계만, 미구현)

```
source_id, author_id, work_id, edition_id, volume_id,
publication_year, source_type, copyright_status, usage_permission,
access_control, tsu_access, metadata_schema_version,
category, category_status, citation_policy, citation_policy_status,
metadata_provenance.crosswalk_id
```

이 필드들은 이미 TSU 레코드(`tsu.json`) 안에 Migration으로 존재하므로
(§Phase5 실측), `qdrant_store.build_point()`가 `record.get(...)`으로
그대로 옮기기만 하면 된다 — **추가 조회/추측 불필요, 순수 pass-through**.

**기존 TSU content(claim/doctrine/evidence 등)는 이번 설계에서도 임의
변형하지 않는다** — payload 구성은 읽기(값 복사)일 뿐 TSU 원본 파일에
쓰기를 하지 않는다.

### 6.3 GAP 판정

```
현재 qdrant_store.py::build_point()는 Metadata Schema 1.1.0 필드를
0/16 포함한다. Embedding을 실제 실행하기 전에 build_point()를 갱신하지
않으면, TSU에 이미 존재하는 Metadata Layer 정보(copyright_status,
tsu_access, author_id 등)가 Qdrant 검색/필터링에서 전혀 활용되지 못한다.
```

**이번 작업에서 `qdrant_store.py`를 실제로 수정하지 않았다**(DESIGN
ONLY 원칙) — 위 필드 목록을 Implementation Task의 정확한 변경 대상으로
제안한다.

---

## Phase 7 — Benchmark Readiness(설계, 미실행)

### 7.1 기존 인프라 재사용(신규 설계 아님)

`NAE/benchmark/`에 이미 Runner/Evaluator/Metrics/Schema가 구현되어
있다(`recall_at_k`/`precision_at_k`/`mean_reciprocal_rank`/`hit_rate`/
`compute_all_metrics`) — 이번 Phase는 이 기존 인프라를 **재사용**하는
설계이지, 처음부터 새로 만드는 것이 아니다.

| 요구 항목 | 기존 인프라 매핑 | 상태 |
|---|---|---|
| 1. Gold query set | `NAE/benchmark/datasets/gold_benchmark_v1.jsonl` | **GAP(아래 §7.2)** |
| 2. expected relevant TSU | `expected.gold_tsu_ids`(schema 필드로 이미 존재) | 구조는 있음 |
| 3. retrieval top-k | `retrieval.top_k`(schema 필드) | 구조는 있음 |
| 4. recall@k | `metrics.py::recall_at_k()` | 구현됨 |
| 5. precision@k | `metrics.py::precision_at_k()` | 구현됨 |
| 6. MRR/nDCG | MRR 구현됨(`mean_reciprocal_rank`), **nDCG 미구현** | **GAP** |
| 7. regression baseline | `NAE/benchmark/reports/`(리포트 산출 경로 존재) | 인프라 있음, 실제 baseline 리포트는 아직 없음(Embedding 자체가 없으므로 당연) |
| 8. dataset version | schema의 `metadata.created_version` 필드 | 구조는 있음 |
| 9. index version | `tsu_schema_version`/`metadata_schema_version`을 리포트에 함께 기록하는 규칙 필요 | **GAP(설계 제안)** — 현재 benchmark schema에는 이 필드가 없음, Evaluator/Runner 확장 시 추가 제안 |
| 10. reproducibility metadata | `collector_version`/`canonical_version` 필드는 있으나 `metadata_schema_version` 없음 | **GAP(설계 제안)** |

### 7.2 핵심 발견 — 기존 Gold 데이터셋은 실제 TSU와 호환되지 않음

`gold_benchmark_v1.jsonl`을 실측한 결과, `gold_tsu_ids`가
`TSU-ACT-ada6a56f8ea13582` 형식이며 `metadata.source: "infrastructure-validation"`
로 명시되어 있다 — 이는 **인프라 검증용 placeholder 데이터**이며,
실제 Migration이 완료된 Dagg/Hiscox TSU의 ID 형식(`TSU-0000001` 순차
7자리)과 **네임스페이스 자체가 다르다.**

**결론**: Retrieval Benchmark를 의미 있게 실행하려면, `verified` 승급이
완료된 실제 Dagg/Hiscox TSU 콘텐츠를 대상으로 **새 Gold Query Set을
사람이 직접 작성**해야 한다(`NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md`
기존 가이드 재사용 가능) — 기존 `gold_benchmark_v1.jsonl`을 그대로
재사용할 수 없다. 이 작업은 사람이 신학적 정확성을 판단해야 하므로
자동 생성 금지 원칙(`NAE/benchmark/schema.py` 헤더 주석: "자동 정답
생성 금지")과도 일치한다.

**판정**: 현재 Benchmark 인프라는 구조적으로 **Vector Index 품질을
검증할 수 있는 형태**이나, 실제 데이터(Gold Query Set)가 준비되지
않아 지금 당장 실행 가능한 상태는 아니다. Vector Index 실행 이후,
별도로 Gold Query Set 작성 작업이 선행되어야 한다.

---

## Phase 8 — Safety / Rollback Design(실행 전 설계)

### 8.1 실행 전 필수 확인 사항

```
1. Review Gate 재확인: eligible(verified) 건수가 실제 사람 검토를
   거쳐 확정된 수와 정확히 일치하는지(현재는 0건 — 아직 아무도
   승급하지 않음, 따라서 지금 이 설계 시점에는 Embedding 실행 자체가
   원천적으로 불가능한 상태)
2. Qdrant collection 사전 상태 스냅샷: `nae_tsu_v1` points_count=0을
   기록해 둔다(이번 조사에서 이미 실측) — 실행 후 points_count가
   정확히 verified 건수만큼만 증가했는지 대조하는 기준선으로 사용
3. Embedding 캐시 디렉토리(`NAE/corpus/embeddings/cache/`) 백업 여부
   결정(캐시는 재계산 가능한 파생 데이터이므로 백업 필수는 아니나,
   재실행 비용 절감을 위해 보존 권장)
```

### 8.2 실행 중 안전장치(기존 구현에 이미 존재, 재확인)

```
- dry_run=True 우선 실행 → 실제 실행 전 would_index 수치 재확인
- fail-soft: embedding_errors는 카운트만 하고 배치 중단하지 않음(기존 설계)
- ensure_collection()이 기존 컬렉션이 있으면 재생성하지 않음(멱등)
```

### 8.3 Rollback 설계(제안, 미실행)

```
Qdrant 레벨: upsert된 point들은 point_id(=TSU 정수 ID) 기준으로
             삭제 가능 — Migration Script의 파일 백업과 달리 Qdrant는
             "실행 전 상태로 되돌리기"가 아니라 "이번에 추가된
             point만 선택적으로 delete" 방식이 되어야 한다(전체
             컬렉션을 지우면 이전에 이미 색인된 다른 배치까지
             손실되므로 위험 — 현재는 points_count=0이라 해당 없지만,
             향후 여러 차례 배치 실행 시 반드시 지켜야 할 원칙)
파일 레벨:   index_report.json은 순수 산출물(추적용)이므로 삭제해도
             안전, TSU 원본(tsu.json)에는 index 단계에서 쓰기가
             전혀 없음(§Phase1 항목1 확인 — indexer.py는 tsu.json을
             읽기만 함)
```

**이번 작업에서 실제 rollback을 수행할 필요 자체가 없었다** — Embedding을
전혀 실행하지 않았으므로 되돌릴 상태 변화도 없다.

---

## 완료 보고

```
STATUS: PASS(설계/감사 완료) / EMBEDDING·QDRANT 실행 없음

CURRENT INDEX STATE:
nae_tsu_v1 collection 존재, points_count=0(정상 — 아직 색인 이력 없음)
review_status: generated=4117, verified=0
eligible for embedding: 0

REVIEW GATE:
generated -> BLOCK 유지, verified만 ELIGIBLE(기존 설계 그대로, 우회 경로 없음 확인)

EMBEDDING CONFIG:
model=bge-m3:latest, dimension=1024, batch/timeout/retry 미설정(WARNING),
cache 정상 구현

QDRANT DESIGN:
nae_tsu_v1(1024, Cosine), nae_qdrant:7333 vs legacy qdrant:6333 물리적 분리 확인
payload에 Metadata Schema 1.1.0 필드 0/16 반영(GAP — Implementation Task 필요)

BENCHMARK READINESS:
기존 인프라(recall/precision/MRR) 재사용 가능하나 Gold Query Set이
placeholder(TSU-ACT-* 형식)이라 실제 Dagg/Hiscox TSU와 비호환 —
신규 Gold Query Set 작성 필요(사람 작성 원칙 유지)

ARCHITECTURE AUDIT:
PASS(core/retrieval.py, core/tsu_builder.py, DBMA core pipeline 전부 무수정)

BLOCKER:
0(이번 작업은 설계/감사만 — Embedding 실행 조건이 아직 안 됨: verified 0건이므로 실행해도 색인 대상이 없음)

WARNING:
1. Qdrant payload에 Metadata Schema 1.1.0 필드 미반영(GAP, Implementation Task 제안)
2. Embedding model version pin 없음("latest" 태그, 재현성 리스크)
3. batch/timeout/retry 정책 미문서화
4. Gold Benchmark 데이터셋이 실제 TSU ID 네임스페이스와 불일치(신규 작성 필요)
5. Benchmark 리포트에 index_version/metadata_schema_version 기록 필드 없음

NEXT STEP:
1. (Implementation Task 제안) qdrant_store.py::build_point()에 Metadata Schema 1.1.0 필드 16개 추가
2. (별도 승인 필요) TSU Review Workflow를 통해 최소 1건 이상 review_status=verified 승급 — 그래야 Embedding 대상이 생김
3. verified 건 발생 후에만 실제 Embedding/Qdrant 실행(dry_run=False)을 별도 작업으로 승인
4. Gold Query Set을 실제 Dagg/Hiscox 콘텐츠 기준으로 사람이 작성(NAE/benchmark/GOLD_BENCHMARK_AUTHORING_GUIDE.md 활용)

EMBEDDING: NOT EXECUTED
QDRANT: NOT EXECUTED
GIT: NOT PERFORMED
```
