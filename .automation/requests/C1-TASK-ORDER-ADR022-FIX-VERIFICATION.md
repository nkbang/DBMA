# C1 Task Order — ADR-022 참조 구현 수정분 재검증

**Task Order:** C1-TASK-ORDER-ADR022-FIX-VERIFICATION
**Date:** 2026-08-14
**발주자:** CUE
**대상:** C1
**근거:** `.automation/audit/ADR-022-CUE-FIX-001.md` — CUE가 C1이 발견한 결함 2건(illegal transition 허용, race condition)을 참조 구현에 수정 반영함. `.automation/workflows/phase-e.json`이 갱신됨(23개 노드).

---

## 원칙 재확인

n8n UI가 source of truth → Export JSON이 artifact → Runtime execution이 evidence. `phase-e.json` 손편집 금지. 이번에도 CUE가 직접 수정했으므로 **C1의 독립 재검증이 필요**하다 — 이번엔 지난번보다 좁은 범위: 새로 고친 두 곳이 실제로 막히는지만 집중 확인.

## 1. Import/Publish

```
docker exec dbma_n8n n8n import:workflow --input=<phase-e.json 경로>
docker exec dbma_n8n n8n publish:workflow --id=9qIO3nFeWRia28Rb
docker restart dbma_n8n
docker logs dbma_n8n --tail 10   # 에러 없이 "Activated workflow" 확인
```

## 2. 회귀 재확인 (기존 5종)

지난번 통과했던 5개 케이스가 이번 수정으로 깨지지 않았는지 재실행:
1. 정상 → `validation_passed`
2. 동일 payload 중복 → `duplicate` (이번 수정에서 순서 문제로 한 번 깨졌다가 CUE가 고침 — **특히 이 케이스를 꼼꼼히 재확인**)
3. 다른 payload → `task_id_payload_conflict`
4. validation 실패 → `failed`
5. 파일 없음 → `file_error`

## 3. 결함 1 재현 시도 (Illegal Transition)

신규 task_id로 task 파일을 만들고 `automation.state`를 직접 `"COMPLETED"`로 조작(evidence 로그는 만들지 않은 상태) 후 webhook 호출:

```json
{"schema_version":"1.0.0","task_id":"...","title":"t","owner":"C1","automation":{"state":"COMPLETED","failure_code":null,"last_transition_id":"fake#9999"}}
```

**기대 결과:** `{"status":"illegal_transition",...}` 응답, 파일의 `automation.state`가 `COMPLETED`로 그대로 유지(덮어써지지 않음). 지난번엔 이게 실패해서 `VALIDATION_PASSED`로 덮어써졌었다.

## 4. 결함 2 재현 시도 (Race Condition)

동일 task_id로 최소 5개 이상 동시 병렬 요청:

```bash
for i in 1 2 3 4 5; do
  curl -s -X POST http://localhost:5678/webhook/dbma-automation-phase-e \
    -H 'Content-Type: application/json' -d '{"task_id":"...","race":true}' &
done
wait
```

**기대 결과:** evidence 파일에 요청 수만큼 줄이 생기고, 각 줄의 `transition_id`가 전부 서로 다름(중복 없음). 지난번엔 3개 요청이 전부 같은 `transition_id`를 받았었다.

## 5. Namespace 무변경 재확인

```
shasum -a 256 /Users/David/DBMA/NAE/pipeline/ingest/state/incremental_state.json
```
CUE가 기록한 값(`e10a396674f4d9084997f21a2d7586d674a3541b6fe356bfd47f4a808c52524a`)과 일치하는지 확인.

## 6. Evidence 보존 및 정리

- curl 명령/응답 원문, evidence 파일 내용을 그대로 보존해 `.automation/evidence/`에 정리
- **테스트에 사용한 임시 task 픽스처 파일은 검증 후 삭제할 것** — 지난번 라운드에서 이 정리가 누락됐었다

## 7. 절대 금지

- `phase-e.json` 손편집
- 실패를 통과로 보고
- 임의로 워크플로우를 고쳐서 결함을 "해결"하는 것 — 결함이 재현되면 그대로 CUE에게 보고, 재현되지 않으면(=수정 확인) 그것도 그대로 보고

## 8. 제출

두 결함이 실제로 막히는지 확인되면 `READY_FOR_CUE_RE_AUDIT`로 제출한다. 결함이 여전히 재현되면 그 원문 증거와 함께 제출한다.
