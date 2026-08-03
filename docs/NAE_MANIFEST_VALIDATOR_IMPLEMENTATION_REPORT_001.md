# NAE Manifest Validator Implementation Report 001

**Project:** NAE-MANIFEST-VALIDATOR-IMPLEMENTATION-001
**Date:** 2026-08-03
**Nature:** Validator 코드 구현 — Metadata Migration/TSU 아님
**Git Commit/Push:** 미수행 — 사용자 승인 대기

---

## 1. Executive Summary

`scripts/manifest_validator.py`를 신규 구현해 Manifest Layer(ADR-019)
파일을 실제로 검증 가능하게 만들었다 — `NAE_MANIFEST_PILOT_REPORT_001.md`
§5가 지적한 BLOCKER(Manifest 파일이 어떤 도구로도 탐색되지 않음)를
해소했다. 실제 Manifest Pilot 10건에 대해 이 새 도구를 실행한 결과,
**Reference Integrity/Authority FK는 전부 PASS**했으나 **Lifecycle
필드 값(metadata_status/tsu_status/embedding_status)이 스키마 정의와
불일치하는 기존 데이터 결함을 실측으로 발견**했다(PASS=98,
WARNING=10, FAIL=30 — 아래 §4 상세). 이 결함은 이번 구현이 만든
문제가 아니라 이전 Pilot 작업에서 이미 존재하던 데이터 오류이며,
**이번 작업 범위(Manifest Pilot 데이터 수정은 허용 목록에 없음)에서는
수정하지 않고 그대로 보고**했다. 신규 테스트 15개 전부 PASS, 기존
`source_validator.py` 관련 테스트 34개도 전부 PASS(회귀 없음).

---

## 2. 구현 내용

### `scripts/manifest_validator.py`(신규)

- `--root`(기본: `resources/theological_sources/manifest`),
  `--registry-path`(**필수**), `--corpus-manifest-root`(선택) 3개 인자.
- Identity(`manifest_id`/`source_id`/`schema_version`) 존재 확인.
- Authority Reference FK(`author_id`/`work_id`/`edition_id`/
  `volume_id`/`issue_id`/`source_id`) — Registry 각 파일(authors/
  works/editions/volumes/issues/sources.yaml)을 읽어 실제 존재 여부
  확인.
- `work_type` 조건부 규칙 — `work_id`로 Registry의 `works.yaml`을
  조회해 `work_type`을 얻고, `source_validator.py`와 동일한 규칙표로
  `edition_id`/`volume_id`/`issue_id` 필수/금지 여부 재확인(값만
  복제, import 의존성은 만들지 않음 — 두 파일이 서로 참조하지 않는
  기존 관례 유지).
- Processing Lifecycle 5개 필드 enum 검증(Manifest Schema Design v1
  정본 값 사용: `ocr_status`는 `complete`, `metadata_status`는
  `verified`, `tsu_status`는 `not_ready`/`ready`/`complete`/`failed`,
  `embedding_status`는 `not_started`/`in_progress`/`complete`/
  `failed`).
- Audit(`created_at`/`updated_at` 필수, `verified_by` 없으면
  WARNING).
- `Source:Manifest = 1:1` 위반 검사(동일 `source_id`가 두 Manifest
  Entry에 걸쳐 나타나면 FAIL).
- `manifest_id` 중복 검사(전체 트리 기준).
- **TSU_ELIGIBLE 계산**(읽기 전용) — 5개 조건 AND, `copyright_status`는
  `--corpus-manifest-root`로 corpus manifest(`source_manifest.yaml`)를
  전수 스캔해 `source_id` 기준 교차 조회. 미지정 시 "조회 불가"로
  자동 BLOCKED 처리(안전한 실패). 출력은 entry 라인에 `TSU_ELIGIBLE=
  READY` 또는 `TSU_ELIGIBLE=BLOCKED — {사유}`로 표시(WARNING 레벨 —
  FAIL이 아님, 이 판정 자체는 데이터 오류가 아니라 상태 보고이므로).

### `tests/test_manifest_validator.py`(신규, 15개)

Identity/Schema 3, Enum 2, Authority FK 3, TSU_ELIGIBLE 5, Source:
Manifest 1:1 위반 1, 실제 Pilot 데이터 회귀 1.

---

## 3. Manifest Pilot 10건 실행 결과

```
--root resources/theological_sources/manifest
--registry-path resources/theological_sources/authority
--corpus-manifest-root resources/theological_sources

=== 결과 요약: PASS=98 WARNING=10 FAIL=30 ===
```

**Authority FK 결과**: 10건 전부 `author_id`/`work_id`/`edition_id`/
`volume_id`(해당 시)/`source_id` PASS — Manifest Pilot Report-001의
Reference Integrity 검증(별도 스크립트, 10/10 PASS)과 **정확히
일치**한다(회귀 확인).

**FAIL 30건의 원인(전부 동일 패턴, 10건 × 3필드)**:

| 필드 | Pilot 데이터 실제 값 | 스키마 정본 값 | 문제 |
|---|---|---|---|
| `metadata_status` | `validated` | `verified` | 값 자체가 다름 |
| `tsu_status` | `pending` | `not_ready`/`ready`/`complete`/`failed` | `pending`이라는 값이 이 필드의 enum에 없음 |
| `embedding_status` | `pending` | `not_started`/`in_progress`/`complete`/`failed` | 동일 |

**원인 분석**: `acquisition_status`는 enum에 `pending`이 포함돼 있어
문제 없이 통과했으나(`pending`/`acquired`/`failed`), Pilot 데이터
작성 시 나머지 3개 필드에도 "아직 시작 안 함"을 뜻하는 값으로
일괄 `pending`을 사용한 것이 원인이다 — 각 필드가 실제로는 서로
다른 "미시작" 표현(`not_ready`/`not_started`)을 쓰도록 설계돼 있었다
(`NAE_CORPUS_MANIFEST_SCHEMA_DESIGN_v1.md` §Phase2). `metadata_status`는
값 자체를 잘못 선택한 것(`validated`는 애초에 정의된 enum에 없음).

**이번 작업에서 수정하지 않은 이유**: 이번 명령서의 허용 목록에
"Manifest Pilot 데이터 수정"이 없다 — `manifest_validator.py` 구현이
목적이었고, 그 도구가 실데이터의 결함을 정확히 잡아낸 것 자체가
성공적인 검증이다. 수정은 별도 승인 작업으로 남긴다(§7 Remaining
Risks #1).

---

## 4. Regression 결과

```
source_validator.py --root resources/theological_sources/baptist   : 21 PASS / 0 WARNING / 0 FAIL (불변)
source_validator.py --root resources/theological_sources(전체)      : 89 PASS / 0 WARNING / 0 FAIL (불변)

tests/test_source_validator_v2.py   15 passed
tests/test_validator_v22.py          19 passed
tests/test_manifest_validator.py     15 passed
합계                                  49 passed, 0 failed
```

`scripts/source_validator.py`는 이번 작업에서 **한 글자도 수정하지
않았다**(git diff 없음, 신규 파일만 추가) — 두 Validator가 완전히
독립적으로 존재함을 재확인.

---

## 5. Remaining Risks

| # | 리스크 | 설명 |
|---|---|---|
| 1 | **Manifest Pilot 10건의 Lifecycle 값 결함**(§3) | 실제 수정은 별도 승인 필요 — 수정 시 `metadata_status: validated→verified`, `tsu_status: pending→not_ready`, `embedding_status: pending→not_started`로 3필드×10건 = 30개 값 교정 |
| 2 | TSU_ELIGIBLE이 전부 BLOCKED로 나온 것도 위 §3 결함의 직접 결과 | Lifecycle 값을 교정하면 10건 모두 `metadata_status=verified`/`ocr_status=complete`/`copyright_status=public_domain`(이미 확인됨) 조건은 충족되므로 READY로 전환될 가능성이 높음(Authority FK도 이미 전부 PASS) — 단, `ocr_quality` 필드가 Pilot 데이터에 아예 없어 "미측정"으로 관대하게 처리되는 점은 별도로 유의 |
| 3 | `_WORK_TYPE_FIELD_RULES` 값이 `source_validator.py`와 `manifest_validator.py` 두 파일에 중복 정의됨 | 두 파일이 서로 import하지 않는 기존 관례를 유지하기 위한 의도된 중복 — 규칙이 바뀌면 두 곳을 함께 갱신해야 함(Validator Boundary Design-001 이후 재확인된 트레이드오프) |
| 4 | `authority_validator.py`(Registry 내부 FK 전담)는 여전히 설계만 존재 | 3-도구 체제 중 2개(`source_validator.py`, `manifest_validator.py`)만 구현됨 |

---

## 6. Migration Readiness

**BLOCKED.** Manifest Validator 구현 완료가 Metadata Migration
승인을 의미하지 않는다(명령서 원칙 재확인). §3의 데이터 결함이
남아 있고, `authority_validator.py`도 미구현이다.

---

## 완료 조건 답변

1. **Manifest Validator 구현 완료 여부** — 예(`scripts/manifest_validator.py`, 15개 테스트 전부 PASS).
2. **Manifest Pilot 10건 PASS 여부** — **아니오** — Authority FK는 10/10 PASS이나 Lifecycle enum 값 결함으로 30건 FAIL(§3, 기존 데이터 문제, 이번 작업에서 발견만 함).
3. **Authority FK PASS 여부** — **예, 10/10 PASS**(Manifest Pilot Report-001의 별도 스크립트 결과와 일치).
4. **TSU_ELIGIBLE 계산 정상 여부** — 계산 로직 자체는 정상 동작(READY/BLOCKED 판정 + 사유 출력, 테스트로 검증됨). 실제 Pilot 10건은 전부 BLOCKED(원인은 §3, 계산기 결함 아님).
5. **기존 Validator Regression 여부** — 없음(21/0/0, 89/0/0 불변, `source_validator.py` 무수정).
6. **Full Repository Regression 여부** — 없음(89 PASS 불변, 49/49 테스트 전부 PASS).
7. **Metadata Migration 착수 가능 여부** — **아니오.** 근거: (a) Manifest Pilot 10건이 실제로는 PASS 상태가 아님(§3), (b) `authority_validator.py` 미구현, (c) 이번 명령서 자체가 Migration을 명시적으로 금지.

---

## 로드맵 갱신

```
Manifest Validator Implementation   ✅ (이번 작업)

C1 Manifest Validator Implementation Review   NEXT
Manifest Pilot 데이터 결함 수정(별도 승인)        NEXT(권고)
Manifest Pilot Re-validation                    FUTURE
TSU_ELIGIBLE Verification                        FUTURE
Metadata Migration Readiness Review               FUTURE
Architecture Freeze v1.0                            FUTURE
Corpus-wide Metadata Migration                       FUTURE
```

---

*RAW 변경, Corpus Manifest 변경, Authority Registry 데이터 변경,
Metadata Migration, TSU/Embedding 생성, Retrieval 코드 변경, Git
Commit/Push — 전부 수행하지 않음.*
