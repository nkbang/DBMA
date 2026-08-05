# NAE Metadata Migration Sequence

**Project:** CUE-TASK-ORDER-041 / NAE-METADATA-MIGRATION-ENGINE-DESIGN-001
**작성일:** 2026-08-03
**성격:** Design Only — `NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md`의
Migration Unit/State Machine/Checkpoint/Rollback/Checksum/Audit Log
설계를 실제 실행 순서(시퀀스)로 재구성한 보조 문서.

---

## 1. 정상 경로(Happy Path) — Migration Unit 1건 실행

```
[사람/CUE]          [Migration Engine]         [3-Validator]      [Git]
    │                      │                        │               │
    │  Migration Plan 등록  │                        │               │
    │─────────────────────▶│                        │               │
    │                      │ Migration Unit ID 계산   │               │
    │                      │ (결정적 해시, 설계 §5)    │               │
    │                      │                        │               │
    │                      │ Migration Lock 획득(§10) │               │
    │                      │                        │               │
    │                      │ PENDING → VALIDATING   │               │
    │                      │ Checkpoint A 생성(§3)   │               │
    │                      │  - 대상 파일 목록 확정    │               │
    │                      │  - sha256(old) 기록(§7) │               │
    │                      │                        │               │
    │                      │ 사전 검증 실행 ─────────▶│               │
    │                      │  - FK 존재 확인          │               │
    │                      │  - canonical_id 형식     │               │
    │                      │  - "이미 목표 상태?" 확인 │               │
    │                      │◀──────────── PASS ──────│               │
    │                      │                        │               │
    │                      │ VALIDATING → MIGRATING │               │
    │                      │ YAML 파일 쓰기(폐쇄 집합  │               │
    │                      │ 전체를 한 번에, §1)       │               │
    │                      │                        │               │
    │                      │ MIGRATING → VERIFYING  │               │
    │                      │ 사후 검증 실행 ─────────▶│               │
    │                      │◀──────────── PASS ──────│               │
    │                      │                        │               │
    │                      │ VERIFYING → COMPLETE   │               │
    │                      │ Checkpoint B 생성(§3)   │               │
    │                      │  - sha256(new) 기록      │               │
    │                      │──────────── commit ────────────────────▶│
    │                      │                        │               │
    │                      │ Audit Log 기록(§6)       │               │
    │                      │ Migration Lock 해제      │               │
    │◀── COMPLETE 보고 ─────│                        │               │
```

---

## 2. 실패 → Rollback 경로

```
[Migration Engine]              [3-Validator]         [Git]
       │                             │                  │
       │ VALIDATING → MIGRATING      │                  │
       │ YAML 쓰기 중 오류 발생        │                  │
       │ (또는 VERIFYING에서 FAIL)    │                  │
       │                             │                  │
       │ MIGRATING/VERIFYING → FAILED│                  │
       │ Audit Log에 사유 기록         │                  │
       │                             │                  │
       │ Rollback 가능 여부 판정(§4)   │                  │
       │  - COMPLETE 이후? NO         │                  │
       │  - 연쇄 의존 Unit 있음? NO    │                  │
       │  - TSU 이미 생성? NO(범위 밖) │                  │
       │  → Rollback 가능             │                  │
       │                             │                  │
       │ Checkpoint A 시점으로 복원 ──────────────────────▶│ (git checkout)
       │                             │                  │
       │ sha256 재계산 → Checkpoint A │                  │
       │ 기록값과 일치 확인             │                  │
       │                             │                  │
       │ 3-Validator 재실행 ─────────▶│                  │
       │◀──────── FAIL 0건 확인 ──────│                  │
       │                             │                  │
       │ FAILED → ROLLED_BACK        │                  │
       │ Audit Log에 원인+Rollback    │                  │
       │ 결과 기록                    │                  │
       │ Migration Lock 해제          │                  │
```

---

## 3. Rollback 불가 → 사람 개입 경로

```
[Migration Engine]                          [사람]
       │                                       │
       │ FAILED 상태                            │
       │ Rollback 가능 여부 판정(§4)              │
       │  - 연쇄 의존 Migration Unit이 이미        │
       │    COMPLETE된 상태 확인됨                │
       │  → 단독 Rollback 시 FK 손상 위험          │
       │  → 자동 Rollback 거부                    │
       │                                       │
       │ Audit Log에 "Rollback 불가, 사람 개입    │
       │ 필요" 기록 + 연쇄 의존 Unit 목록 첨부       │
       │                                       │
       │ Migration Lock 유지(사람이 정리할 때까지,  │
       │ 다른 Migration Unit이 같은 파일을 건드려    │
       │ 상황을 더 꼬이게 하는 것을 방지)            │
       │──────── 알림/보고 ────────────────────▶│
       │                                       │ 수동 검토
       │                                       │ (연쇄 Rollback 순서
       │                                       │  수동 결정 또는
       │                                       │  새 정방향 Migration
       │                                       │  Unit으로 수습)
       │◀──────── 처리 지시 ───────────────────│
       │ Migration Lock 해제(사람 지시 이후)       │
```

---

## 4. Dry Run 경로

```
[사람/CUE]          [Migration Engine]         [3-Validator]
    │                      │                        │
    │  Dry Run 요청          │                        │
    │─────────────────────▶│                        │
    │                      │ Migration Unit ID 계산   │
    │                      │ PENDING → VALIDATING   │
    │                      │ (Checkpoint A 생성 안 함 │
    │                      │  — 쓰기가 없으므로 불필요) │
    │                      │                        │
    │                      │ 사전 검증 실행 ─────────▶│
    │                      │◀───── PASS/WARNING/FAIL─│
    │                      │                        │
    │                      │ MIGRATING 진입하지 않음   │
    │                      │ (설계 §9 — 실제 쓰기 생략) │
    │                      │                        │
    │                      │ 예상 diff 생성            │
    │                      │  (old value → new value) │
    │                      │                        │
    │                      │ Audit Log에               │
    │                      │ result="DRY_RUN" 기록     │
    │◀── Dry Run 결과 보고 ──│                        │
```

---

## 5. Migration 이후 TSU Gate 재계산(설계 §14 시퀀스화)

```
[Migration Engine]              [Manifest Validator]
       │                               │
       │ Migration Unit COMPLETE       │
       │                               │
       │ manifest_dependents 목록 조회  │
       │ (설계 §1)                     │
       │                               │
       │ 영향받은 manifest.yaml만 대상  │
       │ 재검증 요청 ─────────────────▶│
       │                               │ FK 재확인
       │                               │ (canonical_id/legacy_id
       │                               │  변경이 반영됐는지)
       │                               │ TSU_ELIGIBLE 재계산
       │◀────── READY/BLOCKED 결과 ────│
       │                               │
       │ Audit Log에 재계산 결과 기록    │
       │ (선택 사항, §14)               │
       │                               │
       │ ── TSU 생성은 수행하지 않음 ──   │
       │   (core/tsu_builder.py는       │
       │    별도 파이프라인 책임,        │
       │    현재 게이트 미구현 상태)      │
```

---

## 6. 요약: 이 시퀀스 문서가 검증하는 것

이 3개 시퀀스(정상/Rollback/사람개입/Dry Run/TSU Gate)는 모두
`NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md`와
`NAE_METADATA_MIGRATION_STATE_MACHINE.md`에 정의된 상태·전이·설계
항목만 조합해 구성했다 — 이 문서 자체가 새로운 설계 결정을 추가하지
않는다(Design Only 범위 재확인, 코드/데이터/Migration 실행 없음).
