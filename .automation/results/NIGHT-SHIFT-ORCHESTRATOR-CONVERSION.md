# n8n Workflow → NAE Night Shift Orchestrator 전환 결과

- 작성: CUE, 2026-08-15
- 명령: "기존 n8n Workflow를 NAE Night Shift Orchestrator로 전환" (Rev. Bang, HIGH)
- 기준 문서: ADR-022(Approved), ADR-023(Approved), ADR-024(Proposed)

---

## 1. 기존 workflow 재사용 가능 여부 — **가능. 새 workflow 만들지 않음**

라이브 워크플로우 `Phase E State Machine`(id `9qIO3nFeWRia28Rb`)이 명령서 §2의
목표 구조를 이미 전부 담고 있다.

| 명령서 요구 단계 | 기존 노드 | 신규 필요 |
|---|---|---|
| Task Order 수신 | `Webhook` | — |
| 검증 | `Code — Schema Validation` | — |
| 상태 전이/idempotency | `Code — Decide Transition`, `IF Conflict/Duplicate/Illegal` | — |
| 실행 | `Execute Command — cli_driver` | (환경 문제, §3) |
| Test/판정 | `Code — Exit Code Check` | — |
| Evidence 수집 | `Write Task File`, `Write Evidence File` | — |
| 결과 라우팅 | `Respond PASS/FAIL/COMPLETED/PROCESSING_FAILED/...` | — |

**결론: 워크플로우 노드는 1개도 추가·수정하지 않았다.** Night Shift는 별도
시스템이 아니라 이 워크플로우의 **실행 모드**(task queue 구동)로 구현했다.

## 2. 실제 변경한 workflow/node

**없음** — 노드 편집 0건. 변경한 것은 다음뿐이다.

| 파일 | 변경 |
|---|---|
| `.automation/night-shift/run_night_shift.py` | 신규 — 큐 러너(실행 모드) |
| `.automation/night-shift/build_production_queue.py` | 신규 — RAW 코퍼스 → Task Order 생성기 |
| `.automation/night-shift/README.md` | 신규 |
| `.automation/workflows/phase-e-adr022-23node-rollback.json` | 신규 — 라이브 롤백 스냅샷 |
| `docker-compose.yml` | `NODES_EXCLUDE=[]` 추가 (§3-1, **아직 미적용 — 컨테이너 재생성 필요**) |
| `docs/architecture/ADR-023-AMENDMENT-A-Executor-Runtime.md` | 신규(Proposed) |

## 3. 검증 중 발견한 차단 사유 2건 (실측 증거)

### 3-1. ADR-023 Full Processing은 **한 번도 라이브에서 동작한 적이 없다**

- 라이브 인스턴스는 **23노드(ADR-022판)**였다. `phase-e.json` 파일만 28노드였다.
- 행동 증거: 전환 작업 전, `processing_input`을 담은 요청을 webhook에 보냈더니
  `processing_completed`가 아니라 `validation_passed`가 돌아왔다. 28노드판에서는
  `Respond PASS`가 연결되지 않은 고아 노드이므로 이 응답은 나올 수 없다.
- 28노드판을 임포트하자 **활성화가 실패**했다:
  `did fail with error: "Unrecognized node type: n8n-nodes-base.executeCommand"`.
  n8n **2.29.9**는 `executeCommand`를 기본 비활성화한다(`disabled-nodes-v2`
  breaking change). 해제 수단은 환경변수 `NODES_EXCLUDE=[]` 뿐이다.

### 3-2. n8n 컨테이너에는 Python도 `NAE/` 소스도 없다

ADR-023 §4의 커맨드는
`source ~/envs/dbma311/bin/activate && python -m NAE.pipeline.registration.cli_driver ...`
인데,

- `docker exec dbma_n8n command -v python3 python` → **없음**
- 컨테이너 마운트는 `/automation`(=`.automation/`) 하나뿐 — 프로젝트 루트,
  `NAE/` 패키지, `~/envs/dbma311` 전부 컨테이너에 존재하지 않는다(그건 호스트 경로다)

즉 `NODES_EXCLUDE=[]`를 켜도 이 커맨드는 성공할 수 없다. ADR-023 감사의 19개
서브테스트는 `cli_driver`를 **호스트에서 직접 실행**하고 `phase-e.json`을
**파일로 파싱**해 검증한 것이며, **n8n → cli_driver 호출 leg 하나만 미검증**이었다.
cli_driver 자체의 exit code 계약·state mapping·import 경계는 그 증거로 유효하다.

→ Architecture Freeze Rule에 따라 임의로 실행 경로를 바꾸지 않고
`ADR-023-AMENDMENT-A`(Proposed)를 작성해 **Option A(호스트 실행자, CUE 권고) /
Option B(컨테이너 보강)** 선택을 요청한다.

### 3-3. 롤백 및 원복 확인

28노드 임포트로 webhook이 일시적으로 등록 해제됐다(활성화 실패). 즉시
23노드 스냅샷을 재임포트·재발행하여 복구했고, 회귀로 확인했다.

- `Cycle 131: 2026-08-15T06:54:34Z, 7/7 PASS`
- n8n 볼륨 백업: `backups/n8n/dbma_n8n_data_20260815_014139_before_adr023_import.tar.gz`

## 4. C1에게 발행한 Task Order — **0건 (의도적)**

- ADR-023 Amendment A가 **Proposed**이므로, 이를 근거로 구현 명령을 내리는 것은
  Evidence Before Promotion Rule 위반이다. 승인 후 발행한다.
- C1은 현재 ADR-024 NAE Retrieval Bridge 구현 중이다(`NAE/retrieval_adapter.py`
  01:32에 수정됨, `bridge_query()`/mapping/timeout 구현 진행 중). 명령서 §9에 따라
  **중단시키지 않았고, 같은 파일을 건드리지 않았다.**

## 5. 실제 test 결과

| 항목 | 결과 |
|---|---|
| ADR-022 회귀 (7 시나리오) | **7/7 PASS** (Cycle 131) |
| 큐 러너 — validation 경로 | **PASS** — `NSQ-SMOKE-1786776027`, 라이브 webhook 200, task 파일 `VALIDATION_PASSED`, evidence 1줄 기록 확인 |
| 큐 러너 — 실패 라우팅 | **PASS** — webhook 미등록(404) 상황에서 응답을 신뢰하지 않고 `review-queue/`로 이동 + 리뷰 노트 생성 |
| 큐 러너 — production boundary 가드 | 매 task 전후 SHA256 비교, 위반 0건 |
| ADR-023 full processing 경로 | **미실행** (§3 사유) |

## 6. Evidence 위치

- 실행 로그: `.automation/night-shift/logs/night-shift.log`
- 리뷰 큐 샘플: `.automation/review-queue/NSQ-FAILROUTE-1786776386.review.md`
- 회귀: `.automation/evidence/night-shift/cycle-summary.log` (Cycle 131)
- 라이브 워크플로우 스냅샷: `.automation/evidence/_live_export_check.json`
- 롤백 스냅샷: `.automation/workflows/phase-e-adr022-23node-rollback.json`
- 보류된 등록 Task Order 10건: `.automation/night-shift/queue-pending-approval/`

## 7. 현재 NAE Production 진행 단계

| 단계 | 상태 |
|---|---|
| ADR-021 Source Registration | Approved, 구현 완료 |
| ADR-022 Automation State Machine | Approved, **라이브 가동 중** |
| ADR-023 Full Processing | Approved(문서) / **미가동**(실행 환경) — Amendment A 승인 대기 |
| ADR-024 Retrieval Bridge | Proposed, **C1 구현 진행 중** |
| RAW 코퍼스 등록 | 10개 item(Fuller Vol1-8, Hiscox, Dagg) Task Order 생성 완료, **보류** |

## 8. 다음 자동 실행 작업 (승인 즉시)

1. `docker compose up -d n8n` — `NODES_EXCLUDE=[]` 적용
   (**이 세션의 샌드박스가 컨테이너 재생성을 차단해 CUE가 실행하지 못했다**)
2. ADR-023 Amendment A에서 Option A/B 택일
3. Option A라면 추가 구현 없이 즉시:
   `python3 .automation/night-shift/run_night_shift.py --watch 60`
4. `queue-pending-approval/`에서 1건을 `queue/`로 이동 → 파일럿 등록 1건 실행 →
   증거 검증 → 나머지 9건 순차 자동 실행
