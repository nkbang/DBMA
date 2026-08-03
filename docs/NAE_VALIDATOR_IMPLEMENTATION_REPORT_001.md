# NAE Validator Implementation Report 001

**Project:** NAE-VALIDATOR-IMPLEMENTATION-001
**Date:** 2026-08-02
**Nature:** Infrastructure Implementation — Validator 코드 구현(Corpus-wide Metadata Migration 아님)
**Git Commit / Push:** 미수행 — 사용자 승인 대기

---

## 1. 변경 파일

| 파일 | 변경 유형 |
|---|---|
| `scripts/source_validator.py` | 수정(Dual Schema 지원 추가, 기존 로직 보존) |
| `tests/test_source_validator_v2.py` | 신규(pytest, 15개 테스트) |
| `docs/VALIDATOR_IMPLEMENTATION_ANALYSIS.md` | 신규(Phase 1 산출물) |
| `docs/NAE_VALIDATOR_IMPLEMENTATION_REPORT_001.md` | 신규(본 보고서) |

**참고**: 요청된 테스트 파일명은 `tests/validator_test_*.py`였으나,
pytest 기본 discovery 패턴(`test_*.py` 또는 `*_test.py`)과 이 저장소의
기존 관례(`tests/test_*.py`, 예: `test_tag_ingest_validator.py`)를 따라
`tests/test_source_validator_v2.py`로 명명했다 — `validator_test_001.py`
형태는 pytest 기본 설정에서 자동 수집되지 않아 실행되지 않는 파일이
될 위험이 있었다.

---

## 2. 구현 내용

### 2.1 Dual Schema 지원 (Phase 2)

`load_manifest()`가 각 manifest의 최상위 `schema_version` 값을 함께
반환하도록 확장(`entries, schema_version, error` 3-tuple, 기존
2-tuple에서 변경). `detect_schema_major()` 신규 함수가 `"1."`/`"2."`
접두사로 주 버전을 판별 — **Auto/Version Detection 방식**(manifest 내용
기반, 파일 경로 기반이 아님. 경로 기반 분기는 디렉토리 구조가 바뀌면
깨지므로 값 기반이 더 견고하다는 Requirements 문서 §3.1 판단을 그대로
구현).

`validate_entry()`가 `schema_major`에 따라 `_validate_entry_v1()` 또는
`_validate_entry_v2()`로 분기 — **기존 v1 로직은 함수를 그대로 옮기기만
했고 한 글자도 바꾸지 않았다**(회귀 방지, §4 Regression 참고).

### 2.2 Required Field Update (Phase 3)

```python
_V1_REQUIRED_FIELDS = ("source_id", "title", "license", "content_genre", "status")  # 기존 그대로
_V2_REQUIRED_FIELDS = ("source_id", "author_id", "work_id", "edition_id", "title",
                        "publication_year", "category", "source_type", "copyright_status",
                        "usage_permission", "access_control", "citation_policy", "status")
```

`content_genre`(v1) / `category`(v2)는 **필드명이 아예 다른 별도 목록**에
속해 있으므로 자동으로 두 구조 모두 지원한다 — Plan Review-001 F1이
지적한 문제(단일 `_REQUIRED_FIELDS`가 `content_genre`만 요구해 v2
manifest가 전량 FAIL)가 해소됨.

### 2.3 source_type 신규 Enum (Phase 4)

```python
"source_type": ("licensed", "purchased", "personal", "reference", "public_archive")
```

기존 4개 값 유지 + `public_archive` 추가(ADR-016). `copyright_status`/
`usage_permission`/`access_control`도 동일한 `_V2_ENUM_FIELDS` 딕셔너리
구조로 함께 구현.

### 2.4 신규 Metadata 필드 검증 (Phase 5)

| 필드 | 검증 방식 |
|---|---|
| `edition_id` | `_V2_REQUIRED_FIELDS`에 포함 — 누락 시 FAIL(스키마 정책상 required) |
| `volume_id` | 검증 목록에 포함하지 않음 — 스키마상 선택(optional) 필드이며, "다권본일 때만 조건부 필수"라는 조건은 manifest 자체만으로 판단 불가(동일 work_id의 volume 개수를 알아야 함 — 이번 validator는 단일 entry 단위 검사이므로 이 조건부 로직은 범위 밖으로 남김, §6 Remaining Issues) |
| `volume_number` | 존재 시 1 이상의 정수인지 확인(bool은 int의 서브클래스라 별도 제외 처리) |
| `copyright_status`/`usage_permission`/`access_control` | `_V2_ENUM_FIELDS`로 값 검증 |

**Schema의 Required/Optional 정책을 그대로 따름**: `volume_id`/
`volume_number`는 v2.1.0 스키마 정의(`modern/source_manifest.schema.yaml`)에서
`required: false`이므로, 누락 자체는 FAIL 사유가 아니다 — 존재할 때만
형식을 검사한다(값 존재 시 검증, 미존재 시 통과).

### 2.5 archive_source Optional 처리 (Phase 6)

```python
if entry.get("archive_source"):
    if not isinstance(archive_source, str):
        FAIL
    else:
        PASS
# 값이 없으면 이 블록 자체를 건너뜀 — 묵시적 PASS(검사 생략)
```

없는 경우 검사를 생략(암묵적 PASS), 있는 경우 문자열 타입인지만 확인
(내용의 사실 여부는 판단하지 않음 — 기존 `license` 필드 검사 정책과
동일한 성격).

---

## 3. 테스트 결과 (Phase 7)

`tests/test_source_validator_v2.py`, 15개 테스트 전부 PASS:

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

### 요청된 Test 1~6 대응

| # | 요청 | 대응 테스트 | 결과 |
|---|---|---|---|
| Test 1 | 기존 v1.2 Manifest PASS | `TestV1Regression` (2개) | PASS |
| Test 2 | 신규 v2.1.0 Sample PASS | `TestV2ValidManifest` | PASS |
| Test 3 | 잘못된 category FAIL | `TestV2InvalidCategory` | PASS(=FAIL 정상 발생 확인) |
| Test 4 | 잘못된 source_type FAIL | `TestV2InvalidSourceType` (+ 5개 유효값 전수 확인) | PASS |
| Test 5 | edition_id 누락 → 스키마 정책대로 | `TestV2MissingEditionId` — 스키마 정책상 required이므로 FAIL로 확인 | PASS(=FAIL 정상 발생 확인) |
| Test 6 | volume_number 오류 FAIL | `TestV2VolumeNumber` (음수/비정수 2건 + 정상값 1건) | PASS |

추가로 요청 범위를 넘어 자체 보강한 테스트: 인식 불가 `schema_version`
FAIL(Requirements 문서 Error Code E-006 대응), `archive_source` 3가지
경우(없음/문자열/비문자열), v1↔v2 간 `source_id` 중복 검사(네임스페이스
공유 확인).

---

## 4. Regression 결과 (Phase 8)

**기존 Manifest**: `resources/theological_sources/baptist/source_manifest.yaml`
실제 CLI 실행 결과 — **변경 전과 완전히 동일**:

```
=== 결과 요약: PASS=21 WARNING=0 FAIL=0 ===
```

(변경 전 실행 결과도 동일하게 21/0/0이었음 — `NAE_SCHEMA_MIGRATION_REPORT_001.md` §2 Phase 6에 기록된 값과 일치)

**기존 CSV**: `NAE_SOURCE_MANIFEST_v1.csv`, `source_candidates.csv` —
validator가 애초에 CSV를 대상으로 하지 않으므로(`MANIFEST_FILENAME =
"source_manifest.yaml"`만 탐색) 이번 변경과 무관, 영향 없음(확인 완료).

**기존 YAML**: `resources/theological_sources/authority/*.yaml`(Schema
Migration에서 생성한 빈 템플릿) — 파일명이 `source_manifest.yaml`이
아니므로 `rglob` 탐색 대상에 포함되지 않음(실측 확인) — 영향 없음.

**다른 코드와의 연관성**: `grep -rl "source_validator"` 결과
`scripts/source_validator.py` 자기 자신과 신규 테스트 파일 외에는
이 모듈을 import하는 코드가 없음(실측 확인) — 다른 파이프라인에
연쇄 영향 없음.

**종료 코드**: CLI 재실행 결과 `exit=0`(FAIL 없을 때 정상 종료) — 변경 없음.

**결론: Regression 없음.**

---

## 5. Remaining Issues

| # | 항목 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | `volume_id` 조건부 필수 로직 미구현 | "해당 Work가 다권본일 때만 필수"라는 조건은 단일 entry 검사로는 판단 불가 — 동일 manifest 내 같은 `work_id`를 가진 entry 수를 세는 교차 검사가 필요. 이번 구현 범위 밖(Requirements 문서 §4 "조건부 필수"는 TSU 게이트에서 별도 검사하는 것으로 설계됨, validator 자체의 역할은 아님) | 낮음 — 설계상 의도된 분리 |
| 2 | Reference Integrity(authority/*.yaml 참조 무결성) 미통합 | Requirements 문서 §6 Validation Flow 8단계가 "제안"으로만 남긴 항목 — Pilot-002에서 별도 Python 스크립트로 검증 가능함을 이미 실증했으나 `source_validator.py`에는 통합하지 않음(Authority Registry에 아직 실제 데이터가 없어 통합해도 검증할 대상이 없음 — Registry Build 이후 착수가 합리적) | 중간 — 다음 단계(Authority Registry Build)와 연계 |
| 3 | Error Code 미구현 | Requirements 문서 §5가 제안한 E-001~W-002 코드 체계는 텍스트 메시지로만 구현(코드 접두사 없음) — 사람이 읽기에는 문제없으나 자동화(CI 등)에서 파싱하려면 향후 구조화 필요 | 낮음 |
| 4 | v2.1.0 실제 데이터 표본 부족 | 이번 테스트는 합성(synthetic) manifest로 검증했다 — Pilot-001/002의 `authority/pilot/*/manifest_pilot.yaml`은 `DEFAULT_ROOT` 탐색 범위 밖(별도 pilot 디렉토리)이라 실제 CLI로 검증되지 않음 | 중간 — Migration Guide Step 4(Pilot 재검증)에서 다룰 항목 |

---

## 완료 조건 답변

1. **v1.2 Manifest PASS 여부** — **PASS**(21/0/0, 회귀 없음, §4).
2. **v2.1.0 Manifest PASS 여부** — **PASS**(합성 샘플 기준, Test 2, §3).
3. **Backward Compatibility 유지 여부** — **유지됨**. v1 분기 함수(`_validate_entry_v1`)는 기존 코드를 그대로 이동한 것이며, 실제 저장소 매니페스트로 실측 확인.
4. **Migration Guide와 일치 여부** — **일치**. `NAE_SCHEMA_MIGRATION_GUIDE_v1.md` Step 3("Validator")가 요구한 "요구사항 문서 기준 구현 + 회귀 테스트"를 그대로 수행했다.
5. **Metadata Migration을 시작할 준비가 되었는가?** — **부분적으로 준비됨, 완전하지는 않음.** Validator는 v1.2/v2.1.0 모두 검증 가능한 상태이나, Migration Guide Step 4(Pilot 재검증 — 실제 Validator로 Pilot-001/002 산출물 재확인)가 아직 남아 있고, Remaining Issues #2(Reference Integrity 미통합)·#4(실제 pilot 데이터 미검증)가 해소되지 않았다. Corpus-wide Migration(Step 5) 착수 전 최소한 Step 4를 먼저 수행할 것을 권고한다.

---

## 로드맵 갱신

```
RAW Acquisition                 ✅
Corpus Audit                    ✅
Architecture Design             ✅
Authority Design                ✅
Pilot Validation                ✅
Architecture Revision           ✅
Schema Migration Design         ✅
Validator Implementation        ✅ (이번 작업)

Pilot 재검증(실제 Validator)      NEXT (Migration Guide Step 4)
Metadata Migration               NEXT (Step 4 이후, 별도 승인)
Authority Registry Build         NEXT
TSU Migration                    FUTURE
```

---

*Corpus 수정, RAW 수정, Metadata 생성, Authority Registry 구축(실제
데이터), TSU/Embedding 생성, Retrieval 변경, Git Push — 전부 수행하지
않음. Git Commit도 사용자 승인 후에만 수행한다.*
