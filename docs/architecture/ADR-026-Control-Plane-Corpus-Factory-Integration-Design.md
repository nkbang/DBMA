---
title: "ADR-026: Control Plane → Corpus Factory Integration Design"
category: architecture
based_on:
  - docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md (Approved)
  - docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md (Approved)
  - .automation/audit/CONTROL-PLANE-GENERALIZATION-001-CUE-10-GATE-REVIEW.json (CONDITIONAL PASS)
  - .automation/audit/AUTONOMOUS-NIGHT-SHIFT-001-CUE-12-GATE-REVIEW.json (CONDITIONAL PASS)
  - .automation/audit/C1-AUTONOMOUS-NIGHT-SHIFT-001-CUE-AUDIT.json (FAIL, then corrected)
  - .automation/audit/C1-CORRECTION-ORDER-010-CUE-CLOSURE.json (CONDITIONAL PASS)
created: 2026-08-17
scope: DESIGN ONLY. This document specifies the 17-item contract for a future
  Control-Plane-to-Corpus-Factory integration. It authorizes NO implementation,
  NO Corpus Factory connection, and NO production task of any kind. Every
  example in this document uses the isolated `control-plane-pilot` /
  `corpus-factory-pilot` namespaces only.
---

# ADR-026: Control Plane → Corpus Factory Integration Design

| | |
|---|---|
| Status | **Proposed** (design only — not Approved, not implementation-authorized) |
| Approved 범위 | 없음. 이 문서는 계약을 정의만 한다. |
| Date | 2026-08-17 |
| Deciders | CUE (초안) |
| Supersedes | — |
| Extends | ADR-022 §5/§9의 state vocabulary를 그대로 재사용(확장하지 않음) |
| Does NOT extend | Corpus Factory production corpus, `core/retrieval.py`, `data/제련완성본/`, `NAE/pipeline/registration/*`, Fuller Vol.02–08, ADR-025 |

---

## 0. 이 문서가 하지 않는 것

이 문서는 설계다. 다음을 승인하지 않는다:

- Corpus Factory에 대한 실제 연결
- 새 task_type의 실제 구현
- production_mutation=true 경로의 실제 코드
- Fuller Vol.02–08의 어떤 처리도
- 기존 Approved ADR의 변경

구현이 필요해지면, 이 설계를 근거로 별도 Task Order가 CUE로부터 발행되고, 그 Task Order의 완료 조건(구현+테스트+CUE 재감사+Rev. Bang 승인)을 전부 충족해야 이 ADR이 Approved로 승격될 수 있다(Evidence Before Promotion Rule).

## 1. Context

`CONTROL-PLANE-GENERALIZATION-001`(CONDITIONAL PASS)과 `AUTONOMOUS-NIGHT-SHIFT-001`(C1 제출, Correction Order 010 이후 CONDITIONAL PASS)에서 격리된 pilot 범위 안에서 n8n gateway → executor → evidence → CUE review 루프가 실제로 동작함을 증명했다. 오늘 밤 발견된 실제 결함들(payload_signature 재계산, transition_id 공유, heartbeat가 메모리 전용이라 crash를 못 견딤, TaskQueue가 실제 gateway가 찾는 위치에 파일을 쓰지 않음, gateway 응답의 성공/실패를 실제로 검사하지 않음)은 전부 이 설계 문서에 명시적으로 반영했다 — 같은 실수가 Corpus Factory 통합에서 반복되지 않도록 하기 위함이다.

## 2. 17개 계약 항목

### 2.1 Task Contract

기존 `.automation/control-plane/task-contract.schema.json`(additive, Approved schema.json 무관)을 그대로 확장한다. 신규 필드는 전부 optional이거나 corpus-factory 전용 task_type에서만 required로 취급한다 — 기존 `pilot_echo` task_type의 계약을 깨지 않는다.

### 2.2 task_type allowlist

**현재 승인된 값 없음.** Corpus Factory 관련 task_type(예: `corpus_candidate_register`)은 이 문서만으로는 존재해서는 안 된다 — 각 task_type은 별도의 CUE 승인 Task Order를 거쳐 executor의 allowlist(`ALLOWED_TASK_TYPES`)에 명시적으로 추가된다. 오늘 밤 `host_cli_driver`가 승인 없이 allowlist에 들어갔던 사고를 반복하지 않는다.

### 2.3 Scope

```
scope.namespace ∈ {
  "control-plane-pilot"       (현재, isolated, 계속 사용)
  "corpus-factory-pilot"      (신규, isolated, synthetic task만, production 데이터 무관)
  "corpus-factory-production" (미래, 별도 ADR + Rev. Bang 승인 전까지 코드 자체가 존재하면 안 됨)
}
scope.allowed_paths: 화이트리스트. corpus-factory-pilot 네임스페이스에서는
  data/제련완성본/, core/retrieval.py, NAE/pipeline/registration/ 를
  포함하는 경로는 스키마 레벨에서부터 거부한다(policy_enforcement.py의
  check_scope_paths()가 이미 이런 검사를 하고 있다 — 그 패턴을 그대로 재사용).
```

### 2.4 authorized_by

기존과 동일: 비어있지 않은 문자열, 사람 이름 또는 "CUE". Corpus Factory 관련 task는 추가로 `authorized_by_task_order`(어느 Task Order/ADR이 이 task를 승인했는지 참조하는 문자열) 필드를 required로 요구한다 — 감사 추적을 위해서다.

### 2.5 production_mutation

기본값 `false`, 이 값을 변경하는 어떤 코드 경로도 이 설계 범위에서는 구현하지 않는다. 미래에 실제로 `true`가 필요해지면: (1) 별도 ADR, (2) CUE Approval Gate의 task별 사전 승인, (3) `human_confirmed_production: true`라는 별도 필드를 human이 직접 설정(자동화가 스스로 설정 금지) — 세 조건 전부 충족해야 실행 코드가 활성화된다.

### 2.6 Canonical payload_signature

Gateway(n8n)가 raw webhook body에 JS `JSON.stringify()`를 적용한 값이 authoritative. Executor(어떤 종류든)는 이 값을 evidence 로그의 마지막 항목에서 읽어 전파할 뿐, 절대 재계산하지 않는다. 오늘 밤 이 규칙이 두 번(CUE 자신, C1) 위반됐다가 고쳐졌다 — 이 설계에서는 처음부터 이 함수 시그니처를 `(task_id, evidence_dir) -> str`로 고정하고, `(task: dict) -> str` 형태의 함수는 코드베이스에 존재해서는 안 된다.

### 2.7 State Machine

ADR-022 §5의 vocabulary(`RECEIVED, VALIDATION_PASSED, FAILED, RETRY_PENDING, PROCESSING, COMPLETED`)를 **그대로** 쓴다. `PENDING_APPROVAL`, `QUEUED`, `IN_REVIEW` 같은 새 상태를 추가하지 않는다 — 오늘 밤 C1의 제출물에서 발견된 문제(ADR-022 vocabulary 밖 상태 추가)를 반복하지 않는다. 승인 단계가 필요하면 `requires_human_approval: true` 필드 + human이 트리거하는 `RETRY_PENDING`류 게이트로 표현한다, 새 state로 표현하지 않는다.

### 2.8 Executor Boundary

Host executor(별도 프로세스, n8n도 C1도 아님)만이 실제 작업을 수행한다. Corpus Factory 관련 작업이 필요하면, ADR-023의 `cli_driver.py` 패턴처럼 **얇은 CLI 드라이버**를 통해서만 접근한다 — executor 코드 안에 `NAE.pipeline.*`를 직접 import하는 코드는 절대 존재하지 않는다(항상 `subprocess.run([...])` 경계 유지). C1은 이 CLI 드라이버를 구현할 수 있지만, executor의 runtime 호출 대상이 되지는 않는다(C1 ≠ runtime executor 원칙 유지).

### 2.9 Evidence Schema

ADR-022 §11 그대로: `transition_id, task_id, from, to, failure_code, actor, payload_signature, execution_id, timestamp, reason`. 단일 저장 위치는 `.automation/evidence/<task_id>.jsonl`, append-only. **하나의 실행 안에서 서로 다른 두 전이가 같은 transition_id를 공유하지 않는다** — 오늘 밤 CUE와 C1 양쪽에서 발견된 결함이므로, 구현 시 이 항목에 대한 unit test를 반드시 포함한다(예: 같은 프로세스 실행 안에서 작성된 모든 evidence entry의 transition_id가 서로 다른지 assert).

### 2.10 Failure Handling

모든 실패는 명시적 `failure_code`로 구분한다(침묵 실패 금지). 실패한 task는 review 대상 위치로 라우팅되며, 자동으로 지워지거나 재시도되지 않는다.

### 2.11 Explicit Human Retry

`FAILED → RETRY_PENDING`은 사람의 명시적 트리거로만 발생한다(ADR-022 §8). 에이전트(CUE 포함)는 이 전이를 스스로 발생시키면서 `actor: "human"`이라고 기록해서는 안 된다 — 실제로 사람이 그 채팅에서 명시적으로 지시한 경우에만, 그 지시를 근거로 CUE가 대신 실행하고 `actor`에 그 사실을 정확히 기록한다(예: `actor: "CUE (human-instructed via chat, 2026-08-17)"`).

### 2.12 CUE Approval Gate

C1(또는 host executor)의 "성공" 보고만으로 PASS를 선언하지 않는다. CUE는 반드시: raw command, stdout/stderr, exit code, 변경 전/후 파일 상태, evidence 파일, git status/diff를 직접 열어서 교차검증한다. `production_mutation=true`가 필요한 task는 CUE가 설계/task 자체를 사전 승인한 뒤에도, 실행 자체는 별도로 사람이 승인해야 한다(2-key 원칙).

### 2.13 Idempotency / Duplicate Handling

동일 task_id + 동일 canonical payload_signature → `duplicate`(no-op, state 불변). 동일 task_id + 다른 signature → `conflict`(거부, state 불변). 이 로직은 gateway(n8n)의 evidence 로그 마지막 항목 비교로만 판정한다 — 오늘 밤 검증된 패턴 그대로 재사용.

### 2.14 Crash Recovery

Executor의 heartbeat는 **파일 기반**이어야 한다(메모리 전용 금지) — heartbeat를 만든 프로세스 자체가 죽어도, 별도의 복구 프로세스가 그 파일을 읽어 staleness를 판정할 수 있어야 한다. 오늘 밤 C1의 `HeartbeatMonitor`가 메모리 전용이라 이 요구사항을 구조적으로 만족할 수 없었다 — 이 설계에서는 `pilot_executor.py::write_heartbeat()`/`heartbeat_age_s()` 패턴을 그대로 재사용한다.

### 2.15 Orphan PROCESSING Detection

주기적 스윕(`detect_and_recover_stale_workers()` 패턴)이 heartbeat가 임계시간을 넘긴 `PROCESSING` task를 찾아 `FAILED`(failure_code=`STALE_WORKER_TIMEOUT`)로 강제 전이한다. 이 스윕은 **매 실행 사이클 시작 시** 새 task 처리보다 먼저 수행한다.

### 2.16 Shutdown / Restart Recovery

Executor 프로세스가 재시작되면, 가장 먼저 할 일은 orphan PROCESSING 스윕이다(2.15). 큐 상태는 파일시스템 기반으로 영속화되어야 한다 — 메모리 전용 큐(오늘 밤 C1의 `TaskQueue`가 기본값으로 그랬던 것처럼)는 프로세스 재시작 시 큐 내용을 전부 잃는다. 큐 항목은 `.automation/tasks/*.json` 자체를 단일 소스로 삼는다(별도 큐 파일 불필요 — task 파일의 `automation.state`가 곧 큐 위치다).

### 2.17 Night-Shift Queue Semantics

Rev. Bang의 작업 진행 규칙(섹션 E)을 그대로 계약화한다: 한 번에 하나의 authorized task만 실행한다. 현재 task가 PASS/FAIL/HOLD로 종결되기 전에는 다음 task를 시작하지 않는다. n8n 자체의 transport/validation 작업(RECEIVED→VALIDATION_PASSED/FAILED)은 이 규칙의 예외로, executor 작업과 독립적으로 계속 처리될 수 있다(게이트웨이 검증은 여러 task를 동시에 받아도 안전하다 — 실제 실행만 순차적이면 된다).

## 3. Absolute Prohibitions (재확인, 변경 없음)

- `core/retrieval.py` 수정
- `data/제련완성본/` 수정
- NAE production corpus mutation
- Fuller Vol.02–08 bulk processing
- Approved workflow 직접 수정
- 자동 retry / 자동 promotion / 자동 approval
- C1을 runtime executor로 사용하는 설계

## 4. CUE Approval Gate (승격 조건)

이 ADR이 Proposed에서 Approved로 승격되려면:

1. 위 17개 항목 각각에 대한 isolated pilot 구현 + 실제 실행 증거
2. 오늘 밤 발견된 5개 결함(payload_signature 재계산, transition_id 공유, heartbeat 메모리 전용, TaskQueue 파일 위치 불일치, verify_response 상태값 미검증)이 새 구현에서 재현되지 않음을 실행으로 증명
3. CUE 독립 재감사 통과
4. Rev. Bang 승인

4개 전부 충족 전까지는 Proposed 상태를 유지하며, 다른 구현의 근거로 사용하지 않는다.

## 5. Next Task 제안

이 설계가 승인되면(또는 승인 전이라도 Rev. Bang이 명시적으로 지시하면), 다음 단계는 **여전히 corpus-factory-pilot이라는 isolated synthetic namespace 안에서** 이 17개 계약을 실제로 구현·검증하는 것이며, 실제 Corpus Factory 데이터/task_type 연결은 그 다음 단계(별도 승인)다.
