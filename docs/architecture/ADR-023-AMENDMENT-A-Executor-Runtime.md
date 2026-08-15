---
title: "ADR-023 Amendment A: Full Processing Executor Runtime (Execute Command 실행 환경 정정)"
category: architecture
amends: docs/architecture/ADR-023-DBMA-N8N-Automation-Full-Processing.md (Approved, 2026-08-15)
created: 2026-08-15
author: CUE
scope_modified: docs/architecture/ only — 코드·워크플로우 무수정 (승인 전)
---

# ADR-023 Amendment A — Full Processing Executor Runtime

| | |
|---|---|
| Status | **Approved** (2026-08-15, Rev. Bang — "Option A를 승인해 주시면 됩니다" / "여기서 Option A를 승인" 채택 지시) |
| Amends | ADR-023 §4 (Execute Command 노드로 `cli_driver` 호출) |
| Trigger | 2026-08-15 CUE Night Shift 검증에서 ADR-023 Full Processing 경로가 **실행 환경상 작동 불가능**함을 실측으로 확인 |
| 영향 | ADR-023의 결정(“얇은 CLI 드라이버 1개만 추가, `register_source()` 무수정 호출”)은 유지. 그 드라이버를 **어디서 실행하는가**만 정정한다 |
| 채택 옵션 | **Option A — Host Executor.** n8n은 §2의 검증된 범위(수신·검증·상태 전이·증거 기록)만 계속 담당하고, `PROCESSING` 실행은 호스트에서 도는 얇은 실행자가 담당한다. 구현 착수 승인: Rev. Bang, 2026-08-15. Task Order: `.automation/requests/C1-TASK-ORDER-ADR023-AMENDMENT-A-HOST-EXECUTOR.md` |

---

## 1. Problem — 실측으로 확인된 2건

ADR-023은 Approved(2026-08-15)이지만, 그 Full Processing 경로는 **한 번도 n8n을
통해 실행된 적이 없다**. CUE가 2026-08-15 야간 검증에서 다음을 직접 확인했다.

### 1-1. `executeCommand` 노드가 n8n 2.x에서 기본 비활성

- 실측: 라이브 인스턴스 `n8n --version` = **2.29.9**
- 실측: 28-노드 워크플로우 활성화 시도 로그 —
  `Activation of workflow "Phase E State Machine" (9qIO3nFeWRia28Rb) did fail with
  error: "Unrecognized node type: n8n-nodes-base.executeCommand"`
- 원인: `@n8n/config` `NodesConfig.exclude` 기본값이
  `['n8n-nodes-base.executeCommand', 'n8n-nodes-base.localFileTrigger']`.
  n8n 2.0 breaking change(`disabled-nodes-v2`). 해제 수단은 **환경변수
  `NODES_EXCLUDE=[]` 뿐**이며 설정 파일 경로는 없다(`@Env('NODES_EXCLUDE')`).
- 결과: 이 노드를 포함한 워크플로우는 **활성화 자체가 실패**하고, webhook이
  등록되지 않는다.

### 1-2. n8n 컨테이너에 Python도 프로젝트 소스도 없다

ADR-023 §4가 지정한 커맨드:

```
source ~/envs/dbma311/bin/activate && python -m NAE.pipeline.registration.cli_driver --request-json /automation/tasks/<task_id>.json
```

- 실측: `docker exec dbma_n8n command -v python3 python` → **없음**
- 실측: 컨테이너에 `/automation`(=`.automation/`)만 마운트되어 있고 프로젝트
  루트·`NAE/` 패키지·`~/envs/dbma311` 가상환경은 **존재하지 않는다**
- 즉 `~/envs/dbma311`은 **호스트(macOS) 경로**이고, Execute Command 노드는
  **컨테이너 안에서** 실행된다 — 이 커맨드는 어떤 조건에서도 성공할 수 없다

### 1-3. 그래서 ADR-023 감사 증거는 무엇이었나

`.automation/audit/ADR-023-CUE-FINAL-AUDIT.md`의 19개 서브테스트는 `cli_driver`를
**호스트에서 직접 실행한 결과**와 `phase-e.json` **파일 파싱**(노드 수 28 등)으로
검증됐다. cli_driver 자체의 계약(exit code, state mapping, import 경계)은 그 증거로
유효하다. 검증되지 않은 것은 **n8n → cli_driver 호출 leg 하나**다.

---

## 2. Decision (제안)

ADR-023 §4의 “Execute Command 노드” 지정을 다음 중 하나로 정정한다.

### Option A — 호스트 실행자(Host Executor) 분리 **(CUE 권고)**

n8n은 ADR-022가 이미 검증한 범위(수신·검증·상태 전이·증거 기록)만 담당하고,
`PROCESSING` 실행은 호스트에서 도는 얇은 실행자
(`.automation/night-shift/run_night_shift.py`)가 담당한다. 실행자는 호스트의
`~/envs/dbma311` 환경에서 `cli_driver`를 그대로 호출하고, 결과를 다시 n8n에
상태 전이로 보고한다.

- 장점: 컨테이너에 Python/소스/RAW 코퍼스를 마운트하지 않아도 된다.
  `executeCommand`(임의 셸 실행)를 활성화하지 않아 **보안 표면이 늘지 않는다**.
  ADR-022의 검증된 워크플로우를 한 노드도 바꾸지 않는다.
- 단점: 실행 authority가 n8n 밖으로 나간다 — 실행자도 evidence-first 검증
  대상이 되어야 한다(이미 그렇게 구현됨).

### Option B — 컨테이너 실행 환경 보강

`NODES_EXCLUDE=[]`를 설정하고, 프로젝트 루트와 `NAE/corpus/raw`를 컨테이너에
마운트하고, 컨테이너 안에 NAE 의존성이 설치된 Python 환경을 만든다.

- 장점: ADR-023 §4의 원문 그대로 구현된다.
- 단점: n8n 컨테이너에 **임의 셸 실행 권한**이 열린다. Phase E webhook은
  `authentication: none`이므로, localhost에 접근 가능한 무엇이든 임의 명령을
  실행시킬 수 있게 된다. RAW 코퍼스를 컨테이너에 노출해야 한다. 컨테이너
  이미지에 Python 런타임을 추가로 관리해야 한다.

### 권고

**Option A**. ADR-023의 실질(“`register_source()`를 무수정으로 호출하는 얇은
드라이버 하나”)을 그대로 지키면서, 보안 표면과 컨테이너 복잡도를 늘리지 않는다.
Option B는 무인 야간 자동화에 임의 명령 실행 경로를 여는 결정이므로, 선택한다면
webhook 인증 추가가 **함께** 승인되어야 한다.

---

## 3. 이 Amendment가 바꾸지 않는 것

- `NAE/pipeline/registration/pipeline.py::register_source()` — 무수정
- `NAE/pipeline/registration/cli_driver.py`의 exit code 계약과 import 경계 — 유지
- ADR-022 state machine, idempotency, evidence 기록 — 무변경
- ADR-022 §8 “automation은 `FAILED → RETRY_PENDING`을 자동 승격하지 않는다” — 유지

## 4. 승인 조건

Rev. Bang이 Option A / Option B 중 하나를 선택해야 이 Amendment가 Approved가 되고,
그 후에야 C1 구현 작업 명령이 발행된다. 그때까지 ADR-023 Full Processing은
**미가동 상태로 유지**하고, `.automation/night-shift/queue-pending-approval/`의
10개 등록 Task Order는 **보류**한다.
