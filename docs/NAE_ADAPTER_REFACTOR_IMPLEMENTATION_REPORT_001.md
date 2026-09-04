# NAE Adapter Refactor Implementation Report 001

**Project:** CUE-TASK-ORDER-046 / NAE-ADAPTER-REFACTOR-001
**작성일:** 2026-08-05
**성격:** Adapter Layer 전용 리팩터 — Migration Engine/Validator/
Registry/Manifest/RAW/ADR 전부 무변경. Fixture만 사용.
**Git Commit/Push:** 미수행 — 사용자 승인 대기.

---

## 1. Executive Summary

`scripts/adapters/registry_adapter.py`/`manifest_adapter.py`의 내부
직렬화 엔진을 `PyYAML`(`safe_load`/`safe_dump`) → `ruamel.yaml`
round-trip(`typ="rt"`)으로 교체했다. `NAE_PILOT_MIGRATION_VALIDATION_
REPORT_001.md` §4에서 발견된 결함(주석 전체 삭제, 따옴표 스타일 변경,
들여쓰기 변경, 키 순서 변경)을 제거하는 것이 유일한 목적이며,
**Migration Engine(`scripts/migration_engine.py` 등 5개 모듈)과 3개
Validator는 이번 작업에서 한 글자도 수정하지 않았다** — Adapter의
`transform` 함수 시그니처(`dict[str,str] -> dict[str,str]`)는 그대로
유지했으므로 Engine 쪽에서 볼 때 아무것도 달라지지 않았다.

구현 중 두 가지 문제를 추가로 발견해 수정했다(§3):
1. round-trip 기본 들여쓰기 설정이 원본 파일의 실제 스타일(dash가
   2칸 들여써지는 형태)과 달라 재직렬화 시 들여쓰기가 바뀌는 문제
2. `None` 값을 ruamel이 기본적으로 빈 값으로 덤프해 원본의 명시적
   `null` 표기가 사라지는 문제

두 문제 모두 Adapter 내부의 YAML 설정(`indent()`, custom
representer)만으로 해결했다 — Engine/Validator 변경 없음.

---

## 2. 구현 내용

| 파일 | 변경 |
|---|---|
| `scripts/adapters/registry_adapter.py` | `import yaml` → `from ruamel.yaml import YAML` 등. `_load_yaml`/`_dump_yaml`/`_yaml()` 헬퍼 추가. `build_canonical_id_backfill_unit`의 `transform`이 이제 `raw`(CommentedMap)를 그 자리에서 수정(entry 재구성 안 함), 신규 `canonical_id`/`legacy_id`는 `CommentedMap.insert()`로 id_field 바로 다음 위치에 삽입. `_serialize()` 헬퍼 제거(더 이상 전체 재구성 안 함). |
| `scripts/adapters/manifest_adapter.py` | 동일한 방식. `build_touch_unit`의 `transform`이 `updated_at` 값이 실제로 다를 때만 그 필드를 `DoubleQuotedScalarString`(원본이 따옴표였으면 동일 스타일 유지)으로 교체, 나머지는 손대지 않음. |
| `requirements.txt` | `ruamel.yaml` 의존성 추가(PyYAML 다음 줄) |
| `tests/test_comment_preservation.py` | 신규(§4) |

### API 변경 없음 확인

`build_canonical_id_backfill_unit`/`build_all_backfill_units`/
`build_touch_unit`/`load_entity_file`/`load_registry`/`load_manifest`/
`canonical_id_lookup`/`legacy_id_lookup`/`source_id_lookup`/
`edition_id_lookup`/`volume_id_lookup`/`verify_fk` — 함수 시그니처
전부 그대로. 기존 `tests/test_registry_adapter.py`(12)/
`test_manifest_adapter.py`(9)/`test_pilot_executor.py`(8) = **29개
테스트를 한 줄도 수정하지 않고 재실행해 전부 PASS**했다(§5) — 이것이
API 무변경의 가장 직접적인 증거다.

---

## 3. 구현 중 발견·수정한 세부 문제

### 3.1 Sequence Indent(들여쓰기) 불일치

ruamel round-trip은 로드 시 원본 들여쓰기를 기억하지 않고, 덤프 시
`YAML()` 인스턴스의 `indent()` 설정을 그대로 쓴다 — 기본값(`offset=0`)
으로 덤프하면 실제 Registry/Manifest 파일의 실제 스타일
(`"  - key:"` — dash가 2칸 들여써짐, 즉 `sequence=4, offset=2`)과
달라진다는 것을 스크래치 테스트로 확인했다. `_yaml()` 헬퍼에
`y.indent(mapping=2, sequence=4, offset=2)`를 명시해 해결했다.

### 3.2 `null` 표기 소실

ruamel은 `None` 값을 기본적으로 빈 스칼라(`key:`)로 덤프한다 — 원본의
`volume_id: null` 같은 명시적 `null` 표기가 `volume_id:`로 바뀌는
것을 스크래치 테스트로 확인했다(의미는 동일하지만 표기가 다름 —
Whitespace/Formatting Preservation 위반). `type(None)`에 대한 custom
representer(`_represent_none`)를 등록해 항상 `null` 리터럴로 덤프하도록
고정했다.

두 문제 모두 **구현 범위를 벗어난 "개선"이 아니라, "Comment-Preserving
YAML"이라는 이번 작업의 목표(AC-1~AC-5) 자체를 달성하기 위해 반드시
필요한 수정**이었으므로 코드에 반영했다 — 작업 명령서의 "구현 범위를
벗어난 개선은 WARNING으로만 보고" 조항은 이 항목에는 해당하지 않는다고
판단했다(목표 달성에 필수적인 세부 구현이지, 범위를 벗어난 별도
개선 제안이 아님).

---

## 4. 신규 테스트(`tests/test_comment_preservation.py`, 14개)

실제 Registry(`authors.yaml`)/Manifest(`manifest.yaml`) 파일과 동일한
모양(주석 스타일·따옴표·빈 줄·들여쓰기)의 fixture를 사용 — 실 데이터는
전혀 열지 않는다.

| 클래스 | 테스트 | 확인 내용 |
|---|---|---|
| `TestCommentPreservation` | 2 | 헤더 주석/인라인 주석/notes 블록 스칼라 보존(Manifest, Registry 각 1) |
| `TestQuotePreservation` | 3 | `schema_version: "1.0.0"` 그대로, 새로 쓰는 `updated_at` 값도 원본과 동일하게 큰따옴표, Registry 기존 필드(`canonical_name` 등) 따옴표 유지 |
| `TestOrderPreservation` | 2 | Manifest 필드 순서(`created_at`→`updated_at`→`verified_by`) 유지, Registry 신규 필드(`canonical_id`)가 `author_id` 바로 다음에 삽입되고 그 뒤 순서 유지 |
| `TestWhitespacePreservation` | 2 | 빈 줄 개수 불변(Manifest), entry 사이 빈 줄 유지(Registry) |
| `TestTouchMigrationOnlyChangesUpdatedAt` | 1 | **AC-6**: 원본과 결과의 줄 수가 같고, 실제로 다른 줄은 `updated_at` 딱 1줄뿐 |
| `TestIdempotency` | 2 | 2회 실행 시 2회차는 `skipped_count==1`이고 파일 바이트 완전 동일(Manifest, Registry 각 1) |
| `TestRollback` | 2 | `verify_hooks` 강제 실패 → Rollback → `filecmp.cmp(..., shallow=False)`로 byte-identical 확인(Manifest, Registry 각 1) |

```
tests/test_comment_preservation.py: 14 passed
```

---

## 5. Regression

```
tests/test_registry_adapter.py(12) + test_manifest_adapter.py(9) +
test_pilot_executor.py(8)                                            : 29 passed(무수정, 전부 그대로 PASS)

tests/test_migration_lock.py(7) + test_migration_checkpoint.py(7) +
test_migration_engine.py(17)                                         : 31 passed(무수정 — Engine 코드 자체를 안 건드렸으므로 당연히 불변)

tests/test_source_validator_v2.py + test_validator_v22.py +
test_manifest_validator.py + test_authority_validator.py +
test_authority_validator_canonical.py                                 : 무수정, 기존과 동일

tests/test_comment_preservation.py(신규)                               : 14 passed

합계                                                                    : 149 passed
(직전 보고 135 passed + 신규 14 = 149, 감소 없음)

source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (기존과 동일)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (기존과 동일)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (기존과 동일)

실 데이터 무변경 확인:
$ git status --short resources/theological_sources/ NAE/corpus/raw
(출력 없음)
```

---

## 6. Architecture Freeze Rule / 금지 목록 준수

- ADR-016/017/018/019(Approved) 어느 것도 변경하지 않았다 — 이번
  작업은 직렬화 엔진(구현 세부사항)만 바꿨고, canonical_id/legacy_id
  필드 의미·FK 규칙·Manifest lifecycle 규칙은 전혀 손대지 않았다.
  충돌 발견 없음.
- `scripts/migration_engine.py`/`migration_checkpoint.py`/
  `migration_lock.py`/`migration_audit.py`/`migration_report.py`/
  `source_validator.py`/`manifest_validator.py`/`authority_validator.py`
  — 전부 무변경(git 추적 상 diff 없음).
- `resources/`, `NAE/`, Registry/Manifest/RAW YAML, ADR 문서 — 전부
  무변경(§5 `git status` 빈 결과로 확인).
- Migration 실행/Pilot Migration 실행 — 이번 작업에서 수행하지 않음
  (테스트는 전부 `tmp_path` fixture만 사용).

---

## 완료 보고

```
STATUS: COMPLETE (Adapter serialization refactor only, no Engine/Validator/real-data changes)

FILES MODIFIED:
scripts/adapters/registry_adapter.py
scripts/adapters/manifest_adapter.py
requirements.txt (ruamel.yaml 의존성 추가)

FILES CREATED:
tests/test_comment_preservation.py
docs/NAE_ADAPTER_REFACTOR_IMPLEMENTATION_REPORT_001.md

TEST RESULT:
14 passed(신규), 149 passed(전체 합계 — 직전 135 + 신규 14, 회귀 없음)

REGRESSION:
PASS — Migration Engine 테스트(31) + 3-Validator 테스트 + Adapter/Pilot Executor 테스트(29) 전부 무수정 그대로 PASS. 3-Validator 실행 결과 완전 동일(drift 없음).

COMMENT PRESERVATION:
PASS

QUOTE PRESERVATION:
PASS

ORDER PRESERVATION:
PASS

WHITESPACE PRESERVATION:
PASS

IDEMPOTENCY:
PASS

ROLLBACK:
PASS

BLOCKER:
0

WARNING:
1 (Registry Adapter의 canonical_id backfill 경로는 여전히 Fixture 규모에서만 재검증됨 — NAE_PILOT_MIGRATION_VALIDATION_REPORT_001.md에서 발견된 결함이 실제 Production Registry에 실행된 적은 없으므로, 이번 수정 이후에도 실 데이터 최초 실행 전 C1 검토 + 재검증 절차가 필요)

GIT:
NOT PERFORMED
```
