# NAE C1 Status and Next-Work Report
- Report date: 2026-07-31
- Repository: DBMA (David Bang Ministry Archive)
- Branch: main (미확인 — git status 참조)
- HEAD commit: 403ab6581210d1fb77ef5a6508c84a4d40724fb8
- Local working tree: dirty (Remediation-004 관련 신규 파일 다수)
- Report scope: Phase 5.1 Benchmark Retrieval Infrastructure Contract, Phase 5.2 Gold Authoring 전환 현황
- Evidence inspected:
  - `docs/STATE.md`, `docs/TODO.md`
  - `git status --short`, `git log --oneline -20`
  - `NAE/benchmark/schema.py`, `evaluator.py`, `runner.py`, `metrics.py`, `loader.py`
  - `NAE/benchmark/datasets/benchmark_v1.jsonl` (4행), `gold_benchmark_v1.jsonl` (5행)
  - `NAE/corpus/` 하위 디렉터리 전역 (모두 비어 있음)
  - `NAE/pipeline/index/qdrant_store.py`, `indexer.py`, `config.py`
  - `tests/test_nae_benchmark_*.py` (6개), `tests/test_nae_index_*.py` (2개)
  - `evidence/phase5_1_contract/`, `evidence/phase5_1_remediation_004/`, `evidence/phase5_2/`
  - `docs/agents/c1/`, `docs/agents/cue/`, `docs/audit/phase5_1/`

## 1. Executive Status

| 영역 | 상태 | 근거 | 차단 요인 |
|---|---|---|---|
| Phase 5.1 contract | PARTIAL | `evidence/phase5_1_contract/manifest.json`, `self-check-050.md`, `contract-tests.txt` — schema migration, gold_tsu_ids canonical화 완료. 그러나 corpus/indexing 미완료로 retrieval end-to-end 검증 불가 | TSU dataset build 없음, Qdrant collection point 확인 불가 |
| Phase 5.2 gold authoring | IN PROGRESS | `evidence/phase5_2/gold-authoring-skeleton-report.md` — skeleton만 존재. `scripts/author_gold_set.py` 존재. 그러나 canonical corpus/TSU 미완성으로 gold entry 작성 불가 | TSU dataset build 선행 필요 |
| Benchmark schema/loader/validation | COMPLETE | `NAE/benchmark/schema.py` — `gold_tsu_ids` top-level canonical (132행). `BenchmarkExpected.gold_tsu_ids` deprecated (79행). `evaluator.py` 82행에서 `relevant_ids = item.gold_tsu_ids` 사용. `runner.py` 95-100행에서 dummy 제거, `retrieval_fn` 필수화 | — |
| Evaluator gold_tsu_ids rewire | COMPLETE | `NAE/benchmark/evaluator.py::evaluate()` 82행: `relevant_ids = item.gold_tsu_ids`. 86-97행: zero-gold case 처리. 107행: `compute_all_metrics(retrieved_ids, relevant_ids, effective_k)` — expected_scriptures/required_concepts metric 계산에 사용되지 않음 | — |
| Runner actual retrieval injection | COMPLETE (contract 준비됨) | `NAE/benchmark/runner.py` 95-100행: `retrieval_fn is None` 시 `ConfigurationError`. Retriever Protocol (51-52행): `retrieve(query, k) -> List[str]`. 실제 retriever 주입 가능 | 실제 Qdrant retriever adapter 미구현 |
| TSU corpus build | NOT STARTED (empty) | `NAE/corpus/tsu/`, `canonical/`, `metadata/`, `embeddings/` — 모두 `.gitkeep`만. `raw/archive_org/books/` 비어 있음. `scripts/build_tsu_dataset.py` 존재하지만 실행 증거 없음 | 원본 문서 수집 선행 필요 |
| Qdrant indexing | NOT STARTED (empty) | `NAE/pipeline/index/qdrant_store.py`, `indexer.py`, `config.py` — 코드 존재. 그러나 corpus 데이터가 없어 indexing 불가. 실제 Qdrant server collection/point count 증거 없음 | TSU corpus build 선행 필요 |
| Retrieval metrics | PARTIAL (compute only) | `NAE/benchmark/metrics.py` — Precision@K, Recall@K, MRR, nDCG, Hit Rate compute 함수 존재. 그러나 실제 retrieval pipeline과 연결되지 않음 (runner가 Retriever Protocol 요구) | Qdrant index + retriever adapter 필요 |
| Evidence and audit trail | COMPLETE | `evidence/phase5_1_contract/` (manifest, self-check, contract tests), `evidence/phase5_1_remediation_004/` (manifest, pytest, diff, final report), `evidence/phase5_2/` (skeleton) | — |

## 2. Verified Completed Work

### 2.1 Phase 5.1 Schema Migration (gold_tsu_ids canonical)
- Work item: Benchmark schema에서 gold_tsu_ids를 top-level(BenchmarkItem)으로 canonical 이동, expected.gold_tsu_ids deprecated
- Status: VERIFIED COMPLETE
- Evidence:
  - Files: `NAE/benchmark/schema.py::BenchmarkItem.gold_tsu_ids` (132행), `BenchmarkExpected.gold_tsu_ids` deprecated metadata (79-82행)
  - Commit SHA: UNVERIFIED (git log에서 확인 필요)
  - Test or command result: `tests/test_nae_benchmark_schema.py`, `tests/test_nae_benchmark_contract.py` 존재 — 실행 증거는 phase5_1_contract/pytest.txt 참조
- Notes: loader가 legacy JSONL에서 역직렬화 시 expected.gold_tsu_ids도 허용

### 2.2 Evaluator gold_tsu_ids 기반 정답 판정 전환
- Work item: Evaluator가 expected_scriptures/required_concepts 대신 gold_tsu_ids만 canonical ground truth로 사용
- Status: VERIFIED COMPLETE
- Evidence:
  - Files: `NAE/benchmark/evaluator.py::evaluate()` 82행: `relevant_ids = item.gold_tsu_ids`
  - Test or command result: `tests/test_nae_benchmark_evaluator.py` 존재
- Notes: zero-gold case (86-97행)도 처리됨

### 2.3 Runner dummy retrieval 제거 및 retrieval_fn 필수화
- Work item: silent default dummy retrieval 제거, 실제 Retriever 주입 필수화
- Status: VERIFIED COMPLETE
- Evidence:
  - Files: `NAE/benchmark/runner.py` 95-100행: `ConfigurationError` when `retrieval_fn is None`
  - Message: "Silent _dummy_retrieval() default path has been removed."
- Notes: Retriever Protocol (51-52행)로 contract 정의됨

### 2.4 Benchmark metrics computation
- Work item: Precision@K, Recall@K, MRR, nDCG, Hit Rate 계산 함수 구현
- Status: VERIFIED COMPLETE
- Evidence:
  - Files: `NAE/benchmark/metrics.py` — `compute_all_metrics()` 함수 존재
  - Test: `tests/test_nae_benchmark_metrics.py` 존재
- Notes: compute만 가능, 실제 retrieval과 연결되지 않음

### 2.5 Remediation-004 (gold validity diagnostic)
- Work item: GOLD_VALIDITY_STATUSES 추가 (VALID/INVALID_GOLD/DUPLICATE_GOLD), contract tests
- Status: VERIFIED COMPLETE
- Evidence:
  - Files: `NAE/benchmark/schema.py` 51-55행: `GOLD_VALIDITY_STATUSES`
  - Evidence: `evidence/phase5_1_remediation_004/manifest.json`, `pytest-full.txt`, `gold-validity-contract-tests.txt`, `C1-REMEDIATION-004-FINAL-REPORT.md`
  - Commit SHA: UNVERIFIED

### 2.6 Benchmark dataset (소규모)
- Work item: benchmark_v1.jsonl gold entry 포함
- Status: REPORTED COMPLETE (C1 보고 기반)
- Evidence:
  - Files: `NAE/benchmark/datasets/benchmark_v1.jsonl` (4행), `gold_benchmark_v1.jsonl` (5행)
  - Note: 4행은 매우 소규모 — smoke test 수준
- Notes: human review 상태 미확인

## 3. In-Progress and Unverified Work

### 3.1 TSU Dataset Build
- 현재 실제 상태: `NAE/corpus/tsu/` 비어 있음 (.gitkeep만)
- 이미 존재하는 산출물: `scripts/build_tsu_dataset.py` (CLI wrapper), `core/tsu_builder.py` (핵심 로직)
- 누락된 산출물 또는 검증: 원본 문서 수집 → TSU 빌드 → canonical metadata 생성 실행 증거
- 의존성: Phase 5.2 gold authoring, Qdrant indexing 모두 선행
- 위험도: A
- 다음에 해야 할 단 하나의 행동: `scripts/build_tsu_dataset.py` 실행 또는 원본 문서 가용성 확인

### 3.2 Canonical Corpus Build
- 현재 실제 상태: `NAE/corpus/canonical/`, `metadata/`, `embeddings/` 모두 비어 있음
- 이미 존재하는 산출물: 디렉터리 구조, `.gitkeep`
- 누락된 산출물 또는 검증: 실제 canonical 문서, 임베딩 데이터
- 의존성: TSU dataset build 선행
- 위험도: A
- 다음에 해야 할 단 하나의 행동: corpus build pipeline 실행

### 3.3 Qdrant Collection 및 Indexing
- 현재 실제 상태: 코드 존재 (`qdrant_store.py`, `indexer.py`), 그러나 실제 Qdrant server 연결/collection/point 증거 없음
- 이미 존재하는 산출물: `NAE/pipeline/index/` 모듈, `tests/test_nae_index_qdrant_store.py`
- 누락된 산출물 또는 검증: 실제 Qdrant server 가용성, collection 생성, point count
- 의존성: TSU corpus build 선행
- 위험도: A
- 다음에 해야 할 단 하나의 행동: Qdrant server 가용성 확인 (`docker ps` 또는 `qdrant --check`)

### 3.4 Phase 5.2 Gold Entry 작성 준비
- 현재 실제 상태: skeleton report(`gold-authoring-skeleton-report.md`), script(`author_gold_set.py`)만 존재
- 이미 존재하는 산출물: schema (review_status, difficulty, question_type), script
- 누락된 산출물 또는 검증: 실제 gold entry (human-reviewed, 출처·문맥·TSU ID 기록)
- 의존성: TSU dataset build, canonical corpus 선행
- 위험도: B
- 다음에 해야 할 단 하나의 행동: TSU dataset build 후 gold entry 작성 시작

### 3.5 End-to-End Retrieval Evaluation (Smoke Test)
- 현재 실제 상태: metrics compute 가능, runner Retriever Protocol 준비됨, 그러나 실제 retriever adapter 미구현
- 이미 존재하는 산출물: Retriever Protocol contract, Evaluator, metrics
- 누락된 산출물 또는 검증: Qdrant-backed retriever adapter, smoke retrieval 실행 증거
- 의존성: Qdrant indexing 선행
- 위험도: B
- 다음에 해야 할 단 하나의 행동: minimal Qdrant retriever adapter 구현 + smoke test

## 4. Open Issues and Contradictions

### CRITICAL
1. **corpus/canonical/TSU 모두 비어 있음 — gold authoring의 기반 데이터 부재**
   - 분류: CRITICAL
   - `NAE/corpus/tsu/`, `canonical/`, `metadata/` — `.gitkeep`만 존재
   - gold entry 작성의 ground truth가 없음

2. **Qdrant indexing layer 코드는 있으나 실제 server/collection/point 증거 없음**
   - 분류: CRITICAL
   - `NAE/pipeline/index/qdrant_store.py` 등 코드 존재
   - 실제 Qdrant server 가용성, collection 생성, point count 확인 필요

### HIGH
3. **benchmark_v1.jsonl이 4행으로 매우 소규모**
   - 분류: HIGH
   - smoke test 수준 — 실제 retrieval 평가에는 불충분
   - gold_benchmark_v1.jsonl은 5행

4. **Phase 5.2 gold entry의 human review 상태 미확인**
   - 분류: HIGH
   - `gold-authoring-skeleton-report.md`만 존재
   - 실제 gold entry의 review_status, 출처, 문맥 확인 필요

### MEDIUM
5. **runner CLI가 retrieval_fn 요구하지만 제공 방법 미구현**
   - 분류: MEDIUM
   - `runner.py` 212-220행: CLI가 `retrieval_fn`을 요구하나 Python API只能通过
   - `--retrieval-fn` CLI 옵션 미구현

6. **expected_scriptures/required_concepts 가 schema에 여전히 존재 (deprecated)**
   - 분류: MEDIUM
   - `BenchmarkExpected`에 여전히 있음 (83-85행) — deprecated 표시 있으나 제거되지 않음
   - loader가 역직렬화 시 사용

### LOW
7. **evidence/phase5_2/ skeleton만 존재**
   - 분류: LOW
   - `gold-authoring-skeleton-report.md`만 — 실제 gold entry 없음

## 5. Dependency-Ordered Next Plan

| Loop | 작업 | 선행 조건 | 산출물 | 검증 방법 | Evidence 경로 | 위험도 | 완료 정의 |
|---|---|---|---|---|---|---|---|
| 1 | Qdrant server 가용성 확인 | 없음 | collection 존재 여부 | `docker ps` 또는 `qdrant --check` | UNVERIFIED | A | Qdrant server 실행 중, collection 생성 가능 |
| 2 | TSU corpus build (source 문서 가용성 확인 → 빌드) | 원본 문서 가용성 | `NAE/corpus/tsu/`, `canonical/`, `metadata/` 실제 데이터 | 파일 목록, 건수 | `NAE/corpus/*/` | A | TSU dataset이 비어 있지 않고 실제 데이터 포함 |
| 3 | Qdrant indexing 실행 | TSU corpus build 완료 | collection points | point count, `qdrant --info` | UNVERIFIED | A | corpus → Qdrant index 매핑 확인 |
| 4 | Minimal Qdrant retriever adapter 구현 | Qdrant collection 존재 | Retriever Protocol 구현체 | smoke retrieval 테스트 | UNVERIFIED | B | retriever.retrieve(query, k)가 실제 점 반환 |
| 5 | Smoke retrieval evaluation | retriever adapter + index | report.json (metrics) | metrics 계산 결과 | `evidence/smoke/` | B | Precision@K/Recall@K/MRR/nDCG 계산 가능 |
| 6 | Phase 5.2 gold entry 작성 (소규모) | TSU dataset build | gold_benchmark_v1.jsonl 실제 gold entry | review_status, 출처, 문맥 기록 | `NAE/benchmark/datasets/` | B | human-reviewed gold entry 최소 1건 |
| 7 | CUE 검토 제출 패키지 | gold entry 작성 완료 | submission package | manifest, review evidence | `evidence/phase5_2/cue-submission/` | C | CUE 검토 요청 문서화 |
| 8 | P1 감사 제출 패키지 | CUE 승인 후 | audit package | commit SHA, evidence 링크 | `evidence/phase5_2/p1-audit/` | C | P1 독립 감사 요청 |

## 6. Immediate Recommendation

### 지금 즉시 시작해야 할 Loop: Loop 1 (Qdrant server 가용성 확인)
- 이유: corpus build 전에 indexing target 가용성 확인이 선행되어야 함
- 검증 명령: `docker ps | grep qdrant` 또는 `qdrant --check`

### 지금 하면 안 되는 작업:
- Phase 5.2 gold entry 작성 (Loop 6): TSU dataset build 전에는 ground truth 부재
- Corpus build (Loop 2): 원본 문서 가용성 확인 전에는 실행 불가
- Qdrant indexing (Loop 3): corpus build 전에는 데이터 없음

### HQ 또는 CUE 판단이 필요한 사항:
- benchmark_v1.jsonl (4행)의 규모로 Phase 5.1 contract 완료를 승인할지, 최소 항목 수 요구사항 있는지
- `BenchmarkExpected.gold_tsu_ids` deprecated 필드의 제거 시점 (loader 호환성 유지 vs 제거)

### C1이 단독 수행 가능한 범위:
- Loop 1: Qdrant server 가용성 확인
- Loop 5: smoke retrieval evaluation (adapter 구현 후)
- Loop 7: CUE 제출 패키지 작성 (gold entry 작성 후)
- commit/push (Task Order 승인 후)

### 다음 보고 전까지 생성해야 할 증거 목록:
1. Qdrant server 가용성 결과 (`docker ps` 출력 또는 실패 증거)
2. 원본 문서 가용성 확인 결과 (archive.org 등 source 가용성)
3. TSU corpus build 실행 결과 (파일 목록, 건수) — Loop 2 실행 후
4. Qdrant indexing 결과 (collection, point count) — Loop 3 실행 후
5. smoke retrieval evaluation report — Loop 5 실행 후