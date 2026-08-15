# C1 Correction Order 002 — host_executor.py: processing_input 유실 버그

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-15 07:30 UTC) |
| Continues | `C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md` |
| 대상 | 파일럿 실행 1차 (`NAE-REG-BAP-CHURCH-DAGG-001`) |
| 판정 | **FAIL — 그러나 안전하게 fail-closed됨.** Production mutation 0건. |

---

## 무엇이 일어났나 (raw evidence로 확인)

`.automation/evidence/night-shift/host-executor-implementation/pilot-dagg/`:

```
exit_code.txt : 2
stderr.log    : {"error": "missing field: automation.processing_input"}
```

`cli_driver.py`가 입력 검증(exit 2)에서 즉시 실패했다. `register_source()`는
**호출조차 되지 않았다** — CUE가 확인: `NAE/pipeline/registration/state/
registration_state.json`은 여전히 미존재, `raw_checksum_ledger.jsonl`은 여전히
0줄. **좋은 소식: fail-closed 계약이 정확히 작동했다.**

## Root cause (CUE가 evidence로 확정 — 재조사 불필요)

`.automation/evidence/NAE-REG-BAP-CHURCH-DAGG-001.jsonl`을 직접 열어보면:

1. 첫 줄(`RECEIVED → VALIDATION_PASSED`, actor: automation/n8n)의
   `payload_signature`에는 **원본 payload 전체가 그대로 들어있고
   `processing_input`도 완전하다.**
2. 그런데 n8n이 그 시점에 다시 쓴 `.automation/tasks/NAE-REG-BAP-CHURCH-DAGG-001.json`을
   보면 `automation` 객체에 `state`/`failure_code`/`last_transition_id`만 있고
   **`processing_input`이 사라져 있다.**

원인은 n8n의 (무변경 대상인) `Code — Decide Transition` 노드 코드에 있다:

```js
const updatedTask = Object.assign({}, task, {
  automation: {
    state: newState,
    failure_code: failureCode,
    last_transition_id: transitionId
  }
});
```

이 노드는 `task.automation`을 **통째로 교체**한다 — ADR-022 스키마(state/
failure_code/last_transition_id)만 알고, ADR-023이 나중에 추가한
`processing_input`은 이 노드가 작성될 때 존재하지 않았으므로 보존 로직이 없다.
그래서 n8n이 task 파일을 다시 쓸 때마다 `processing_input`이 지워진다.

`host_executor.py`의 `process_task()`는 `submit_via_webhook()`이 반환한
(n8n이 다시 쓴) `task_data`를 그대로 `cli_driver`에 넘기고 있어서, 이미 지워진
`processing_input`을 그대로 전달하게 된다.

## 수정 범위 (n8n 노드는 여전히 건드리지 않는다 — 작업 명령서 원칙 유지)

**`host_executor.py`만 고친다.** `queue_item`(host_executor가 원래 갖고 있던,
`processing_input`이 온전한 원본)을 이미 알고 있으므로, n8n 왕복 후 그 값을
다시 병합해 넣으면 된다.

`process_task()`에서 `task_data`를 얻은 직후(웹훅 경로든, 이미
`VALIDATION_PASSED`인 task 파일을 읽는 경로든 **둘 다**), cli_driver에 넘기기
전에:

```python
task_data.setdefault("automation", {})
task_data["automation"]["processing_input"] = processing_input  # queue_item에서 가져온 원본
```

로 복구한 뒤 임시 파일에 쓴다. `submit_via_webhook()` 자체를 바꿀 필요는 없다
(그 함수의 책임은 n8n 왕복까지이고, n8n이 지운 필드를 그 함수가 다시 채워 넣는
것보다 `process_task()`에서 한 번에 병합하는 편이 두 진입 경로(webhook 신규 제출
/ 이미 VALIDATION_PASSED된 task 파일 재사용) 모두를 커버한다).

## 재실행

1. 수정 후 `NAE-REG-BAP-CHURCH-DAGG-001`을 **다시** 파일럿으로 돌린다. 현재
   task 파일이 `FAILED`이므로, 이번 재실행 전에 `.automation/tasks/
   NAE-REG-BAP-CHURCH-DAGG-001.json`과 `.automation/evidence/
   NAE-REG-BAP-CHURCH-DAGG-001.jsonl`을 삭제하고 `INITIATED` 상태로 새로
   제출한다(ADR-022 idempotency 규칙상 `FAILED`에서 새 execution으로 재실행하는
   것은 §8 표에 정의된 정상 경로 — 사람이 원인을 고친 뒤 다시 제출하는 것과
   동일하다. **자동 `FAILED → RETRY_PENDING` 승격이 아니라, 버그 수정 후
   재제출이므로 허용된다.**)
2. `cli_driver`가 이번엔 `processing_input`을 받는지, exit code가 무엇인지,
   실제로 `register_source()`까지 도달하는지 evidence로 남긴다.
3. **성공(exit 0, final_state=QUALITY_PASSED)해야만** 나머지 9건
   (`pilot-queue-backup/`에 대피된 파일들)을 `queue/`로 복귀시키고 확대한다.
   또 실패하면 멈추고 evidence만 남긴다 — 계속 자동 재시도하지 않는다.

## 잘한 것 (그대로 유지)

- 나머지 9건을 `pilot-queue-backup/`으로 대피시켜 `queue/`에 파일럿 1건만
  남긴 것 — 작업 명령서 §4/§5 정확히 준수.
- fail-closed: `register_source()` 미호출, production mutation 0건.
- evidence 스키마(`transition_id`/`payload_signature`/`actor`) — n8n 것과 정확히
  동일한 형식으로 기록됨.
