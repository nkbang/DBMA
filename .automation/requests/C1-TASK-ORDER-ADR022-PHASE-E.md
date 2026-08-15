# C1 Task Order — ADR-022 Phase E 구현

**Task Order:** C1-TASK-ORDER-ADR022-PHASE-E
**Date:** 2026-08-13
**발주자:** CUE (Architecture/Governance/Independent Verification)
**대상:** C1 (implementation)
**근거 문서:** `docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md`
**ADR-022 현재 상태:** `Proposed / Design Review Complete / Implementation Authorized` — **Approved 아님.** 설계는 CUE 검토 2회를 통과했고 구현 착수는 승인됐지만, ADR 최종 승격(Approved)은 (1) 구현 완료 (2) Test Matrix 증거 제출 (3) CUE 독립 재감사 통과 (4) Rev. Bang 승인 4가지를 전부 거쳐야 한다. **C1은 ADR 문서의 Status를 직접 바꾸지 않는다.**

---

## 이번 Phase E의 목표 (한 문장)

**새로운 automation state machine을 "설계대로 구현하고 증명하는 것"이지, Full Processing을 시작하는 것이 아니다. `PROCESSING`과 `COMPLETED`의 실제 transition 및 production mutation은 절대 구현하지 않는다.**

---

## 1. ADR-022 구현 범위

구현할 state (ADR-022 §5, §9):

```
RECEIVED → VALIDATION_PASSED
RECEIVED → FAILED
FAILED → RETRY_PENDING   (사람의 명시적 트리거로만, §8)
```

**절대 구현 금지:**
- `PROCESSING`, `COMPLETED` 상태로의 실제 전이 코드 — 값 자체(enum)는 스키마에 존재해도 되지만, 그 상태로 옮기는 로직/노드/워크플로우는 만들지 않는다.
- `RETRY_PENDING → PROCESSING` 전이 코드
- 자동화가 스스로 `FAILED → RETRY_PENDING`을 트리거하는 코드 (사람만 가능, §8)

## 2. Namespace 보호 (ADR-022 §3, §4)

- `NAE/pipeline/registration/state/registration_state.json` — **손대지 않는다.** 구현 전/후 SHA256 대조로 무변경 증명(§15-9, 아래 8항).
- ADR-020 `incremental_state.json` — 손대지 않는다.
- `.automation/tasks/schema.json`의 **기존 최상위 `state` 필드**(현재 값 `"IDLE"`) — 의미를 바꾸지 않는다. deprecated 표시만 하고 더는 갱신하지 않는다.
- 신규 상태는 전부 `automation` 하위 객체 안에서만 관리한다(ADR-022 §13.1의 JSON Schema diff 그대로 적용).

## 3. Failure 분리 (ADR-022 §6)

```
state = FAILED
failure_code =
  VALIDATION_FAILED
  FILE_ERROR
  PARSE_ERROR
  TASK_ID_PAYLOAD_CONFLICT
```

`state !== "FAILED"`이면 `failure_code`는 반드시 `null`. ADR-022 §13.2의 `if/then/else` 상호 제약을 그대로 구현한다.

## 4. Idempotency (ADR-022 §7)

```
same task_id + same payload_hash (SHA256)
    → no-op, 새 전이 없음, evidence에 duplicate_of 기록

same task_id + different payload_hash
    → 거부, "TASK_ID_PAYLOAD_CONFLICT" 응답, state 불변, evidence 기록
```

## 5. Transition ID (ADR-022 §11)

```
transition_id = "{task_id}#{순번:04d}"
예: "ADR-021-PILOT-001#0001"
```

순번은 해당 task_id의 `.automation/evidence/` 로그에서 마지막 순번 + 1로 산정. **동시 요청 시 순번 경합(race condition)을 반드시 테스트할 것** — 원자적 append 또는 `.automation/locks/`(기존 디렉터리) 기반 lock으로 보호.

## 6. Audit History (ADR-022 §11)

- `automation.state`(task 파일 내부): **현재 state만, overwrite.**
- `.automation/evidence/`: **전체 이력, append-only.** 각 전이마다 `transition_id`, `task_id`, `from`, `to`, `failure_code`, `actor`, `payload_hash`, `execution_id`, `timestamp`, `reason` 포함(ADR-022 §11 예시 JSON 그대로).

## 7. 가장 중요한 구현 규칙 — n8n workflow JSON 손작성 금지

Phase B~D에서 손작성 JSON(`readWriteFiles` 오타, `destinationOutputField` 오기입, IF `operation` 객체 형식 오류, `respondWith:"expression"`, `=` 접두사 누락, `$json.error` 구조 오판 — 6건)이 반복 REJECT의 원인이었다. 이번엔 예외 없이:

```
n8n Editor UI에서 실제 node 설정
    ↓
n8n export:workflow로 export
    ↓
export된 JSON을 읽고 실제 값 확인
    ↓
import → publish → docker restart
    ↓
docker logs에서 activation 에러 없음 확인
    ↓
curl로 execution test
```

이 순서를 어기고 JSON을 손으로 고쳐서 제출하면 CUE Re-audit에서 즉시 REJECT한다.

## 8. C1 자체 검증 — 제출 전 필수

ADR-022 §15의 **9개 test case 전부**를 실제 execution으로 수행하고, 아래를 evidence로 남길 것:

| # | 케이스 | 남겨야 할 evidence |
|---|---|---|
| 1 | 신규 task, 정상 JSON | curl 명령 원문 + 응답 원문 + `automation.state` 값 + evidence 로그 2건(transition_id 포함) |
| 2 | 신규 task, validation 실패 | 〃 + `failure_code: VALIDATION_FAILED` |
| 3 | 신규 task, 파일 없음 | 〃 + `failure_code: FILE_ERROR` |
| 4 | 동일 task_id + 동일 payload 중복 요청 | 새 전이 없음 확인 + evidence의 `duplicate_of` 필드 |
| 5 | 동일 task_id + 다른 payload | `TASK_ID_PAYLOAD_CONFLICT` 응답 원문 + state 불변 확인 |
| 6 | 금지된 전이 강제 시도(예: 외부에서 COMPLETED 직접 쓰기) | 거부 응답 + 이상 evidence |
| 7 | `FAILED → RETRY_PENDING` (사람이 트리거) | 전이 성공 + `actor: "human"` evidence |
| 8 | 자동화가 스스로 RETRY_PENDING 트리거 시도 | 이 코드 자체가 존재하지 않음을 workflow export로 증명(테스트가 아니라 "코드 부재 증명") |
| 9 | NAE Registration State 파일 무변경 | 구현 전/후 `registration_state.json` SHA256 비교, 두 값 동일 |

## 9. 절대 금지 (재확인)

- `PROCESSING`/`COMPLETED` 실제 전이 코드 구현
- `NAE/pipeline/registration/state/*.json`, ADR-020 `incremental_state.json` 수정
- 기존 최상위 `state` 필드 의미 변경
- 자동화가 스스로 `RETRY_PENDING` 승격
- n8n workflow JSON 손작성(UI+export 경로 우회)
- Phase B~D 승인 워크플로우(`dbmaAutomationTest01`)의 기존 노드(Read/Write Files, Extract From File, Code — Schema Validation, IF, 3개 Respond 노드) 파라미터 변경 — state 기록은 그 위에 얹는 방식으로만(ADR-022 §14)
- **ADR-022 문서의 Status 필드를 C1이 직접 수정** — 승격은 CUE + Rev. Bang의 몫

## 10. 다음 단계

```
C1 Build
   ↓
C1 Evidence (위 8항 9개 케이스 전부)
   ↓
CUE Independent Re-audit (Phase B~D와 동일 방식 — 실행 재현 기반, 문서/이름만으로 판단 안 함)
   ↓
Rev. Bang Approval
   ↓
ADR-022 Status → Approved
```

완료되면 `READY_FOR_CUE_RE_AUDIT`로 제출하라.
