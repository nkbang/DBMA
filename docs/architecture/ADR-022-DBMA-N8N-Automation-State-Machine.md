---
title: "ADR-022: DBMA n8n Automation Task State Machine (Pilot Phase E)"
category: architecture
based_on:
  - .automation/PRODUCTION_RULES.md
  - .automation/tasks/schema.json
  - .automation/audit/ADR-021-PILOT-001-CUE-AUDIT-PHASE-B-D.md
  - .automation/audit/ADR-021-PILOT-001-CUE-REAUDIT-PHASE-B-D-REJECTED.md
  - .automation/audit/ADR-021-PILOT-001-CUE-FINAL-APPROVAL.md
  - docs/architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md (§10, namespace 분리 선례)
created: 2026-08-13
revised: 2026-08-13 (CUE Review 1차 반영 — IDLE 제거, namespace 분리, state
  명칭 충돌 해소, idempotency conflict 규칙 추가)
revised_2: 2026-08-13 (CUE Review 2차 반영 — schema 1.1.0 JSON Schema diff
  확정, transition_id uniqueness scope 명확화)
scope: `.automation/tasks/*.json`의 신규 `automation` 하위 객체(state,
  failure_code) 확장. Phase B~D에서 승인된 워크플로우
  (`DBMA Automation TEST (Phase B~D)`, workflow id `dbmaAutomationTest01`)의
  기존 노드는 이 ADR로 재작업하지 않음. NAE Source Registration state
  machine(ADR-021 §10, `NAE/pipeline/registration/state.py`)과
  ADR-020 `ProcessingState`는 이 ADR과 물리적·개념적으로 완전히 분리—
  무변경. Retrieval Engine, TSU Pipeline, RAW 데이터, 기존 Production
  Registry 무관.
---

# ADR-022: DBMA n8n Automation Task State Machine (Pilot Phase E)

| | |
|---|---|
| Status | **Approved** (2026-08-14, Rev. Bang 최종 승인. §17 승격 조건 4개 전부 충족 — `.automation/audit/ADR-022-CUE-FINAL-APPROVAL.md` 참고) |
| Approved 범위 | `RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`(human trigger)까지. idempotency, payload conflict detection, transition_id, evidence 기록, race-condition protection, NAE state isolation 포함 |
| Approved 범위 아님 | `VALIDATION_PASSED → PROCESSING → COMPLETED`, Production Mutation. Full Processing 운영 승인이 아니며, 별도 ADR + CUE Approval Gate 필요 |
| Date | 2026-08-13 |
| Deciders | CUE (초안 + Review), Rev. Bang (승인 대기) |
| Supersedes | — |
| Extends | `.automation/tasks/schema.json` v1.0.0 (신규 `automation` 하위 객체 추가, additive) |
| Superseded by | — |
| Does NOT extend | `docs/architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md` §10의 NAE Registration State Machine(`DISCOVERED → REGISTERED → RAW_PRESERVED → VALIDATED → EXTRACTED → QUALITY_PASSED`), ADR-020 `ProcessingState`. 이 ADR은 그 둘과 **이름이 겹치는 상태값이 있더라도 의미·저장소·authority가 완전히 다른 별개의 state machine**을 정의한다(§3). |
| 명명 규약 참고 | 이 문서가 다루는 자동화 Pilot의 task_id는 `ADR-021-PILOT-001`이지만, 이는 실제 `ADR-021`(NAE Source Registration, Approved)과 **무관한 별개의 task_id 문자열**이다. 이 ADR은 실제 ADR 번호 계열에 맞춰 `ADR-022`로 신규 발번한다. `docs/architecture/ADR-021-PILOT-SPECIFICATION.md`(NAE Human Review Disposition v2 Pilot)도 이 자동화 작업과 무관한 별개 문서다. **향후 신규 automation task_id는 ADR 번호를 포함하지 않는 형식(예: `DBMA-N8N-000001`, `automation-20260814-0001`)을 권장한다** — 기존 `ADR-021-PILOT-001`은 이미 evidence/audit 문서 전체에서 참조 중이므로 소급 변경하지 않는다. |

---

## 1. Status

Proposed. C1 구현 착수 전, CUE가 state machine 계약을 먼저 확정하기 위한 초안이다. CUE 1차 Review(본 리비전)에서 4개 필수 수정과 5개 권장사항을 반영했다. 이 ADR이 Approved로 승격되기 전까지 C1은 `.automation/tasks/schema.json`이나 관련 워크플로우 로직을 변경하지 않는다(Architecture Freeze Rule 및 Evidence Before Promotion Rule 적용 대상).

## 2. Context

ADR-021-PILOT-001(n8n Automation Pilot) Phase B~D가 CUE 승인을 받았다(`.automation/audit/ADR-021-PILOT-001-CUE-FINAL-APPROVAL.md`). 승인 범위는 다음으로 한정된다:

```
Webhook → Read File → Extract → Schema Validation → PASS/FAIL/ERROR Respond
```

이 범위에서 `.automation/tasks/schema.json`의 `state` 필드는 예시값 `"IDLE"` 하나만 존재하며, enum이나 전이 규칙이 정의되어 있지 않다.

Rev. Bang이 이제 Phase E(상태 전이) 검토를 요청했다. Phase B~D 구현 과정에서 다음이 반복적으로 드러났다:

- n8n의 실제 runtime contract(파라미터 이름, 에러 출력 구조, 표현식 문법)는 노드 이름이나 문서만으로는 예측 불가능했고, 매번 실행으로만 확정할 수 있었다(`readWriteFiles`→`readWriteFile` 오타, `destinationOutputField`→`destinationKey`, IF `operation` 객체→문자열, `respondWith:"expression"` 존재하지 않는 값, `responseBody`의 `=` 접두사 누락, `$json.error`가 객체가 아닌 문자열 등 6건 전부 실행 재현으로만 발견됨).
- 따라서 Phase E도 workflow 구현을 먼저 만들고 나중에 state를 끼워 맞추는 방식으로 가면 동일한 시행착오가 재발할 가능성이 높다.

CUE Review에서 추가로 발견된 context: **`ADR-021` §10에 이미 별도의 state machine이 존재한다** — NAE Source Registration의 `DISCOVERED → REGISTERED → RAW_PRESERVED → VALIDATED → EXTRACTED → QUALITY_PASSED`(저장소: `NAE/pipeline/registration/state/registration_state.json`, ADR-020의 `incremental_state.json`과도 물리적으로 분리). 이 선례는 "이름이 비슷한 state machine이라도 파일/네임스페이스를 완전히 분리한다"는 이 저장소의 기존 관행이며, ADR-022도 동일 관행을 따른다(§3).

## 3. Problem

state 전이를 도입하려면 최소한 다음이 선결되어야 하는데, 현재 전혀 정의돼 있지 않다:

1. `state` enum의 authority — 누가, 어디서 정의하고 바꾸는가
2. **이 state machine이 ADR-021의 NAE Registration State Machine과 이름/의미가 충돌하지 않는가** (CUE Review에서 최우선 governance point로 지적됨)
3. 허용된 전이 경로와 금지된 전이 경로
4. 동일 `task_id`가 중복 요청됐을 때, 그리고 **동일 `task_id`에 다른 payload가 온 경우** state가 깨지지 않는가(idempotency)
5. `FAILED` 상태에서 재처리가 가능한가, 가능하다면 어떤 경로로
6. state mutation과 production content mutation의 경계
7. 모든 전이가 evidence로 남는가, current state와 history가 구분되는가

## 4. Decision

`.automation/tasks/schema.json`에 **신규 하위 객체 `automation`**을 additive로 추가하고(§13), 그 안에 명시적 enum `state`와 `failure_code`를 정의한다. 이 state machine은:

- **NAE Registration State Machine(ADR-021 §10)을 대체하거나 재정의하지 않는다.** 완전히 별개의 lifecycle — "n8n automation 요청이 파일을 읽고 검증하는 과정"의 상태이지, "신학 원문이 등록·보존·추출되는 과정"의 상태가 아니다.
- 저장소도 분리한다: automation state는 `.automation/tasks/*.json`의 `automation` 객체 + `.automation/evidence/`(append-only transition log)에만 존재하며, `NAE/pipeline/registration/state/registration_state.json`이나 ADR-020 `incremental_state.json`을 전혀 참조·수정하지 않는다.
- n8n 워크플로우 자체(Phase B~D에서 승인된 노드 구성)는 이 ADR로 재작업하지 않는다 — state 기록은 그 뒤에 별도 단계로 덧붙이는 확장이다(§14).

## 5. State Model

**CUE Review 반영: `IDLE` 제거.** `IDLE`은 task의 lifecycle 상태가 아니라 "아직 task가 존재하지 않는 시스템 준비 상태"이므로 enum에서 제외한다. task 파일은 최초 생성 시점에 이미 `RECEIVED`로 기록되거나, 파일만 있고 `automation` 객체 자체가 아직 없는 상태(= state 미부여, "no transition yet")로 둔다.

**CUE Review 반영: `VALIDATED` → `VALIDATION_PASSED`로 명칭 확정.** ADR-021의 NAE Registration State Machine도 `VALIDATED`라는 값을 쓰기 때문에, 같은 문자열을 두 개의 다른 state machine이 공유하면 로그·감사에서 혼동될 위험이 크다(§3-2, §7). Phase B~D의 실제 runtime 응답이 이미 `status: "validated"` / `"validation_failed"` 형태였으므로 `VALIDATION_PASSED`/`FAILED`+`failure_code: VALIDATION_FAILED`로의 매핑은 기존 semantics와 자연스럽게 맞는다.

```
RECEIVED → VALIDATION_PASSED → [PROCESSING → COMPLETED]   (PROCESSING/COMPLETED는 Future — §8)
RECEIVED → FAILED
VALIDATION_PASSED → FAILED
FAILED → RETRY_PENDING → [PROCESSING]                       (〃)
```

| State (namespace: `automation.state`) | 의미 | 진입 조건 |
|---|---|---|
| `RECEIVED` | Webhook이 요청을 받아 파일을 찾음 | Read/Write Files 성공 |
| `VALIDATION_PASSED` | Schema Validation PASS | Code 노드 `valid:true` |
| `FAILED` | 임의 단계에서 실패, terminal이 아님(재시도 가능). 원인은 `automation.failure_code`에 별도 기록(§6) | 파일 없음/파싱 실패/validation FAIL |
| `RETRY_PENDING` | 재처리 대기, `FAILED`에서만 진입 | 사람의 명시적 재시도 지시 |
| `PROCESSING` (Future) | 실제 처리 진행 중 | 별도 ADR 승인 후에만 코드 활성화 |
| `COMPLETED` (Future, terminal) | 처리 완료 | 별도 ADR 승인 후에만 코드 활성화 |

**이번 ADR의 실제 구현 범위는 `RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`까지다.** `PROCESSING`, `COMPLETED`는 vocabulary(값 존재)만 예약하고, 실제로 그 상태로 전이시키는 코드는 이 ADR로 구현하지 않는다(§8, §12).

## 6. Failure Code (신규, CUE Review 권장사항 반영)

state는 lifecycle만 표현하고, 실패 원인은 별도 필드로 분리한다:

```json
{
  "automation": {
    "state": "FAILED",
    "failure_code": "FILE_ERROR"
  }
}
```

| `failure_code` | 대응하는 Phase B~D 응답 |
|---|---|
| `VALIDATION_FAILED` | `status: "validation_failed"` |
| `FILE_ERROR` | `status: "file_error"` |
| `PARSE_ERROR` | HTTP 422 ingress-level 거부(malformed JSON, Phase B~D §Test 6) — 이 경우는 애초에 워크플로우에 도달하지 못하므로 `automation.state`가 기록되지 않을 수 있음(도달 전 실패, §10에서 별도 처리) |
| `TASK_ID_PAYLOAD_CONFLICT` | §7 idempotency 충돌 (신규) |

`state`를 원인별로 쪼개지 않고(`VALIDATION_FAILED_STATE` 같은 state를 만들지 않고) `FAILED` 하나로 통일 + `failure_code`로 원인을 구분하는 것은, 향후 실패 원인이 늘어나도 **allowed transition matrix(§9)를 다시 손댈 필요가 없게** 하기 위함이다.

## 7. Idempotency (CUE Review 반영 — payload conflict 규칙 추가)

동일 `task_id`로 webhook이 중복 호출됐을 때, `automation.evidence`의 마지막 기록된 `payload_hash`(요청 body의 SHA256)를 기준으로 판단한다:

| 상황 | 처리 |
|---|---|
| 동일 `task_id` + 동일 `payload_hash`, 현재 state가 이미 `RECEIVED` 이상 | **no-op** — 새 전이를 만들지 않고 현재 state를 그대로 반환. 중복 요청 자체는 evidence에 `duplicate_of: <transition_id>`로 기록(전이는 아님) |
| 동일 `task_id` + **다른** `payload_hash` | **거부**, `automation.state`는 변경하지 않고 응답에 `"error": "TASK_ID_PAYLOAD_CONFLICT"` 반환. 이 상황 자체를 evidence에 기록(§11) |
| 금지된 전이를 요구하는 요청(§9 whitelist에 없음) | 거부 + 이상 evidence 기록(§9) |

동시 요청(race condition)에 대한 lock 전략은 §14 구현 세부사항이며, 최소한 **state 순서를 위반하는 쓰기를 거부**하는 방식이어야 한다(예: `COMPLETED` 이후 `RECEIVED` 쓰기 요청이 오면 무시 + 이상 evidence 기록).

## 8. Retry / Recovery

- `FAILED → RETRY_PENDING`은 **사람의 명시적 지시로만** 발생한다. n8n 워크플로우가 자동으로 `FAILED`를 `RETRY_PENDING`으로 승격하는 로직은 이번 ADR에서 금지한다(Production Rule 5: governance-sensitive 작업에는 human approval 경로가 남아있어야 함).
- `RETRY_PENDING → PROCESSING` 실제 코드는 별도 ADR(Full Processing 승인) 없이는 구현하지 않는다.

## 9. Transition Matrix (신규, CUE Review 권장사항 반영 — Allowed/Forbidden 통합 표)

| From | To | Allowed | Actor | 비고 |
|---|---|---|---|---|
| (없음, 신규 task) | `RECEIVED` | ✅ | Automation | Read/Write Files 성공 |
| `RECEIVED` | `VALIDATION_PASSED` | ✅ | Automation | Code 노드 `valid:true` |
| `RECEIVED` | `FAILED` | ✅ | Automation | `failure_code` 필수 동반 |
| `VALIDATION_PASSED` | `FAILED` | ✅ | Automation | 이 경로가 실제로 발생하는 시나리오는 이번 구현 범위(§5)에 없음 — PROCESSING이 없으므로. 향후 PROCESSING 단계 실패 대비 vocabulary만 예약 |
| `FAILED` | `RETRY_PENDING` | ✅ | **Human만** | §8 |
| `RETRY_PENDING` | `RECEIVED` | ✅ | Human 지시에 따른 재실행 | 재실행은 새 execution으로 처리, 동일 task_id 재사용 |
| `VALIDATION_PASSED` | `PROCESSING` | ⏸ Future | Future ADR | 이번 ADR로 구현 금지 |
| `PROCESSING` | `COMPLETED` | ⏸ Future | Future ADR | 〃 |
| `PROCESSING` | `FAILED` | ⏸ Future | Future ADR | 〃 |
| `RETRY_PENDING` | `PROCESSING` | ⏸ Future | Future ADR | 〃 |
| `COMPLETED` | 임의 상태 | ❌ | — | terminal, 모든 전이 금지 |
| `RETRY_PENDING` | `FAILED` | ❌ | — | RECEIVED를 거치지 않고 직행 금지 |
| 동일 `task_id`, 동일 payload | (전이 없음) | no-op | — | §7 |
| 동일 `task_id`, 다른 payload | (전이 없음) | ❌ `TASK_ID_PAYLOAD_CONFLICT` | — | §7 |
| 표에 없는 임의 전이 | — | ❌ (기본 거부) | — | whitelist 방식 — 명시된 것만 허용 |

구현체는 이 표에 `✅`로 명시된 것만 통과시키고, `⏸ Future`는 이번 ADR 구현 범위에서 **코드 자체가 존재하지 않아야** 한다(§12).

## 10. Error Semantics

Phase B~D 감사에서 이미 확정된 원칙을 그대로 승계한다: 모든 실패는 **원인이 구분되는 명시적 응답**이어야 하고, HTTP 200 + 빈 바디 같은 침묵 실패는 금지한다.

malformed JSON(HTTP 422, n8n core body-parser 레벨 거부)처럼 **워크플로우 자체에 도달하지 못하는 실패**는 `automation.state`를 아예 기록하지 않는다(해당 task_id의 task 파일 자체를 찾기 전에 거부되므로 어느 task에 귀속시킬 state가 없음) — 이는 침묵 실패가 아니라 ingress 레벨에서 이미 명시적 422를 반환하므로 §10 원칙 위반이 아니다. 단, 향후 모니터링을 위해 ingress-level 거부도 별도 로그(워크플로우 외부, 웹서버 access log 수준)로는 남아야 한다는 점을 기록해둔다(이번 ADR 구현 범위 밖, 참고용).

## 11. Audit Evidence — Transition ID (신규, CUE Review 1차 권장사항 반영, 2차 Review로 uniqueness scope 확정)

**Uniqueness scope(CUE Review 2차 반영):** `transition_id`는 **`task_id` + 해당 task 내 순번**의 조합으로 유일성을 보장한다 — `task_id` 자체가 이미 시스템 전역에서 유일하다고 가정하므로(기존 `.automation/tasks/{task_id}.json` 1:1 대응 구조, §7 idempotency의 전제와 동일), 조합 `"{task_id}#{순번:04d}"`는 자동으로 전역 유일이 된다. 순번은 해당 task_id 내에서 1부터 시작하는 단조 증가 정수이며, `.automation/evidence/` 로그에 이미 기록된 해당 task_id의 마지막 순번 + 1로 결정한다(append 시점에 evidence 로그 자체를 조회해 다음 순번 산정 — 별도 카운터 저장소 불필요).

```
transition_id = "{task_id}#{순번:04d}"
예: "ADR-021-PILOT-001#0001", "ADR-021-PILOT-001#0002"
```

동시 요청으로 순번이 경합할 경우(§7 race condition과 동일 문제), 구현은 `.automation/evidence/` append를 원자적 단일 쓰기로 처리하거나, 파일 lock(`.automation/locks/`, 기존 디렉터리 재사용)으로 순번 산정 구간을 보호해야 한다 — 이번 ADR 범위에서는 원칙만 정의하고 구체적 lock 메커니즘은 C1 구현 시 §14 배선과 함께 CUE가 재감사한다.

모든 state 전이는 다음 필드를 `.automation/evidence/`에 append-only로 기록한다:

```json
{
  "transition_id": "ADR-021-PILOT-001#0002",
  "task_id": "ADR-021-PILOT-001",
  "from": "RECEIVED",
  "to": "VALIDATION_PASSED",
  "failure_code": null,
  "actor": "automation",
  "payload_hash": "<sha256>",
  "execution_id": "<n8n execution id>",
  "timestamp": "2026-08-13T12:00:00Z",
  "reason": "schema validation passed"
}
```

**Current state와 history 분리(CUE Review 권장사항 반영):** `automation.state`(task 파일 내부)는 **가장 최근 state만** 담는 필드이고, 전체 이력은 `.automation/evidence/`의 append-only `transition_id` 로그가 단일 authority다. task 파일의 `automation.state`는 매 전이마다 overwrite되지만, evidence 로그는 절대 overwrite/삭제하지 않는다 — ADR-021 §10이 실패 상태를 별도 exception queue로 분리해 append 방식으로 유지하는 것과 동일한 원칙이다.

기존 `task.evidence` 배열(schema.json v1.0.0, 자유 형식)과는 별도 채널로 유지한다 — 기존 필드의 의미를 재정의하지 않는다.

## 12. Production Mutation Boundary

**State mutation ≠ Production content mutation.** 이 ADR이 승인되어 `RECEIVED → VALIDATION_PASSED/FAILED → RETRY_PENDING`이 구현되더라도:

- `.automation/tasks/*.json`의 `automation.state` 필드 갱신과 `.automation/evidence/`에의 append는 automation 메타데이터 쓰기이며, Production Rule 1("n8n MUST NOT mutate Production data")이 금지하는 "Production data"에 해당하지 않는다.
- `PROCESSING`, `COMPLETED`로의 실제 전이 코드(=태스크가 지시하는 실제 작업을 수행하는 로직)는 Retrieval Engine, TSU Pipeline, RAW 데이터 등 **진짜 Production 데이터에 닿을 가능성**이 있으므로, 이 ADR은 그 코드를 구현하지 않고 상태값의 존재만 정의한다(§9 Future 행). 실제 `PROCESSING` 로직은 별도 ADR + CUE Approval Gate + human approval 경로 설계가 선행되어야 한다.

## 13. Schema Compatibility

`.automation/tasks/schema.json`을 `1.0.0 → 1.1.0`으로 additive 변경한다.

### 13.1 JSON Schema diff (CUE Review 2차 반영 — 확정)

`.automation/tasks/schema.json`의 최상위 `properties`에 아래 블록을 **추가**한다(기존 프로퍼티는 한 글자도 수정하지 않음):

```json
{
  "properties": {
    "automation": {
      "type": ["object", "null"],
      "default": null,
      "description": "ADR-022 automation task lifecycle state. NAE Registration State(ADR-021 §10)와 무관한 별개 namespace.",
      "properties": {
        "state": {
          "type": ["string", "null"],
          "enum": [null, "RECEIVED", "VALIDATION_PASSED", "FAILED", "RETRY_PENDING", "PROCESSING", "COMPLETED"],
          "default": null,
          "description": "PROCESSING/COMPLETED는 §5 Future — 이번 ADR 구현 범위에서 이 값으로의 실제 전이 코드는 존재하지 않는다(값 자체만 예약)."
        },
        "failure_code": {
          "type": ["string", "null"],
          "enum": [null, "VALIDATION_FAILED", "FILE_ERROR", "PARSE_ERROR", "TASK_ID_PAYLOAD_CONFLICT"],
          "default": null,
          "description": "state가 FAILED일 때만 non-null. 그 외 state에서는 null이어야 한다(§13.2 상호 제약)."
        },
        "last_transition_id": {
          "type": ["string", "null"],
          "pattern": "^.+#[0-9]{4,}$",
          "default": null,
          "description": "§11 형식 \"{task_id}#{순번}\". 이 필드는 캐시일 뿐 authority가 아니다 — authority는 .automation/evidence/ 로그."
        }
      },
      "required": ["state", "failure_code", "last_transition_id"],
      "additionalProperties": false
    }
  }
}
```

**정책 확정(CUE Review 2차 요구사항 반영):**

| 정책 | 값 | 근거 |
|---|---|---|
| `additionalProperties` (automation 객체 내부) | `false` | 향후 임의 필드가 검증 없이 섞여 들어가는 것을 방지 — §6/§9에서 정의한 vocabulary 밖의 값은 스키마 레벨에서부터 거부 |
| `required` (automation 객체 내부) | `["state", "failure_code", "last_transition_id"]` | 3개 필드는 항상 키 자체는 존재하되 값은 `nullable` — "필드 누락"과 "아직 값 없음"을 구분하기 위함(Phase B~D Code 노드 검증 로직의 `missing field: X` 패턴과 일관) |
| `state`/`failure_code`/`last_transition_id`의 nullable 여부 | 셋 다 `["...", "null"]`로 **nullable 허용** | `automation` 객체 자체가 `null`이 아니라 존재하되 아직 전이가 없는 task(§13.2 신규 task 초기값)를 표현하기 위해 필요 |
| `automation` 객체 자체 | `["object", "null"]`, default `null` | 기존(v1.0.0) task 파일과의 하위호환 — `automation` 키가 아예 없거나 `null`이면 "automation lifecycle 진입 전" |
| `failure_code`가 non-null일 수 있는 조건 | `state === "FAILED"`일 때만 | JSON Schema 표준 `if/then`으로 강제 가능(§13.2에 별도 명시) — 이번 diff에는 서술만 포함, 실제 `if/then` 절 추가는 C1 구현 시 CUE가 재감사 |

### 13.2 상호 제약 (state ↔ failure_code)

```json
{
  "if": { "properties": { "automation": { "properties": { "state": { "const": "FAILED" } } } } },
  "then": { "properties": { "automation": { "properties": { "failure_code": { "not": { "const": null } } } } } },
  "else": { "properties": { "automation": { "properties": { "failure_code": { "const": null } } } } }
}
```

즉 `state !== "FAILED"`이면 `failure_code`는 반드시 `null`이어야 하고, `state === "FAILED"`이면 `failure_code`는 반드시 §6 enum 중 하나여야 한다. 이 제약은 §9 Transition Matrix의 "FAILED 전이는 failure_code 필수 동반"과 스키마 레벨에서 동일하게 강제된다.

### 13.3 기존 필드와의 관계

- **CUE Review 1차 반영 유지: automation state를 신규 최상위 필드가 아니라 `automation` 하위 객체로 격리**한다 — 기존 `state`(schema.json v1.0.0의 최상위 필드, 현재 예시값 `"IDLE"`)와 이름이 겹치는 문제를 원천 차단하고, NAE 쪽 metadata/state 의미와도 물리적으로 분리된 namespace임을 스키마 구조로 강제한다.
- 기존 최상위 `state` 필드(v1.0.0)는 **deprecated로 표시하되 삭제하지 않는다** — 하위호환. 신규 구현은 `automation.state`만 사용하고 최상위 `state`는 더 이상 갱신하지 않는다.
- 기존 필드(`owner`, `phase`, `requires_human_approval`, `evidence`, `audit`, `production_mutation`, `notes`)는 한 글자도 변경하지 않는다.
- 하위호환: 기존 task 파일(`ADR-021-PILOT-001.json`, 최상위 `state: "IDLE"`)은 `automation` 필드가 없는 상태(또는 `null`)로도 그대로 유효하다 — 소비자는 `automation` 필드 부재/`null`을 "아직 automation lifecycle 진입 전"으로 해석한다.

## 14. n8n Implementation Boundary

Phase B~D에서 승인된 워크플로우(`dbmaAutomationTest01`)의 기존 노드 체인은 변경하지 않는다. state 기록은 다음 중 하나로 **얹는다**(C1 구현 시 선택, CUE가 재감사):

- (a) 기존 워크플로우의 PASS/FAIL/ERROR Respond 노드 **직전**에 state-write 단계를 추가, 또는
- (b) 기존 워크플로우와 완전히 분리된 별도 워크플로우가 execution 로그/webhook 결과를 구독해 state를 기록

C1은 (a)/(b) 중 어느 쪽이든 Phase B~D 승인 워크플로우의 기존 노드(Read/Write Files, Extract From File, Code — Schema Validation, IF, 기존 3개 Respond 노드)의 **파라미터를 변경하지 않는다** — Phase B~D REJECT→APPROVE 왕복에서 소모한 비용을 반복하지 않기 위함이다.

## 15. Test Matrix

C1 구현 후 CUE가 재감사할 최소 케이스 (모두 **실행 재현**으로 검증 — Phase B~D와 동일 원칙, 문서/이름만으로 판단 금지):

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 신규 task, 정상 JSON | `RECEIVED → VALIDATION_PASSED`, evidence 2건(transition_id 2개) |
| 2 | 신규 task, validation 실패 | `RECEIVED → FAILED`(`failure_code: VALIDATION_FAILED`), evidence 2건 |
| 3 | 신규 task, 파일 없음 | `RECEIVED → FAILED`(`failure_code: FILE_ERROR`) |
| 4 | 동일 task_id + 동일 payload 중복 요청 | 새 전이 없음, state 불변, evidence에 `duplicate_of` 기록 |
| 5 | 동일 task_id + **다른** payload 재요청 | `TASK_ID_PAYLOAD_CONFLICT` 응답, state 불변, evidence 기록 |
| 6 | 금지된 전이 강제 시도(외부에서 `COMPLETED` 직접 쓰기 시도) | 거부 + 이상 evidence 기록 |
| 7 | `FAILED → RETRY_PENDING` (사람이 명시적으로 트리거) | 전이 성공, evidence에 트리거 주체(`actor: "human"`) 기록 |
| 8 | `FAILED → RETRY_PENDING`을 자동화가 스스로 트리거 시도 | 거부(§8 원칙 위반이므로 애초에 구현되지 않아야 함 — 코드 자체가 없어야 PASS) |
| 9 | NAE Registration State(`registration_state.json`)에 어떤 영향도 없는지 | 구현 전/후 해당 파일 SHA256 비교로 무변경 확인 |

모든 케이스에서 `production_mutation: false` 불변 확인, `PROCESSING`/`COMPLETED` 실제 코드가 이번 구현물에 전혀 존재하지 않음을 workflow export로 확인(코드가 없다는 것 자체가 이번 ADR 범위 준수의 증거).

## 16. Rollback

- `schema.json`을 `1.0.0`으로 되돌리는 것은 additive 변경(신규 `automation` 객체 추가)이었으므로 안전 — 신규 필드를 무시하면 기존 소비자에 영향 없음.
- state-transition 기록 계층(§14)을 비활성화해도 Phase B~D 승인 워크플로우는 독립적으로 계속 동작한다(§14에서 "얹는" 구조로 설계했기 때문).
- `automation.state`/`.automation/evidence/`를 전량 삭제해도 NAE Registration State(`registration_state.json`)나 ADR-020 `incremental_state.json`에는 어떤 영향도 없다(§4, §15-9로 검증).

## 17. CUE Approval Gate

```
CUE (이 문서, 소유)
 ├── state vocabulary (§5, §6)
 ├── transition matrix (§9)
 ├── governance (§8, §12)
 ├── schema authority (§13)
 ├── mutation boundary (§12)
 ├── namespace 분리 (§3, §4 — NAE Registration State와 무관함을 보장)
 └── acceptance criteria (§15)

C1 (구현, 소유)
 ├── n8n implementation (§14)
 ├── execution
 ├── testing (§15 실행)
 └── evidence collection (§11)

CUE
 └── independent re-audit (Phase B~D와 동일 방식: 실행 재현 기반, 문서/이름만으로 판단 금지)
```

**승격 조건(Evidence Before Promotion Rule):** 이 ADR은 (1) 구현 완료 (2) §15 Test Matrix 전부 실행 증거 제출 (3) CUE 독립 재감사 통과 (4) Rev. Bang 승인, 4개 전부 충족 시에만 Proposed → Approved로 승격한다. 그 전까지는 다른 구현의 근거로 쓰지 않는다.

**이 ADR이 승인되어도 `PROCESSING`/`COMPLETED`(Full Processing)는 여전히 승인되지 않는다.** 그건 별도 ADR의 범위다.
