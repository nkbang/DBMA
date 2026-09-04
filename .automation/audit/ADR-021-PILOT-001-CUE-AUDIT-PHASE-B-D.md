# CUE Audit & Design — ADR-021 Pilot Phase B~D (JSON Parse → Schema Validation → Governance Gate)

- task_id: ADR-021-PILOT-001
- reviewer: CUE
- date: 2026-08-13
- role: Architecture / Governance / Independent Verification (구현 아님)
- production_mutation: false (본 문서는 설계·감사 산출물이며 Production 변경 없음)

---

## 1. Phase A 감사 결과 — Read/Write Files from Disk 실제 출력 구조

n8n `n8n-nodes-base` v2.29.9 소스코드(`nodes/Files/ReadWriteFile/actions/read.operation.js`)를 직접 확인함. 추측 아님.

**Read operation 실제 출력:**

```js
{
  binary: { [dataPropertyName]: binaryData },   // 기본 key: "data"
  json: {
    mimeType, fileType, fileName, fileExtension, fileSize
  }
}
```

**핵심 사실:**
- `json` 필드에는 **파일 내용이 들어가지 않는다.** 메타데이터(파일명/크기/타입)만 존재.
- 실제 파일 바이트는 `binary.data`(base64)에 있다.
- 따라서 현재 워크플로우(`Webhook → Read/Write Files from Disk → Respond`)는 JSON 내용을 전혀 파싱하지 않고 있었음 — Phase A 관문 통과는 "파일 접근 성공"만 검증한 것이며 "내용 사용 가능"은 아직 미검증 상태였음. 이 구분을 명확히 인계서에 반영함.

---

## 2. Phase B 설계 — JSON Parse

`Extract From File` 노드(`ExtractFromFile.node.js`)의 `fromJson` operation을 사용한다. 소스 확인(`actions/moveTo.operation.js`):

```js
if (operation === 'fromJson') {
  convertedValue = (convertedValue === '') ? {} : jsonParse(convertedValue);
}
set(newItem.json, destinationKey, convertedValue);
```

**권장 노드 설정 (C1 구현 대상):**

| 필드 | 값 |
|---|---|
| Node | Extract From File |
| Operation | Extract From JSON (`fromJson`) |
| Input Binary Field | `data` (Read/Write Files from Disk의 기본 dataPropertyName과 일치해야 함) |
| Destination Output Field | `task` |
| Options → Keep Source | `json` (원본 메타데이터 보존, 감사 추적용) |

결과: `{{$json.task}}` 에 task JSON object 전체가 위치.

**연결 구조 (확정):**

```
Webhook
   ↓
Read/Write Files from Disk (fileSelector: /automation/tasks/{{ $json.task_id }}.json)
   ↓
Extract From File (fromJson → task)
   ↓
Code (Schema Validation)
   ↓
IF (Gate)
   ↓
Respond to Webhook (PASS / FAIL 분기)
```

주의: 현재 `fileSelector`가 고정 문자열(`/automation/tasks/*`)이면 여러 파일이 매칭되어 다중 아이템이 생성될 수 있다. Pilot 단계에서는 요청받은 `task_id` 하나만 읽도록 `fileSelector`를 파라미터화할 것을 권고(3항 참고). 단, 이는 **workflow 내부 로직 변경**이며 `.automation/tasks/*` 아래 파일 자체나 schema를 건드리지 않으므로 ADR-021 범위 내 정상 변경으로 판단.

---

## 3. Phase C 설계 — Schema Validation (Governance-safe)

**설계 원칙:**
- `schema.json`을 **읽기만** 한다 (수정 금지 — Protected Path 성격에 준함).
- Validation 로직은 n8n **Code 노드**(JS, sandbox 내 실행, 외부 side-effect 없음)로 구현 — 별도 서비스 호출이나 파일 쓰기 없음.
- 검증 실패 시 **downstream 실행이 물리적으로 차단**되어야 한다(IF 노드로 분기, FAIL 경로는 Respond만 하고 종료 — 이후 어떤 mutation 노드에도 도달 불가능한 구조).

**검증 항목 (인계서 5항 기준, 최소 필수 키 존재 + 타입 체크):**

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

**중요 — schema 자체 변경 금지 원칙 준수:**
`task.schema_version`이 `.automation/tasks/schema.json`의 버전과 다르면 **FAIL로 처리하고 CUE에게 ADR/schema governance 검토를 요청**해야 한다. Code 노드가 임의로 새 상태값이나 필드를 추가/보정하지 않는다 (인계서 9항 Phase E 단서와 동일 원칙).

---

## 4. Phase D 설계 — Governance Gate

`IF` 노드로 `{{$json.valid}}` 분기.

**TRUE (PASS) 분기 → Respond to Webhook:**
```json
{
  "status": "validated",
  "task_id": "{{$json.task.task_id}}",
  "mode": "TEST_ONLY",
  "production_mutation": false,
  "note": "Pilot PASS does NOT authorize Full Processing"
}
```

**FALSE (FAIL) 분기 → Respond to Webhook:**
```json
{
  "status": "validation_failed",
  "errors": "{{$json.errors}}",
  "production_mutation": false
}
```

**절대 준수:** 두 분기 모두 Respond 노드에서 종료된다. PASS 분기 뒤에 Production mutation 노드(DB write, Retrieval Engine 호출 등)를 이어붙이는 것은 이번 Pilot 완료조건 범위 밖이며, 붙이려면 별도 ADR Amendment + CUE 승인이 선행되어야 한다 — 인계서 10항 "Pilot PASS를 Production authorization으로 해석 금지"와 직결.

---

## 5. Phase E(상태 전이 로깅) — 이번 단계 판정

인계서 9항 자체가 명시: "실제 상태값을 추가하거나 기존 schema를 변경해야 한다면 CUE가 먼저 검토해야 한다." → 현재 `schema.json`에는 `state` enum이 정의돼 있지 않고 예시 값(`IDLE→RECEIVED→...`)은 신규 상태값이다. **이번 Phase B~D 구현 범위에서 Phase E는 보류한다.** State machine 확장은 별도 ADR 초안 작성 후 진행 — Architecture Freeze Rule 대상은 아니지만(schema.json은 ADR이 아님), 인계서가 스스로 건 제약을 CUE가 존중.

---

## 6. C1에게 전달할 구현 지시 (요약)

1. `Read/Write Files from Disk`의 `fileSelector`를 `/automation/tasks/{{ $json.body.task_id }}.json` 형태로 파라미터화 (Webhook body에서 task_id를 받아 단일 파일만 읽도록)
2. `Extract From File` 노드 추가 — Operation: Extract From JSON, Input Binary Field: `data`, Destination: `task`
3. `Code` 노드 추가 — 위 3항 검증 스크립트 그대로 사용 (임의 변경 금지)
4. `IF` 노드 추가 — 조건: `{{$json.valid}} === true`
5. `Respond to Webhook` 노드 2개로 분리 (PASS/FAIL), 위 4항 payload 그대로 사용
6. 두 응답 모두 `production_mutation: false` 하드코딩 유지 (동적 계산 금지 — 이번 Pilot 단계는 이 값이 항상 false여야 하는 불변식)

구현 완료 후 다음 두 케이스로 검증:
- `{"task_id":"ADR-021-PILOT-001"}` → PASS 응답
- `{"task_id":"NONEXISTENT-999"}` → 파일 없음 → 현재 read.operation.js 기준 `No file(s) found` 에러 발생 (nodeVersion>1) → FAIL 경로로 이어지는지 확인 (에러 발생 시 IF 이전에 워크플로우가 죽지 않도록 Read/Write 노드에 `Continue On Fail` 설정 필요 — 이 부분도 C1 구현 시 반영)

## 7. Execution-level 증명 (C1 지적 반영, 2026-08-13 추가)

노드 이름/문서만으로 판단하지 않고, 격리된 임시 워크플로우(`CUE-CONTRACT-TEST-DO-NOT-USE`, id=`cueContractTest01`)를 만들어 **실제 n8n 2.29.9 실행**으로 계약을 증명함. Production/Pilot 워크플로우는 전혀 건드리지 않았고, 검증 완료 후 워크플로우·워크플로우 row(DB)·테스트 픽스처 파일을 모두 삭제해 원상복구함(`dbma` 등 기존 5개 워크플로우 무결 확인).

### 7.1 Binary Contract 증명 (양성 케이스)

```
POST /webhook/cue-contract-test {"file":"/automation/tasks/ADR-021-PILOT-001.json"}
→ HTTP 200
→ { "task": { "schema_version":"1.0.0", "task_id":"ADR-021-PILOT-001", ... } }
```

`Read/Write Files from Disk`(binary.data) → `Extract From File`(Operation: fromJson, Input Binary Field: `data`, Destination: `task`) → `$json.task`에 원본 schema 필드 그대로 매핑됨을 실측 확인. Phase B 설계(2항)가 정확함.

### 7.2 Negative Test 5종 결과

최초 테스트에서 `Read/Write Files from Disk`의 `typeVersion`을 `1`로 잘못 설정했다가, 실제 Pilot/Production 워크플로우가 `1.1`을 쓰고 있음을 발견하고 **재검증으로 자체 정정**함(대조 근거: `n8n export:workflow` 출력).

`typeVersion 1.1` 기준 최종 결과:

| 케이스 | 내부 execution status (DB `execution_entity`) | Webhook HTTP 응답 |
|---|---|---|
| 정상 JSON | success | 200, `{"task": {...}}` |
| 필수 필드 누락 | success (Extract는 성공 — 필드 누락은 Code/schema validation 단계 책임) | 200, `{"task": {...부분 필드...}}` |
| 잘못된 datatype (`production_mutation:"false"`(문자열), `evidence`가 array 아님) | success (Extract 단계는 타입을 검사하지 않음 — 마찬가지로 Code 단계 책임) | 200, 원본 그대로 전달 |
| **malformed JSON** | **error** (`Expected property name or '}' in JSON at position 2`) | **200, 빈 바디** |
| **존재하지 않는 파일** | **error** (`No file(s) found`, `typeVersion>1`이므로 정상적으로 에러 발생) | **200, 빈 바디** |

### 7.3 중대 발견 — Silent Failure Risk (신규, C1/구현 필수 반영 사항)

노드가 내부적으로 에러를 던졌을 때(malformed JSON, 파일 없음) **워크플로우 실행은 DB상 명확히 `error`로 기록되지만, 호출자에게는 HTTP 200 + 빈 바디가 돌아간다.** 즉 에러 캡처용 Respond 노드나 `Continue On Fail` / error-output 분기가 없으면:

- FAIL 상태가 IF Gate까지 도달하지 못하고 워크플로우가 죽어버림 → 4항에서 설계한 `Respond FAIL` 페이로드(`status:"validation_failed"`)가 **아예 발동되지 않음**.
- 호출자 입장에서는 "정상 처리됐지만 내용이 비어있는 응답"과 "내부 에러로 죽은 응답"이 **HTTP status code만으로는 구분 불가능**.

이는 인계서 Governance Rule 8번("Failed validation MUST stop downstream automation")의 "정지"는 만족하지만(다운스트림 실행이 실제로 안 됨), 9번("Every audit result MUST reference evidence")과 충돌한다 — 에러가 evidence 없이 침묵 처리됨.

**C1 구현 필수 요구사항 (기존 6항에 추가):**

7. `Read/Write Files from Disk`와 `Extract From File` 양쪽 노드에 **On Error: Continue (using error output)** 설정을 반드시 켜고, error 출력을 별도 브랜치로 연결해 `Respond to Webhook`(FAIL, `status:"file_error"` 또는 `status:"parse_error"`, `error.message` 포함)로 이어지게 할 것. 이 브랜치가 없는 구현은 **CUE Re-audit에서 REJECT 대상**.
8. 각 에러 유형(file not found / malformed JSON / parse 실패)이 서로 다른 `status` 문자열로 응답에 구분 표시되어야 한다 — 모두 뭉뚱그려 "invalid"로 처리하지 말 것(원인 추적성, PRODUCTION_RULES 6·7번 로깅/근거 원칙).

## 8. 최종 판정

**Phase A~D 설계는 Production-safe이나, 7.3의 Silent Failure 방지 조치(7·8항)가 구현에 포함되지 않으면 승인 보류.** C1은 위 6항 + 7·8항을 모두 반영해 구현하고, 완료 후 CUE가 동일한 5종 케이스(정상/필드누락/타입오류/malformed/파일없음)로 재감사한다. `production_mutation:false` 하드코딩 여부와 FAIL 브랜치에 mutation 노드가 없다는 것도 워크플로우 JSON(export)으로 재확인한다.

Mandatory Workflow 준수: C1 Build → **CUE Re-audit(7·8항 포함 재확인)** → (필요시) C1 Correct → CUE Approve.
