# NAE Validator Review-001 Report

**Date:** 2026-08-02  
**Author:** C1 (Validator Review Agent)  
**Status:** FINAL REPORT  
**Scope:** `scripts/source_validator.py` (NAE-VALIDATOR-IMPLEMENTATION-001 구현 결과물)  
**Review Type:** Code Review, Schema Compliance, Regression Audit, Migration Readiness

---

## 1. Executive Summary

CUE가 완료한 **NAE-VALIDATOR-IMPLEMENTATION-001** 결과물(`scripts/source_validator.py`)은 v1.2(NAE-PD)와 v2.1.0(NAE-MODERN, ADR-016) 스키마를 모두 검증하는 **Dual Schema Validator**로 구현되었다.

**최종 판정: APPROVED WITH CONDITIONS** (조건부 승인)

### 주요 발견 사항

| 항목 | 결과 |
|---|---|
| Code Review (Dual Schema 지원) | PASS |
| Schema Compliance (v2.1.0 신규 항목) | PASS |
| Regression Test (기존 v1.2 호환성) | PASS (실제 실행: 21/0/0) |
| Architecture Compliance (ADR-001/014/015/016) | PASS |
| Migration Readiness | READY WITH CONDITIONS |

---

## 2. Code Review

### 2.1 v1.2 지원 유지 여부

**검증 결과: PASS**

- `_V1_REQUIRED_FIELDS = ("source_id", "title", "license", "content_genre", "status")` — 기존 필드 그대로 유지
- `_validate_entry_v1()` 함수가 기존 로직을 **그대로 이동**(한 글자도 변경 없음)
- `license` 필드 존재 여부 검사(값의 타당성 판단은 하지 않음) — 기존 정책 준수
- `content_genre` 필드명 유지(v1.2 전용)

**실제 실행 결과:**
```
resources/theological_sources/baptist/source_manifest.yaml
=== 결과 요약: PASS=21 WARNING=0 FAIL=0 ===
```
변경 전과 완전히 동일한 결과(회귀 없음).

### 2.2 v2.1.0 지원 여부

**검증 결과: PASS**

- `_V2_REQUIRED_FIELDS`에 13개 필수 필드 정의:
  ```python
  ("source_id", "author_id", "work_id", "edition_id", "title",
   "publication_year", "category", "source_type", "copyright_status",
   "usage_permission", "access_control", "citation_policy", "status")
  ```
- `_V2_ENUM_FIELDS` 딕셔너리로 enum 값 검증:
  - `source_type`: licensed, purchased, personal, reference, public_archive
  - `copyright_status`: public_domain, copyrighted, licensed, unknown
  - `usage_permission`: research, citation_only, internal_use, no_redistribution
  - `access_control`: public, restricted, private

### 2.3 Version Detection

**검증 결과: PASS**

- `detect_schema_major()` 함수가 `schema_version` 값의 접두사로 판별:
  - `"1."` → `"1"` (v1.x)
  - `"2."` → `"2"` (v2.x)
  - 그 외 → `None` (인식 불가, FAIL)
- **파일 경로 기반이 아닌 값 기반** — 디렉토리 구조가 바뀌어도 견고함(Requirements 문서 §3.1 판단 준수)

### 2.4 Required Field 처리

**검증 결과: PASS**

- v1.2와 v2.1.0이 **별도 목록**에 속 — `content_genre`(v1) / `category`(v2)는 필드명이 다르지만 자동으로 두 구조 모두 지원
- Plan Review-001 F1이 지적한 문제(단일 `_REQUIRED_FIELDS`가 `content_genre`만 요구해 v2 manifest가 전량 FAIL)가 해소됨

### 2.5 Optional Field 처리

**검증 결과: PASS**

- `volume_number`: 존재할 경우 1 이상의 정수인지 확인(bool은 int의 서브클래스라 별도 제외)
- `archive_source`: 없으면 PASS(검사 생략), 있으면 문자열 타입인지만 확인
- `volume_id`: 스키마상 선택(optional) 필드 — 누락 자체는 FAIL 사유 아님

### 2.6 Error Handling

**검증 결과: WARNING**

- Error Code(E-001~W-002)가 텍스트 메시지로만 구현(코드 접두사 없음)
- 사람이 읽기에는 문제없으나 자동화(CI 등)에서 파싱하려면 향후 구조화 필요
- **Remaining Issues #3**로 기록됨(우선순위: 낮음)

### 2.7 Validation Flow

**검증 결과: PASS**

1. `validate()` → `find_manifests()` → `load_manifest()` → `detect_schema_major()`
2. `validate_entry()` → `_validate_entry_v1()` 또는 `_validate_entry_v2()` 분기
3. `status` 검사(스키마 공통)
4. `source_id` 중복 검사(전체 트리 기준, v1/v2 네임스페이스 공유)

---

## 3. Schema Compliance

### 3.1 v2.1.0 신규 항목 검증 여부

| 필드 | 스키마 required | Validator 구현 | 결과 |
|---|---|---|---|
| `source_type` | true (enum) | `_V2_ENUM_FIELDS` 포함, public_archive 추가 | PASS |
| `public_archive` | (source_type 값) | enum values에 포함 | PASS |
| `copyright_status` | true (enum) | `_V2_ENUM_FIELDS` 포함 | PASS |
| `usage_permission` | true (enum) | `_V2_ENUM_FIELDS` 포함 | PASS |
| `access_control` | true (enum) | `_V2_ENUM_FIELDS` 포함 | PASS |
| `edition_id` | true | `_V2_REQUIRED_FIELDS` 포함 | PASS |
| `volume_id` | false (조건부 필수) | 검증 목록 미포함(설계상 의도된 분리) | PASS(설계 준수) |
| `volume_number` | false | 존재 시 1+ 정수 검사 | PASS |
| `citation_policy` | true | `_V2_REQUIRED_FIELDS` 포함 | PASS |

### 3.2 Schema 정의와 코드 일치성

**검증 결과: PASS**

- `resources/theological_sources/modern/source_manifest.schema.yaml`의 `fields` 정의와 `_V2_REQUIRED_FIELDS`/`_V2_ENUM_FIELDS`가 일치
- 값 체계의 유일한 정본은 `NAE_METADATA_GOVERNANCE_v1.md §4` — 코드가 그 값을 그대로 사용

---

## 4. Regression Test

### 4.1 기존 v1.2 Manifest 검증 결과

**실제 CLI 실행 결과:**
```
=== 결과 요약: PASS=21 WARNING=0 FAIL=0 ===
```
- `resources/theological_sources/baptist/source_manifest.yaml` — 21개 항목 전부 PASS
- 변경 전 실행 결과와 완전히 동일(회귀 없음)

### 4.2 기존 CSV 영향 여부

**검증 결과: PASS (무관)**

- validator가 CSV를 대상으로 하지 않음(`MANIFEST_FILENAME = "source_manifest.yaml"`만 탐색)
- `NAE_SOURCE_MANIFEST_v1.csv`, `source_candidates.csv` — 영향 없음

### 4.3 기존 YAML 영향 여부

**검증 결과: PASS (무관)**

- `resources/theological_sources/authority/*.yaml` — 파일명이 `source_manifest.yaml`이 아니므로 탐색 대상 아님
- 실측 확인 완료

### 4.4 다른 코드와의 연관성

**검증 결과: PASS (무관)**

- `grep -rl "source_validator"` 결과 — 자기 자신과 신규 테스트 파일 외에는 이 모듈을 import하는 코드가 없음
- 다른 파이프라인에 연쇄 영향 없음

### 4.5 pytest 테스트 결과

**실제 테스트 실행 결과:**
```
tests/test_source_validator_v2.py::TestV1Regression::test_valid_v1_entry_passes PASSED
tests/test_source_validator_v2.py::TestV1Regression::test_real_repo_manifest_unchanged PASSED
tests/test_source_validator_v2.py::TestV2ValidManifest::test_valid_v2_entry_passes PASSED
tests/test_source_validator_v2.py::TestV2InvalidCategory::test_missing_category_fails PASSED
tests/test_source_validator_v2.py::TestV2InvalidSourceType::test_invalid_source_type_fails PASSED
tests/test_source_validator_v2.py::TestV2InvalidSourceType::test_all_valid_source_type_values_pass PASSED
tests/test_source_validator_v2.py::TestV2MissingEditionId::test_missing_edition_id_fails PASSED
tests/test_source_validator_v2.py::TestV2VolumeNumber::test_negative_volume_number_fails PASSED
tests/test_source_validator_v2.py::TestV2VolumeNumber::test_non_integer_volume_number_fails PASSED
tests/test_source_validator_v2.py::TestV2VolumeNumber::test_valid_volume_number_passes PASSED
tests/test_source_validator_v2.py::TestUnrecognizedSchemaVersion::test_unrecognized_schema_version_fails PASSED
tests/test_source_validator_v2.py::TestArchiveSourceOptional::test_missing_archive_source_passes PASSED
tests/test_source_validator_v2.py::TestArchiveSourceOptional::test_string_archive_source_passes PASSED
tests/test_source_validator_v2.py::TestArchiveSourceOptional::test_non_string_archive_source_fails PASSED
tests/test_source_validator_v2.py::TestSourceIdDedupAcrossSchemas::test_duplicate_source_id_across_v1_and_v2_fails PASSED

15 passed in 0.06s
```

---

## 5. Architecture Compliance

### 5.1 ADR-001 (RetrievalEngine) 준수

**검증 결과: PASS**

- validator가 RetrievalEngine를 호출하거나 변경하지 않음
- 읽기 전용 — manifest 파일이나 원문을 수정하지 않음(코드 주석 명시)

### 5.2 ADR-014 (NAE-MODERN Layer) 준수

**검증 결과: PASS**

- v2.1.0 스키마 검증 로직이 ADR-014 §3.4/§3.5와 일치
- `source_type`, `copyright_status`, `usage_permission`, `access_control` 4개 신규 필드 검증
- NAE-PD(NAE-MODERN) 분리 원칙 위반 없음

### 5.3 ADR-015 (Corpus Ingestion Standard) 준수

**검증 결과: PASS**

- Lifecycle(Registration → Validation → Classification → ...)의 Validation 단계와 일치
- Quality Gate(3단계 판정: PASS/WARNING/FAIL) 지원
- `status` enum 재사용(NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 2 Lifecycle과 대응)

### 5.4 ADR-016 (Metadata Authority Model Revision) 준수

**검증 결과: PASS**

- `edition_id` 필수 필드 승격 반영(스키마 정책상 required이므로 누락 시 FAIL)
- `volume_id` 조건부 필수 — TSU 게이트에서 별도 검사(validator 자체의 역할 아님, 설계상 의도된 분리)
- `volume_number` 신규 필드 검증(1 이상의 정수)
- `source_type`에 `public_archive` 값 추가 반영

### 5.5 RAW Immutable 위반 여부

**검증 결과: PASS (위반 없음)**

- validator가 원본 파일을 읽기 전용으로만 접근
- manifest 파일이나 원문을 수정하지 않음(코드 주석 명시)

### 5.6 DBMA/NAE Boundary 위반 여부

**검증 결과: PASS (위반 없음)**

- `DEFAULT_ROOT = os.path.join("resources", "theological_sources")` — 기존 디렉토리 구조 유지
- NAE-PD / NAE-MODERN / DBMA 분리 원칙 위반 없음

---

## 6. Risk Assessment

| # | Category | Level | Description |
|---|---|---|---|
| 1 | Code Quality | LOW | Error Code(E-001~W-002)가 텍스트 메시지로만 구현 — CI 자동화를 위해 구조화 필요 |
| 2 | Schema Coverage | LOW | `volume_id` 조건부 필수 로직 미구현 — TSU 게이트에서 별도 검사(설계상 의도된 분리) |
| 3 | Reference Integrity | MEDIUM | Authority 레지스트리 참조 무결성 검증 미통합 — Registry Build 이후 착수 |
| 4 | Pilot Data Validation | MEDIUM | v2.1.0 실제 데이터 표본 부족 — Migration Guide Step 4(Pilot 재검증)에서 다룰 항목 |
| 5 | Regression | NONE | 기존 v1.2 manifest 검증 결과 동일(21/0/0, 회귀 없음) |
| 6 | Architecture | NONE | ADR-001/014/015/016 모두 준수 — 코드 변경/RAW immutable/Boundary 위반 없음 |

---

## 7. Migration Readiness

### 7.1 Metadata Migration 가능 여부

**판정: READY WITH CONDITIONS**

#### 조건부 준비 완료 항목

| 항목 | 상태 |
|---|---|
| Dual Schema Validator 구현 | ✅ 완료 (v1.2 + v2.1.0) |
| Required Field 검증 | ✅ 완료 (13개 필수 필드) |
| Enum 값 검증 | ✅ 완료 (4개 필드, 전 값 포함) |
| Regression 테스트 | ✅ 완료 (15개 pytest 전부 PASS) |
| 실제 v1.2 manifest 검증 | ✅ 완료 (21/0/0, 회귀 없음) |

#### 미완료 항목 (Migration 착수 전 필요)

| # | 항목 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | Pilot 재검증(실제 Validator) | Migration Guide Step 4 — Pilot-001/002 산출물을 실제 Validator로 재확인 | 높음 |
| 2 | Reference Integrity 검증 | Authority 레지스트리 참조 무결성 — Registry Build 이후 착수 | 중간 |
| 3 | Error Code 구조화 | E-001~W-002 코드 체계 — CI 자동화를 위해 필요 | 낮음 |

### 7.2 Corpus-wide Migration 착수 전 체크리스트

- [ ] Migration Guide Step 4(Pilot 재검증) 완료
- [ ] Pilot-001/002 manifest를 실제 Validator로 검증하여 PASS 확인
- [ ] Authority 레지스트리 실제 데이터 생성(Reference Integrity 검증 대상 확보)
- [ ] 사용자 승인(Corpus-wide Migration은 별도 승인 필요)

---

## 8. Final Recommendation

### 8.1 판정: **APPROVED WITH CONDITIONS**

```text
APPROVED ✓ (조건부)
APPROVED WITH CONDITIONS ✓
REJECTED ✗
```

**조건부 승인 이유:**
- Dual Schema Validator 구현이 적절함(v1.2 + v2.1.0)
- Regression 테스트 전부 PASS(15/15, 실제 v1.2 manifest 21/0/0)
- Architecture Compliance(ADR-001/014/015/016) 모두 준수
- 단, Migration Guide Step 4(Pilot 재검증)가 아직 남아 있음

### 8.2 다음 단계

| 단계 | 상태 | 비고 |
|---|---|---|
| Validator Implementation | ✅ 완료 | 이번 작업 |
| Pilot 재검증(실제 Validator) | ⏳ NEXT | Migration Guide Step 4 |
| Metadata Migration | ⏳ NEXT | Step 4 이후, 별도 승인 |
| Authority Registry Build | ⏳ NEXT | |
| TSU Migration | 🔮 FUTURE | |

### 8.3 최종 질문 답변

#### Q1. Validator Implementation이 승인 가능한가?

**조건부 승인.** Dual Schema 지원, Required Field 검증, Enum 값 검증, Regression 테스트가 적절함. 단, Pilot 재검증 전까지 Corpus-wide Migration은 착수하지 말 것.

#### Q2. 기존 v1.2 Manifest에 회귀가 없는가?

**예.** 실제 실행 결과 21/0/0(변경 전과 완전히 동일). pytest TestV1Regression도 PASS.

#### Q3. v2.1.0 스키마를 충분히 검증하는가?

**예.** 13개 필수 필드, 4개 enum 필드, volume_number/archive_source 선택 필드가 모두 검증됨. 단, 실제 pilot 데이터로 재검증 필요.

#### Q4. Metadata Migration을 시작할 준비가 되었는가?

**부분적으로 준비됨, 완전하지는 않음.** Validator는 v1.2/v2.1.0 모두 검증 가능한 상태이나, Migration Guide Step 4(Pilot 재검증)가 아직 남아 있음. Corpus-wide Migration(Step 5) 착수 전 최소한 Step 4를 먼저 수행할 것을 권고한다.

#### Q5. Authority Registry 구축을 시작할 준비가 되었는가?

**예.** Validator Review가 완료되었으므로, Authority Registry Build를 다음 단계로 착수 가능. 단, Reference Integrity 검증은 Registry에 실제 데이터가 들어온 후에야 의미 있음.

#### Q6. TSU Pipeline 연결을 시작할 준비가 되었는가?

**아직 아님.** Metadata Migration(Step 5)과 Authority Registry Build가 먼저 필요. TSU 게이트에서 `volume_id` 조건부 필수 검사가 별도로 설계되어 있으므로, 그 게이트 구현도 필요.

---

## Appendix A: Reviewed File Paths

| Document | Path | Status |
|---|---|---|
| Validator Implementation | scripts/source_validator.py | 구현 완료 |
| Test Suite | tests/test_source_validator_v2.py | 15개 테스트 PASS |
| Schema v2.1.0 | resources/theological_sources/modern/source_manifest.schema.yaml | 스키마 |
| Implementation Report | docs/NAE_VALIDATOR_IMPLEMENTATION_REPORT_001.md | 보고서 |
| Requirements | docs/NAE_SOURCE_VALIDATOR_REQUIREMENTS_v1.md | 요구사항 명세 |
| Migration Guide | docs/NAE_SCHEMA_MIGRATION_GUIDE_v1.md | 마이그레이션 가이드 |
| Metadata Governance | docs/NAE_METADATA_GOVERNANCE_v1.md | 값 체계 정본 |

## Appendix B: Test Coverage Summary

| Test Class | Tests | Coverage | Result |
|---|---|---|---|
| TestV1Regression | 2 | 기존 v1.2 manifest PASS, 회귀 없음 | ✅ PASS |
| TestV2ValidManifest | 1 | 신규 v2.1.0 sample PASS | ✅ PASS |
| TestV2InvalidCategory | 1 | 누락된 category → FAIL | ✅ PASS(=FAIL 정상 발생) |
| TestV2InvalidSourceType | 2 | 잘못된 source_type → FAIL, 전 값 PASS | ✅ PASS |
| TestV2MissingEditionId | 1 | 누락된 edition_id → FAIL | ✅ PASS(=FAIL 정상 발생) |
| TestV2VolumeNumber | 3 | 음수/비정수 → FAIL, 정상값 → PASS | ✅ PASS |
| TestUnrecognizedSchemaVersion | 1 | 인식 불가 버전 → FAIL | ✅ PASS(=FAIL 정상 발생) |
| TestArchiveSourceOptional | 3 | 없음/문자열/비문자열 | ✅ PASS |
| TestSourceIdDedupAcrossSchemas | 1 | v1↔v2 간 중복 → FAIL | ✅ PASS(=FAIL 정상 발생) |
| **Total** | **15** | **전부** | **✅ 15/15 PASS** |

---

*Corpus 수정, RAW 수정, Metadata 생성, Authority Registry 구축(실제 데이터), TSU/Embedding 생성, Retrieval 변경 — 전부 수행하지 않음. Git Commit/Push도 수행하지 않음.*

**Report End**