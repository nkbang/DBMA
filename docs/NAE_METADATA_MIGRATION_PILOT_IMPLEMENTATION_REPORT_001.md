# NAE Metadata Migration Pilot Implementation Report 001

**Project:** NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001
**작성일:** 2026-08-05
**성격:** Registry/Manifest Adapter + Pilot Executor 구현 — 실 Registry/
Manifest/RAW 데이터는 전혀 건드리지 않음(Pilot Fixture만 사용).
**Git Commit/Push:** 미수행 — 사용자 승인 대기.

---

## 1. Executive Summary

`scripts/migration_engine.py`(NAE-METADATA-MIGRATION-IMPLEMENTATION-001)
는 그대로 두고, 그 위에 Domain을 아는 계층(Adapter)만 신규 구현했다.
Engine 코드는 이번 작업에서 **한 글자도 수정하지 않았다**. Registry
Adapter/Manifest Adapter/Pilot Executor 3개 모듈 + 테스트 3개 파일(29
테스트)을 작성했고, 전부 `tmp_path` 임시 디렉토리(Pilot Fixture)만
대상으로 실행된다 — 실 `resources/theological_sources/authority/`,
`resources/theological_sources/manifest/pilot/`, `NAE/corpus/raw/` 중
어느 것도 변경되지 않았음을 `git status --short`로 확인했다(§6).

---

## 2. 구현 내용

| 모듈 | 역할 | Domain 지식 |
|---|---|---|
| `scripts/adapters/registry_adapter.py` | Registry YAML load, `canonical_id_lookup`/`legacy_id_lookup`, canonical_id backfill `MigrationUnit` 생성 | ADR-016(5-tier 모델) + ADR-017(canonical_id lowercase snake_case, Option B) |
| `scripts/adapters/manifest_adapter.py` | Manifest load, `source_id_lookup`/`edition_id_lookup`/`volume_id_lookup`, FK 재검증(`verify_fk`), Audit 필드 touch `MigrationUnit` 생성 | ADR-019(Manifest FK 필드, Processing Lifecycle) |
| `scripts/migrate_pilot.py` | Registry 로드 → Unit 생성 → Engine 실행(Dry Run/Execute) → Manifest FK 재검증 → Report 순서로 오케스트레이션, `PilotReport` 출력 형식(Registry/Manifest/Changed/Skipped/Rollback/Time) | 없음(흐름만 — Adapter가 만든 `MigrationUnit`을 Engine에 넘길 뿐) |

### 계층 분리 확인

```
migration_engine.py  (Domain을 모름 — 이번 작업에서 무변경)
        ▲
        │ import (단방향)
        │
adapters/registry_adapter.py, adapters/manifest_adapter.py  (Domain을 앎)
        ▲
        │ import
        │
migrate_pilot.py  (흐름만 담당)
```

`scripts/migration_engine.py`는 `scripts/adapters/`를 import하지 않는다
(반대 방향으로만 의존) — Engine이 Adapter의 존재를 모른다는 요구사항을
코드 구조로 보장한다.

### Option B 원칙 재확인(핵심 설계 결정)

Registry Adapter의 `build_canonical_id_backfill_unit`은 **기존 ID
필드(author_id 등)를 절대 변경하지 않고 `canonical_id`/`legacy_id`만
추가**한다. Manifest는 그 기존 ID 필드를 그대로 참조하므로, Manifest
Adapter의 역할은 FK 값을 고쳐 쓰는 것이 아니라 **FK가 여전히 유효한지
재검증**하는 것으로 제한했다(`verify_fk`) — `build_touch_unit`은
Audit 필드(`updated_at`)만 갱신하며 FK 필드는 일절 다루지 않는다.
`test_pilot_executor.py::TestExecute::test_execute_writes_registry_and_preserves_manifest_fk`
가 이 불변성(Registry에는 `canonical_id: fuller_andrew` 추가, Manifest
의 `author_id: FULLER-ANDREW-001`은 그대로)을 직접 검증한다.

### Idempotency 버그 수정(구현 중 발견)

최초 구현에서 `transform`이 항상 `yaml.safe_dump`로 재직렬화하다 보니,
**논리적으로 아무것도 바뀌지 않았는데도 YAML 포맷(따옴표 스타일 등)이
달라져 Engine의 텍스트 비교 기반 Idempotency 체크가 오작동**하는
문제를 테스트로 발견했다(`test_backfill_is_noop_when_nothing_to_fill`
최초 FAIL). 두 Adapter의 `transform` 모두 "실제로 필드가 바뀐 경우에만
재직렬화, 아니면 원본 텍스트를 그대로 반환"하도록 수정해 해결했다 —
Engine 코드는 건드리지 않고 Adapter 쪽에서 수정(계층 분리 원칙 유지).

---

## 3. 테스트

| 파일 | 테스트 수 | 대상 |
|---|---|---|
| `tests/test_registry_adapter.py` | 12 | load/lookup, canonical_id backfill(정상/no-op/ADR-017 형식 위반/기존 FK 불변), 파일당 1 Unit 생성 |
| `tests/test_manifest_adapter.py` | 9 | load/lookup(source/edition/volume), FK 재검증(정상/Broken/canonical_id backfill에 영향받지 않음), Audit touch(정상/Idempotent) |
| `tests/test_pilot_executor.py` | 8 | Dry Run(무변경 확인), Execute(Registry 변경 + Manifest FK 불변), FK Broken 탐지, Checkpoint 생성 확인, **VERIFYING 실패 시 자동 Rollback**, 전체 Pilot 흐름 Idempotency(2회 실행 시 2회차 전부 skip) |
| **합계** | **29** | 전부 PASS |

```
tests/test_registry_adapter.py + test_manifest_adapter.py + test_pilot_executor.py: 29 passed
```

---

## 4. Regression

```
source_validator.py --root resources/theological_sources        : PASS=89  WARNING=0  FAIL=0  (기존과 동일)
manifest_validator.py(Pilot, corpus-manifest-root 지정)           : PASS=138 WARNING=0  FAIL=0  (기존과 동일)
authority_validator.py(Production)                                : PASS=128 WARNING=26 FAIL=0  (기존과 동일)

전체(source/manifest/authority validator + migration engine/checkpoint/
lock + registry/manifest adapter + pilot executor) pytest             : 135 passed
```

기존 106개 테스트 전부 무변화로 통과, 신규 29개 추가 — **106 PASS
기준선 유지 확인.**

---

## 5. 완료 시 답변(작업 명령서 §6~9 대응)

### Adapter 100% 커버?

핵심 경로(load/lookup/backfill/no-op/형식 위반/FK 재검증/Audit
touch/Idempotency) 전부 테스트로 커버. 다만 실제 Production Registry
5개 파일 전체(28 entity)에 대한 실행은 이번 구현 범위 밖(Pilot Fixture
로만 검증) — Pilot Migration 실행 단계에서 다뤄야 할 항목.

### Pilot Executor 테스트(Dry Run/Failure/Rollback/Checkpoint)?

전부 구현·확인:
- Dry Run: 실제 쓰기 없음, FK Broken 없음 확인
- Failure: Registry 불완전 시 FK Broken 정확히 탐지(개수까지 확인)
- Rollback: VERIFYING 실패 hook 주입 시 자동 Rollback → 원본 파일 텍스트 완전 복원 확인
- Checkpoint: Migration Unit ID(결정적 해시, `registry:authors` 등)로 before/after Checkpoint 생성 확인

### 금지 목록 준수(§8)?

```
$ git status --short resources/theological_sources/authority resources/theological_sources/manifest NAE/corpus/raw
(출력 없음 — 무변경)
```

`NAE/corpus/raw/`, `resources/.../authority/*.yaml`,
`resources/.../manifest/pilot/*.yaml` 전부 미변경 확인. 모든 테스트는
`tmp_path`(pytest 임시 디렉토리) Fixture만 사용했다.

---

## 완료 보고

```
STATUS: COMPLETE (Adapter + Pilot Executor implementation only, no real data changes)

FILES CREATED:
scripts/adapters/registry_adapter.py
scripts/adapters/manifest_adapter.py
scripts/migrate_pilot.py
tests/test_registry_adapter.py
tests/test_manifest_adapter.py
tests/test_pilot_executor.py
docs/NAE_METADATA_MIGRATION_PILOT_IMPLEMENTATION_REPORT_001.md

FILES MODIFIED:
(없음 — scripts/migration_{engine,checkpoint,lock,audit,report}.py 전부 무변경)

TEST RESULT:
29 passed(Registry Adapter 12, Manifest Adapter 9, Pilot Executor 8)

REGRESSION:
PASS — 기존 106 PASS 기준선 유지, 전체 135 passed. source_validator 89/0/0, manifest_validator 138/0/0, authority_validator 128/26/0 전부 기존과 동일(drift 없음)

BLOCKER:
0

WARNING:
1 (실 Production Registry 28 entity 전체에 대한 실행은 아직 검증되지 않음 — Pilot Fixture 규모에서만 확인됨. 실제 Pilot Migration 착수 시 canonical_id_map/legacy_id_map을 NAE_ID_GOVERNANCE_v1.md §6.2 매핑표에서 가져와 첫 실행해봐야 함)

NEXT STEP:
C1에 NAE-METADATA-MIGRATION-PILOT-REVIEW-001 전달(Adapter/Engine 분리, ADR-016/017/019 준수, Dry Run 무변경, Rollback 경계, Pilot이 실 Registry를 변경하지 않는지 검토) → 승인 후 실제 Pilot Migration(Production Registry 대상, §6.2 매핑표 사용) 착수

GIT:
NOT PERFORMED(사용자 승인 대기)
```
