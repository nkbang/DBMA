# C1 Task Order — Autonomous Night-Shift Control Plane

**Task Order:** C1-TASK-ORDER-AUTONOMOUS-NIGHT-SHIFT-001
**Date:** 2026-08-17
**발주자:** Rev. Bang (via CUE relay)
**대상:** C1 (implementation)
**근거 문서:** `.automation/audit/CONTROL-PLANE-GENERALIZATION-001-CUE-10-GATE-REVIEW.json`(CONDITIONAL PASS), `docs/architecture/ADR-022-DBMA-N8N-Automation-State-Machine.md`(Approved), `docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md`(Approved), `.automation/night-shift/host_executor.py`(기존 Option A 패턴), `.automation/night-shift/pilot_executor.py`(CUE의 canonical payload_signature propagation 구현 참고)
**현재 상태:** 신규 task order. C1 구현 착수 전 CUE gate는 존재하지 않음 — **C1은 스스로 CUE gate를 PASS로 선언하지 않는다.** 구현+테스트 완료 후 STOP하고 evidence를 CUE에 제출한다.

---

## 목표 (한 문장)

**Corpus Factory production 실행을 시작하지 않고, 격리된 synthetic task만으로 autonomous night-shift control plane(큐/의존성/게이트웨이/executor/heartbeat/stale-worker 감지/evidence/아침 요약)을 구현하고 증명하는 것.**

## 절대 금지

- `core/retrieval.py` 수정
- `data/제련완성본/` 접근
- production Qdrant 접근
- production `registration_state.json` 수정
- Fuller Vol.02–08 처리
- 기존 Approved n8n workflow(`Phase E State Machine`, `DBMA Automation TEST (Phase B~D)`) 직접 수정
- ADR-025 상태 변경
- 자동 retry 구현 (FAILED → RETRY_PENDING은 사람 트리거만, ADR-022 §8)

## 구현 범위 (12개 항목)

1. **Task Queue contract** — 대기/실행/완료 큐 디렉터리 구조 정의(신규, 기존 `.automation/night-shift/queue`·`done`과 충돌하지 않는 별도 namespace 사용)
2. **Task dependency handling** — task 파일에 `depends_on: [task_id, ...]` 필드, 의존 task가 전부 `COMPLETED`일 때만 실행 대기열에서 꺼냄
3. **n8n gateway/control-plane integration** — 기존 `Control Plane Pilot (Isolated)` 워크플로우(id `y9U4bFEWm4ZnEf3j`, CUE 소유) 확장 또는 별도 신규 워크플로우로 진행. **Phase E는 손대지 않는다.**
4. **Host executor dispatch contract** — n8n은 gateway만, 실제 실행은 host executor(신규 프로세스)가 담당(Option A 패턴 그대로)
5. **Executor policy enforcement** — task_type allowlist, namespace 강제, production_mutation 강제 false — CUE의 `pilot_executor.py::check_isolation_contract()` 패턴 참고(재사용 권장, 재발명 금지)
6. **Heartbeat** — executor가 작업 진행 중 주기적으로 heartbeat 기록(파일 또는 evidence)
7. **Stale-worker detection** — heartbeat가 임계시간 이상 갱신되지 않으면 stale로 판정
8. **Terminal-state enforcement** — stale worker가 감지된 task는 `PROCESSING`에 무한정 머물지 않고 명시적 terminal state(`FAILED`, failure_code로 원인 구분)로 강제 전이. **자동으로 RETRY_PENDING으로 승격하지 않는다.**
9. **Evidence collection** — ADR-022 §11 형식 유지, append-only, **모든 전이는 유일한 `transition_id`를 가져야 한다**(동일 실행 내 여러 전이가 transition_id를 공유하는 버그를 CUE가 이전 라운드에서 발견·수정한 바 있음 — 동일 결함 재현 금지, 구현 후 유일성 직접 검증할 것)
10. **Duplicate/conflict protection** — 동일 task_id + 동일 canonical `payload_signature` → DUPLICATE(no-op). 동일 task_id + 다른 signature → CONFLICT. **payload_signature는 gateway가 만든 값을 executor가 그대로 전파하며 재계산하지 않는다**(CUE가 확인한 canonical 정의: gateway의 raw webhook body에 대한 JS `JSON.stringify()`)
11. **Safe failure handling** — 실패는 항상 명시적 failure_code로 구분, 침묵 실패 금지
12. **Morning summary generation** — 배치 실행 후 처리된 task 목록/성공-실패 카운트/stale-worker 복구 이력을 요약한 문서 생성(형식 자유, 사람이 읽기 쉽게)

## 필수 원칙 (재확인)

- n8n = orchestration/gateway. 실제 실행 로직을 n8n 안에 넣지 않는다(Execute Command로 production 코드를 직접 부르지 않는다 — Phase E의 과거 시행착오와 ADR-023 Option A 채택 이유 참고).
- host executor = 실제 실행.
- C1 = implementation agent. runtime executor로 스스로를 취급하지 않는다(즉 이 시스템이 "C1을 호출"하는 방식으로 설계하지 않는다 — night-shift는 host executor 프로세스가 담당).
- canonical `payload_signature`는 gateway가 만든 값 그대로 유지.
- evidence는 append-only.
- 자동 retry 금지.
- `production_mutation` 기본값 `false`, 이 태스크의 모든 synthetic task에서 `true`가 되는 경로가 있으면 안 됨.
- Corpus Factory production corpus와 완전히 격리(namespace 분리, 별도 task_id prefix 사용 권장 — 예: `NIGHT-SHIFT-PILOT-*`).

## C1이 제출해야 할 것

- design (설계 문서, 짧아도 됨 — 최소 위 12항목이 어떻게 연결되는지 다이어그램/설명)
- implementation (코드)
- tests
- n8n export (신규/확장 workflow의 `export:workflow` 결과 JSON)
- raw execution evidence (curl 명령 원문 + 응답 원문 + evidence jsonl)
- failure evidence (의도적 실패 케이스 최소 1건)
- crash/recovery evidence (heartbeat 끊김 → stale-worker 감지 → terminal state 강제 전이가 실제로 재현된 증거)
- morning summary sample (실제 생성된 샘플 1건)

## 금지 사항 (재확인)

- **C1은 CUE gate를 스스로 PASS로 선언하지 않는다.** 구현+테스트가 끝나면 여기서 멈추고 evidence를 CUE에 제출한다. PASS/FAIL/HOLD 판정은 CUE 독립검증 이후에만 나온다.
- n8n workflow JSON 손작성 금지(UI 구성 → export → 값 확인 순서, 이 저장소의 기존 규칙 그대로).
- 기존 Approved workflow 노드 파라미터 변경 금지.

---

## 참고 — CUE가 병행 진행 중인 사항

Rev. Bang의 동일 지시에 따라 CUE도 독립적으로 동일 영역(G1–G12: Task Contract/Queue/Authorization/Executor Isolation/Signature/Duplicate-Conflict/Dependency/Heartbeat/Crash Recovery/Evidence Integrity/Production Isolation/End-to-End Night Simulation)을 별도의 격리된 pilot으로 진행한다. C1의 구현과 CUE의 구현은 **서로 다른 격리 네임스페이스**를 사용하며 상호 간섭하지 않는다. C1 제출 evidence는 CUE가 자신의 구현 경험을 근거로 독립 재감사한다.
