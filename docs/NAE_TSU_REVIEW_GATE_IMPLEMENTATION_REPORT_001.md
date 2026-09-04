# NAE TSU Review Gate Implementation Report 001

**Project:** NAE-TSU-REVIEW-GATE-IMPLEMENTATION-001
**작성일:** 2026-08-07
**성격:** Review Gate 구현 — Vector Index 생성, BGE-M3 embedding 실행,
Qdrant 변경, Retrieval 변경 전부 미수행.
**Git Commit/Push:** 미수행.

---

## Phase 1 — Current State Audit

### 1. 현재 TSU schema 확인

`NAE/pipeline/tsu/claim.py::ClaimResult`(builder.py가 그대로 TSU
레코드에 반영)에 `review_status: str = "unverified"` 필드가 이미
존재한다 — 그러나 **이 값은 항상 `"unverified"` 고정**이며, 다른
어떤 값(`generated`/`reviewed`/`verified`/`rejected`)도 코드
어디에서도 할당되지 않는다(`grep` 결과 `claim.py` 1곳뿐).

### 2. review_status 필드 존재 여부

존재하지만 **단일 값(`unverified`)만 실제로 쓰인다** — 이번
작업(Phase 2)이 정의하는 4-상태 모델(`generated`/`reviewed`/
`verified`/`rejected`)은 스키마 문서 수준에서는 이번에 처음
확정되는 것이고, 기존 `"unverified"` 값과의 관계는 이번 설계에서
정리하지 않는다(WARNING, §종합).

### 3. TSU 생성 경로 확인

`NAE/pipeline/tsu/runner.py` → `NAE/pipeline/tsu/gate_adapter.py`
(Crosswalk Gate) → `builder.py::build_tsu_for_identifier()` →
`tsu_root/{identifier}/tsu.json` 저장. `review_status`는 여기서
`"unverified"`로 고정 저장된다(§1).

### 4. Embedding 입력 경로 확인(**중요 발견**)

`NAE/pipeline/index/indexer.py::load_records()`:

```python
def load_records(identifier: str, tsu_root: Path = tsu_config.TSU_ROOT) -> list[dict]:
    verified_path = tsu_root / identifier / "tsu_verified.json"
    plain_path = tsu_root / identifier / "tsu.json"
    path = verified_path if verified_path.exists() else plain_path
    ...
```

**`tsu_verified.json`이 없으면 `tsu.json`(review_status와 무관하게
전부)을 그대로 embedding 대상으로 삼는다** — 즉 현재 코드는
`review_status`를 전혀 확인하지 않고, "Phase 3.5(중복 탐지)가
실행됐는가"만 확인한다. 이것이 이번 작업의 목적(§0)이 지적한
정확한 문제 — **Review Gate가 없으면 unverified TSU가 그대로
Embedding으로 흘러간다.**

**추가 발견 — 이름 충돌**: `tsu_verified.json`의 "verified"는
`NAE/pipeline/verify/duplicate.py`(Phase 3.5 중복 탐지)가 실행됐다는
뜻이고 `score`/`duplicate_of` 필드를 담는다 — 이번 작업이 정의하는
`review_status == "verified"`(사람이 claim 품질을 확인했다는 뜻)와
**완전히 다른 개념**이다. 이 둘을 같은 이름 때문에 혼동하지 않도록
Review Gate 모듈 docstring에 명시적으로 경고를 남겼다.

### 보고

```
현재 TSU 상태 모델: review_status 필드는 존재하나 "unverified" 고정값만 실사용
변경 필요 여부: 예 — Embedding 진입점(indexer.py)이 review_status를 전혀 검사하지 않음(Gate 부재)
영향 범위: NAE/pipeline/index/indexer.py(Wiring 대상, 이번 Task는 인터페이스만 제공 — §Phase4)
```

---

## Phase 2 — Review Status Contract

```
generated  -> Embedding 불가(TSU 생성 직후 기본 상태)
reviewed   -> Embedding 불가(사람이 검토를 시작했으나 미완료)
verified   -> Embedding 허용(유일하게 허용되는 상태)
rejected   -> Embedding 불가(폐기)

+ review_status 없음(None)     -> BLOCK
+ review_status가 4개 값 밖    -> BLOCK(ERROR 상태 별도 도입하지 않음, 아래 설계 근거)
+ 빈 TSU 레코드({}/None)       -> BLOCK
```

**설계 결정(ERROR vs BLOCK)**: 이 Gate는 "잘못된 값"과 "아직 검토
전"을 구분하지 않고 전부 BLOCK으로 통합했다 — Crosswalk TSU Gate
(`scripts/crosswalk/tsu_gate.py`)가 `ERROR`를 별도로 둔 이유는
"저장소 자체가 손상됐다"는 시스템 신뢰성 문제였지만, 여기서는
TSU 레코드 하나하나가 독립적이라 한 레코드의 `review_status` 오타가
전체 저장소 신뢰성 문제로 번지지 않는다 — 단일 판정 원칙("verified만
통과, 나머지는 전부 막는다")이 더 단순하고 안전하다.

---

## Phase 3 — Review Gate Module

```
NAE/pipeline/tsu/review_gate.py (신규)
  check_tsu_review_status(tsu_record) -> ReviewGateResult(status, reason, tsu_id, review_status)
  filter_embedding_eligible(tsu_records) -> ReviewGateBatchSummary(total, pass_count, block_count, pass_records, block_details)
```

`ReviewGateStatus` = `REVIEW_GATE_PASS` / `REVIEW_GATE_BLOCK`(2-상태,
§Phase2 근거). 순수 함수 — 부작용 없음(파일 쓰기/embedding 호출/
Qdrant 접근 전부 없음).

---

## Phase 4 — Vector Pipeline 보호 Interface

```python
load_embedding_eligible_records(identifier, tsu_root) -> (list[dict], ReviewGateBatchSummary)
```

`tsu_root/{identifier}/tsu.json`을 읽어 `verified`만 반환하는 함수 —
`indexer.py::load_records()`를 대체할 인터페이스로 설계했다.

**이번 Task는 이 인터페이스를 `indexer.py`에 실제로 배선하지
않았다** — Task 지시(Vector Index 생성 금지, BGE-M3 embedding 실행
금지, Qdrant 변경 금지)와 이 프로젝트가 지금까지 지켜온 Design/
Review/Implementation 3단계 분리 관례(TSU Gate와 동일 패턴)를 따라,
"임시 filter가 아니라 Gate layer에서 차단"이라는 요구사항은 이
인터페이스 자체의 존재로 충족하되, `indexer.py` 수정(실제 배선)은
별도 승인 작업으로 남긴다(§종합 NEXT STEP).

---

## Phase 5 — Tests(29개, 요구 최소 20건 초과)

`tests/test_tsu_review_gate.py`:

| 클래스 | 개수 | 대상 |
|---|---|---|
| TestGeneratedBlocked | 2 | ①generated→BLOCK |
| TestReviewedBlocked | 2 | ②reviewed→BLOCK |
| TestVerifiedPasses | 3 | ③verified→PASS |
| TestRejectedBlocked | 2 | ④rejected→BLOCK |
| TestMissingReviewStatus | 2 | ⑤review_status 없음→BLOCK |
| TestInvalidStatus | 3 | ⑥잘못된 status→BLOCK |
| TestEmptyTsu | 2 | ⑦empty TSU→BLOCK |
| TestMultipleTsuBatch | 4 | ⑧multiple batch 처리 |
| TestSummaryCounts | 3 | ⑨summary count 확인 |
| TestLoadEmbeddingEligibleRecords | 3 | Phase4 인터페이스(파일 기반) |
| TestProductionTsuUntouched | 1 | Production TSU 무변경 재확인 |
| TestIdempotency | 2 | 반복 호출 안정성 |
| **합계** | **29** | 요구 10개 항목 전부 포함 + 초과 달성 |

```
$ pytest tests/test_tsu_review_gate.py -q
29 passed
```

### Regression(⑩)

```
$ pytest tests/test_crosswalk*.py tests/test_tsu_pipeline_wiring.py \
         tests/test_manual_crosswalk_pilot.py tests/test_tsu_review_gate.py \
         tests/test_source_validator_v2.py tests/test_validator_v22.py \
         tests/test_manifest_validator.py tests/test_authority_validator.py \
         tests/test_authority_validator_canonical.py tests/test_migration_lock.py \
         tests/test_migration_checkpoint.py tests/test_migration_engine.py \
         tests/test_registry_adapter.py tests/test_manifest_adapter.py \
         tests/test_pilot_executor.py tests/test_comment_preservation.py -q
359 passed(직전 330 + 신규 29, 감소 없음)
```

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## Phase 6 — Architecture Boundary Audit

```
$ git diff --stat core/retrieval.py NAE/pipeline/tsu/builder.py
(출력 없음 — 둘 다 0줄 변경)

$ git status --short core/ scripts/adapters/ resources/theological_sources/ docs/architecture/
(출력 없음)
```

Crosswalk schema(`scripts/crosswalk/schema.py`), Manifest, Registry,
RAW corpus, Canonical corpus — 전부 이번 작업에서 무접촉(신규 파일
`review_gate.py`가 이들 중 어느 것도 import하지 않음, 코드 확인).

---

## 완료 보고

```
STATUS: COMPLETE (Review Gate implementation — interface only, not wired into indexer.py yet)

FILES CREATED:
NAE/pipeline/tsu/review_gate.py
tests/test_tsu_review_gate.py
docs/NAE_TSU_REVIEW_GATE_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
(없음)

REVIEW STATUS MODEL:
generated/reviewed/rejected -> BLOCK, verified -> PASS(유일 허용), 없음/잘못된 값/빈 레코드 -> BLOCK(ERROR 상태 미도입, 설계 근거 §Phase2)

GATE RESULT:
check_tsu_review_status()/filter_embedding_eligible() 전부 구현·테스트 완료. 29개 테스트로 PASS/BLOCK 전 케이스 검증

TEST RESULT:
29 passed(요구 20 이상)

REGRESSION:
359 passed(직전 330 + 신규 29, 감소 없음)

VALIDATOR DRIFT:
0 (89/0/0, 138/0/0, 128/26/0)

FORBIDDEN PATH CHECK:
PASS (core/retrieval.py, builder.py 0줄 변경; Crosswalk schema/Manifest/Registry/RAW/Canonical 전부 무접촉)

BLOCKER:
0

WARNING:
2
  1. Phase 4 인터페이스(`load_embedding_eligible_records`)가 아직 `NAE/pipeline/index/indexer.py`에 배선되지 않음 — 지금 `indexer.py::load_records()`를 그대로 실행하면 `tsu_verified.json`이 없는 한 review_status와 무관하게 전부 embedding 대상이 됨(§Phase1 발견 그대로 유지, "Vector Index 생성 금지" 제약 때문에 이번 Task는 배선하지 않음)
  2. `tsu_verified.json`(Phase 3.5 중복탐지)과 `review_status="verified"`(사람 검토)가 "verified"라는 이름을 공유하나 의미가 다름 — 향후 두 개념을 하나의 파일/필드로 통합할지, 계속 분리 유지할지 별도 설계 결정 필요

NEXT STEP:
NAE-TSU-REVIEW-GATE-WIRING-001(가칭) — indexer.py::load_records()를 review_gate.load_embedding_eligible_records()로 교체하는 별도 승인 작업. 그 전까지는 실제 Vector Index/embedding 실행을 하지 않는 것을 강력히 권고(Gate가 아직 실행 경로에 연결되지 않았으므로)

GIT:
NOT PERFORMED
```
