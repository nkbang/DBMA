# NAE Metadata Migration Pilot Implementation Review 001

**Project:** CUE-TASK-ORDER-042 / NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001
**작성일:** 2026-08-05
**검토 성격:** Read-Only Architecture/Implementation Review (수정 없음)

---

## Executive Summary

Metadata Migration Pilot Implementation(NAE-METADATA-MIGRATION-PILOT-IMPLEMENTATION-001)은 Migration Engine Design 001(§Q6 우선순위 1~4순위)에 기반한 **Engine + Adapter + Pilot Executor**의 완전한 구현체이다.

**판정: APPROVED WITH CONDITIONS**

---

## 2. Reviewed Documents/Files

### 설계 문서
| 문서 | 상태 |
|---|---|
| `docs/NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md` | Design Only (TASK-ORDER-041) |

### 구현 파일
| 파일 | 역할 |
|---|---|
| `scripts/migration_engine.py` | Migration Engine (State Machine/Checkpoint/Lock/Audit/Idempotency/Rollback) |
| `scripts/adapters/registry_adapter.py` | Authority Registry Adapter (5-tier entity YAML 처리) |
| `scripts/adapters/manifest_adapter.py` | Manifest Layer Adapter (FK verify + Audit touch) |
| `scripts/migrate_pilot.py` | Pilot Executor (Orchestration) |
| `scripts/migration_audit.py` | Audit Logger |
| `scripts/migration_checkpoint.py` | Checkpoint Manager |
| `scripts/migration_lock.py` | Migration Lock |
| `scripts/migration_report.py` | Report Generator |

### Test 파일
| 파일 | 역할 |
|---|---|
| `tests/test_migration_engine.py` | Engine 핵심 로직 테스트 |
| `tests/test_registry_adapter.py` | Registry Adapter 테스트 |
| `tests/test_manifest_adapter.py` | Manifest Adapter 테스트 |
| `tests/test_pilot_executor.py` | Pilot Executor 통합 테스트 |
| `tests/test_migration_checkpoint.py` | Checkpoint 테스트 |
| `tests/test_migration_lock.py` | Lock 테스트 |

---

## 3. Existing Architecture Compatibility

### ADR-016 (5-tier Model) — PASS
- Registry Adapter의 `ENTITY_FILES` 매핑(§registry_adapter.py:41-47)이 `authors/works/editions/volumes/sources` 5개 entity를 정확히 반영
- FK 방향(자식→부모)이 ADR-016 모델과 일치
- Migration Unit이 "폐쇄 집합" 원칙을 준수 (§design §1)

### ADR-017 (Option B: canonical_id backfill, 기존 FK 불변) — PASS
- `build_canonical_id_backfill_unit()` (§registry_adapter.py:116-173)이 `canonical_id`만 채우고 `author_id`/`work_id` 등 기존 FK 필드는 건드리지 않음
- `CANONICAL_ID_RE` (§registry_adapter.py:52)가 lowercase snake_case 형식 강제
- `canonical_id_map`/`legacy_id_map`이 호출자 주입 방식 (정책과 실행 분리, §design §Q1)

### ADR-018 (Periodical 확장) — PASS (설계상 가능)
- `ENTITY_FILES`에 `volumes`가 포함되어 있어 periodical(volume+issue) 확장에 대응 가능
- **조건:** 실제 periodical entity YAML이 생성되면 Adapter에 `issues` entity 추가 필요 (현재 구현은 5개 entity로 고정)

### ADR-019 (Manifest Layer) — PASS
- Manifest Adapter의 `verify_fk()` (§manifest_adapter.py:72-99)가 Registry Migration 후 FK 유효성 재확인
- `build_touch_unit()` (§manifest_adapter.py:102-133)이 `updated_at` Audit 필드만 갱신 (FK 값 변경 없음)
- Manifest Layer의 `tsu_status`/`acquisition_status` 등 lifecycle 필드는 Migration Engine이 건드리지 않음 (별도 TSU Pipeline 책임, §design §14)

### ID Governance v1 — PASS
- `build_canonical_id_backfill_unit()`의 `canonical_id_map` 주입 방식이 ID Governance §6.2 매핑표 정책과 일치
- "Adapter가 값을 결정하지 않고 호출자가 결정한 값만 적용" (§registry_adapter.py:12-15 주석)

---

## 4. Migration Engine Review (ADR-014/ADR-015 유사 구조)

### State Machine (§design §2 / §engine:85-351) — PASS
```
PENDING -> VALIDATING -> MIGRATING -> VERIFYING -> COMPLETE
                  \-> FAILED -> ROLLED_BACK(가능한 경우만)
```
- `execute()` (§engine:162-263)가 정상 경로(PENDING→COMPLETE) 구현
- 실패 경로(Failed→Rolled Back)가 `_rollback()` (§engine:313-351)에서 처리
- **역행 규칙:** `rollback_supported()` (§engine:296-301)가 COMPLETE 이후 Rollback 거부

### Checkpoint (§design §3 / §checkpoint.py) — PASS
- Checkpoint A(pre-migration)와 Checkpoint B(post-migration) 모두 구현
- Migration Unit 1개 = Checkpoint 1개 (분할 Checkpoint 금지, §design §3)

### Idempotency (§design §5 / §engine:191-205) — PASS
- `old_contents == new_contents` 체크로 no-op COMPLETE
- 결정적 Migration Unit ID: `hash(target_key:migration_version)` (§engine:58-61)

### Rollback (§design §4 / §engine:313-351) — PASS
- Checkpoint A(before) 복원 구현
- **불가능한 경우:** COMPLETE 이후 (§engine:299-300), 의존 순서 역순 연쇄 Rollback 불가 (§design §4-2)

### Migration Lock (§design §10 / §lock.py) — PASS
- 파일 단위 Lock 구현
- timeout 지원 (좀비 Lock 방지)

### Dry Run (§design §9 / §engine:113-159) — PASS
- `dry_run()`이 VALIDATING까지만 실행, MIGRATING(실제 쓰기) 건너뜀
- Audit Log에 `result: "DRY_RUN"` 기록

---

## 5. Registry Adapter Review (ADR-014 유사)

### Domain Separation — PASS
- Registry YAML 구조(`authors/works/editions/volumes/sources`)만 처리
- Manifest/Corpus/TSU 경로와 분리 (§registry_adapter.py:17-20: "어떤 실제 경로도 하드코딩하지 않음")

### Storage Architecture — PASS
- Pilot Fixture 전용 (`--registry-root` 필수 인자, §migrate_pilot.py:106)
- 실 Production/Pilot Registry 경로를 기본값으로 갖지 않음 (§migrate_pilot.py:12-17)

### Metadata Impact — PASS
- `canonical_id` 필드만 추가 (기존 ID 필드 변경 없음)
- `legacy_id` 배열은 기존 값 보존 + append (§registry_adapter.py:154-156)

### Copyright Governance — PASS
- Registry Adapter가 저작권 정보를 다루지 않음 (Manifest Layer의 책임)

---

## 6. Manifest Adapter Review (ADR-015 유사)

### Lifecycle — PASS
- Manifest의 `updated_at` Audit 필드만 갱신 (§manifest_adapter.py:122)
- FK 값 변경 없음 (§manifest_adapter.py:10-13: "FK 자체는 안 바뀌어야 함을 재확인")

### Authority Model — PASS
- `author_id`/`work_id`/`edition_id`/`volume_id`/`source_id` FK 검증 (§manifest_adapter.py:41, §manifest_adapter.py:80-86)
- 동일 저자/동명이인/Edition 관리는 Registry Adapter가 아닌 호출자(정책 계층)의 책임

### Duplicate Policy — PASS
- Manifest Adapter가 데이터 삭제를 수행하지 않음 (verify만 수행)

---

## 7. Metadata Compatibility Audit

### 기존 Schema 변경 없이 가능한가? — YES
- `canonical_id` 필드 추가: ADR-017에서 이미 승인된 필드
- `legacy_id` 배열 추가: ADR-017에서 이미 승인된 필드
- Manifest Layer의 FK 값 변경 없음 (§design §Q1)

### Migration 필요한가? — NO (Schema Versioning 불필요)
- Registry `schema_version: "1.0"` 그대로 유지 (§design §11)
- Migration Version과 Schema Version은 별개 축 (§design §11)

### Versioning 방식 적절한가? — YES
- Migration Version: `1.0.0` (Engine 로직 버전, §design §11)
- Schema Version: 기존 `1.0` (Registry) / `v2.2.x` (Manifest) 변경 없음

---

## 8. TSU Pipeline Compatibility

### 현재 TSU 구조와 충돌하는가? — NO
- Migration Engine이 TSU를 생성하지 않음 (§design §14, §engine:100-103 주석)
- `verify_hooks` (§engine:92, §engine:104)가 TSU ELIGIBLE 재계산을 위한 확장점 (실제 Validator 연결은 향후 Pilot Migration 단계)

### TSU Schema 변경 필요한가? — NO
- Migration Engine이 TSU 스키마를 건드리지 않음
- Manifest의 `tsu_status`는 TSU Pipeline의 책임 (§design §14)

---

## 9. Retrieval Compatibility

### RetrievalEngine과 충돌하는가? — NO
- Migration Engine이 Retrieval 경로(`core/retrieval.py`)를 건드리지 않음
- Registry canonical_id backfill은 Metadata Layer 내부 작업일 뿐, Retrieval API와 무관

### Source weighting / Domain filter / Authority ranking — 보호됨
- 이 기능들은 Manifest/Corpus Layer에서 동작 (Migration Engine이 건드리지 않음)
- FK 참조 무결성만 보장되면 Retrieval에 영향 없음 (§manifest_adapter.py:72-99)

---

## 10. Identified Risks

| 항목 | 평가 | 근거 |
|---|---|---|
| Architecture | PASS | ADR-016~019와 충돌 없음 |
| Metadata | PASS | 기존 Schema 변경 없음, canonical_id/legacy_id는 이미 승인된 필드 |
| TSU | PASS | Migration Engine이 TSU 생성 안 함 (§design §14) |
| Retrieval | PASS | Retrieval 경로 건드리지 않음 |
| Copyright | PASS | Registry Adapter가 저작권 정보 안 다룸 |
| Future Expansion | WARNING | Periodical `issues` entity 추가 필요 (§5-1), 분산 Migration (§design §Q2) |

---

## 11. Recommendations

### 즉시 조치 필요 (CONDITIONS)
1. **Pilot Migration 실행 전 Dry Run 필수** (§design §9): 실제 Pilot Fixture(`resources/theological_sources/manifest/pilot/`)에서 `--dry-run` 실행 후 VALIDATING 결과 확인
2. **3-Validator 재실행 조건 명시**: `verify_hooks`에 실제 Validator 연결 필요 (현재는 확장점만 존재, §engine:100-103)

### 향후 조치
3. **Periodical `issues` entity 추가**: ADR-018 준수 위해 `editions` 아래 `issues` entity 지원 필요 (§registry_adapter.py:41-47)
4. **분산 Migration 설계**: 다중 프로세스 실행 필요 시 별도 ADR 발행 (§design §Q2)

---

## 12. Final Verdict

**판정: APPROVED WITH CONDITIONS**

### 승인 조건
1. Pilot Migration 실행 전 `--dry-run`으로 VALIDATING 결과 확인
2. `verify_hooks`에 실제 Validator 연결 (3-Validator 재실행)

### 조건부 승인 이유
- Engine/Adapter/Executor 구현이 설계 문서(§Q6 우선순위 1~4순위)를 정확히 반영
- ADR-016~019, ID Governance v1과 충돌 없음
- Metadata Layer 구축 전에 수정해야 할 문제: **없음** (canonical_id/legacy_id는 이미 승인된 필드)

---

## 13. Required Questions Answered

### Q1. CUE 설계가 현재 NAE 구조와 충돌하는가?
**아니오.** ADR-016~019, ID Governance v1과 충돌 없음. Engine/Adapter 구현이 설계 문서를 정확히 반영.

### Q2. ADR-014 (NAE-Modern-Corpus-Layer)는 승인 가능한가?
**별도 검토 필요.** 이번 리뷰는 Metadata Migration Pilot에 집중. ADR-014는 별도 Architecture Design Review (§NAE_ARCHITECTURE_DESIGN_REVIEW_001.md 참조).

### Q3. ADR-015 (NAE-Corpus-Ingestion-Standard)는 승인 가능한가?
**별도 검토 필요.** 이번 리뷰는 Metadata Migration Pilot에 집중. ADR-015는 별도 Architecture Design Review (§NAE_ARCHITECTURE_DESIGN_REVIEW_001.md 참조).

### Q4. Metadata Layer 구축 전에 수정해야 할 문제가 있는가?
**없음.** canonical_id/legacy_id 필드는 ADR-017에서 이미 승인됨. 기존 Schema 변경 불필요.

### Q5. TSU Pipeline으로 넘어가도 되는가?
**조건부 YES.** Pilot Migration(Dry Run + 3-Validator 재실행) 성공 후 TSU Pipeline 진행 가능.

### Q6. Retrieval Architecture를 보호하고 있는가?
**예.** Migration Engine이 Retrieval 경로(`core/retrieval.py`)를 건드리지 않음. FK 무결성만 보장되면 Retrieval에 영향 없음.

---

*Git Commit/Push 미수행 — 워킹트리에만 존재. 이 문서는 Read-Only Review 결과임.*