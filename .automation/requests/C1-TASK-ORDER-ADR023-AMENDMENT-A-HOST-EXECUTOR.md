# C1 Task Order — ADR-023 Amendment A: Host Executor Runtime (Option A)

| | |
|---|---|
| Issued by | CUE, on Rev. Bang's approval (2026-08-15 — "Option A를 승인해 주시면 됩니다" / "여기서 Option A를 승인") |
| Mission | RAW → Registration → Full Processing 실제 무인 실행 |
| Priority | P0 |
| Mode | Autonomous / No Questions / Night Shift 계속 |
| Design basis | `docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md` (Approved), `docs/architecture/ADR-023-AMENDMENT-A-Executor-Runtime.md` (Approved, Option A) |
| Supersedes | (없음 — NAE Retrieval Bridge 미션은 종료됐다. 이 작업은 새 미션이다) |

---

## 배경 (재조사 금지 — 이미 CUE가 실측 확인함)

- n8n 2.29.9는 `executeCommand` 노드를 기본 비활성화한다. 활성화 강행 시 그 노드가
  포함된 워크플로우는 아예 활성화가 실패한다(재현됨).
- n8n 컨테이너에는 Python도 `NAE/` 소스도 `~/envs/dbma311`도 없다. ADR-023 §4의
  커맨드는 컨테이너 안에서 실행될 수 없다.
- 라이브 워크플로우는 현재 **23노드(ADR-022 검증 범위)**로 운영 중이다. 28노드판
  (Execute Command 포함, `.automation/workflows/phase-e.json`)은 **한 번도 라이브에서
  성공 실행된 적이 없다** — 활성화 자체가 실패했었다.
- **이 28노드판을 직접 열어보면 알 수 있는 사실**: `Execute Command — cli_driver`
  이후의 `Code — Exit Code Check → IF Process Result → Respond COMPLETED/
  PROCESSING_FAILED` 경로에는 **task 파일이나 evidence 파일에 쓰는 노드가 없다**
  — HTTP 응답으로만 반환되고 디스크에 영속화되지 않는다. Host Executor는 이 영속화
  책임까지 대신 져야 한다(아래 계약 참고). 이건 새로 발견하라는 뜻이 아니라, 이미
  파일을 열어 확인된 사실이니 그대로 받아서 구현만 하면 된다.

## 목표 구조 (Option A, 그대로 구현)

```
n8n (기존, 무변경)                     Host Executor (신규)
  Webhook 수신                            │
  Schema Validation                       │
  RECEIVED → VALIDATION_PASSED/FAILED     │
  task/evidence 기록                      │
  HTTP 응답                               │
                                           │  (VALIDATION_PASSED + processing_input
                                           │   있는 task를 host에서 감지)
                                           ▼
                              ~/envs/dbma311/bin/python -m
                              NAE.pipeline.registration.cli_driver
                              --request-json <task.json>
                                           │
                              exit code 계약(ADR-023 §12)으로 판정
                                           │
                              VALIDATION_PASSED → PROCESSING → COMPLETED/FAILED
                              task 파일 갱신 + evidence 기록 (host executor 책임)
```

n8n 워크플로우 노드는 **1개도 건드리지 않는다.** n8n은 계속 RECEIVED/VALIDATION_PASSED/
FAILED만 책임진다.

## 반드시 그대로 유지해야 하는 계약 (재설계 금지 — n8n의 기존 코드에서 그대로 가져다 쓸 것)

### 1. State mapping (n8n `Code — Exit Code Check` 노드의 로직, `phase-e.json`에서 확인됨)

```
exit 0 + stdout.final_state == "QUALITY_PASSED"          -> COMPLETED, failure_code=null
exit 0 + stdout.final_state == "REGISTRATION_FAILED"      -> FAILED, REGISTRATION_FAILED
exit 0 + stdout.final_state == "RAW_CHECKSUM_MISMATCH"    -> FAILED, RAW_CHECKSUM_MISMATCH
exit 0 + stdout.final_state == "EXTRACTION_FAILED"        -> FAILED, EXTRACTION_FAILED
exit 0 + stdout.final_state == "QUALITY_GATE_FAILED"      -> FAILED, QUALITY_GATE_FAILED
exit 0 + 그 외 값 / stdout 파싱 실패                        -> FAILED, INTERNAL_STATE_MAPPING_ERROR
exit 1                                                     -> FAILED, FILE_ERROR
exit 2                                                     -> FAILED, VALIDATION_FAILED
exit 3                                                     -> FAILED, RAW_CHECKSUM_MISMATCH
그 외 exit code                                            -> FAILED, INTERNAL_STATE_MAPPING_ERROR
```

### 2. 허용된 전이만 실행 (ADR-023 §8 표 그대로)

- `VALIDATION_PASSED → PROCESSING` : 허용
- `PROCESSING → COMPLETED` / `PROCESSING → FAILED` : 허용
- 그 외(특히 `FAILED → RETRY_PENDING` 자동 승격): **절대 금지** — ADR-022 §8과
  이번 세션의 Night Shift 러너(`run_night_shift.py`)에 이미 명문화된 원칙과 동일.
  Host Executor에 재시도 로직을 넣지 마라. 실패한 task는 그대로 FAILED로 남긴다.

### 3. Evidence entry 스키마 (n8n `Code — Decide Transition`의 `evidenceEntry`와 동일 필드)

```json
{
  "transition_id": "<task_id>#<sequence>",
  "task_id": "...",
  "from": "VALIDATION_PASSED",
  "to": "COMPLETED | FAILED",
  "failure_code": null,
  "actor": "host_executor",
  "payload_signature": "<processing_input의 sha256>",
  "execution_id": "<host executor 자체 실행 id>",
  "timestamp": "<ISO8601>",
  "reason": "..."
}
```
`.automation/evidence/<task_id>.jsonl`에 **append**한다(n8n이 쓰던 파일과 동일 파일,
동일 append-only 방식).

### 4. Task 파일 갱신

`.automation/tasks/<task_id>.json`의 `automation.state`/`automation.failure_code`/
`automation.last_transition_id`를 갱신하고 **pretty JSON으로 덮어쓴다** — n8n의
`Convert Task to JSON`(indent 2) 방식과 동일한 포맷으로.

## 구현 지시

1. **호스트 환경 최소 확인** — 장시간 조사 금지, 아래만 실행하고 evidence로 남긴다:
   - `~/envs/dbma311/bin/python -c "import NAE.pipeline.registration.cli_driver"` 성공 확인
   - `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/`가 실제 존재하는지 확인
2. **Host Executor 구현** — `.automation/night-shift/host_executor.py`(신규 파일).
   기존 `.automation/night-shift/run_night_shift.py`가 이미 하고 있는 webhook 제출 +
   evidence-first 검증 로직은 그대로 재사용하되(중복 구현 금지, import해서 쓰거나
   함수를 공유), 그 다음 단계로 PROCESSING leg를 추가한다:
   - `.automation/tasks/*.json` 중 `automation.state == "VALIDATION_PASSED"`이고
     `automation.processing_input.raw_item_dir`이 비어있지 않은 task를 찾는다.
   - 이미 `COMPLETED`/`FAILED`로 끝난 task는 건너뛴다(evidence 파일의 마지막
     transition으로 판단).
   - `subprocess`로 `cli_driver.py`를 직접 호출한다(import 금지 — ADR-023 §9의
     import 경계를 그대로 지키기 위해 프로세스 경계를 유지한다).
   - 위 mapping table로 결과를 판정하고, evidence append + task 파일 갱신을 수행한다.
   - 모든 예외는 fail-closed로 FAILED 처리한다 — 절대 상태를 모호하게 남기지 않는다.
3. **Production Boundary 검증**을 코드가 아니라 **실행으로** 증명한다:
   - `git diff core/retrieval.py NAE/pipeline/registration/pipeline.py` 매 실행 전후 빈 출력
   - `host_executor.py`의 import 문에 `NAE.pipeline.tsu/ingest/embed/index`나
     `qdrant_client`가 없음을 `grep`으로 확인
4. **1건 E2E dry-run**: `.automation/night-shift/queue/NAE-REG-BAP-CHURCH-DAGG-001.json`
   (가장 작은 단일 볼륨, 파일럿에 적합)만 대상으로 전체 사이클을 1회 실행한다:
   webhook 제출 → VALIDATION_PASSED → Host Executor → `cli_driver` 실행 →
   `NAE/pipeline/registration/state/registration_state.json`에 실제
   `QUALITY_PASSED` 기록 확인. **이건 실제 production mutation이다** — 성공해도
   실패해도 정확히 무엇이 기록됐는지 evidence에 남긴다.
5. **성공 시에만** 나머지 9건(`NAE-REG-BAP-MISS-FULLER-VOL01~08`,
   `NAE-REG-BAP-CHURCH-HISCOX`)으로 확대한다. 1건이 실패하면 **자동으로 다음 9건에
   진행하지 말고** 원인을 evidence에 남기고 멈춘다(이건 예외적으로 STOP 대상 —
   production mutation 첫 실행이므로 3회 재시도 규칙보다 우선한다).

## 금지 사항 (반복 — 이번에도 동일)

```
❌ n8n 워크플로우 노드 변경
❌ core/retrieval.py 변경
❌ NAE/pipeline/registration/pipeline.py 변경 (register_source() 무수정 원칙 유지)
❌ 새 ADR 생성
❌ Qdrant write operation
❌ FAILED → RETRY_PENDING 자동 승격 로직
```

## Evidence

`.automation/evidence/night-shift/host-executor-implementation/`에
`env-check/`, `host-executor-code/`(git diff), `pilot-dagg/`(1건 E2E 전체 로그 +
`registration_state.json` 전/후 diff), `bulk-9/`(확대 실행 시) 로 남긴다.
매 단계 `command.txt`/`exit_code.txt`(숫자만)/`stdout.log`/`stderr.log`.

## Stop 조건

- 파일럿 1건이 실패하면 즉시 멈추고 원인만 기록(위 §5)
- `core/retrieval.py` 또는 `pipeline.py`를 건드려야 해결되는 문제일 때
- 그 외에는 질문 없이 계속 진행한다.
