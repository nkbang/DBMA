# NAE C1 Status and Next-Work Report
- Report date: 2026-07-31
- Repository: DBMA (https://github.com/nkbang/DBMA.git / nas: http://100.94.139.122:3000/David/DBMA.git)
- Branch: `dev/nae-benchmark-contract`
- HEAD commit: `403ab6581210d1fb77ef5a6508c84a4d40724fb8` (2026-07-31 13:39 UTC)
- Local working tree: clean (uncommitted changes 없음)
- Report scope: NAE Phase 5.1/5.2 전체 현황 — benchmark, evaluator, runner, corpus, Qdrant index, gold authoring, evidence
- Evidence inspected:
  - `git status --short`, `git log --oneline -30`
  - `NAE/benchmark/schema.py`, `NAE/benchmark/loader.py`, `NAE/benchmark/runner.py`, `NAE/benchmark/evaluator.py`, `NAE/benchmark/metrics.py`
  - `NAE/benchmark/datasets/benchmark_v1.jsonl` (dataset 존재)
  - `NAE/docker-compose.yml` (Qdrant compose)
  - `curl http://localhost:7333/collections/nae_tsu_v1` (Qdrant collection 상태)
  - `docs/STATE.md`, `docs/SPRINT33-D-preflight-issues.md`, `docs/TODO.md`
  - `evidence/phase5_1_contract/README.md`, `evidence/phase5_2/gold-authoring-skeleton-report.md`
  - `tests/test_nae_benchmark_schema.py`, `tests/test_nae_benchmark_loader.py`, `tests/test_nae_benchmark_metrics.py`, `tests/test_nae_benchmark_contract.py`
  - pytest 실행 결과 (89 tests: 86 passed, 3 failed)

## 1. Executive Status

| 영역 | 상태 | 근거 | 차단 요인 |
|---|---|---|---|
| Phase 5.1 contract | PARTIAL | `evidence/phase5_1_contract/README.md` 존재, `docs/STATE.md` §3.2에 "완료 보고" — 그러나 benchmark schema/loader/evaluator 간 contract gap 존재 (UNVERIFIED) | 없음 — 다만 gold entry schema 정합성 문제 확인 |
| Phase 5.2 gold authoring | IN PROGRESS | `evidence/phase5_2/gold-authoring-skeleton-report.md` skeleton만 존재, 실제 gold entry 작성 증거 없음 | human review 프로세스 미정착, TSU corpus build 선행 필요 |
| Benchmark schema/loader/validation | PARTIAL — schema gap 있음 | `NAE/benchmark/schema.py::BenchmarkEntrySchema`에 `gold_tsu_ids` 필드 정의 확인됨. 그러나 loader가 schema 검증 엄격하게 적용하는지 미확인 | gold entry 스키마 정합성 검증 테스트 부족 |
| Evaluator `gold_tsu_ids` rewire | PARTIAL — 코드 존재, 검증 필요 | `NAE/benchmark/evaluator.py`에 `gold_tsu_ids` 기반 판정 로직 구현됨. 그러나 실제 Qdrant retrieval 평가 연결 여부 미확인 | Qdrant index empty (points_count=0)로 실제 평가 불가 |
| Runner actual retrieval injection | PARTIAL — dummy 제거 확인 | `NAE/benchmark/runner.py:99`에서 `_dummy_retrieval()` silent path 제거 확인. 그러나 실제 retriever 주입 경로 미확인 | retriever adapter 미구현 또는 연결 증거 부족 |
| TSU corpus build | NOT STARTED / BLOCKED | `NAE/corpus/` 디렉터리 존재하지만 실제 corpus 데이터 생성 증거 없음. STATE.md §3.1에서 "corpus build 선행" 필요하다고 명시 | TSU dataset → corpus 인제스트 pipeline 미실행 |
| Qdrant indexing | PARTIAL — collection 존재, index empty | `curl http://localhost:7333/collections/nae_tsu_v1`: `points_count=0`, `indexed_vectors_count=0`. Collection schema는 정의됨 | corpus build 후 indexing 필요 |
| Retrieval metrics | UNVERIFIED | `NAE/benchmark/metrics.py`에 Precision@K, Recall@K, MRR, nDCG 정의 확인. 그러나 실제 실행 증거 없음 (Qdrant empty) | Qdrant index + 실제 retrieval pipeline 연결 필요 |
| Evidence and audit trail | PARTIAL | `evidence/phase5_1_contract/` 하에 README, manifest.json, self-check-050.md, cue-submission-request.md 존재. `evidence/phase5_2/` skeleton 보고만 있음 | Phase 5.2 gold authoring evidence 미생성 |

## 2. Verified Completed Work

### Work item: Phase 5.1 Benchmark Infrastructure Code
- Status: REPORTED COMPLETE (STATE.md §3.2에서 "완료" 보고)
- Evidence:
  - Files: `NAE/benchmark/schema.py`, `NAE/benchmark/loader.py`, `NAE/benchmark/runner.py`, `NAE/benchmark/evaluator.py`, `NAE/benchmark/metrics.py`
  - Commit SHA: `403ab6581210d1fb77ef5a6508c84a4d40724fb8` (HEAD, branch `dev/nae-benchmark-contract`)
  - Test or command result: pytest 89 tests — 86 passed, 3 failed (UNVERIFIED: 3개 실패가 benchmark contract에 영향)
- Notes: 코드 구조는 완성되었으나, gold entry schema 정합성 검증 테스트 부족. 3개 실패 테스트 확인 필요.

### Work item: Qdrant NAE Instance Provisioning
- Status: VERIFIED COMPLETE
- Evidence:
  - File: `NAE/docker-compose.yml` — `nae_qrnt` 서비스 정의 (port 7333)
  - Command: `docker ps` — `6eee16980812 qdrant/qdrant:latest ... nae_qrnt` (Up 12 hours)
  - Command: `curl http://localhost:7333/collections` — `{"collections":[{"name":"nae_tsu_v1"}]}`
- Notes: Qdrant 컨테이너는 실행 중이고 collection은 생성됨. 그러나 points_count=0.

### Work item: Benchmark Dataset Skeleton
- Status: REPORTED COMPLETE
- Evidence:
  - File: `NAE/benchmark/datasets/benchmark_v1.jsonl` — 파일 존재
  - Commit SHA: HEAD에 포함
- Notes: dataset schema가 gold_tsu_ids 기반인지, 실제 entry가 채워졌는지 확인 필요.

### Work item: Evidence Directory Structure
- Status: VERIFIED COMPLETE
- Evidence:
  - Directory: `evidence/phase5_1_contract/` — README.md, manifest.json, self-check-050.md, cue-submission-request.md
  - Directory: `evidence/phase5_2/` — gold-authoring-skeleton-report.md (skeleton만)
- Notes: Phase 5.2 evidence는 skeleton 상태.

## 3. In-Progress and Unverified Work

### 작업명: Phase 5.2 Gold Authoring — 실제 gold entry 작성
- 현재 실제 상태: skeleton 보고만 있음, 실제 gold entry 작성 안 됨
- 이미 존재하는 산출물: `evidence/phase5_2/gold-authoring-skeleton-report.md`
- 누락된 산출물: 실제 gold_tsu_ids 목록, human review 기록, 출처·문맥·TSU ID 추적성
- 의존성: TSU corpus build → Qdrant indexing → gold entry 작성
- 위험도: A
- 다음에 해야 할 단 하나의 행동: `scripts/author_gold_set.py` 실행 또는 gold authoring 스크립트 작성 및 human review 프로세스 정의

### 작업명: Evaluator `gold_tsu_ids` 기반 정답 판정 검증
- 현재 실제 상태: 코드 존재, 그러나 3개 테스트 실패로 검증 불완전
- 이미 존재하는 산출물: `NAE/benchmark/evaluator.py`
- 누락된 산출물: gold_tsu_ids 기반 판정이 실제 Qdrant retrieval과 연결되어 평가되는지 확인하는 end-to-end smoke test
- 의존성: Qdrant index populated → evaluator rewire 검증
- 위험도: A
- 다음에 해야 할 단 하나의 행동: 실패한 3개 테스트 원인 분석 및 수정

### 작업명: Runner 실제 retriever 주입 및 dummy 제거 확인
- 현재 실제 상태: `_dummy_retrieval()` silent path 제거 확인됨. 그러나 실제 retriever adapter 연결 증거 미확인
- 이미 존재하는 산출물: `NAE/benchmark/runner.py`
- 누락된 산출물: retriever adapter가 runner에 주입되어 실제 Qdrant 조회를 하는지 확인
- 의존성: Qdrant index populated → runner-retriever 연결 검증
- 위험도: B
- 다음에 해야 할 단 하나의 행동: `runner.py`에서 retriever adapter 주입 경로 grep 및 실제 Qdrant 호출 추적

### 작업명: TSU Corpus Build
- 현재 실제 상태: NOT STARTED (NAE/corpus/ 디렉터리만 존재)
- 이미 존재하는 산출물: 없음
- 누락된 산출물: corpus 인제스트 스크립트 실행, corpus 데이터 파일
- 의존성: 없음 (첫 번째 선행 작업)
- 위험도: A
- 다음에 해야 할 단 하나의 행동: TSU dataset에서 corpus 인제스트 스크립트 작성/실행

### 작업명: Qdrant Index Population
- 현재 실제 상태: collection 존재, points_count=0 (empty)
- 이미 존재하는 산출물: `nae_tsu_v1` collection schema
- 누락된 산출물: corpus embedding → Qdrant point upload 스크립트 실행
- 의존성: TSU corpus build 완료
- 위험도: A
- 다음에 해야 할 단 하나의 행동: corpus build 후 embedding + Qdrant point upload

## 4. Open Issues and Contradictions

### CRITICAL: pytest 3개 실패 — benchmark contract 검증 불완전
- 분류: CRITICAL
- 설명: pytest 89 tests 중 3개 실패. 실패 테스트가 benchmark schema/loader/evaluator 간 contract gap을 드러냄.
- 근거: `pytest` 실행 결과 — 86 passed, 3 failed
- 구체적 실패 테스트명:
  1. `tests/test_nae_benchmark_metrics.py::TestRecallAtK::test_recall_empty_relevant` (line 49)
  2. `tests/test_nae_benchmark_metrics.py::TestPrecisionAtK::test_precision_duplicate_retrieved_not_double_counted` (line 123)
  3. `tests/test_nae_benchmark_metrics.py::TestComputeAllMetrics::test_compute_all_metrics_empty_relevant` (line 234)

### HIGH: Qdrant collection empty (points_count=0)
- 분류: HIGH
- 설명: `nae_tsu_v1` collection은 존재하지만 인덱스 비어 있음. 실제 retrieval 평가 불가.
- 근거: `curl http://localhost:7333/collections/nae_tsu_v1` — `{"points_count": 0}`
- 영향: retrieval metrics, evaluator rewire 모두 UNVERIFIED

### HIGH: corpus build 미실행
- 분류: HIGH
- 설명: `NAE/corpus/` 디렉터리만 존재, 실제 corpus 데이터 없음.
- 근거: `list_files(NAE/corpus/)` — 비어있거나 skeleton만 존재
- 영향: Qdrant indexing 불가 → retrieval 평가 불가

### MEDIUM: gold authoring skeleton만 존재
- 분류: MEDIUM
- 설명: `evidence/phase5_2/gold-authoring-skeleton-report.md`는 skeleton. 실제 gold entry 작성 안 됨.
- 근거: 파일 존재 확인, 그러나 content가 skeleton임
- 영향: Phase 5.2 목적 (human-reviewed gold benchmark 작성) 미달성

### MEDIUM: 문서와 코드의 상태 불일치
- 분류: MEDIUM
- 설명: STATE.md §3.2에서 Phase 5.1 "완료"로 보고하나, benchmark schema/loader 간 contract gap과 pytest 실패가 있음.
- 근거: `docs/STATE.md` §3.2 vs `pytest` 결과 (3 failures)
- 영향: "완료" 선언의 신뢰성 저하

### LOW: dummy retrieval 코드 잔존 여부
- 분류: LOW
- 설명: `runner.py:99`에 `_dummy_retrieval()` 관련 메시지 잔존. 그러나 "removed" 메시지가 있으므로 실제 코드는 제거된 것으로 보임.
- 근거: `grep "dummy" NAE/benchmark/runner.py` — 1줄만 매칭
- 영향: 낮 — 코드 삭제 후 cleanup 미비로 추정

## 5. Dependency-Ordered Next Plan

| Loop | 작업 | 선행 조건 | 산출물 | 검증 방법 | Evidence 경로 | 위험도 | 완료 정의 |
|---|---|---|---|---|---|---|---|
| 1 | TSU Corpus Build | 없음 | corpus 인제스트 스크립트 실행, corpus 데이터 파일 | `NAE/corpus/`에 실제 파일 생성 확인 | corpus 파일 목록 | A | corpus에 ≥1개 문서 파일 존재 |
| 2 | Qdrant Index Population | Loop 1 완료 | embedding + Qdrant point upload | `curl .../nae_tsu_v1`에서 `points_count > 0` | Qdrant API 응답 | A | indexed_vectors_count > 0 |
| 3 | Evaluator `gold_tsu_ids` rewire 검증 | Loop 2 완료 | smoke retrieval 평가 스크립트 | 실제 Qdrant 조회 → evaluator 판정 → metrics 계산 | smoke test 실행 결과 | A | 3개 실패 테스트 통과 + smoke 평가 통과 |
| 4 | Runner retriever adapter 연결 검증 | Loop 2 완료 | runner-retriever 연결 확인 | `runner.py`에서 실제 Qdrant 호출 추적 | runner 코드 grep + 실행 로그 | B | runner가 Qdrant에 실제 조회 요청 |
| 5 | Phase 5.2 Gold Authoring | Loop 1 완료 | gold entry 작성 (gold_tsu_ids 기반), human review 기록 | `evidence/phase5_2/`에 실제 gold entry 파일 생성 | gold entry 파일 존재 + content 검증 | A | ≥1개 gold entry가 gold_tsu_ids + 출처 + 문맥 포함 |
| 6 | CUE 검토 제출 패키지 | Loop 3, 5 완료 | CUE 제출 문서 + evidence bundle | `evidence/phase5_2/cue-submission.md` 생성 | 제출 파일 존재 | B | CUE 파일에 Phase 5.2 gold authoring 결과 요약 |
| 7 | P1 감사 제출 패키지 | Loop 6 + HQ 승인 | P1 제출 문서 + evidence bundle | `evidence/phase5_2/p1-audit-request.md` 생성 | 제출 파일 존재 | B | P1 파일에 gold entry 검증 요청 포함 |

## 6. Immediate Recommendation

### 지금 즉시 시작해야 할 Loop: Loop 1 (TSU Corpus Build)
- corpus build가 선행되지 않으면 Qdrant indexing, retrieval 평가, gold authoring 모두 불가.
- 가장 근본적인 선행 작업.

### 지금 하면 안 되는 작업:
- Loop 6 (CUE 제출): corpus/build → indexing → evaluation이 선행되지 않은 상태에서의 제출은 근거 없음.
- Loop 5 (Gold Authoring): corpus가 없으면 gold entry 작성 불가 (TSU ID 매핑 필요).
- 코드 리팩터링: 현황 파악 및 evidence 수집 완료 전까지 금지.

### HQ 또는 CUE 판단이 필요한 사항:
- Phase 5.1 "완료" 선언 재검토: STATE.md §3.2에서 완료 보고했으나 pytest 3개 실패와 schema contract gap 존재. HQ가 "완료" 재판단 필요.
- gold authoring 범위: 어떤 theological source를 gold entry 기준으로 사용할지 HQ 결정 필요.

### C1이 단독 수행 가능한 범위:
- Loop 1 (corpus build): TSU dataset에서 corpus 인제스트
- Loop 2 (Qdrant indexing): corpus embedding + point upload
- Loop 3, 4 (evaluator/runner 검증): 코드 grep + smoke test 실행
- Loop 5 (gold authoring 스크립트 작성): HQ가 source 결정 후 실행

### 다음 보고 전까지 생성해야 할 증거 목록:
1. corpus 인제스트 실행 결과 (`NAE/corpus/` 파일 목록)
2. Qdrant points_count > 0 확인 (`curl` 출력)
3. pytest 재실행 결과 (3개 실패 해결 후 89/89 passed)
4. smoke retrieval 평가 결과 (metrics 계산 출력)
5. gold authoring 스크립트 실행 결과 (`evidence/phase5_2/gold-entries.jsonl` 또는 유사 파일)