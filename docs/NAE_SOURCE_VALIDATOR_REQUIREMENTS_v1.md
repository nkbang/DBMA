# NAE Source Validator Requirements v1

작성일: 2026-08-02
상태: 요구사항 명세 — **`scripts/source_validator.py` 코드는 이번 문서로
수정하지 않는다**(NAE-SCHEMA-MIGRATION-001 금지 사항). 실제 구현은 별도
승인 작업.
근거: [ADR-016](architecture/ADR-016-NAE-Metadata-Authority-Model-Revision.md),
[`NAE_METADATA_GOVERNANCE_v1.md`](NAE_METADATA_GOVERNANCE_v1.md) §7.3,
[`NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md`](NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md) F1

---

## 1. 현재 코드 상태 (실측, 2026-08-02)

```python
# scripts/source_validator.py (발췌, 실제 코드 재인용 — 수정 없음)
DEFAULT_ROOT = os.path.join("resources", "theological_sources")
_REQUIRED_FIELDS = ("source_id", "title", "license", "content_genre", "status")
_VALID_STATUSES = (
    "PREPARED", "ACQUIRED", "VERIFIED", "INGESTED",
    "approved_for_acquisition", "permission_required", "verification_pending",
)
```

- `DEFAULT_ROOT`는 `resources/theological_sources/` 전체를 `rglob`으로
  탐색 — **경로는 하드코딩되어 있지 않다**(이전 문서의 추측은 실측으로
  정정됨, `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` 각주 참고).
- `_REQUIRED_FIELDS`가 **필드명**을 하드코딩 — `content_genre`를 요구하나
  v2.1.0 스키마는 `category`를 사용 → 확장 없이 modern manifest를 그대로
  검증하면 전량 FAIL(Plan Review-001 F1, BLOCKER 한정 Step 2).
- `status` enum은 v1.2/v2.1.0 공통(변경 불필요).

---

## 2. category ↔ content_genre 대응

| 스키마 | 필드명 | 타입 | 값 예시 |
|---|---|---|---|
| v1.2(NAE-PD) | `content_genre` | array[string] | confession/theology/history/commentary/sermon/mission/church_practice/pastoral |
| v2.1.0(NAE-MODERN) | `category` | string(단일) | theology/commentary/sermons/missions/ministry/apologetics/reference |

**중요한 차이**: `content_genre`는 배열(복수 허용), `category`는 단일
문자열이다(복수 분류는 `subcategory`로 표현, v2.1.0 스키마 정의 참고) —
단순 필드명 치환이 아니라 **타입도 다르다**. Validator 확장 시 이 타입
차이도 함께 처리해야 한다(단일값을 배열로 강제 변환하거나, 스키마별로
검사 로직을 분리).

**요구사항 R-V1**: `_REQUIRED_FIELDS`를 고정 튜플이 아니라
`schema_version`별 딕셔너리로 정의할 것:

```python
# 요구사항 의사코드 — 실제 구현 아님
_REQUIRED_FIELDS_BY_VERSION = {
    "1.2": ("source_id", "title", "license", "content_genre", "status"),
    "2.1.0": ("source_id", "title", "author_id", "work_id", "edition_id",
              "category", "publication_year", "source_type",
              "copyright_status", "usage_permission", "access_control",
              "citation_policy", "status"),
}
```

---

## 3. Schema Version 분기

### 3.1 분기 기준

manifest 파일의 최상위 `schema_version` 필드 값으로 분기한다 —
파일 경로(디렉토리)로 분기하지 않는다(경로 규칙이 바뀌어도 검증 로직이
깨지지 않도록, 값 기반 분기가 더 견고함).

```python
# 요구사항 의사코드
if data.get("schema_version", "1.2").startswith("1."):
    required = _REQUIRED_FIELDS_BY_VERSION["1.2"]
elif data.get("schema_version", "").startswith("2."):
    required = _REQUIRED_FIELDS_BY_VERSION["2.1.0"]  # 2.0.0/2.1.0 등 2.x 전체 매칭
else:
    # 알 수 없는 버전 — FAIL 처리(아래 Error Code E-006)
    ...
```

### 3.2 v1.2

- `_REQUIRED_FIELDS`: 기존 그대로(§1 인용, 변경 없음)
- enum 검사: `status`만(기존과 동일, `license` 값 자체는 검사하지 않음 —
  기존 스키마 주석 정책 유지)

### 3.3 v2.1.0

- Required Fields: §4 참고
- enum 검사 대상 추가: `source_type`, `copyright_status`,
  `usage_permission`, `access_control`, `status` — 값이 `NAE_METADATA_GOVERNANCE_v1.md`
  §4의 허용 목록에 있는지 확인(v1.2는 `license` 값 자체를 검사하지 않는
  기존 정책과 달리, v2.1.0은 신규 enum 필드들의 값 타당성도 검사 대상에
  포함 — 저작권 거버넌스 필드이므로 오타/오기입 시 실제 노출 사고로
  이어질 수 있어 더 엄격하게 검사).

---

## 4. Required / Optional Fields (v2.1.0)

정본: `resources/theological_sources/modern/source_manifest.schema.yaml`
(Phase 1 산출물). 요약:

**Required** (12개): `source_id`, `author_id`, `work_id`, `edition_id`,
`title`, `publication_year`, `category`, `source_type`, `copyright_status`,
`usage_permission`, `access_control`, `citation_policy`, `status`

**Optional**: `author_name`(주의: 실질적으로는 author_id 산출에 쓰이므로
등록 절차상 필요하나 스키마 필수는 아님), `volume_id`, `volume_number`,
`title_variants`, `edition`, `publisher`, `language`, `subcategory`,
`theological_position`, `denomination`, `license`, `tsu_access`,
`archive_source`, `topics`, `scripture_reference`, `doctrine_tags`,
`local_path`, `aliases`

**조건부 필수(스키마 required와 별개의 게이트)**:
- `volume_id` — 해당 Work가 다권본(Edition 산하 volume ≥ 2)일 때만 TSU
  진입 전 필수(GOVERNANCE §6). Validator의 필드 존재 검사(PASS/FAIL)와
  TSU 게이트는 **별개 검사**로 구현할 것 — 이 요구사항 명세가 다루는
  범위는 전자(manifest 필드 존재 검사)뿐이다.
- `tsu_access` — 등록 시점에는 선택이나 TSU 파이프라인 진입 전 필수.

---

## 5. Error Code (제안)

기존 코드는 `PASS`/`WARNING`/`FAIL` 3단계 텍스트 라인만 출력한다(Error
Code 없음). 구현 확장 시 아래 코드 체계 도입을 제안한다(제안만, 강제 아님):

| Code | 의미 | 현재 판정 |
|---|---|---|
| E-001 | 필수 필드 누락/공백 | FAIL |
| E-002 | `license` 필드 없음(v1.2 한정) | FAIL |
| E-003 | `status` 값이 허용 enum 밖 | FAIL |
| E-004 | `source_id` 중복(전체 트리 기준) | FAIL |
| E-005 (신규) | v2.1.0 enum 필드(`source_type`/`copyright_status`/`usage_permission`/`access_control`) 값이 GOVERNANCE 허용 목록 밖 | FAIL |
| E-006 (신규) | `schema_version` 값이 인식 불가(1.x/2.x 어느 쪽도 아님) | FAIL |
| W-001 (신규) | 다권본으로 추정되나(동일 work_id 복수 entry) `volume_id` 없음 | WARNING |
| W-002 (신규) | `archive_source` 없음 | WARNING(FAIL 아님, §Phase 3.3 인용) |

---

## 6. Validation Flow (제안)

```
1. manifest 파일 탐색 (rglob, 기존 로직 유지)
2. 파일별 YAML 파싱 (기존 로직 유지)
3. schema_version 판별 → 1.2 / 2.1.0 분기 (§3, 신규)
4. 분기된 Required Fields 존재 검사 (§4, 신규 확장)
5. v2.1.0인 경우 enum 필드 값 검사 (§3.3, 신규)
6. status enum 검사 (기존 로직 유지, 양쪽 스키마 공통)
7. source_id 전체 트리 중복 검사 (기존 로직 유지, 스키마 무관 공통)
8. (신규, 선택) Reference Integrity 검사 — author_id/work_id/edition_id/
   volume_id가 authority/*.yaml에 존재하는지. 이번 요구사항 명세에서는
   "제안"으로만 남긴다 — Pilot-002에서 별도 Python 스크립트로 이미 검증
   가능함을 실증했으므로(구조 검증됨), source_validator.py에 통합할지
   별도 스크립트로 유지할지는 구현 단계에서 결정.
9. 결과 출력 (PASS/WARNING/FAIL 카운트, 기존 형식 유지 + Error Code 부기 제안)
```

---

## 7. 구현 시 회귀 테스트 요구사항

- 기존 v1.2 manifest(예: `resources/theological_sources/baptist/source_manifest.yaml`)에
  대한 기존 검증 결과가 이번 확장 전후로 **동일**해야 한다(회귀 없음).
- v2.1.0 manifest 예시(Pilot-001/002의 `manifest_pilot.yaml` — 단, 이들은
  `authority/pilot/` 하위에 있어 `DEFAULT_ROOT` 탐색 범위 밖일 수 있음,
  구현 시 pilot 파일을 실제 검증 대상에 포함할지 여부도 결정 필요)에 대해
  Required Fields 검사가 정상 동작해야 한다.

---

## 완료 조건 대응

이 문서는 **요구사항 명세**이며 구현이 아니다. 실제 구현은
`docs/NAE_SCHEMA_MIGRATION_GUIDE_v1.md`가 정의하는 Migration Step 3에서
별도 승인 후 진행한다.
