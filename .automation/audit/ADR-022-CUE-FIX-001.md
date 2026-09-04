# CUE Fix — ADR-022 참조 구현 결함 2건 수정

- 대상: `.automation/workflows/phase-e.json` (`Phase E State Machine`, id `9qIO3nFeWRia28Rb`)
- 근거: `.automation/audit/ADR-022-CUE-REAUDIT-001.md`
- date: 2026-08-14
- production_mutation: false

## 수정 1 — Race Condition (transition_id 충돌)

**변경 전:** `transition_id`를 `.automation/evidence/{task_id}.jsonl`을 읽어 줄 수(`lines.length + 1`)로 계산 — 동시 요청 시 여러 실행이 같은 파일을 동시에 읽어 같은 순번을 계산하는 read-race가 존재했다.

**변경 후:** n8n이 각 실행(execution)에 부여하는 `$execution.id`(정수, n8n 자체가 원자적으로 증가시켜 할당)를 그대로 순번으로 사용. 파일을 읽어 순번을 "계산"하지 않으므로 read-race 자체가 없어진다. ADR-022 §11의 `"{task_id}#{순번:04d}"` 포맷은 그대로 유지(`String(executionId).padStart(4,'0')`).

**검증:** 동일 task_id로 5개 동시 요청 → evidence 5줄 전부 서로 다른 `transition_id`, 유실/중복 없음 (재현 로그: 본 세션 curl 병렬 실행 결과, execution_id 47~51).

## 수정 2 — Transition Matrix 미강제 (금지된 전이 허용)

**변경 전:** `isConflict` 판단이 `.automation/evidence/`의 마지막 항목(`lastEntry`) 존재 여부에 의존 — 해당 task_id의 evidence 로그가 없는 상태(파일 직접 조작, evidence 유실 등)에서는 어떤 검사도 통과하지 못한 채 그대로 통과되어 `automation.state`가 덮어써졌다.

**변경 후:** evidence 로그와 무관하게, **task 파일에 현재 기록된 `automation.state` 자체**를 기준으로 whitelist 검사(`ALLOWED_FROM`)를 추가:

```js
const ALLOWED_FROM = {
  VALIDATION_PASSED: [null, 'RECEIVED'],
  FAILED: [null, 'RECEIVED', 'VALIDATION_PASSED']
};
const isIllegalTransition = !!currentState && !(ALLOWED_FROM[newState] || []).includes(currentState);
```

신규 `IF Illegal Transition` 노드 + `Respond ILLEGAL_TRANSITION` 노드 추가. **체크 순서가 중요함을 실행으로 확인**: 처음엔 Duplicate 체크보다 먼저 배치했다가, 정상적인 반복요청(`VALIDATION_PASSED → VALIDATION_PASSED`, 즉 진짜 duplicate)까지 illegal로 오판하는 회귀가 발생 → `IF Conflict → IF Duplicate → IF Illegal Transition` 순서로 재배치해 해결(같은 payload의 반복은 duplicate가 먼저 흡수, illegal 체크는 "evidence 없이 상태만 조작된" 경우에만 도달).

**검증:** `automation.state:"COMPLETED"`로 직접 조작한 task 파일에 웹훅 재호출 → `{"status":"illegal_transition","current_state":"COMPLETED","attempted_state":"FAILED",...}` 응답, 파일의 `automation.state`는 `COMPLETED`로 보존(덮어쓰기 없음).

## 회귀 확인

기존 5종 케이스(정상/duplicate/conflict/validation FAIL/파일없음) 전부 재실행 — 이번 수정으로 인한 회귀 없음 확인.

## Namespace 무변경 재확인

```
NAE/pipeline/ingest/state/incremental_state.json SHA256:
e10a396674f4d9084997f21a2d7586d674a3541b6fe356bfd47f4a808c52524a
(수정 전/후 동일)
```

`NAE/pipeline/registration/state/`에는 여전히 파일 없음(ADR-021 registration 파이프라인 미실행 상태, 무변경).

## 남은 사항

이번 수정도 CUE 자신이 직접 했다. 독립성 원칙에 따라 **C1의 재검증이 한 번 더 필요**하다 — 특히 결함 2건의 재현 시나리오(§테스트 6, race condition)를 C1이 스스로 다시 시도해 실제로 막히는지 확인해야 한다.
