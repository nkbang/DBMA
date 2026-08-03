# Validator Implementation Analysis

작성일: 2026-08-02
Project: NAE-VALIDATOR-IMPLEMENTATION-001 Phase 1
대상: `scripts/source_validator.py` (구현 전 상태 분석)

---

## v1.2 처리 방식(구현 전)

- `DEFAULT_ROOT = resources/theological_sources`, `rglob("source_manifest.yaml")`로
  하위 전체 탐색 — 경로는 하드코딩되어 있지 않음(이전 문서들의 추측을
  실측으로 정정한 사실 재확인, `NAE_MODERN_CORPUS_ARCHITECTURE_v1.md` 각주).
- 단일 스키마만 가정 — `schema_version` 필드를 읽지도 분기하지도 않음.
  모든 manifest를 동일한 `_REQUIRED_FIELDS`로 검사.

## Required Field 구조(구현 전)

```python
_REQUIRED_FIELDS = ("source_id", "title", "license", "content_genre", "status")
```

고정 튜플 — 스키마별 분기 없음. v2.1.0 manifest(`category` 필드 사용)를
그대로 검사하면 `content_genre` 누락으로 전량 FAIL(Plan Review-001 F1,
BLOCKER 한정 Step 2 — 이번 구현으로 해소 대상).

## Optional Field 구조(구현 전)

명시적 optional 목록 없음 — `_REQUIRED_FIELDS`에 없는 필드는 전부
암묵적으로 optional 취급(검사 대상 아님).

## Validation Flow(구현 전)

```
1. find_manifests(root)          — rglob
2. load_manifest(path)           — YAML 파싱, sources 배열 추출
3. validate_entry(entry, ...)    — 필수 필드/license/status 검사
4. source_id 중복 검사(전체 트리 기준)
5. 결과 집계(PASS/WARNING/FAIL 카운트) + 라인 출력
```

## Error Reporting(구현 전)

텍스트 라인만(`[PASS]`/`[WARNING]`/`[FAIL] {message}`) — 별도 Error
Code 없음. 종료 코드는 FAIL 존재 여부로만 결정(`1 if fail_count > 0 else 0`).

## Schema Loading 방식(구현 전)

**스키마 파일(`source_manifest.schema.yaml`)을 실제로 로드하지 않는다** —
`_REQUIRED_FIELDS`/`_VALID_STATUSES` 상수가 스키마 정의를 코드에 직접
하드코딩한 것이며, 스키마 YAML 파일은 사람이 읽는 문서로만 존재하고
검증기가 파싱해서 사용하지는 않는다(이 구조는 이번 구현에서도 유지 —
스키마 파일을 동적으로 로드하는 것은 범위 밖, 상수 하드코딩 방식을
스키마 버전별로 분기하는 선에서 해결).

---

## 구현 방향 요약 (Phase 2~6 적용 결과)

| 구분 | 구현 전 | 구현 후 |
|---|---|---|
| 스키마 인식 | 없음(단일 스키마 가정) | `schema_version` 값으로 "1"/"2" 주 버전 판별 |
| Required Fields | 고정 5개 | v1: 기존 5개 그대로 / v2: 신규 13개 |
| Enum 검증 | `status`만 | v1: `status`만(기존 유지) / v2: `status` + `source_type`/`copyright_status`/`usage_permission`/`access_control` |
| 신규 필드 검증 | 해당 없음 | `volume_number`(1 이상 정수), `archive_source`(선택, 문자열 타입만) |
| source_id 중복 검사 | 전체 트리 공통 | 변경 없음(v1/v2 네임스페이스 공유 유지) |
| license 필드 검사 | v1 공통 필수 검사 | v1 전용으로 유지(v2는 `copyright_status`가 대체) |

상세 구현/테스트 결과는 [`NAE_VALIDATOR_IMPLEMENTATION_REPORT_001.md`](NAE_VALIDATOR_IMPLEMENTATION_REPORT_001.md) 참고.
