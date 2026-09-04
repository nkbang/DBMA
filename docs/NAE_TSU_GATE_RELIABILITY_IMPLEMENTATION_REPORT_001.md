# NAE TSU Gate Reliability Implementation Report 001

**Project:** NAE-TSU-GATE-RELIABILITY-IMPLEMENTATION-001
**작성일:** 2026-08-05
**성격:** C1 `NAE-TSU-GATE-CONNECTION-REVIEW-001` 승인 조건(3개) 구현 —
TSU Pipeline 실행, TSU 생성, Crosswalk record 생성, Production corpus
변경 전부 미수행.
**Git Commit/Push:** 미수행 — C1 Review 승인 전까지 대기.

---

## 1. Summary

C1의 3개 조건을 전부 구현했다:

1. `TSU_GATE_ERROR` 상태 추가(`scripts/crosswalk/tsu_gate.py`)
2. Crosswalk Storage corruption detection 추가
   (`scripts/crosswalk/storage/yaml_repository.py`)
3. Gate Orchestrator 구현(`scripts/crosswalk/gate_orchestrator.py`, 신규)

구현 과정에서 **실제 버그 하나를 발견해 수정**했다(§3) — 신규
저장소를 만들자마자(레코드 0건 상태) `validate_storage()`를 호출하면
`index.json`이 아직 없다는 이유로 거짓 `ERROR`가 나는 문제였다.
Repository 생성자가 `crosswalk.yaml`과 함께 `index.json`도 초기화
하도록 고쳐서 해결했다.

---

## 2. Files

### 생성

```
scripts/crosswalk/gate_orchestrator.py
tests/test_crosswalk_storage_corruption.py
tests/test_crosswalk_gate_orchestrator.py
docs/NAE_TSU_GATE_RELIABILITY_IMPLEMENTATION_REPORT_001.md
```

### 변경

```
scripts/crosswalk/tsu_gate.py              # TsuGateStatus(PASS/BLOCK/ERROR) 추가, eligible은 하위호환 property로 유지
scripts/crosswalk/storage/yaml_repository.py  # check_parse/check_schema/check_index_consistency/validate_storage 추가, 생성자 index 초기화 버그 수정
tests/test_crosswalk_tsu_gate.py            # ERROR/상태값 검증 테스트 9개 추가(11→20)
```

절대 변경 금지 목록(`core/`, `scripts/migration_engine.py`,
`scripts/adapters/`, `NAE/corpus/{raw,canonical,tsu}`,
`resources/theological_sources/`, `docs/ADR-*`) 어디에도 손대지
않았다(§6).

---

## 3. Phase 1 — TSU_GATE_ERROR State

```python
class TsuGateStatus(str, Enum):
    PASS = "TSU_GATE_PASS"
    BLOCK = "TSU_GATE_BLOCK"
    ERROR = "TSU_GATE_ERROR"
```

`check_tsu_gate()`에 `storage_error: str | None = None` 파라미터를
추가 — 주어지면 다른 어떤 조건보다 우선해 즉시 `ERROR`를 반환한다
(§NAE_TSU_GATE_CONNECTION_DESIGN_001.md §4 설계 그대로: "저장소를
신뢰할 수 없으면 그 안의 어떤 판정도 신뢰할 수 없다").

**하위 호환성**: 기존 `TsuGateResult.eligible`(bool)을 `status ==
PASS`로 계산하는 `@property`로 유지 — 기존 61개(→104개) 테스트가
전부 코드 수정 없이 그대로 통과했다(§5).

### 구현 중 발견한 버그(신규 저장소 오탐)

`YamlCrosswalkRepository.__init__`은 `crosswalk.yaml`이 없으면
생성했지만 `index.json`은 `add()` 호출 전까지 만들지 않았다 — 그
사이 `validate_storage()`를 호출하면 "index.json 없음"으로 **정상
상태를 ERROR로 오판**했다. 수동 테스트(`python3 -c ...`)로 실제
재현·확인한 뒤, 생성자에서 `index.json`도 함께 초기화하도록 수정했다:

```python
if self.index_manager is not None and not self.index_manager.index_path.exists():
    self._refresh_index(self.list_all())  # 빈 목록 -> index.json = {}
```

`tests/test_crosswalk_storage_corruption.py::TestFreshRepositoryIsValid`
가 이 수정을 회귀 방지 테스트로 고정한다.

---

## 4. Phase 2 — YAML Corruption Detection

`YamlCrosswalkRepository`에 3개 검사 + 1개 통합 메서드 추가:

| 메서드 | 검사 내용 | 실패 시 |
|---|---|---|
| `check_parse()` | YAML 파싱 가능 여부(Check 1) | `(False, "YAML parse 실패: ...")` |
| `check_schema()` | 레코드별 5개 필수 필드(`crosswalk_id`/`source_identifier`/`target_identifier`/`mapping_status`/`confidence`) 키 존재(Check 2) | `(False, "...필수 필드 누락: [...]")` |
| `check_index_consistency()` | `index.json`이 `crosswalk.yaml`로부터 다시 계산한 값과 일치하는지(Check 3) | `(False, "...불일치(rebuild 가능 상태...)")` — **자동 복구하지 않음** |
| `validate_storage()` | 위 3개를 순서대로 실행, 첫 실패에서 중단 | `(False, 사유)` |

**YAML authority 원칙 재확인**: `check_index_consistency()`가
불일치를 발견해도 `index.json`을 다시 쓰지 않는다 — "rebuild 가능한
상태"라는 사실만 보고하고, 실제 재생성은 호출자가
`IndexManager.rebuild()`를 명시적으로 호출해야 한다(`tests/
test_crosswalk_storage_corruption.py::TestBrokenIndex::
test_index_mismatch_detected_not_silently_fixed`가 "값이 여전히
WRONG"임을 직접 확인).

---

## 5. Phase 3 — Gate Orchestrator

```
Manifest Entry(ManifestEntryInput: source_identifier, tsu_eligible)
        │
        ▼
[repository에 validate_storage()가 있으면 먼저 호출]
        │  실패 시 → check_tsu_gate(storage_error=...) → ERROR
        ▼
CrosswalkResolver.resolve_record(source_identifier)
        │  예외 발생 시 → check_tsu_gate(storage_error=str(exc)) → ERROR
        ▼
check_tsu_gate(tsu_eligible, record) → PASS/BLOCK
```

`GateOrchestrator`는 `scripts.crosswalk.repository`/`resolver`/
`tsu_gate` 3개만 import한다 — AST 파싱으로 구조적으로 재확인
(`tests/test_crosswalk_gate_orchestrator.py::TestArchitectureBoundary`):

```
$ grep -n "^from\|^import" scripts/crosswalk/gate_orchestrator.py
from dataclasses import dataclass
from .repository import CrosswalkRepository
from .resolver import CrosswalkResolver
from .tsu_gate import TsuGateResult, check_tsu_gate
```

`NAE/pipeline/tsu`, `core.retrieval`, `core.tsu_builder`,
`NAE/pipeline/embed` 어느 것도 등장하지 않는다 — TSU 생성/Manifest
수정/RAW 접근/Retrieval 호출/Embedding 생성 중 어느 것도 코드
구조상 불가능하다.

---

## 6. Tests

| 파일 | 테스트 수 | 요구 최소 | 대상 |
|---|---|---|---|
| `tests/test_crosswalk_tsu_gate.py` | 20(기존 11 + 신규 9) | 15 | PASS/BLOCK/ERROR 3개 상태, 하위호환, Idempotency |
| `tests/test_crosswalk_storage_corruption.py`(신규) | 13 | 10 | invalid YAML/missing field/broken index/schema mismatch/자동복구 없음 확인 |
| `tests/test_crosswalk_gate_orchestrator.py`(신규) | 10 | 10 | resolver→validator→gate flow(PASS/BLOCK/ERROR 3경로), Architecture Boundary(AST 검사), Idempotency |
| **합계(신규 3개 파일 기준)** | **43** | 35 | 요구치 초과 |
| **Crosswalk 전체** | **139**(기존 104 + 신규 35, tsu_gate 순증분 포함) | | |

```
$ pytest tests/test_crosswalk_tsu_gate.py tests/test_crosswalk_storage_corruption.py \
         tests/test_crosswalk_gate_orchestrator.py -q
43 passed in 0.18s

$ pytest tests/test_crosswalk*.py -q
139 passed in 0.21s
```

---

## 7. Regression

```
$ pytest tests/test_source_validator_v2.py tests/test_validator_v22.py \
         tests/test_manifest_validator.py tests/test_authority_validator.py \
         tests/test_authority_validator_canonical.py tests/test_migration_lock.py \
         tests/test_migration_checkpoint.py tests/test_migration_engine.py \
         tests/test_registry_adapter.py tests/test_manifest_adapter.py \
         tests/test_pilot_executor.py tests/test_comment_preservation.py \
         tests/test_crosswalk_schema.py tests/test_crosswalk_repository.py \
         tests/test_crosswalk_validator.py tests/test_crosswalk_resolver.py \
         tests/test_crosswalk_tsu_gate.py tests/test_crosswalk_storage.py \
         tests/test_crosswalk_storage_corruption.py tests/test_crosswalk_gate_orchestrator.py -q
288 passed in 0.66s
```

**288 passed**(직전 253 + 신규 35, 감소 없음).

### Validator

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 8. Forbidden Scope Verification

```
$ git status --short core/ scripts/migration_engine.py scripts/adapters/ \
    NAE/corpus/raw NAE/corpus/canonical NAE/corpus/tsu \
    resources/theological_sources/ docs/architecture/
(출력 없음)

$ grep -c "crosswalk_id" NAE/metadata/crosswalk/crosswalk.yaml
0
```

**금지 영역 변경 0. Crosswalk records 여전히 0건.**

---

## 완료 보고

```
STATUS: COMPLETE (TSU Gate reliability implementation only — no TSU execution, no mapping records created)

FILES CREATED:
scripts/crosswalk/gate_orchestrator.py
tests/test_crosswalk_storage_corruption.py
tests/test_crosswalk_gate_orchestrator.py
docs/NAE_TSU_GATE_RELIABILITY_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
scripts/crosswalk/tsu_gate.py (TsuGateStatus PASS/BLOCK/ERROR 추가, eligible 하위호환 유지)
scripts/crosswalk/storage/yaml_repository.py (corruption detection 3종 + validate_storage 추가, 신규 저장소 오탐 버그 수정)
tests/test_crosswalk_tsu_gate.py (ERROR/상태 검증 테스트 9개 추가)

TEST RESULT:
신규 3개 파일 43 passed(요구 35 이상 충족: Gate 20/요구15, Corruption 13/요구10, Orchestrator 10/요구10)
Crosswalk 전체: 139 passed

REGRESSION RESULT:
288 passed(기존 253 + 신규 35, 감소 없음)

VALIDATOR DRIFT:
0 (source 89/0/0, manifest 138/0/0, authority 128/26/0 — 전부 baseline 일치)

FORBIDDEN PATH CHECK:
PASS (core/, migration_engine.py, adapters/, NAE/corpus/{raw,canonical,tsu}, resources/theological_sources/, docs/architecture/ 전부 git status 빈 결과)

BLOCKER:
0

WARNING:
0

NEXT STEP:
C1 TSU Gate Reliability Review 요청 → 승인 후 TSU Pipeline Resume Preflight(Crosswalk Record Population Design + Manual Mapping Approval 선행) → TSU Pipeline Activation

GIT:
NOT PERFORMED
```
