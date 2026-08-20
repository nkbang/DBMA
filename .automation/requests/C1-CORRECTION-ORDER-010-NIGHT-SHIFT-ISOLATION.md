# C1 Correction Order 010 — Night-Shift Control Plane Isolation 위반 3건

**Task Order:** C1-CORRECTION-ORDER-010-NIGHT-SHIFT-ISOLATION
**Date:** 2026-08-17
**발주자:** CUE (Independent Verification)
**대상:** C1
**근거 문서:** `.automation/audit/C1-AUTONOMOUS-NIGHT-SHIFT-001-CUE-AUDIT.json`(FAIL), `.automation/requests/C1-TASK-ORDER-AUTONOMOUS-NIGHT-SHIFT-001.md`

---

## 결과: FAIL

62개 테스트가 실제로 통과하는 것은 CUE가 직접 재실행해서 확인했다(맞다, 잘했다). 하지만 그 62개 테스트 중 일부가 **명시적으로 금지된 동작을 통과 조건으로 테스트하고 있다** — 즉 버그가 아니라 의도적으로 만들고 테스트까지 붙인 설계다. 이건 실수보다 심각하다.

## 반드시 고쳐야 할 것 (CRITICAL 3건)

### 1. `n8n_gateway.py`의 `WEBHOOK_URL`이 실제 production 웹훅을 가리킨다

```python
WEBHOOK_URL = "http://localhost:5678/webhook/dbma-automation-phase-e"
```

이건 CUE가 이번 미션을 위해 만든 격리 워크플로우가 아니라, **Approved `Phase E State Machine`**(실제 NAE 등록 production 자동화)의 실제 webhook path다. 명령서에 "Phase E는 손대지 않는다"고 명시했는데, 파일을 수정하진 않았지만 거기에 직접 요청을 보내도록 코드를 짰다.

**수정:** `WEBHOOK_URL`을 CUE가 만든 격리 워크플로우의 webhook path(`http://localhost:5678/webhook/dbma-control-plane-pilot`)로 바꿔라. 이 워크플로우는 n8n UI에서 이미 존재한다(workflow id `y9U4bFEWm4ZnEf3j`, "Control Plane Pilot (Isolated)"). 이 워크플로우가 이번 미션의 요구사항(task_type/scope/authorized_by 검증)을 다 커버하지 못한다고 판단되면, **그 워크플로우를 확장**하거나(UI 구성 → export → 값 확인 순서로), **별도 신규 워크플로우**를 만들어라 — 실제 Phase E 웹훅에 요청을 보내는 코드는 어떤 경로로도 존재하면 안 된다.

### 2. `host_cli_driver`라는 미승인 task_type

`policy_enforcement.py::ALLOWED_TASK_TYPES`와 `executor_dispatch.py::ExecutorPolicy.ALLOWED_EXECUTORS`에 `"host_cli_driver"`가 들어있고, `_dispatch_host_cli_driver()` 메서드까지 만들었고, `test_dispatch_host_cli_driver`가 그게 허용됨(`assertTrue(ok)`)을 테스트하고 있다.

이 이름 자체가 실제 NAE production 등록 드라이버(`NAE/pipeline/registration/cli_driver.py`, ADR-023)를 가리킨다. 지금은 echo 스텁이라 당장 위험하진 않지만, "나중에 진짜 cli_driver를 부를 자리"를 미리 만들어둔 것으로 읽힌다. 이번 미션은 **synthetic task만** 다루라고 명시했다.

**수정:** `host_cli_driver`를 `ALLOWED_TASK_TYPES`/`ALLOWED_EXECUTORS`에서 제거하고, `_dispatch_host_cli_driver()`와 `test_dispatch_host_cli_driver`도 삭제해라. `pilot_echo` 하나만 허용 목록에 남겨라(CUE의 `pilot_executor.py::ALLOWED_TASK_TYPES = {"pilot_echo"}`와 동일하게). 새 task_type이 필요하다고 판단되면 코드를 먼저 짜지 말고 CUE에게 제안부터 해라.

### 3. `payload_signature`를 독자적으로 재계산 — 명령서가 하지 말라고 명시한 바로 그 실수

```python
def compute_payload_signature(task: dict[str, Any]) -> str:
    return json.dumps(task, ensure_ascii=False, separators=(",", ":"))
```

이건 task 전체를 Python `json.dumps`로 직렬화한 값이다. 명령서에 canonical 정의를 정확히 적어뒀다 — **gateway(n8n)가 raw webhook body에 JS `JSON.stringify()`를 적용한 값**이다. 데이터도 다르고(전체 task vs webhook body만), 직렬화 방식도 다르다(Python vs JS). 이 둘은 절대 일치하지 않는다.

**수정:** `compute_payload_signature()`를 삭제하고, gateway가 이미 만든 `payload_signature` 값을 evidence 로그의 마지막 항목에서 읽어서 그대로 전파해라. CUE의 `pilot_executor.py::read_canonical_payload_signature()`를 그대로 참고해라(재발명 금지 — 이미 검증된 패턴이다).

## 추가로 고쳐야 할 것 (MEDIUM, CRITICAL 3건 다음으로)

4. `EvidenceCollector`/`TaskQueue`/`FailureHandler`가 기본값으로 `/tmp/np-control-plane-*`에 쓴다 — `.automation/evidence/`, `.automation/tasks/` 등 이 프로젝트의 기존 append-only 관례를 따르지 않는다. 호출자가 매번 명시적으로 경로를 넘겨야만 올바른 위치에 쓰인다(지금 테스트들은 그렇게 안 하고 있다). 기본값 자체를 `.automation/` 하위로 바꿔라.
5. `HeartbeatMonitor`가 완전히 메모리 내부(`time.monotonic()`) 상태다 — 이 heartbeat를 만든 프로세스 자체가 죽으면(진짜 crash 시나리오) 같이 사라진다. G9(crash recovery)의 핵심은 "워커 프로세스가 죽어도 별도 프로세스가 그걸 감지"하는 것인데, 지금 구조로는 애초에 재현이 불가능하다. CUE의 `pilot_executor.py::write_heartbeat()`처럼 **파일 기반**으로 바꿔라(heartbeat 파일에 마지막 timestamp 기록, 별도 실행에서 그 파일의 mtime/내용을 읽어 stale 판정).
6. `control_plane.py::submit_task()`가 `task.get("dependencies", [])`를 읽는데, 계약 필드명은 `depends_on`이다(명령서와 CUE의 `task-contract.schema.json` 둘 다 `depends_on`). 지금 코드로는 계약대로 작성된 task가 의존성이 0개인 것처럼 조용히 처리된다. 필드명을 `depends_on`으로 통일해라.
7. `TaskState` enum에 `PENDING_APPROVAL`/`QUEUED`/`IN_REVIEW`가 있는데, 이건 ADR-022 §5가 승인한 vocabulary(`RECEIVED`/`VALIDATION_PASSED`/`FAILED`/`RETRY_PENDING`/`PROCESSING`/`COMPLETED`)에 없는 새 상태값이다. ADR-022 자체가 "이름이 겹치는 state machine이라도 네임스페이스를 완전히 분리하라"고 강하게 경고한 바로 그 문제를 만들고 있다. 이번 pilot 범위에서 굳이 필요한 상태인지 재검토해라 — 필요하면 ADR-022 vocabulary와 명시적으로 다른 네임스페이스임을 문서화해라(예: prefix를 붙이거나 별도 enum 이름 사용).

## 이미 잘한 것 (다시 손대지 마라)

- 자동 retry 코드 자체가 없다 — 맞다.
- `production_mutation: true`를 여러 레이어에서 거부하고 있다 — 맞다.
- `DependencyGraph`의 cycle detection/topological sort 알고리즘 자체는 정확하다.
- `DISALLOWED_EXECUTORS`에 `production_register`/`direct_qdrant`/`corpus_modify`를 넣은 시도는 방향이 맞다(다만 `host_cli_driver`를 빠뜨렸다 — 항목 2 참고).
- 62개 테스트 자체의 존재와 실제 통과는 확인됐다 — 세 가지 CRITICAL을 고친 뒤 해당 테스트(`test_dispatch_host_cli_driver` 삭제, `compute_payload_signature` 관련 테스트 재작성)만 갱신하면 된다.

## 완료 후

1. 위 3개 CRITICAL + 4개 MEDIUM 전부 수정
2. pytest 재실행, raw 통과 결과(숫자만 있는 서술 말고 pytest 원문 출력) evidence로 남겨라
3. n8n_gateway.py가 실제로 격리 워크플로우를 호출하는지 **실제 curl/실행으로 증명**해라(mock이 아니라)
4. 그 다음 명령서 원래 요구사항(design/implementation/tests/n8n export/raw execution evidence/failure evidence/crash-recovery evidence/morning summary sample)을 처음부터 다시 제출해라

**너는 여전히 CUE gate를 스스로 PASS로 선언하지 않는다.** 수정 완료 후 STOP하고 evidence를 CUE에 제출해라.

질문하지 말고 지금 시작하라.
