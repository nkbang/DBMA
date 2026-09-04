# C1 Task Order — ADR-022 Phase E 독립 검증

**Task Order:** C1-TASK-ORDER-ADR022-INDEPENDENT-VERIFICATION
**Date:** 2026-08-13
**발주자:** CUE
**대상:** C1
**전제:** `.automation/workflows/phase-e.json`은 CUE가 직접 빌드·실행 검증한 **참조 구현(reference implementation)**이다. CUE가 만든 것을 CUE가 재감사하면 독립성이 성립하지 않으므로, 이번 단계는 **C1의 독립 검증**이다. ADR-022는 아직 `Proposed / Design Review Complete / Implementation Authorized`이며 **Approved 아니다.**

---

## 절대 원칙 (Phase B~D 교훈 재확인)

> **n8n UI가 source of truth → Export JSON이 artifact → Runtime execution이 evidence.**

`phase-e.json`을 손으로 고치지 않는다. 수정이 필요하면 n8n Editor UI에서 고치고 `export:workflow`로 다시 뽑는다. 이 원칙을 어기면 즉시 중단하고 CUE에게 보고한다.

## 1. 동결 대상 — 절대 임의 수정 금지

- `.automation/workflows/phase-e.json` (21개 노드, CUE 참조 구현)
- `docker-compose.yml`의 n8n volumes 섹션

## 2. Mount 확인 (1차 확인 사항)

`docker-compose.yml`에서 다음이 정확히 이 형태인지 확인:

```yaml
volumes:
  - n8n_data:/home/node/.n8n
  - ./.automation:/automation:ro
  - ./.automation/tasks:/automation/tasks:rw
  - ./.automation/evidence:/automation/evidence:rw
```

**`/automation` 전체가 `:rw`로 바뀌어 있으면 즉시 중단하고 CUE에게 보고한다** — `schema.json`, `PRODUCTION_RULES.md`, 아키텍처 문서 등 governance 파일은 반드시 `:ro`여야 한다. `tasks/`와 `evidence/`만 `:rw`인 것이 맞다.

## 3. Canonical Phase B~D 복구 검증 (Phase E와 분리해서 별도로)

CUE가 볼륨 유실 후 `.automation/workflows/ADR-021-PILOT-PHASE-B-D.json`에서 재-import했다고 보고했다. 이것도 별도 evidence로 확인한다 — Phase E 승인과 절대 묶지 않는다:

```
n8n list:workflow로 workflow id `dbmaAutomationTest01` 존재 + active 확인
   ↓
curl -X POST http://localhost:5678/webhook/dbma-automation-test -d '{"task_id":"ADR-021-PILOT-001"}'
   ↓
{"status":"validated",...} 응답 원문 확보 (Phase B~D 원래 계약 그대로인지)
```

## 4. Phase E Import/Publish

```
docker exec dbma_n8n n8n import:workflow --input=<phase-e.json 경로>
docker exec dbma_n8n n8n publish:workflow --id=9qIO3nFeWRia28Rb
docker restart dbma_n8n
docker logs dbma_n8n --tail 10   # "Activated workflow" 에러 없이 뜨는지 확인
```

## 5. Export ↔ 실제 워크플로우 일치 확인

```
docker exec dbma_n8n n8n export:workflow --id=9qIO3nFeWRia28Rb --output=/tmp/verify.json
```

`.automation/workflows/phase-e.json`과 diff해서 node 구성이 동일한지 확인(재import 과정에서 값이 유실/변형되지 않았는지).

## 6. ADR-022 §15 Test Matrix 9개 전체 (5개가 아니라 9개 전부)

CUE가 실행한 것은 5개뿐이다(정상/duplicate/conflict/validation FAIL/file 없음). §15 전체 9개를 실행하라:

| # | 시나리오 |
|---|---|
| 1 | 신규 task, 정상 JSON → `RECEIVED → VALIDATION_PASSED` |
| 2 | 신규 task, validation 실패 → `FAILED`(`VALIDATION_FAILED`) |
| 3 | 신규 task, 파일 없음 → `FAILED`(`FILE_ERROR`) |
| 4 | 동일 task_id + 동일 payload 중복 → no-op, `duplicate` |
| 5 | 동일 task_id + 다른 payload → `TASK_ID_PAYLOAD_CONFLICT` |
| 6 | 금지된 전이 강제 시도(외부에서 task 파일의 `automation.state`를 `COMPLETED`로 직접 써넣고 webhook 재호출) → 워크플로우가 이 값을 무시/거부하는지, 아니면 실수로 덮어쓰는지 확인 — **CUE 참조 구현이 이 케이스를 실제로 막는지는 검증되지 않았다. 여기서 결함이 나와도 정상이다, 그대로 보고하라** |
| 7 | `FAILED → RETRY_PENDING`을 사람이 명시적으로 트리거(현재 워크플로우엔 이 경로 자체가 없다 — 없다는 것을 확인하는 것이 테스트다) |
| 8 | 자동화가 스스로 RETRY_PENDING 승격 시도 — 코드 자체가 없음을 workflow export로 증명 |
| 9 | NAE Registration State 파일 무변경 — 아래 8항 참고 |

## 7. Race Condition 테스트 (신규, CUE 미실시)

동일 task_id로 **동시에** 2개 이상의 요청을 병렬로 보내 `transition_id` 순번이 충돌 없이 부여되는지 확인:

```bash
for i in 1 2 3; do
  curl -s -X POST http://localhost:5678/webhook/dbma-automation-phase-e \
    -H 'Content-Type: application/json' -d '{"task_id":"ADR-021-PILOT-001","race":true}' &
done
wait
cat .automation/evidence/ADR-021-PILOT-001.jsonl
```

evidence 파일에 `transition_id`가 중복되지 않고 순차적으로 부여됐는지, 또는 race로 인해 evidence 유실/덮어쓰기가 발생했는지 그대로 보고한다. **CUE 참조 구현은 이 케이스를 명시적으로 처리하지 않는다(§11에서 "구체 메커니즘은 C1 구현 시 CUE가 재감사" 라고 명시했던 부분) — 실패해도 그대로 보고하라, 숨기지 마라.**

## 8. Namespace 무변경 확인

```bash
find /Users/David/DBMA/NAE/pipeline/registration/state -type f 2>&1
shasum -a 256 /Users/David/DBMA/NAE/pipeline/ingest/state/incremental_state.json
# (Phase E 테스트 실행 전/후 각각 실행해서 두 값이 같은지 비교)
```

## 9. Production Mutation 부재 확인

`phase-e.json`을 열어(export한 JSON 그대로) `PROCESSING`, `COMPLETED`로의 실제 전이 노드/코드가 **존재하지 않음**을 확인한다. 코드가 없다는 것 자체가 증거다.

## 10. Evidence 보존

각 테스트의 curl 명령 원문, HTTP 응답 원문, `docker logs` 관련 구간, evidence 파일 내용, SHA256 비교 결과를 `.automation/evidence/`(또는 별도 리포트 파일)에 정리해서 보존한다. 요약하지 말고 원문 그대로.

## 11. 절대 금지

- `phase-e.json` 손편집
- `docker-compose.yml`의 mount를 `/automation` 전체 `:rw`로 확대
- Phase E 검증 결과와 Phase B~D 복구 검증을 하나의 evidence로 뭉뚱그리기
- 6/7/8/race-condition 테스트에서 나온 실패를 숨기거나 "일단 통과"로 보고
- `phase-e.json`이 실패한 부분을 발견해도 임의로 워크플로우를 고쳐서 통과시키는 것 — **실패는 실패로 보고하고 CUE의 수정 지시를 기다린다**

## 12. 제출

완료되면 `READY_FOR_CUE_RE_AUDIT`로 제출한다. 이때 위 1~10항 evidence가 전부 포함되어 있어야 하며, 6/7/8/race-condition에서 발견된 결함(있다면)도 함께 포함한다. CUE는 그 evidence를 기준으로 재감사하고, 필요하면 참조 구현을 수정하는 후속 지시를 낸다.
