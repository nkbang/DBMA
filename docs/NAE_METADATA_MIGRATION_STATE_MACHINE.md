# NAE Metadata Migration State Machine

**Project:** CUE-TASK-ORDER-041 / NAE-METADATA-MIGRATION-ENGINE-DESIGN-001
**작성일:** 2026-08-03
**성격:** Design Only — `NAE_METADATA_MIGRATION_ENGINE_DESIGN_001.md`
§2의 State Machine을 다이어그램·전이표 형태로 상세화한 보조 문서.
독립적으로 읽어도 이해되도록 핵심 정의를 반복 포함한다.

---

## 1. 상태 다이어그램

```
                    ┌─────────┐
                    │ PENDING │
                    └────┬────┘
                         │ (Migration Unit 큐 진입,
                         │  Checkpoint A 생성)
                         ▼
                  ┌──────────────┐
        ┌────────▶│  VALIDATING  │
        │         └──────┬───────┘
        │                │
        │      ┌─────────┴─────────┐
        │      │                   │
        │  (검증 통과)          (검증 실패)
        │      │                   │
        │      ▼                   ▼
        │  ┌──────────┐      ┌──────────┐
        │  │ MIGRATING│      │  FAILED  │◀──────────┐
        │  └────┬─────┘      └────┬─────┘           │
        │       │                 │                 │
        │  (쓰기 완료)      (Rollback 시도)           │
        │       │                 │                 │
        │       ▼                 ▼                 │
        │  ┌──────────┐    ┌─────────────┐           │
        │  │VERIFYING │    │ Rollback    │           │
        │  └────┬─────┘    │ 가능?(§4)   │           │
        │       │          └──┬───────┬──┘           │
        │  ┌────┴────┐        │       │              │
        │  │         │      YES      NO              │
        │(사후검증  (사후검증    │       │              │
        │  통과)     실패)      ▼       ▼              │
        │  │         │   ┌──────────┐ ┌──────────┐   │
        │  │         └──▶│  FAILED  │ │  FAILED  │   │
        │  │              (재시도용)│ │ (최종,   │   │
        │  │             └────┬─────┘ │ 사람개입)│   │
        │  │                  │       └──────────┘   │
        │  │            (Rollback 실행)               │
        │  │                  ▼                       │
        │  │           ┌─────────────┐                │
        │  │           │ ROLLED_BACK │                │
        │  │           └─────────────┘                │
        │  ▼                                          │
        │┌──────────┐                                 │
        ││ COMPLETE │ (종단 상태 — §2 역행 규칙)         │
        │└──────────┘                                 │
        │                                              │
        └── (새 PENDING 재발행, §8 Failure Recovery) ───┘
```

---

## 2. 상태 전이표

| From | To | 조건 | 부수 효과 |
|---|---|---|---|
| (없음) | PENDING | Migration Plan에 Migration Unit 등록 | Migration Unit ID 결정적 생성(설계 문서 §5) |
| PENDING | VALIDATING | 처리 시작(Migration Lock 획득, 설계 문서 §10) | **Checkpoint A 생성**(설계 문서 §3) — 대상 파일 목록 + 현재 sha256 기록 |
| VALIDATING | MIGRATING | 사전 검증 전부 PASS(FK 존재, canonical_id 형식, 목표 상태와 현재 상태가 다름 — 다르지 않으면 no-op COMPLETE 직행, 설계 문서 §5) | — |
| VALIDATING | FAILED | 사전 검증 중 하나라도 FAIL | 사유를 Audit Log에 기록 |
| MIGRATING | VERIFYING | 대상 YAML 파일 전부 쓰기 완료(flush) | — |
| MIGRATING | FAILED | 쓰기 도중 오류(디스크/권한/프로세스 중단 등) | **부분 실패 의심 상태** — 설계 문서 §8 "부분 실패"로 취급, 자동 Rollback 시도 우선 |
| VERIFYING | COMPLETE | 3-Validator 재실행 결과 FAIL 0건 + 목표 필드 값이 실제로 반영됨 확인 | **Checkpoint B 생성**(설계 문서 §3) — 새 sha256 + git commit 해시를 Audit Log에 기록 |
| VERIFYING | FAILED | 3-Validator 재실행에서 FAIL 발생(예상치 못한 FK 손상) | 사유를 Audit Log에 기록, **최우선 자동 Rollback 대상** |
| FAILED | ROLLED_BACK | Rollback 절차(설계 문서 §4) 성공 | Checkpoint A 시점으로 복원 확인, Audit Log에 원인+Rollback 결과 기록 |
| FAILED | FAILED(최종) | Rollback 불가능(설계 문서 §4의 3가지 사유 중 하나) | 사람 개입 요청, 자동 처리 종료 |
| FAILED | (새) PENDING | 사람 확인 후 재시도 결정(설계 문서 §8 Failure Recovery) | 새 Migration Unit ID 발행이 아니라 **동일 결정적 ID로 재등록**(Idempotency, 설계 문서 §5) |
| COMPLETE | — | **전이 없음(종단 상태)** | 문제 발견 시 새로운(역방향) Migration Unit을 별도로 발행 |
| ROLLED_BACK | — | **전이 없음(종단 상태)** | 재시도하려면 새 PENDING을 처음부터 생성 |

---

## 3. 금지된 전이(역행 규칙 재확인)

| 금지된 전이 | 이유 |
|---|---|
| COMPLETE → (임의 상태) | Audit Log 불변성 — 완료된 사실을 사후에 지우거나 되돌리지 않는다(설계 문서 §2, §6) |
| MIGRATING → ROLLED_BACK(직접) | "Rollback을 시도했다"와 "Rollback이 완료됐다"를 구분해야 함 — 반드시 FAILED를 거쳐 Rollback 가능 여부(§4)를 판정한 뒤에만 ROLLED_BACK |
| FAILED → COMPLETE | 실패 레코드를 성공으로 승격시키지 않는다 — 재시도는 항상 새 PENDING(같은 Migration Unit ID, Idempotency로 안전) |
| VALIDATING → COMPLETE(직접) | MIGRATING/VERIFYING을 생략할 수 없다 — 단, "이미 목표 상태와 동일"한 no-op 케이스는 예외적으로 VALIDATING에서 즉시 COMPLETE 판정 가능(설계 문서 §5-2, 실제 쓰기가 없으므로 MIGRATING/VERIFYING을 건너뛰어도 무결성 위험이 없음) |

---

## 4. 상태별 소요 시간 가정(설계 참고용, 구현 시 재측정 필요)

이번 문서는 Design Only이므로 실측값이 아니라 **구현 단계에서
검증해야 할 가정**만 기록한다:

- VALIDATING: Registry/Manifest 조회 + FK 대조 — Pilot 규모(28
  entity)에서는 밀리초 단위로 예상(authority_validator.py 실행 시간
  0.2초대 실측치 참고)
- MIGRATING: YAML 파일 쓰기 — Migration Unit당 수 개 파일, 초 단위
  이하 예상
- VERIFYING: 3-Validator 전체 재실행 — 현재 Pilot 규모 기준 1초
  미만(§Phase4 Readiness Review 실측 fixture 없음, pytest 기준
  0.1~0.2초대와 유사할 것으로 추정)

Corpus-wide 규모(§Performance, 설계 문서 §12)에서는 이 가정을 반드시
재측정해야 한다 — 이번 설계는 그 재측정이 필요하다는 사실만 명시.
