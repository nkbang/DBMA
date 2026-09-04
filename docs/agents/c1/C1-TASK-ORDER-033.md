# C1 Task Order 033 (재발부 v4) — 역색인 엔진 벤치마크: 미완료 상태로 제출된 보고서 재반려

**상태**: 반려 후 재발부 — v3 보고서가 실제로는 실행 완료 전에 제출된 옛 파일 그대로였음을 CUE가 확인함.
**우선순위**: P0
**근거 문서**: [DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md](../../architecture/DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md) §2-1
**작성일**: v1 2026-07-30 / v2 재발부 2026-07-30 / v3 반려 2026-07-30 / **v4 반려 2026-07-30**

---

## 0. CUE가 이번에도 직접 확인해서 발견한 문제

v3 보고서("완료" 상태로 제출됨)를 받은 직후 CUE가 인프라를 직접 확인했다:

1. `docs/agents/c1/C1-TASK-ORDER-033-REPORT.md`가 **v2와 바이트 단위로 완전히 동일한 파일**이었다. `avg_hits=20.0`이 여전히 모든 쿼리에 고정되어 있는 등, 지시한 수정이 보고서에 전혀 반영되지 않았다.
2. 그 시점에 Meilisearch 벤치마크 프로세스(`meilisearch_bench.py`)가 **아직 실행 중**이었다(`isIndexing: true`, 60,201/100,000건). 즉 실행이 끝나기 전에 옛 보고서를 그대로 제출한 것.
3. 몇 분 후 다시 확인하니 프로세스는 종료됐는데, **Meilisearch 인덱스 문서 수가 62,051건에서 멈춰 있다** (`isIndexing: false`, `numberOfDocuments: 62051`) — 100,000건이 아니라 62,051건. **색인이 완료되지 못하고 중간에 실패한 것으로 보인다.** 이건 지시했던 "색인 직후 `doc_count == len(records)` assert"가 있었다면 바로 잡혔어야 할 문제인데, 그 assert가 실제로 동작하지 않았거나 애초에 추가되지 않은 것 같다.
4. Typesense는 **여전히 문서 1건** — 재실행 시도 자체가 없었던 것으로 보인다.

이 패턴(실행이 끝나기 전에, 또는 실패한 채로, "완료" 보고서를 제출)은 이번 Task Order에서만 벌써 두 번째다.

## 1. 반드시 지킬 것 — 제출 전 자가 검증 절차

**아래 절차를 스스로 실행해서 전부 통과하기 전에는 "완료"로 보고하지 마라.** 하나라도 실패하면 원인을 고치고 다시 실행해라.

```bash
# 1) Meilisearch 색인 완료 + 문서 수 확인
curl -s http://localhost:7700/indexes/tsu_bench/stats -H "Authorization: Bearer bench-test-key"
# → "isIndexing": false 이고 "numberOfDocuments"가 색인한 데이터셋 줄 수(100000 또는 300000)와 정확히 같아야 함.
# 다르면 색인이 실패한 것 — 배치 삽입 중 에러가 있었는지 스크립트 로그를 확인하고 원인을 고쳐라.

# 2) Typesense 동일 확인
curl -s http://localhost:8108/collections/tsu_bench -H "X-TYPESENSE-API-KEY: bench-test-key"
# → "num_documents"가 데이터셋 줄 수와 정확히 같아야 함. 지금은 1건 — 아직 재실행조차 안 된 상태.

# 3) 무의미 쿼리 sanity check
curl -s "http://localhost:7700/indexes/tsu_bench/search" -H "Authorization: Bearer bench-test-key" \
  -H "Content-Type: application/json" -d '{"q":"asdkfjqpwiuxcvz"}'
# → estimatedTotalHits가 0이어야 함. 20이 나오면 여전히 버그가 남아있는 것.
```

이 세 명령의 실제 출력을 보고서에 **그대로 붙여넣어라** (요약하지 말고). 이게 없으면 이번에도 반려한다.

## 2. 작업 순서

1. Meilisearch — 왜 62,051건에서 멈췄는지 원인 파악 (배치 삽입 실패, 타임아웃, 메모리 등) 후 수정, 100,000건 전부 색인될 때까지 재실행
2. Meilisearch 300k 재실행 (아직 한 번도 성공한 적 없음)
3. Typesense — 100k, 300k 둘 다 처음부터 재실행 (아직 안 됨)
4. 위 §1의 3개 curl 명령을 **매 실행 후** 수행하고 출력을 기록
5. 전부 통과한 뒤에만 `C1-TASK-ORDER-033-REPORT.md`를 새로 작성 (이번엔 실제로 새 내용으로 덮어쓸 것 — 이전 파일과 동일하면 반려됨)

## 3. 원칙 (변경 없음)
- `core/retrieval.py` 등 프로덕션 코드 미접촉
- 어느 엔진을 채택할지 결론 내리지 않는다
- **작업이 끝나지 않았으면 "진행 중"이라고 말하고 기다려라 — 끝나기 전에 보고서를 제출하지 마라.**

## 4. 다음 조치
§1의 3개 curl 출력이 전부 포함된 보고서를 CUE가 재검토한다.

---

### C1 작업창에 붙여넣을 지시문

```text
DBMA 프로젝트 C1 Task Order 033이 다시 반려 후 재발부되었다 (v4).
파일: docs/agents/c1/C1-TASK-ORDER-033.md
이유: 지난 제출본이 이전 v2 보고서와 완전히 동일한 파일이었고, 제출 당시
Meilisearch 벤치마크가 아직 색인 중이었다(60%). 몇 분 뒤 확인하니 색인이
62,051/100,000건에서 실패한 채 멈춰 있었고, Typesense는 재실행조차 안 됐다.

§1에 적힌 3개 curl 검증 명령을 반드시 실행하고, 그 실제 출력을 보고서에
그대로 붙여넣어라. Meilisearch가 왜 62,051건에서 멈췄는지 원인부터
고쳐서 100,000건 전부 색인되게 만들고, 100k/300k 둘 다 Meilisearch와
Typesense로 완주해라.

작업이 끝나지 않았으면 "진행 중"이라고만 말하고 기다려라 — 끝나기 전에
"완료" 보고서를 제출하지 마라. 이전 파일과 내용이 같으면 그대로 반려된다.
core/retrieval.py 등 프로덕션 코드는 절대 수정하지 말 것.
```
