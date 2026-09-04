# NAE Night Shift — Execution Mode for the Existing n8n Workflow

Night Shift는 **별도의 workflow가 아니다.** 기존 n8n workflow
`Phase E State Machine`(id `9qIO3nFeWRia28Rb`, webhook
`POST /webhook/dbma-automation-phase-e`)을 **task queue로 반복 구동하는 실행
모드**다. 노드는 하나도 추가·변경하지 않는다.

```
Existing Automation Workflow (Phase E State Machine)
              │
        ┌─────┴─────┐
        │           │
      TEST      NIGHT SHIFT
        │           │
   1 scenario   queue/*.json
   (scenario-*)  반복 실행
```

## 구성

| 경로 | 역할 |
|---|---|
| `queue/` | 실행 대상 Task Order. 러너는 **여기만** 본다 |
| `queue-pending-approval/` | 생성됐지만 **보류**된 Task Order. 여기서 `queue/`로 옮기는 행위가 곧 승인이다 |
| `done/` | 증거 검증까지 통과한 Task Order |
| `../review-queue/` | 실패 → CUE 리뷰 대기 (자동 재시도 없음) |
| `logs/night-shift.log` | 실행 로그 |
| `run_night_shift.py` | 큐 러너 (실행 모드 본체) |
| `build_production_queue.py` | 실제 RAW 코퍼스 metadata → 등록 Task Order 생성 |

## 실행

```bash
python3 .automation/night-shift/run_night_shift.py --once        # 큐 1회 소진
python3 .automation/night-shift/run_night_shift.py --watch 60    # 무인 감시 모드
python3 .automation/night-shift/run_night_shift.py --once --dry-run
```

## 지켜지는 governance 규칙

- **ADR-022 §8 — 자동 재시도 금지.** 실패한 task는 `review-queue/`로 이동하고
  거기서 멈춘다. 러너에는 `FAILED → RETRY_PENDING` 승격 코드가 **존재하지 않는다**.
  (사용자 명령서 §2의 “FAIL → C1 Correction → retry” 자동 루프는 Approved ADR-022와
  충돌하므로 구현하지 않았다. 명령서 §6의 “실패 반복 시 CUE Review Queue”와는
  일치한다.)
- **Evidence-first.** n8n이 `processing_completed`를 응답해도 그것만으로 PASS
  처리하지 않는다. `.automation/tasks/<task_id>.json`의 `automation.state`,
  `.automation/evidence/<task_id>.jsonl`의 마지막 전이, 그리고 ADR-021
  `registration_state.json`의 `QUALITY_PASSED`를 **디스크에서 다시 읽어** 대조한다.
  셋 중 하나라도 어긋나면 FAIL이다.
- **Production Boundary.** 매 task 전후로 보호 경로(`core/retrieval.py`,
  `core/module_registry.py`, `NAE/pipeline/registration/pipeline.py`,
  `.automation/tasks/schema.json`, ADR-022/023 문서)의 SHA256을 비교한다. 하나라도
  바뀌면 전체 실행을 즉시 중단한다(exit 2).
- **Bounded.** task 1건당 제출은 1회. `--watch`는 빈 폴링이 `--max-idle-cycles`
  (기본 480회)에 도달하면 스스로 멈춘다.

## 현재 가동 범위 (2026-08-15)

- ✅ `RECEIVED → VALIDATION_PASSED / FAILED` (ADR-022) — 라이브에서 검증됨
- ⛔ `PROCESSING → COMPLETED` (ADR-023) — **미가동**.
  `docs/architecture/ADR-023-AMENDMENT-A-Executor-Runtime.md` 승인 전까지 보류.
  이유: n8n 2.29.9는 `executeCommand` 노드를 기본 비활성화하며, n8n 컨테이너에는
  Python도 `NAE/` 소스도 없다 — ADR-023 §4의 커맨드는 실행 자체가 불가능하다.
