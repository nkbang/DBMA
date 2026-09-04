# NAE Crosswalk Adapter Implementation Report 001

**Project:** NAE-CROSSWALK-ADAPTER-IMPLEMENTATION-001
**작성일:** 2026-08-05
**성격:** Crosswalk 데이터 구조/Adapter/Validator/TSU Gate Interface 구현
— 실제 TSU 생성, Corpus Migration, Retrieval 코드 수정, 실제 매핑 생성
전부 미수행.
**Git Commit/Push:** 미수행 — C1 Review 승인 전까지 대기.

---

## 1. Executive Summary

C1 승인된 `NAE_IDENTIFIER_CROSSWALK_SCHEMA_001.md`/`NAE_IDENTIFIER_
CROSSWALK_MAPPING_POLICY_001.md`/`NAE_TSU_IDENTIFIER_CONTRACT_001.md`
를 실제 코드로 옮겼다. `scripts/crosswalk/` 5개 모듈(schema/repository/
validator/resolver/tsu_gate) + 신규 테스트 4개 파일(61 테스트)을
작성했다. **저장 위치(ADR-019 Storage Decision)는 여전히 확정하지
않았다** — `CrosswalkRepository`는 추상 인터페이스이고, 제공된
`InMemoryCrosswalkRepository`는 명시적으로 "참조/테스트용, production
storage 결정 아님"으로 문서화했다.

실제 매핑 레코드는 **이번 구현에서 0건도 생성하지 않았다** — 코드와
테스트는 전부 합성(synthetic) fixture만 사용했다.

---

## 2. 구현 내용

| 파일 | 역할 |
|---|---|
| `scripts/crosswalk/__init__.py` | 패키지 docstring, storage-agnostic 원칙 명시 |
| `scripts/crosswalk/schema.py` | `CrosswalkRecord` dataclass, 4개 enum(`SourceType`/`TargetType`/`MappingStatus`/`Confidence`), `confidence_score()`, `CrosswalkRecord.is_gate_eligible()` |
| `scripts/crosswalk/repository.py` | `CrosswalkRepository`(ABC) + `InMemoryCrosswalkRepository`(참조 구현) |
| `scripts/crosswalk/validator.py` | `validate()` — Check 1~5(중복 ID/중복 source-target 쌍/evidence 누락/mapping_status·confidence 정합성/Broken Reference) |
| `scripts/crosswalk/resolver.py` | `CrosswalkResolver.resolve()`/`resolve_record()` — exact match만, fuzzy/추론 없음 |
| `scripts/crosswalk/tsu_gate.py` | `check_tsu_gate()` — TSU_ELIGIBLE ∧ mapping_status=manual-confirmed 판정, 순수 함수(부작용 없음) |

### 계층 분리 확인

```
scripts/adapters/*, scripts/migration_engine.py  ← 무수정(import 없음)
NAE/pipeline/tsu/*                                ← 무수정(import 없음)
        ▲
        │ (아직 배선되지 않음 — Contract 001 §5 그대로)
scripts/crosswalk/*                                ← 신규, 독립 패키지
```

`scripts/crosswalk/`는 Migration Engine/Adapter나 TSU Pipeline 어느
것도 import하지 않는다 — 반대로 그쪽에서 `scripts/crosswalk`를
import하는 코드도 이번 구현에서 추가하지 않았다(§7 "구현 금지: TSU
Builder 변경/Manifest 변경/Pipeline 변경" 그대로 준수).

---

## 3. Confidence 필드 처리에 대한 설계 판단(명시적 기록)

작업 명령서 §4 Rule 2는 "confidence < 1.0 → unresolved"로 **수치
비교**를 요구했으나, C1이 이미 승인한 `NAE_IDENTIFIER_CROSSWALK_
SCHEMA_001.md`는 `confidence`를 **enum**(`high`/`medium`/`low`)으로
정의했다. 두 요구사항이 문자 그대로는 다른 타입을 전제하고 있어,
스키마 필드 타입을 바꾸는 대신 **enum은 그대로 유지하고, Gate 판정
전용 수치 매핑**(`CONFIDENCE_SCORE = {HIGH: 1.0, MEDIUM: 0.66,
LOW: 0.33}`)을 추가해 두 문서 요구사항을 동시에 만족시켰다:

- 이미 승인된 Schema 001의 필드 타입(enum) — **변경 없음**
- 이번 작업 명령서의 "confidence < 1.0 → unresolved" 규칙 —
  `confidence_score(confidence) < 1.0`로 그대로 구현(사실상
  `HIGH`만 Gate를 통과)

이것이 Architecture Freeze Rule 정신에 부합하는 해석이라고 판단해
**중단 후 확인 절차를 밟지 않고 진행**했다 — 두 요구사항이 실제로는
호환 가능했기 때문이다(이전 canonical_id UPPER_SNAKE_CASE 사례처럼
값 자체가 반대 방향이라 절충 불가능한 충돌이 아니었음). C1 Review
시 이 판단의 타당성을 재검토해 줄 것을 요청한다(§완료 보고
NEXT STEP).

---

## 4. Mapping Policy Rule 구현 확인

| Rule | 구현 위치 | 강제 방식 |
|---|---|---|
| Rule 1(추측 매핑 금지) | `schema.py`의 `MappingStatus` enum — `auto-guessed`/`inferred`/`unknown-match` 같은 값은애초에 `CrosswalkRecord` 생성 자체가 `ValueError`로 실패(구조적으로 존재 불가능). `validator.py`에 방어적 이중 검사(`_EXPLICITLY_FORBIDDEN_STATUS_STRINGS`)도 추가 | 코드 레벨 강제(런타임 예외) |
| Rule 2(Confidence Gate, confidence < 1.0 → unresolved) | `schema.py::confidence_score()` + `CrosswalkRecord.is_gate_eligible()` + `resolver.py::resolve()` | `HIGH`(1.0)만 통과, `MEDIUM`/`LOW`는 `resolve()`가 `None` 반환 |
| Rule 3(Evidence 필수, manual-confirmed) | `schema.CrosswalkRecord.is_gate_eligible()`(Gate 레벨) + `validator._check_missing_evidence()`(배치 검증 레벨) | 이중 강제 — Resolver가 evidence 없는 레코드를 애초에 반환하지 않고, Validator가 별도로 배치 전체를 훑어 FAIL 보고 |

---

## 5. 테스트

| 파일 | 테스트 수 | 대상 |
|---|---|---|
| `tests/test_crosswalk_schema.py` | 19 | 구성/직렬화/confidence_score/Gate eligibility |
| `tests/test_crosswalk_validator.py` | 15 | Check 1~5, 빈 입력, Idempotency |
| `tests/test_crosswalk_resolver.py` | 16 | resolve 성공/실패(6가지 실패 사유)/exact-match-only(fuzzy 금지 실증)/Idempotency |
| `tests/test_crosswalk_tsu_gate.py` | 11 | Gate PASS/6가지 BLOCKED 사유/Idempotency |
| **합계** | **61** | 요구 최소 30건의 2배 이상, 전부 PASS |

```
tests/test_crosswalk_schema.py + test_crosswalk_validator.py +
test_crosswalk_resolver.py + test_crosswalk_tsu_gate.py            : 61 passed
```

---

## 6. Regression

```
tests/test_source_validator_v2.py + test_validator_v22.py +
test_manifest_validator.py + test_authority_validator.py +
test_authority_validator_canonical.py + test_migration_lock.py +
test_migration_checkpoint.py + test_migration_engine.py +
test_registry_adapter.py + test_manifest_adapter.py +
test_pilot_executor.py + test_comment_preservation.py +
test_crosswalk_*(4개 파일)                                          : 210 passed(직전 149 + 신규 61, 감소 없음)

source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

### 금지 목록 준수 확인

```
$ git status --short core/ NAE/corpus/raw NAE/corpus/canonical NAE/pipeline/tsu scripts/migration_engine.py scripts/adapters/ docs/architecture/
(출력 없음 — 전부 무변경)
```

---

## 완료 보고

```
STATUS: COMPLETE (Crosswalk data structure/Adapter/Validator/TSU Gate interface only — no TSU generation, no Corpus migration, no Retrieval changes, no real mappings created)

FILES CREATED:
scripts/crosswalk/__init__.py
scripts/crosswalk/schema.py
scripts/crosswalk/repository.py
scripts/crosswalk/validator.py
scripts/crosswalk/resolver.py
scripts/crosswalk/tsu_gate.py (Phase 7 interface, 예상 목록 외 추가 — TSU Gate Adapter 요구사항 충족을 위해 별도 파일로 분리)
tests/test_crosswalk_schema.py
tests/test_crosswalk_validator.py
tests/test_crosswalk_resolver.py
tests/test_crosswalk_tsu_gate.py (예상 목록 외 추가)
docs/NAE_CROSSWALK_ADAPTER_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
(없음)

CROSSWALK STATUS:
스키마/Repository 인터페이스/Validator/Resolver/TSU Gate 전부 구현·테스트 완료. 실제 매핑 레코드 0건(합성 fixture만 사용). 저장 위치 미확정(ADR-019 조건부 보류 유지 — InMemoryCrosswalkRepository는 참조 구현일 뿐).

VALIDATOR RESULT:
Crosswalk Validator(신규, 독립) 61개 테스트 전부 PASS. 기존 3-Validator는 무수정.

REGRESSION:
PASS — 210 passed(직전 149 + 신규 61), source/manifest/authority validator 전부 baseline과 완전 일치(DRIFT=0)

ADR IMPACT:
없음(ADR-001/014~019 전부 무변경) — Confidence 필드 처리는 승인된 Schema 001의 enum 타입을 유지하면서 작업 명령서의 수치 규칙을 병행 구현하는 방식으로 해결(§3), ADR 재검토 불필요로 판단

BLOCKER:
0

WARNING:
1 (Confidence 필드의 enum vs 수치 비교 요구사항 절충 방식(§3)에 대해 C1의 재검토 권장 — 기술적으로는 양쪽 요구사항을 모두 충족했으나, 원 설계 의도와 다르게 해석했을 가능성을 배제할 수 없음)

NEXT STEP:
C1에 NAE-CROSSWALK-ADAPTER-REVIEW-001 요청(특히 §3 Confidence 절충 판단 재검토 요청) → 승인 후 PHASE 1(ADR-019 Storage Decision Review, 이번 구현으로 도출된 3개 저장 위치 후보 중 확정) → 실제 매핑 생성(사람 검증) → PHASE 4 TSU Gate Integration → PHASE 5 C1 TSU Pipeline Resume Review

GIT:
NOT PERFORMED
```
