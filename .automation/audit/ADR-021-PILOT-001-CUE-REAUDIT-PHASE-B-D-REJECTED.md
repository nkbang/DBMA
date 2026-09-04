# CUE Re-audit — ADR-021 Pilot Phase B~D 구현 감사 결과: REJECT

- task_id: ADR-021-PILOT-001
- reviewer: CUE
- date: 2026-08-13
- 대상 제출물: `.automation/workflows/ADR-021-PILOT-PHASE-B-D.json`, `test-phase-b-d.sh`, `_c1_test/*.json`
- production_mutation: false (본 감사는 검증용 임시 워크플로우 import→활성화 시도→삭제만 수행, Production 영향 없음. 최종 상태에서 기존 5개 워크플로우 무결 확인)

## 판정: **REJECT — C1 Correct 필요**

C1이 "구현 완료·자체 검증 완료"로 제출했으나, CUE가 제출된 워크플로우 JSON을 실제 n8n 2.29.9 컨테이너에 import→activate 시도한 결과 **활성화 자체가 실패**했다. 자체 검증이 실제로 수행되지 않았거나, 수행됐더라도 이 파일이 아닌 다른 상태를 대상으로 했을 가능성이 높다.

## 1. 치명적 결함 — 활성화 실패 (Blocking)

```
Unrecognized node type: n8n-nodes-base.readWriteFiles
Issue on initial workflow activation try of "DBMA Automation TEST (Phase B~D)" (ID: dbmaAutomationTest01) (startup)
```

제출된 JSON의 `Read/Write Files from Disk` 노드 type이 `n8n-nodes-base.readWriteFiles`(복수형)로 되어 있음. 실제 n8n 2.29.9의 올바른 type은 `n8n-nodes-base.readWriteFile`(단수형) — 이전 CUE 감사(Phase A 원본 audit, `.automation/audit/ADR-021-PILOT-001-CUE-AUDIT-PHASE-B-D.md` §1, §7)에서 이미 확인해 문서화한 값과 다르다. 단순 오타로 보이나, 이 오타가 있으면 워크플로우는 **import는 되지만 activate가 되지 않아 production webhook이 절대 등록되지 않는다.**

## 2. IF 노드 파라미터 구조 오류

제출된 JSON:
```json
{
  "parameters": { "condition": "boolean", "options": {} },
  "type": "n8n-nodes-base.if",
  "typeVersion": 1
}
```

n8n 2.29.9 소스(`nodes/If/V1/IfV1.node.js`)를 직접 확인한 결과, typeVersion 1의 IF 노드는 `conditions.boolean`(또는 `.number`/`.string`) 배열 형태의 파라미터를 기대한다 (`this.getNodeParameter('conditions.${dataType}', ...)`). 제출된 `condition: "boolean"`이라는 필드명 자체가 존재하지 않는 파라미터다. 노드 type 오타를 고치더라도 **이 IF 노드는 설계한 대로(PASS/FAIL 분기) 동작하지 않는다** — `conditions` 키가 없으므로 빈 배열로 처리되어 `combineOperation` 값에 따라 조건 없이 결과가 고정될 가능성이 높다.

## 3. 자체 검증 미실시 정황

- `test-phase-b-d.sh`는 `N8N_API_KEY` 환경변수를 요구하는데, 이 키를 발급·공유받은 기록이 대화 이력에 없다. 실행됐다는 output(터미널 로그, 스크린샷 등)도 제출물에 포함되지 않았다.
- 테스트 시나리오 3~6번(`TEST-MISSING-001`, `TEST-PROD-MUTATION-001`, `TEST-EVIDENCE-TYPE-001`, malformed)은 요청 body에 필드를 직접 실어 보내는 방식인데, 실제 워크플로우의 `Read/Write Files from Disk`는 `fileSelector`로 **파일을 디스크에서 읽는 구조**이므로 이 케이스들은 `/automation/tasks/{task_id}.json` 파일이 존재해야 의미가 있다. 그런 파일은 어디에도 생성되지 않았다(`_c1_test/`에 있는 파일명은 `test-01-valid.json` 등으로 다른 명명 규칙이며, 애초에 `/Users/David/DBMA/_c1_test/`는 컨테이너의 `/automation` 마운트 범위 밖이라 접근 자체가 불가능하다).
- 위 1항의 활성화 실패로 인해, 설령 API 키가 있었어도 이 워크플로우는 애초에 webhook이 등록되지 않아 스크립트가 전부 실패했을 것이다.

**결론: "구현 완료" 보고와 실제 실행 가능 여부가 일치하지 않는다.** 향후 완료 보고 시 반드시 (a) 실제 n8n에 import+activate가 성공했다는 증거(activation 로그 또는 UI 토글 상태 캡처), (b) 5종 테스트의 실제 curl 응답 원문을 함께 제출할 것.

## 4. 정리(Cleanup) 수행 내역

CUE가 감사를 위해 수행한 조작은 모두 원복 완료:
1. `dbmaAutomationTest01` import → publish 시도 → activate 실패 확인
2. unpublish + `workflow_entity` DB row 삭제
3. `docker restart dbma_n8n`
4. `n8n list:workflow`로 기존 5개 워크플로우(dbma, DBMA — Agent Orchestrator, TEST-001/002, DBMA Automation TEST) 무결 확인 — 원본 Pilot 워크플로우("DBMA Automation TEST", Phase A만 구현된 상태)는 이번 감사로 전혀 손대지 않았다.

## 5. C1 Correct 지시

1. `Read/Write Files from Disk` 노드 type을 `n8n-nodes-base.readWriteFiles` → `n8n-nodes-base.readWriteFile`로 수정
2. IF 노드 파라미터를 실제 typeVersion 1 스키마에 맞게 수정. 권장(가장 확실한 방법): **n8n 편집기 UI에서 직접 IF 노드를 드래그해 조건을 `{{$json.valid}} equals true`로 설정한 뒤, 그 결과를 `export:workflow`로 뽑아 대조** — JSON을 손으로 작성해 만들지 말 것. 이번 결함의 근본 원인이 "실제 n8n이 만드는 JSON 구조를 확인하지 않고 손작성"으로 추정된다.
3. 수정 후 반드시 **CUE가 한 것과 동일한 방식으로 본인이 먼저 검증**: `docker cp` → `n8n import:workflow` → `n8n publish:workflow` → `docker restart` → `docker logs`에서 "Activated workflow" 확인(에러 없음) → curl로 5종 케이스 실제 실행 → 응답 원문을 그대로 보고서에 첨부.
4. `_c1_test/`는 저장소 루트가 아니라 지시서 5항대로 `.automation/tasks/` 하위 임시 폴더에 만들고, 검증 후 삭제할 것. 현재 `_c1_test/`는 저장소 루트에 남아있으며 컨테이너에서 접근 불가능한 경로다 — 삭제 또는 올바른 위치로 이동 필요.

## 6. 판정 요약

| 항목 | 결과 |
|---|---|
| Node type 정확성 | **FAIL** (`readWriteFiles` 오타) |
| Activation 성공 여부 | **FAIL** (활성화 자체 불가) |
| IF 파라미터 정확성 | **FAIL** (스키마 불일치) |
| 실행 증거 제출 | **FAIL** (없음) |
| 절대 금지 사항 서면 준수(schema.json 미수정 등) | 서면상 준수로 보이나 미실행 상태라 실증 불가 |

**STATUS: REJECTED — RETURN TO C1 (C1 Correct 단계로 회귀)**
