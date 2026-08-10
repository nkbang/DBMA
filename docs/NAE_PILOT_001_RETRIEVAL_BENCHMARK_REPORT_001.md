# NAE Pilot 001 — Retrieval Benchmark Report 001

**작성일:** 2026-08-09
**성격:** 사용자 승인("승인")에 따른 실제 Retrieval Benchmark 최초 실행.
**Authority:** Gold Query Set 초안(사용자 "승인") + `docs/NAE_PILOT_001_EMBEDDING_EXECUTION_REPORT_001.md`(Qdrant points_count=10)
**Git Commit/Push:** 미수행.

> **후속 업데이트(2026-08-09):** 이 문서의 draft Gold Query Set은 사용자
> 승인을 거쳐 `NAE/benchmark/datasets/pilot_001_gold_v1.jsonl`
> (`review_status: approved`)로 정식 승격됨. 상세는
> `docs/NAE_PILOT_001_GOLD_QUERY_SET_APPROVAL_001.md` 참고.

---

## 1. Gold Query Set

- 파일: `NAE/benchmark/datasets/pilot_001_gold_draft.jsonl`
- 10개 질의, 각각 실제 verified TSU 10건의 `claim`/`doctrine` 내용에 근거해 작성.
- `review_status: "draft"`로 저장 — `NAE/benchmark/schema.py`의 "자동 정답 생성
  금지" 원칙에 따라 CUE가 gold_tsu_ids 매핑을 임의로 구성했음을 명시. 사용자가
  본 대화에서 "승인"함으로써 이번 1회 실행의 근거로만 사용, 영구 승인된 gold
  benchmark로 격상하려면 별도 확인 필요.

## 2. 실행

```
retriever = NaeQdrantRetriever()  # nae_tsu_v1, bge-m3:latest, 읽기 전용
runner.run_benchmark(dataset='pilot_001_gold_draft.jsonl', retrieval_fn=retriever,
                      top_k=5, output='pilot_001_gold_draft_results.jsonl')
```

Qdrant/Production 파일 모두 읽기 전용 접근만 발생(upsert/delete 없음).

## 3. 결과

```
total_questions: 10
passed: 10 / failed: 0 / skipped: 0 / retrieval_errors: 0

recall@5:    1.0
precision@5: 0.22 (평균; Q06만 gold 2건이라 0.4, 나머지는 0.2 — 컬렉션
             전체가 10건뿐이므로 top-5 분모 효과, 예상된 값)
mrr:         1.0
hit_rate@5:  1.0
```

10개 질의 전부 gold TSU가 top-1(MRR=1.0 전 항목 동일)로 정확히 검색됨,
Q06(당파적 분쟁, gold 2건: TSU-0003524/0003525)도 top-5 내 2건 모두 포함.

## 4. 해석과 한계

- 표본이 10건(verified 전체)뿐이라 이 수치를 일반화된 시스템 성능으로
  보고할 수 없음 — Pilot 규모에서 "임베딩+검색 파이프라인이 배선상
  정상 작동한다"를 확인하는 스모크 테스트 성격.
- Gold Query Set 자체가 draft이므로, 이 결과를 향후 회귀 기준선으로
  고정하려면 Gold Query Set의 정식 승인(review_status: draft→approved)이
  선행되어야 함.
- 대규모(4,107건) 코퍼스로 Review Gate가 확장된 이후 재실행 시 이
  수치는 하락할 것으로 예상되며, 그것이 정상.

---

## 완료 보고

```
STATUS: PASS

GOLD QUERY SET: NAE/benchmark/datasets/pilot_001_gold_draft.jsonl (10건, review_status=draft, 사용자 1회성 승인)
RESULTS: NAE/benchmark/datasets/pilot_001_gold_draft_results.jsonl

METRICS: recall@5=1.0, precision@5=0.22, mrr=1.0, hit_rate@5=1.0
RETRIEVAL ERRORS: 0

PRODUCTION MUTATION: 0 (읽기 전용)

FILES ADDED:
NAE/benchmark/nae_retriever.py
NAE/benchmark/datasets/pilot_001_gold_draft.jsonl
NAE/benchmark/datasets/pilot_001_gold_draft_results.jsonl
docs/NAE_PILOT_001_RETRIEVAL_BENCHMARK_REPORT_001.md

GIT: NOT PERFORMED

NEXT STEP:
Pilot 001 End-to-End 사이클(Migration→Payload Contract→Human Review
Gate→Promotion→Remediation→Embedding→Qdrant→Retrieval Benchmark) 전
구간 완료. Gold Query Set 정식 승인 여부, 또는 Pilot 범위를 4,107건
generated TSU로 확장하는 Human Review 계속 진행 여부는 별도 작업
명령 대기.
```
