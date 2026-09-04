# NAE Validator v2.2 Implementation Report 001

**Project:** NAE-VALIDATOR-V2.2-IMPLEMENTATION-001
**Date:** 2026-08-02
**Nature:** Validator 코드 구현 — Metadata Migration/TSU 아님
**Git Commit/Push:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

`scripts/source_validator.py`를 3-트랙 스키마 라우팅(v1.2/v2.1.x/v2.2.x)으로
확장하고, `work_type` 기반 Edition/Volume/Issue 조건부 필드 규칙,
선택적 Authority Reference FK 검증(`--registry-path`), 선택적
Manifest Layer 필드 검증(`manifest_id`가 있는 entry만)을 구현했다.
기존 v1.2/v2.1.x 로직은 함수 단위로 그대로 보존했다(문자 그대로
재사용, 새 코드로 재작성하지 않음) — 회귀 없음을 실측 확인(21 PASS/
0 FAIL 격리 재확인, 89 PASS/0 FAIL 전체 재확인). 신규 테스트
19개(`tests/test_validator_v22.py`) 전부 PASS, 기존 테스트
15개(`tests/test_source_validator_v2.py`)도 전부 PASS(단, 그중 1개는
Pilot 파일이 이후 커밋에서 늘어나며 깨진 낡은 전체-트리 카운트
가정을 이번에 `baptist/`로 스코프 한정해 수정 — 아래 §3에서 상세).

---

## 2. 변경 파일

| 파일 | 변경 유형 |
|---|---|
| `scripts/source_validator.py` | 수정(3-트랙 라우팅, work_type 조건부 규칙, FK 검증, Manifest 필드 검증 추가) |
| `tests/test_validator_v22.py` | 신규(19개 테스트) |
| `tests/test_source_validator_v2.py` | 수정(1개 테스트의 root 스코프 버그 수정, 회귀 로직 자체는 무변경) |
| `docs/NAE_VALIDATOR_V22_IMPLEMENTATION_REPORT_001.md` | 신규(본 보고서) |

---

## 3. v1.2 Compatibility 결과

**PASS.** `_validate_entry_v1()` 함수는 이번 작업에서 **한 글자도
수정하지 않았다**(git diff 확인 가능). `--root
resources/theological_sources/baptist`로 격리 실행한 결과:

```
=== 결과 요약: PASS=21 WARNING=0 FAIL=0 ===
```

**부수 발견 및 수정**: `tests/test_source_validator_v2.py::
TestV1Regression::test_real_repo_manifest_unchanged`가 `root =
resources/theological_sources`(전체 트리)를 검사하며 `pass_count ==
21`을 기대하고 있었는데, 이 가정은 **이번 작업 이전에 이미 깨져
있었다** — 이전 커밋들(Pilot Manifest Fix-001 등)에서 Pilot
`source_manifest.yaml` 파일들이 늘어나며 전체 트리 스캔 결과가
89 PASS가 됐기 때문이다(내가 이번에 만든 문제가 아니라, 발견 시점에
이미 깨져 있던 테스트). 테스트의 의도(v1.2 전용 회귀 확인)에 맞게
`root`를 `baptist/`로 좁혀 수정했다 — 검증 로직 자체는 손대지 않음.

---

## 4. v2.2 Validation Rules

### Schema Version Routing

```
1.x        → legacy validation(v1.2, 무변경)
2.0.x/2.1.x → modern validation(기존 v2.1 로직, 무변경)
2.2.x 이상   → modern validation + conditional rules(신규)
```

### work_type 조건부 규칙(`_WORK_TYPE_FIELD_RULES`)

| work_type | edition_id | volume_id | issue_id |
|---|---|---|---|
| `monograph`(누락 시 기본값) | required | forbidden | forbidden |
| `multi_volume` | required | required | forbidden |
| `collection` | required | required | forbidden |
| `periodical` | optional | optional(최소 1개, volume_id 또는 issue_id) | optional(동일) |

**"collection"에 대한 문서화된 가정**: 명령서가 `work_type` 허용값에
`collection`을 포함시켰으나 그에 대한 별도 조건부 규칙을 명시하지
않았다 — 이번 구현은 `collection`을 `multi_volume`과 동일하게
취급했다(§Remaining Risks #1에 재확인 필요 항목으로 기록).

### Authority Reference FK(`--registry-path`, 선택)

미지정 시 schema validation만 수행(FK 검사 건너뜀) — 실제 Registry
데이터 마이그레이션 없이도 이번 명령서의 금지 사항을 지키면서
"인터페이스만 설계"한다는 Phase 6 요구를 충족.

### Manifest Layer 필드(선택, opt-in)

`manifest_id` 필드가 entry에 있을 때만 `schema_version`(top-level)/
`manifest_id`/`source_id` 필수 확인 + `processing_status` enum
(`acquired`/`ocr_complete`/`metadata_complete`/`tsu_ready`/`embedded`)
검증을 수행한다. **역행 검사(lifecycle enforcement)는 구현하지
않았다** — 명령서 Phase 7 지시대로 `verified_by`(audit 필드) 존재
여부만 확인(없으면 WARNING, FAIL 아님).

---

## 5. Test Results

```
tests/test_source_validator_v2.py   15 passed
tests/test_validator_v22.py          19 passed
합계                                  34 passed, 0 failed
```

| 요청된 Test | 결과 |
|---|---|
| Test 1: v1.2 Regression(21 PASS) | PASS(§3) |
| Test 2: v2.1 기존 데이터 PASS | PASS(`test_v21_routes_to_modern_without_conditional_rules`가 v2.1 자체 회귀도 함께 확인) |
| Test 3: monograph + edition PASS | PASS(`test_monograph_with_edition_passes`) |
| Test 4: monograph - edition missing FAIL | PASS(`test_monograph_missing_edition_fails`) |
| Test 5: periodical + issue PASS | PASS(`test_periodical_with_issue_passes`) |
| Test 6: book + issue FAIL | PASS로 확인(`test_monograph_with_issue_fails` — "book"이라는 work_type 값은 존재하지 않아 `monograph`로 대체 구현, §Remaining Risks #2) |
| Test 7: multi_volume + volume PASS | PASS(`test_multi_volume_with_edition_and_volume_passes`) |
| Test 8: schema_version invalid FAIL | PASS(`test_unrecognized_schema_version_fails`) |
| Test 9: unknown work_type FAIL | PASS(`test_unknown_work_type_fails`) |
| Test 10: manifest status validation PASS | PASS(`test_manifest_status_valid_passes`) |

요청 범위를 넘어 자체 보강: FK 검증 3건(no-registry/missing-FK/
present-FK), Manifest 필드 3건(무영향/잘못된 status/audit 누락
WARNING), periodical 최소 요구 미충족 1건, work_type 누락 시 기본값
1건.

---

## 6. Architecture Impact

- ADR-016/017/018/019 중 어느 것도 개정 불필요 — 이번 구현은 이미
  확정된 설계(`NAE_SCHEMA_V2_2_APPLICATION_REPORT_001.md`,
  `NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md`)를 코드로 옮긴 것이다.
- `NAE_VALIDATOR_BOUNDARY_DESIGN_001.md`가 제안한 3-도구 체제
  (`source_validator.py`/`authority_validator.py`/
  `manifest_validator.py`) 중 이번 구현은 **`source_validator.py`
  하나에 세 트랙 전부를 통합**했다 — 별도 `manifest_validator.py`
  파일을 새로 만들지 않고 기존 도구에 opt-in 방식으로 얹었다(entry에
  `manifest_id`가 없으면 완전히 비활성). 이는 Validator Boundary
  Design-001의 "3개 도구"안과 다른 실제 구현 선택이며, §9 Remaining
  Risks에 재검토 항목으로 남긴다.

---

## 7. Remaining Risks

| # | 리스크 | 설명 |
|---|---|---|
| 1 | `collection` work_type 규칙이 문서화되지 않은 가정(multi_volume과 동일 취급) | 실제 Collection형 자료(예: early_baptist_collection)에 적용 전 재검토 필요 |
| 2 | Test 6("book + issue FAIL")의 `book`이 실제 enum 값이 아님 | 명령서 예시가 `work_type=book`을 썼으나 Application Report/이번 구현 모두 `book`이 아니라 `monograph`를 사용 — 동일한 취지(단권 자료)로 `monograph`로 대체 구현, 실제로는 `book`이라는 값 자체가 존재하면 `test_unknown_work_type_fails`처럼 FAIL 처리됨(별도 확인 가능) |
| 3 | Validator Boundary Design-001의 "3-도구 분리"안과 실제 구현(단일 파일 통합)이 다름 | 향후 Registry/Manifest 데이터가 실제로 생성되는 시점에 분리가 필요한지 재검토(§6) |
| 4 | `processing_status` 역행 검사 미구현(의도된 범위 제한, 명령서 지시대로) | Manifest 실 데이터가 생기고 실제 lifecycle enforcement가 필요해지면 별도 작업 필요 |
| 5 | Registry FK 검증(`--registry-path`)이 아직 어떤 CI/자동화에도 연결되지 않음 | 옵션 플래그로만 존재, 기본 실행에는 영향 없음(의도된 설계) |

---

## 8. Migration Readiness

**BLOCKED.** Validator 구현 완료가 Metadata Migration 승인을
의미하지 않는다(명령서 "최종 판정 기준" 재확인) — Registry 실제
Migration, Manifest 실 데이터, Pilot 확대 전부 별도 승인 필요.

---

## 완료 조건 답변

1. **v1.2 Regression PASS인가?** — 예(21 PASS/0 FAIL, 격리 재확인).
2. **v2.2 validation PASS인가?** — 예(19개 신규 테스트 전부 PASS).
3. **Periodical validation 가능한가?** — 예(work_type=periodical, volume_id/issue_id 중 최소 1개 요구).
4. **Edition conditional rule 적용됐는가?** — 예(monograph/multi_volume/collection 필수, periodical 선택).
5. **Issue validation 적용됐는가?** — 예(periodical만 허용, 그 외 금지).
6. **Manifest Layer validation 준비됐는가?** — 예, 단 opt-in(manifest_id 있는 entry만) + 역행 검사 없이 필드/enum 검증만.
7. **Metadata Migration 가능 상태인가?** — 아니오(BLOCKED, §8).
8. **TSU Pipeline 진입 가능한가?** — 아니오.

---

```
STATUS: COMPLETE (design-to-code, no migration performed)
FILES CHANGED: scripts/source_validator.py, tests/test_validator_v22.py (new), tests/test_source_validator_v2.py (1 test scope fix)
TEST RESULT: 34 passed, 0 failed (15 existing + 19 new)
REGRESSION: v1.2 isolated 21/0/0 unchanged; full-tree 89/0/0 unchanged
MIGRATION READINESS: BLOCKED
COMMIT WAITING FOR APPROVAL
```

---

## 로드맵 갱신

```
Validator v2.2 Implementation   ✅ (이번 작업)

C1 Validator Review              NEXT
Schema v2.2 Final Approval        FUTURE
Manifest Pilot                     FUTURE
Metadata Migration Approval         FUTURE
TSU Pipeline                          FUTURE
```

---

*RAW 수정, Registry YAML 수정, Pilot 데이터 수정, Metadata Migration,
TSU/Embedding 생성, Retrieval 코드 변경, Git Commit/Push — 전부
수행하지 않음.*
