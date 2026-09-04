# CUE 최종 승인 — ADR-021 Pilot Phase B~D

- task_id: ADR-021-PILOT-001
- reviewer: CUE
- date: 2026-08-13
- production_mutation: false

## 판정: **APPROVED**

`.automation/workflows/ADR-021-PILOT-PHASE-B-D.json`(n8n `export:workflow` 실제 산출물, workflow ID `dbmaAutomationTest01`, canonical Pilot workflow)이 5종 케이스 전부 명확하고 구분되는 응답을 실제 실행으로 반환함을 CUE가 독립적으로 재현·확인했다.

## 최종 검증 결과 (실행 원문)

Workflow Functional Tests(5종, 워크플로우 내부에서 도달·처리됨):

| # | 케이스 | 응답 | HTTP |
|---|---|---|---|
| 1 | 정상 JSON | `{"status":"validated","task_id":"ADR-021-PILOT-001","mode":"TEST_ONLY","production_mutation":false,"note":"Pilot PASS does NOT authorize Full Processing"}` | 200 |
| 2 | 필수 필드 누락 | `{"status":"validation_failed","errors":"missing field: state,...","production_mutation":false}` | 200 |
| 3 | 타입 오류 | `{"status":"validation_failed","errors":"production_mutation must be false in PILOT phase,evidence must be an array","production_mutation":false}` | 200 |
| 4 | 파일 없음 | `{"status":"file_error","message":"No file(s) found","production_mutation":false}` | 200 |
| 5 | Empty file | `{"status":"validation_failed","errors":"missing field: schema_version,...(전체 10개 필드 누락)","production_mutation":false}` — Extract From File의 `fromJson`이 빈 문자열을 `{}`로 처리(moveTo.operation.js), 이후 Code 노드가 필수 필드 전부 누락으로 정상 FAIL 판정 | 200 |

HTTP Ingress Test(워크플로우 도달 전, n8n 코어 미들웨어 레벨에서 별도로 처리됨 — workflow-level 5종과 혼동하지 않도록 구분):

| # | 케이스 | 응답 | HTTP |
|---|---|---|---|
| 6 | Malformed JSON body | `{"code":422,"message":"Failed to parse request body",...}` (n8n core `body-parser.js`가 워크플로우 도달 전에 차단) | 422 |

**Silent Failure(HTTP 200 + 빈 바디) 완전히 해소됨** — 이전 REJECT의 핵심 사유가 실행으로 해결 확인됨. 6종(workflow 5 + ingress 1) 전부 명확하고 구분되는 응답.

## 이번 라운드에서 CUE가 추가로 발견/수정한 결함 (C1 미발견분)

C1이 Extract From File(`binaryPropertyName`/`destinationKey`)과 IF(`conditions.boolean` + `operation` 문자열) 수정까지는 올바르게 완료했으나, 그 다음 단계에서 아래 결함이 남아 있었다. CUE가 격리된 디버그 워크플로우로 각각 실행 재현 후 확정·수정:

1. **Respond to Webhook — PASS/ERROR의 `respondWith` 값이 `"expression"`으로 되어 있었음** — 이런 값은 n8n에 존재하지 않는다(유효값: json/text/jwt/binary/redirect/allIncomingItems/firstIncomingItem/noData). 실제 에러: `The Response Data option "expression" is not supported!`. `"json"`으로 수정.
2. **`responseBody` 필드에 `{{ }}` 표현식이 있었지만 값 앞에 `=`가 없어 n8n이 표현식으로 인식하지 못함** — 문자열이 그대로(`"{{$json.task.task_id}}"`) 응답에 찍혔다. 값 앞에 `=`를 붙여 mixed-expression으로 평가되도록 수정 (PASS/FAIL/ERROR 3개 노드 전부).
3. **ERROR 노드가 `$json.error?.node?.name` / `$json.error?.message` 같은 객체 경로를 가정했지만, 실제 Read/Write Files from Disk의 에러 출력은 `$json.error`가 평문 문자열**(`"No file(s) found"`)임을 실행으로 확인. `message: "{{$json.error}}"`로 단순화해 실제로 원인 메시지가 응답에 담기도록 수정.

세 건 모두 "노드 이름/문서가 아니라 실제 실행으로 증명"하는 방식으로 확정했으며, 손작성 JSON을 그대로 신뢰하지 않고 매 수정마다 격리 워크플로우로 먼저 검증한 뒤 canonical 워크플로우에 반영했다.

## Governance 체크리스트 최종 확인

| 항목 | 확인 |
|---|---|
| schema.json 수정 | 미수정 (읽기 전용 유지) |
| state enum 확장(Phase E) | 보류 유지 |
| PASS 뒤 Production mutation 노드 연결 | 없음 (workflow export로 확인, Respond 노드에서 전부 종료) |
| production_mutation: false 하드코딩 | 5개 응답 전부 하드코딩 값, 동적 계산 없음 |
| fileSelector 파라미터화 | `/automation/tasks/{{task_id}}.json`, 고정 글롭 아님 |
| On Error: Continue 배선 | Read/Write Files, Extract From File 양쪽 error output → 전용 Respond ERROR로 연결 확인 |
| 테스트 픽스처 잔존 여부 | `_c1_test/`, `test-cases/`(저장소 루트+`.automation/tasks/` 하위 잔존분) CUE가 전량 삭제 |

## 정리(Cleanup) 내역

- CUE가 검증 과정에서 만든 임시 디버그 워크플로우 3개(`cueContractTest01`은 이전 라운드, `cueDebugTest01`, `cueIfDebugTest01`, `cueErrDebugTest01`) 전부 unpublish + DB row 삭제 + 재시작으로 원복
- C1이 저장소 루트/`.automation/tasks/`에 남긴 테스트 픽스처 폴더(`_c1_test/`, `test-cases/`) 삭제
- `.automation/workflows/ADR-021-PILOT-PHASE-B-D.json`을 실제 활성 워크플로우의 `export:workflow` 산출물로 교체 저장 (이제 이 파일이 손작성이 아닌 실행 검증된 canonical 버전)
- `.automation/workflows/test-phase-b-d.sh`를 API 키 불필요 버전으로 재작성(실제 워크플로우는 `authentication: none`이므로 API 키가 애초에 불필요했음), 5종 케이스 모두 통과 확인 후 픽스처 자동 정리

## Workflow Inventory (승인 이후, 사용자 승인 하에 정리 완료)

| ID | 이름 | active | 판정 | 조치 |
|---|---|---|---|---|
| `fS6HDuv0D8uIbl88` | dbma | true | Pilot과 무관(별도 production 워크플로우) | 유지 |
| `aYV91ZBOXfqhxI5o` | DBMA — Agent Orchestrator | false | Pilot과 무관 | 유지 |
| `XzQ8oGucgAfw1V7m` | DBMA-AUTOMATION-TEST-001 | false | Pilot 초기 테스트 잔재, superseded | **삭제** |
| `uv1WoxZ4dLEHPZjJ` | DBMA-AUTOMATION-TEST-002 | false | Pilot 초기 테스트 잔재, superseded | **삭제** |
| `CTTcuMcQQvnK0I19` | DBMA Automation TEST | false | Phase A만 구현된 구버전, superseded | **삭제** |
| `dbmaAutomationTest01` | **DBMA Automation TEST (Phase B~D)** | **true** | **Canonical, APPROVED** | 유지 |

사용자 명시적 승인(2026-08-13) 하에 superseded 3개를 DB에서 완전 삭제, `docker restart`로 반영 확인. 삭제 후 canonical workflow 정상 동작 재확인(`{"status":"validated",...}` 200). 최종 n8n 워크플로우 목록: `dbma`, `DBMA — Agent Orchestrator`, `DBMA Automation TEST (Phase B~D)` 3개만 존재 — "One Pipeline, One Config, One Execution State" 원칙 충족.

## 최종 판정

**STATUS: APPROVED.** Mandatory Workflow 완료: C1 Build → CUE Audit → C1 Correct → CUE Re-audit(REJECT) → C1 Correct → CUE Re-audit(추가 결함 3건 발견·CUE 직접 수정·재검증) → **CUE Approve** → Workflow Inventory 정리(superseded 3개 삭제).

```
ADR-021 Pilot Phase B–D
Status: APPROVED
Canonical Workflow: DBMA Automation TEST (Phase B~D) (dbmaAutomationTest01)
Execution: VERIFIED
Binary Contract: VERIFIED
Extract Contract: VERIFIED
IF Contract: VERIFIED
Validation: VERIFIED
Error Handling: VERIFIED
Silent Failure: ELIMINATED
Workflow Inventory: CLEANED (3 superseded workflows deleted)
Production Mutation: FORBIDDEN / NOT APPROVED
Phase E: DEFERRED
Full Processing: NOT APPROVED
```

Pilot PASS는 Full Processing 승인이 아니다. 다음 단계(Phase E 상태 전이 확장, 또는 Full Processing 검토)는 별도 ADR/작업 지시가 필요하다.
