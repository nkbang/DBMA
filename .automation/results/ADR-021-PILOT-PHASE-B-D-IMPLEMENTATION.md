# ADR-021 Pilot Phase B~D 구현 완료 보고서

**Task ID:** ADR-021-PILOT-001  
**구현자:** C1  
**작성일:** 2026-08-13  
**상태:** CUE Re-audit 요청  

---

## 1. 구현 내용 요약

### 1.1 워크플로우 구조 (Phase B~D)

```
Webhook (POST /webhook/dbma-automation-test)
   │
   ▼
Read/Write Files from Disk (fileSelector: /automation/tasks/{{ $json.body.task_id }}.json)
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

### 1.2 노드별 구현 사항

| 노드 | 설정 | 비고 |
|------|------|------|
| Webhook | path: `dbma-automation-test`, typeVersion: 2.1, authentication: none | 슬러그만 사용 (전체 URL 아님) |
| Read/Write Files from Disk | fileSelector: `={{ "/automation/tasks/" + $json.body.task_id + ".json" }}`, typeVersion: 1.1 | 파라미터화됨 (고정 글롭 아님) |
| Extract From File | operation: `fromJson`, inputBinaryField: `data`, destinationOutputField: `task` | On Error: Continue 설정 |
| Code — Schema Validation | 문서 3.3 스크립트 그대로 사용 | 임의 변경 없음 |
| IF | condition: `{{ $json.valid }} === true` | boolean 조건 |
| Respond PASS | status: `validated`, production_mutation: false (하드코딩) | Pilot PASS 메시지 포함 |
| Respond FAIL | status: `validation_failed`, errors: `{{$json.errors}}` | validation 실패 사유 포함 |
| Respond ERROR | status: `file_error`/`parse_error`, node: `{{$json.error?.node?.name}}` | 에러 원인별 구분 |

### 1.3 핵심 안전 장치

1. **On Error: Continue** — Read/Write Files from Disk와 Extract From File 양쪽에 설정
2. **ERROR 분기** — 파일 없음/malformed JSON 시 명시적 응답 (빈 바디 금지)
3. **production_mutation: false 하드코딩** — 두 응답 모두 동적 계산 아님
4. **PASS 뒤 mutation 노드 없음** — DB write/Retrieval Engine 호출 연결 안 됨

---

## 2. 생성된 파일 목록

| 파일 | 용도 |
|------|------|
| `.automation/workflows/ADR-021-PILOT-PHASE-B-D.json` | 워크플로우 JSON (n8n import용) |
| `.automation/workflows/test-phase-b-d.sh` | curl 테스트 스크립트 |
| `_c1_test/test-01-valid.json` | Test 1: 정상 케이스 |
| `_c1_test/test-03-missing-fields.json` | Test 3: 필드 누락 |
| `_c1_test/test-04-prod-mutation.json` | Test 4: production_mutation !== false |
| `_c1_test/test-05-evidence-type.json` | Test 5: evidence 타입 오류 |
| `_c1_test/test-06-malformed.json` | Test 6: malformed JSON |

---

## 3. n8n 활성화 방법 (사용자 수행 필요)

### 3.1 API 키 생성

1. n8n 웹 인터페이스 (`http://localhost:5678`) 접속
2. 왼쪽 메뉴 → **Personal** → **Settings** → **API Keys**
3. **Create Key** 클릭 → 키 복사
4. 터미널에서: `export N8N_API_KEY=<복사한 키>`

### 3.2 워크플로우 import 및 활성화

1. n8n 웹 인터페이스에서 **Import from URL** 또는 **Import from File** 사용
2. `.automation/workflows/ADR-021-PILOT-PHASE-B-D.json` 파일 선택
3. 우측 상단 **Activate** 토글 켜기
4. Webhook 노드의 path가 `dbma-automation-test`인지 확인

### 3.3 테스트 실행

```bash
export N8N_API_KEY=<your-api-key>
bash .automation/workflows/test-phase-b-d.sh
```

---

## 4. 검증 케이스 (5종)

| # | 케이스 | 기대 결과 | 상태 |
|---|--------|-----------|------|
| 1 | `{task_id: "ADR-021-PILOT-001"}` | `status: "validated"` (PASS) | 대기 (API 키 필요) |
| 2 | `{task_id: "NONEXISTENT-999"}` | `status: "file_error"` (ERROR) | 대기 (API 키 필요) |
| 3 | 필수 필드 누락 | `status: "validation_failed"` (FAIL) | 대기 (API 키 필요) |
| 4 | `production_mutation: true` | `status: "validation_failed"` (FAIL) | 대기 (API 키 필요) |
| 5 | `evidence: "not-an-array"` | `status: "validation_failed"` (FAIL) | 대기 (API 키 필요) |

---

## 5. 절대 준수 사항 확인

| 항목 | 준수 여부 | 비고 |
|------|-----------|------|
| schema.json 수정 금지 | ✅ | 읽기 전용 |
| state enum 확장 금지 | ✅ | Phase E 보류 |
| PASS 뒤 mutation 노드 없음 | ✅ | Respond 노드에서 종료 |
| production_mutation: false 하드코딩 | ✅ | 동적 계산 아님 |
| On Error: Continue 양쪽 노드 | ✅ | ERROR 분기 연결 |
| fileSelector 파라미터화 | ✅ | `/automation/tasks/{{ $json.body.task_id }}.json` |

---

## 6. CUE Re-audit 요청 사항

CUE는 다음을 독립적으로 재확인하십시오:

1. **워크플로우 JSON export** — mutation 노드 미연결 여부
2. **5종 케이스 재실행** — PASS/FAIL/ERROR 구분 정확성
3. **On Error: Continue 설정** — ERROR 분기 정상 동작
4. **production_mutation: false 하드코딩** — 동적 계산 아님 확인
5. **file_selector 파라미터화** — 고정 글롭 아님 확인

---

**제출 상태:** `READY_FOR_CUE_RE_AUDIT`

Pilot PASS는 Full Processing 승인이 아니다.
