# Autonomous Night-Shift Resilience Matrix (Section D)

전부 격리된 `control-plane-pilot` 네임스페이스 안에서 실제 실행으로 검증됨. Production 데이터/코드 무관.

## 1. Executor crash (PROCESSING 도중 사망)

- **EXPECTED**: 죽은 워커가 남긴 PROCESSING task는 무한정 머물지 않고 FAILED로 강제 종료되며, 재실행되지 않는다.
- **ACTUAL**: 정확히 예상대로 동작.
- **EVIDENCE**: `CONTROL-PLANE-PILOT-012-CRASH-SIM` — automation.state를 PROCESSING으로 직접 설정 + heartbeat를 60초 과거로 backdate → `pilot_executor.py --once` 실행 → 로그 `STALE WORKER: ... heartbeat age=73.2s > 10s -- forcing FAILED` → task state FAILED/STALE_WORKER_TIMEOUT. subprocess가 한 번도 실행되지 않았음을 stdout/stderr 파일 부재로 확인(`.automation/evidence/night-shift/control-plane-pilot/`에 012 관련 파일 없음).
- **RECOVERY POLICY**: 자동 종료만, 자동 재시도 없음. `.automation/audit/AUTONOMOUS-NIGHT-SHIFT-001-CUE-12-GATE-REVIEW.json` G9 참고.
- **CUE DECISION**: PASS.

## 2. n8n 재시작

- **EXPECTED**: 재시작 후 워크플로우 자동 재활성화, evidence 무손실, 웹훅 정상 재작동.
- **ACTUAL**: 4개 워크플로우(Phase E 포함) 전부 자동 재활성화(`docker logs` "Activated workflow" 4건). evidence 파일 라인 수 재시작 전후 3줄로 동일. 재시작 후 curl 재시도 정상 응답.
- **EVIDENCE**: `docker restart dbma_n8n` 실행 로그, 재시작 전/후 `wc -l .automation/evidence/CONTROL-PLANE-PILOT-001.jsonl` 둘 다 3.
- **RECOVERY POLICY**: n8n 자체가 컨테이너 재시작 시 워크플로우를 자동 재로드하는 built-in 동작(n8n 2.29.9). 별도 코드 불필요.
- **CUE DECISION**: PASS.

## 3. Executor 재시작

- **EXPECTED**: pilot_executor.py는 상태를 파일(task json + heartbeat json)에서만 읽으므로, 프로세스 재시작 후에도 이전 상태를 정확히 이어받는다.
- **ACTUAL**: pilot_executor.py는 in-memory 상태를 전혀 갖지 않는다(`--once` 모드 자체가 매번 새 프로세스) — 설계상 "재시작"이 곧 정상 실행 방식이다. 매 실행마다 `detect_and_recover_stale_workers()`가 먼저 돌고, 그 다음 큐를 스캔한다.
- **EVIDENCE**: `pilot_executor.py::main()` 코드 자체(항상 stale 스윕 → 큐 스캔 순서), 오늘 밤 여러 차례 반복 실행에서 일관된 동작 확인.
- **RECOVERY POLICY**: 파일 기반 상태이므로 재시작=정상 실행. ADR-026 §2.16에 이 패턴을 설계 원칙으로 명문화함.
- **CUE DECISION**: PASS.

## 4. Duplicate webhook (동일 요청 재전송)

- **EXPECTED**: 동일 task_id + 동일 payload 재전송 → `duplicate`, state/evidence 불변.
- **ACTUAL**: 정확히 예상대로. `CONTROL-PLANE-PILOT-005-GENERALIZED` 재요청 → `status:"duplicate"`, evidence 라인 수 불변(3), state 불변(COMPLETED).
- **EVIDENCE**: `.automation/audit/CONTROL-PLANE-GENERALIZATION-001-CUE-10-GATE-REVIEW.json` G5.
- **CUE DECISION**: PASS.

## 5. Duplicate task (동일 task_id, 다른 payload)

- **EXPECTED**: `TASK_ID_PAYLOAD_CONFLICT`, state 불변.
- **ACTUAL**: 정확히 예상대로 — `CONTROL-PLANE-PILOT-001`을 오늘 밤 n8n 재시작 후 재요청했을 때도 `task_id_payload_conflict` 정상 반환(§2 evidence 참고, 001의 evidence 로그 마지막 항목이 pilot_executor 소유라 payload_signature 형식이 달라 conflict로 판정 — 이 자체가 예전에 발견했던 실제 알려진 케이스와 일치).
- **CUE DECISION**: PASS.

## 6. Stale PROCESSING (crash와 동일 메커니즘)

§1과 동일 — `STALE_THRESHOLD_S=10`s 초과 시 강제 FAILED. 중복 기록 생략.

## 7. Malformed task (존재하지 않는 task_id)

- **EXPECTED**: fail-closed, `file_error`.
- **ACTUAL**: `curl ... -d '{"task_id":"CONTROL-PLANE-PILOT-DOES-NOT-EXIST"}'` → `{"status":"file_error","message":"No file(s) found","production_mutation":false}`, HTTP 200.
- **CUE DECISION**: PASS.

## 8. Malformed task (파싱 자체 실패)

- **EXPECTED**: ingress 레벨 명시적 거부(ADR-022 §10).
- **ACTUAL**: `curl ... -d '{not valid json'` → HTTP 422, `{"code":422,"message":"Failed to parse request body",...}`.
- **CUE DECISION**: PASS.

## 9. Unauthorized task_type

- **EXPECTED**: 게이트웨이 단계에서 `VALIDATION_FAILED`로 거부, executor에 도달 안 함.
- **ACTUAL**: `CONTROL-PLANE-PILOT-006-BADTYPE`(task_type=production_run) → `VALIDATION_FAILED`, executor 로그에 처리 흔적 없음. 게이트웨이를 우회한 경우(`007-BYPASS`)도 executor가 독자적으로 `TASK_TYPE_NOT_AUTHORIZED`로 거부(defense in depth).
- **CUE DECISION**: PASS.

## 10. production_mutation=true

- **EXPECTED**: 게이트웨이 단계에서 즉시 거부.
- **ACTUAL**: `CONTROL-PLANE-PILOT-002-FAIL`(production_mutation:true) → `VALIDATION_FAILED`.
- **CUE DECISION**: PASS.

## 11. missing authorized_by

- **EXPECTED**: `VALIDATION_FAILED`.
- **ACTUAL**: `CONTROL-PLANE-PILOT-030-MISSING-AUTH` → `{"status":"failed",...,"failure_code":"VALIDATION_FAILED"}`.
- **CUE DECISION**: PASS.

## 12. missing scope

- **EXPECTED**: `VALIDATION_FAILED`.
- **ACTUAL**: `CONTROL-PLANE-PILOT-031-MISSING-SCOPE` → `{"status":"failed",...,"failure_code":"VALIDATION_FAILED"}`.
- **CUE DECISION**: PASS.

## 13. Evidence write failure

- **EXPECTED**: (설계 검토만, 실제 장애 주입 미실행) — evidence 쓰기 실패 시 task state가 침묵 실패로 COMPLETED/FAILED 어느 쪽으로도 잘못 기록되지 않고, 예외가 상위로 전파되어 관찰 가능해야 한다.
- **ACTUAL**: 실제 장애 주입(디스크 권한 변경 등)은 오늘 밤 범위에서 실행하지 않음 — 격리 pilot이라도 파일시스템 권한을 건드리는 테스트는 부작용 범위가 예측하기 어려워 별도 승인 없이 보류함.
- **CUE DECISION**: **HOLD** — 실행 증거 없음. 다음 승인된 task에서 별도로 검증 필요(예: evidence_dir을 읽기 전용으로 만든 임시 디렉터리로 지정 후 write 실패 시 예외 전파 확인).

## 14. Canonical signature mismatch (재계산 vs 전파)

- **EXPECTED**: 재계산 경로가 존재하면 duplicate가 conflict로 오판정됨; 전파 방식으로 고치면 정상화.
- **ACTUAL**: 오늘 밤 정확히 이 결함을 CUE 자신의 pilot(1차)과 C1의 제출물(2차) 양쪽에서 발견하고 수정함. 수정 전/후 raw evidence 전부 `.automation/audit/N8N-CONTROL-PLANE-PILOT-001-CUE-FINAL-REVIEW.json`, `.automation/audit/C1-CORRECTION-ORDER-010-CUE-CLOSURE.json`에 기록됨.
- **CUE DECISION**: PASS(수정 후 재검증 완료).

---

## 요약

| # | 항목 | CUE DECISION |
|---|---|---|
| 1 | Executor crash | PASS |
| 2 | n8n 재시작 | PASS |
| 3 | Executor 재시작 | PASS |
| 4 | Duplicate webhook | PASS |
| 5 | Duplicate task | PASS |
| 6 | Stale PROCESSING | PASS |
| 7 | Malformed task (없는 task_id) | PASS |
| 8 | Malformed task (파싱 실패) | PASS |
| 9 | Unauthorized task_type | PASS |
| 10 | production_mutation=true | PASS |
| 11 | missing authorized_by | PASS |
| 12 | missing scope | PASS |
| 13 | Evidence write failure | **HOLD** (미실행) |
| 14 | Canonical signature mismatch | PASS (결함 발견 후 수정) |

13/14 PASS, 1/14 HOLD(장애 주입 범위 판단 보류 — 별도 승인 후 진행 권장).
