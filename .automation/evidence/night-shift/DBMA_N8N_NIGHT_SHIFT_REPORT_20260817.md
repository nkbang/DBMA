# DBMA Night-Shift Report — 2026-08-17

**주제:** Autonomous Control-Plane 구축 (n8n Gateway + Host Executor + Evidence + CUE Governance)
**최종 상태:** HOLD (`NO_ELIGIBLE_CORPUS_TASK`) — 정상 idle, 실패 아님
**Production mutation:** 0건 (전체 세션에 걸쳐 `registration_state.json` 해시 불변, Phase E 23노드 불변)

---

## 진행률

```
[x] Pilot                              — 격리 control-plane-pilot 워크플로우 구축·검증
[x] Control Plane Generalization       — 일반화된 12-Gate 계약, CONDITIONAL PASS
[x] Correction Order 010               — C1 제출물 감사→FAIL→수정→CONDITIONAL PASS
[x] ADR-026 설계                        — Corpus Factory Integration 17개 계약 (Proposed)
[x] CFI-Pilot-001                      — corpus-factory-pilot 네임스페이스 격리 증명, CONDITIONAL PASS(자기감사)
[x] C1 독립 교차검증                    — 실결함 2건 발견·수정, 오판정 1건 정정
[ ] 실제 Corpus Factory 단일 task       — HOLD (등록 가능한 신규 raw 후보 없음)
진행률: 로드맵상 계획된 단계 전부 완료, 다음 단계는 신규 raw 확보 대기
```

---

## 1. 배경 — 왜 시작됐는가

Rev. Bang이 "n8n이 작업을 운반하고, C1이 구현하고, CUE가 governance/audit을 담당하는 무인 실행 구조"를 요청. CUE는 이를 곧바로 구현하지 않고 먼저 기존 n8n automation 상태를 조사(ADR-022/023 Approved 확인, `host_executor.py` Option A 패턴 발견, 오늘자 DBMA/NAE isolation 사건 확인)한 뒤 isolated pilot부터 단계적으로 진행.

## 2. 단계별 요약

### 2.1 Control Plane Pilot (isolated)
- Phase E State Machine(Approved, 23노드)을 n8n UI **Duplicate** 기능으로 복제 → `Control Plane Pilot (Isolated)`(id `y9U4bFEWm4ZnEf3j`), webhook path `dbma-control-plane-pilot`.
- `.automation/night-shift/pilot_executor.py` 신규 — NAE/production import 0개, task_type allowlist, 파일 기반 heartbeat.
- **발견·수정한 버그**: gateway와 executor가 서로 다른 `payload_signature` 알고리즘을 써서 duplicate가 CONFLICT로 오판정되던 결함 → executor가 gateway의 값을 그대로 전파하도록 수정.
- 판정: [`N8N-CONTROL-PLANE-PILOT-001-CUE-FINAL-REVIEW.json`](../../audit/N8N-CONTROL-PLANE-PILOT-001-CUE-FINAL-REVIEW.json) PASS

### 2.2 Control Plane Generalization (G1-G12)
- Task Contract, Queue, Dependency(G7), Heartbeat(G8), Crash Recovery(G9), Evidence Integrity(G10), Production Isolation(G11), End-to-End Night Simulation(G12) 등 12개 게이트를 CUE가 직접 격리 구현·실행.
- **발견·수정한 버그**: 하나의 실행 안에서 PROCESSING/COMPLETED 두 전이가 `transition_id`를 공유하던 결함.
- **실제 crash 시뮬레이션**: PROCESSING+backdated heartbeat → stale-worker 감지 → FAILED 강제 전이, subprocess 미실행 증명.
- 판정: [`CONTROL-PLANE-GENERALIZATION-001-CUE-10-GATE-REVIEW.json`](../../audit/CONTROL-PLANE-GENERALIZATION-001-CUE-10-GATE-REVIEW.json), [`AUTONOMOUS-NIGHT-SHIFT-001-CUE-12-GATE-REVIEW.json`](../../audit/AUTONOMOUS-NIGHT-SHIFT-001-CUE-12-GATE-REVIEW.json) — 둘 다 CONDITIONAL PASS(G7/G9 human-retry 실증만 DEFERRED)

### 2.3 C1 제출물 감사 → Correction Order 010
- C1에게 동일 12항목을 병행 지시. C1 제출물을 원문 코드/실행으로 직접 감사한 결과 **FAIL**:
  - `n8n_gateway.py`가 격리 워크플로우가 아니라 **실제 Approved Phase E production 웹훅**을 직접 가리킴
  - 미승인 task_type `host_cli_driver`가 allowlist에 들어가 테스트까지 통과되어 있음(실제 NAE cli_driver를 가리키는 이름)
  - `payload_signature`를 독자 재계산(명령서가 명시적으로 금지한 바로 그 패턴)
- Correction Order 010 발행 → C1이 일부만 수정(회귀 4건 발생) → **CUE가 직접 완료**(C1 relay 불가 시간대, CLAUDE.md CUE Operating Policy 근거) — 새 결함(transition_id 공유) 재발견·수정, 새 통합 결함(gateway `file_error` 응답을 `verify_response()`가 검증 안 함) 발견·기록.
- 판정: [`C1-CORRECTION-ORDER-010-CUE-CLOSURE.json`](../../audit/C1-CORRECTION-ORDER-010-CUE-CLOSURE.json) CONDITIONAL PASS, 61/61 pytest

### 2.4 ADR-026 — Corpus Factory Integration 설계 (Proposed, 구현 아님)
- [`docs/architecture/ADR-026-Control-Plane-Corpus-Factory-Integration-Design.md`](../../../docs/architecture/ADR-026-Control-Plane-Corpus-Factory-Integration-Design.md) — 17개 계약(Task Contract~Night-Shift Queue Semantics) 설계, 오늘 밤 발견한 5개 실결함을 설계 원칙에 명문화.
- 저항성 매트릭스 14개 시나리오 실제 검증(13 PASS, 1 HOLD): [`AUTONOMOUS-NIGHT-SHIFT-001-RESILIENCE-MATRIX.md`](AUTONOMOUS-NIGHT-SHIFT-001-RESILIENCE-MATRIX.md) — executor crash, **n8n 실제 재시작**(evidence 무손실 확인), duplicate, malformed task, missing field 등.

### 2.5 CORPUS-FACTORY-INTEGRATION-PILOT-001
- ADR-026 중 미증명 3항목(namespace 분리, CLI-driver-boundary, `authorized_by_task_order`)을 CUE가 직접 격리 구현·실행. 신규 namespace `corpus-factory-pilot`, task_type `corpus_pilot_echo`, 신규 CLI driver 스크립트.
- **CUE 발행+CUE 실행**이므로 자기감사 한계를 명시적으로 기록: [`CORPUS-FACTORY-INTEGRATION-PILOT-001-CUE-SELF-REVIEW.json`](../../audit/CORPUS-FACTORY-INTEGRATION-PILOT-001-CUE-SELF-REVIEW.json) CONDITIONAL PASS

### 2.6 C1 독립 교차검증
- C1에게 "CUE의 작업을 의심하고 깨보라"는 검증 전용 task 발행.
- **C1이 정확히 찾은 실결함 2건**: (a) heartbeat/evidence가 namespace별로 분리 안 됨, (b) executor가 `authorized_by_task_order`를 독자 재검증 안 함(defense-in-depth 누락) → **CUE가 둘 다 수정, 재검증 완료**.
- **C1의 핵심 FAIL 주장(게이트웨이가 검증 안 함)은 오판정** — 제가 건드린 적 없는 별개의 stale 파일(`phase-e.json`)을 근거로 한 것으로 판명, 실제 라이브 워크플로우는 빈 문자열까지 거부함을 재현으로 반박.
- 판정: [`CFI-PILOT-001-CROSS-VERIFICATION-CUE-CLOSURE.json`](../../audit/CFI-PILOT-001-CROSS-VERIFICATION-CUE-CLOSURE.json) — 양쪽 모두의 실수를 서로 잡아낸 사례로 기록.

### 2.7 실제 Corpus Factory 단일 task 시도 → HOLD
- Rev. Bang이 "실제 Corpus Factory 처리"로 로드맵을 이어가려 함. CUE가 범위(Registration까지, ADR-023 경계)를 확인받고 후보 탐색.
- **독립 인벤토리 확인**: raw 폴더 실제 문서 10건 = 등록 완료(QUALITY_PASSED) 10건, 정확히 1:1 일치. 신규 미등록 후보 없음. 빈 폴더(AF1815/PBC1742/TH1612) 3개는 raw 자체가 없음.
- Rev. Bang의 상태 요약 중 "n8n OFFLINE" 주장을 직접 재현으로 **정정**(실제로는 8시간 정상 가동 중).
- 판정: [`CORPUS-FACTORY-SINGLE-TASK-PILOT-CUE-HOLD.json`](../../audit/CORPUS-FACTORY-SINGLE-TASK-PILOT-CUE-HOLD.json) **HOLD** — `NO_ELIGIBLE_CORPUS_TASK`, 정상 idle 상태로 세션 종료.

---

## 3. 오늘 밤 발견·수정한 실제 결함 (전부 raw 증거 보유)

| # | 결함 | 발견 주체 | 심각도 |
|---|---|---|---|
| 1 | payload_signature 재계산으로 duplicate가 CONFLICT 오판정 | CUE 자기검증 | HIGH |
| 2 | 동일 실행 내 두 전이가 transition_id 공유 (2회 재발) | CUE 자기검증 (2회) | MEDIUM |
| 3 | C1 제출물: gateway가 실제 production 웹훅을 직접 호출 | CUE 감사 | CRITICAL |
| 4 | C1 제출물: 미승인 task_type `host_cli_driver` | CUE 감사 | CRITICAL |
| 5 | C1 제출물: payload_signature 독자 재계산 반복 | CUE 감사 | CRITICAL |
| 6 | C1 제출물: 함수 시그니처 변경 후 호출부 미갱신으로 실제 회귀 4건 | CUE 감사(pytest 재실행) | HIGH |
| 7 | control_plane.py가 실제 gateway `file_error` 응답을 검증 안 함 | CUE(실제 dry_run=False 실행) | MEDIUM(기록만, 미수정) |
| 8 | namespace별 heartbeat/evidence 파일 미분리 | **C1 교차검증** | MEDIUM |
| 9 | executor가 authorized_by_task_order를 독자 재검증 안 함 | **C1 교차검증** | MEDIUM |

## 4. 최종 상태

```
n8n          UP (정상 가동)
Corpus       NO_ELIGIBLE_CORPUS_TASK
Executor     IDLE
CUE          HOLD
C1           WAIT
Production   UNTOUCHED (registration_state.json 해시 전체 세션 불변)
```

## 5. 다음 단계 (승인 대기)

새 raw source가 확보되기 전까지:
- C1: 신규 코퍼스 다운로드 금지, 기존 등록 문서 재처리 금지, Corpus Factory 코드 임의 확장 금지
- n8n 큐는 비어있는 상태 유지(정상)
- 신규 raw 확보 시(별도 ADR-021 RAW preservation task) ADR-023 경계 안에서 첫 단일 task registration pilot 재시도 가능
- 항목 7(gateway 응답 검증 누락)은 아직 미수정 — 후속 필요 시 별도 Correction Order 대상
