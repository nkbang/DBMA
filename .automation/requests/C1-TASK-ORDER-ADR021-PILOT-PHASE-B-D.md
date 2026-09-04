# C1 Task Order — ADR-021 Pilot Phase B~D 구현

**Task ID:** ADR-021-PILOT-001
**Task Order:** C1-TASK-ORDER-ADR021-PHASE-B-D
**Date:** 2026-08-13
**발주자:** CUE (Architecture/Governance/Independent Verification)
**대상:** C1 (implementation)
**참조 감사 문서:** `.automation/audit/ADR-021-PILOT-001-CUE-AUDIT-PHASE-B-D.md`

---

## 1. 배경

n8n Pilot 워크플로우("DBMA Automation TEST")는 현재 `Webhook → Read/Write Files from Disk → Respond`까지만 구현되어 있고, HTTP 200을 반환하지만 이는 "파일 접근 성공"만 증명하며 **파일 내용을 JSON으로 파싱하거나 schema를 검증하지 않는다.** CUE가 n8n 2.29.9 실제 소스코드와 격리된 테스트 워크플로우 실행으로 이를 증명했다(위 audit 문서 1~2, 7항).

C1은 이 워크플로우에 Phase B(JSON Parse) ~ D(Governance Gate)를 추가 구현한다.

## 2. 목표 구조

```
Webhook
   │
   ▼
Read/Write Files from Disk   (fileSelector를 body.task_id 기반으로 파라미터화)
   │  binary.data                         │ On Error: Continue (error output)
   ▼                                       │
Extract From File (fromJson)               │
   │  $json.task                          │ On Error: Continue (error output)
   ▼                                       │
Code — Schema Validation                   │
   │  $json.valid / $json.errors          │
   ▼                                       │
IF (valid === true)                        │
   │                          │            │
   ▼ TRUE                     ▼ FALSE      ▼ (모든 error 출력 분기 합류)
Respond PASS              Respond FAIL  ◄──┘
```

## 3. 노드별 구현 지시

### 3.1 Read/Write Files from Disk
- `fileSelector`: `={{ "/automation/tasks/" + $json.body.task_id + ".json" }}` (요청받은 task_id 하나만 읽도록 파라미터화. 현재처럼 `/automation/tasks/*` 고정 글롭 금지 — 다중 아이템 생성 방지)
- typeVersion: `1.1` (현재 값 유지)
- **On Error: Continue (using error output)** 로 설정하고, error 출력을 별도 브랜치로 빼서 FAIL Respond 노드에 연결

### 3.2 Extract From File
- Operation: **Extract From JSON** (`fromJson`)
- Input Binary Field: `data`
- Destination Output Field: `task`
- Options → Keep Source: `json`
- **On Error: Continue (using error output)** 설정, error 출력을 FAIL Respond 노드로 연결 (malformed JSON 대비)

### 3.3 Code — Schema Validation
아래 스크립트를 그대로 사용한다 (임의 변경/필드 추가 금지 — `.automation/tasks/schema.json`은 읽기 전용, 수정 대상 아님):

```js
const task = $json.task;
const required = [
  'schema_version','task_id','title','owner','state','phase',
  'requires_human_approval','production_mutation','evidence','audit'
];
const errors = [];

for (const key of required) {
  if (!(key in task)) errors.push(`missing field: ${key}`);
}
if (task.production_mutation !== false) {
  errors.push('production_mutation must be false in PILOT phase');
}
if (typeof task.audit !== 'object' || !('status' in (task.audit||{}))) {
  errors.push('audit structure invalid');
}
if (!Array.isArray(task.evidence)) {
  errors.push('evidence must be an array');
}

return [{
  json: {
    valid: errors.length === 0,
    errors,
    task
  }
}];
```

### 3.4 IF 노드
- 조건: `{{ $json.valid }}` === `true`

### 3.5 Respond to Webhook — PASS (IF TRUE)
```json
{
  "status": "validated",
  "task_id": "{{$json.task.task_id}}",
  "mode": "TEST_ONLY",
  "production_mutation": false,
  "note": "Pilot PASS does NOT authorize Full Processing"
}
```

### 3.6 Respond to Webhook — FAIL (IF FALSE)
```json
{
  "status": "validation_failed",
  "errors": "{{$json.errors}}",
  "production_mutation": false
}
```

### 3.7 Respond to Webhook — ERROR (신규, 3.1/3.2의 error 출력 합류)
파일 노드/파싱 노드 자체가 에러를 던진 경우용. **원인별로 `status` 문자열을 구분**할 것 (뭉뚱그려 "invalid" 금지):
```json
{
  "status": "file_error",
  "node": "{{$json.error?.node?.name || 'unknown'}}",
  "message": "{{$json.error?.message}}",
  "production_mutation": false
}
```
(malformed JSON은 `parse_error`, 파일 없음은 `file_error` 등 실제 에러 메시지를 반영해 구분 표시)

## 4. 절대 금지 (재확인)

- PASS 분기 뒤에 Production mutation 노드(DB write, Retrieval Engine 호출 등) 연결 금지
- `schema.json` 파일 수정 금지
- `state` enum 확장 등 신규 상태값 도입 금지 (Phase E는 별도 ADR 검토 후 진행 — 이번 범위 아님)
- 두 Respond 노드 모두 `production_mutation: false`는 **하드코딩** 유지 (동적 계산 금지)

## 5. 완료 후 자체 검증 (C1이 먼저 수행)

다음 5개 케이스를 직접 curl로 호출해 결과를 스크린샷 또는 로그로 남길 것:

1. `{"task_id":"ADR-021-PILOT-001"}` → PASS 응답
2. 존재하지 않는 task_id → **명시적 FAIL/ERROR 응답** (200 빈 바디 금지 — 이게 이번 지시의 핵심)
3. 필수 필드가 누락된 테스트용 task 파일 → validation FAIL 응답
4. `production_mutation`이 `false`가 아닌 값인 테스트 파일 → validation FAIL 응답
5. `evidence`가 배열이 아닌 테스트 파일 → validation FAIL 응답

테스트용 파일은 `.automation/tasks/` 바깥이나 `_c1_test/` 같은 임시 하위 폴더에 만들고, 검증 완료 후 반드시 삭제할 것(레포에 잔존 금지).

## 6. 다음 단계

구현 및 자체 검증 완료 후 **CUE Re-audit**을 요청한다. CUE는 동일한 5개 케이스를 독립적으로 재실행하고, workflow JSON export로 mutation 노드 미연결 여부를 재확인한 뒤 승인 여부를 판정한다.

```
C1 Build → CUE Re-audit → (필요시) C1 Correct → CUE Approve
```

Pilot PASS는 Full Processing 승인이 아니다.
