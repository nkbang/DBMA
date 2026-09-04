# NAE Pilot 001 — Gold Query Set Approval 001

**작성일:** 2026-08-09
**성격:** 사용자 명시적 승인("승인")에 따른 Gold Query Set 정식 승격
(`review_status: draft → approved`).
**Authority:** `docs/NAE_PILOT_001_RETRIEVAL_BENCHMARK_REPORT_001.md`(draft
1회성 실행 결과) + 사용자 승인.
**Reviewer:** David / **Review Date:** 2026-08-09

---

## 1. 승인 내용

`NAE/benchmark/datasets/pilot_001_gold_draft.jsonl`(10건, `review_status:
draft`)을 사용자에게 질의-정답 매핑 표로 재제시, 전건 승인받음. 파일을
`NAE/benchmark/datasets/pilot_001_gold_v1.jsonl`로 이동(rename)하고 10건
전부 `review_status: "approved"`로 갱신.

> `NAE/benchmark/schema.py::BenchmarkMetadata`는 `reviewer`/`review_date`
> 필드를 갖지 않아(스키마 외 속성) JSONL에는 넣지 않고 이 문서에 감사
> 기록으로 남긴다. 개별 승인 근거는 본 문서와 대화 기록.

## 2. 승인된 10건

| ID | Gold TSU | Doctrine |
|---|---|---|
| PILOT001-Q01 | TSU-0000025 | Sanctification |
| PILOT001-Q02 | TSU-0000033 | Soteriology |
| PILOT001-Q03 | TSU-0000199 | Baptism |
| PILOT001-Q04 | TSU-0000330 | Lord's Supper |
| PILOT001-Q05 | TSU-0000713 | Ecclesiology |
| PILOT001-Q06 | TSU-0003524, TSU-0003525 | Church Discipline |
| PILOT001-Q07 | TSU-0003525 | Church Discipline |
| PILOT001-Q08 | TSU-0003647 | Soteriology |
| PILOT001-Q09 | TSU-0003661 | Baptism |
| PILOT001-Q10 | TSU-0003893 | Lord's Supper |

## 3. 승인본 재실행 결과

승인 후 파일 경로 변경(`pilot_001_gold_v1.jsonl`)에 대해 동일 조건으로
`NaeQdrantRetriever` + `runner.run_benchmark()` 재실행, draft 실행과
동일한 결과 재확인(회귀 없음):

```
total_questions: 10 / passed: 10 / failed: 0 / retrieval_errors: 0

recall@5:    1.0
precision@5: 0.22
mrr:         1.0
hit_rate@5:  1.0
```

결과 파일: `NAE/benchmark/datasets/pilot_001_gold_v1_results.jsonl`

## 4. 지위

이 Gold Query Set(`pilot_001_gold_v1.jsonl`)은 이제 **정식 승인된
회귀 기준선**이다. 향후 인덱스/임베딩/검색 로직 변경 시 이 데이터셋
재실행 결과와 비교해 회귀 여부를 판단할 수 있다. 단, 표본이 10건
(Pilot verified 전체)뿐이므로 일반화된 시스템 성능 지표로 인용해서는
안 되며, Pilot 규모 스모크 회귀 기준으로만 사용한다. 코퍼스가
4,107건 규모로 확장되면 별도의 확장 Gold Query Set이 필요하다.

기존 draft 산출물(`pilot_001_gold_draft.jsonl`,
`pilot_001_gold_draft_results.jsonl`)은 승인본으로 대체되어 삭제.

---

## 완료 보고

```
STATUS: PASS

GOLD QUERY SET: NAE/benchmark/datasets/pilot_001_gold_v1.jsonl (10건, review_status=approved)
RESULTS: NAE/benchmark/datasets/pilot_001_gold_v1_results.jsonl

METRICS: recall@5=1.0, precision@5=0.22, mrr=1.0, hit_rate@5=1.0 (draft 실행과 동일, 회귀 없음)

FILES:
NAE/benchmark/datasets/pilot_001_gold_draft.jsonl -> NAE/benchmark/datasets/pilot_001_gold_v1.jsonl (rename)
NAE/benchmark/datasets/pilot_001_gold_draft_results.jsonl (삭제, 승인본 결과로 대체)
NAE/benchmark/datasets/pilot_001_gold_v1_results.jsonl (신규)
docs/NAE_PILOT_001_GOLD_QUERY_SET_APPROVAL_001.md (신규)

GIT: 커밋/Push 대기

NEXT STEP:
Pilot 001 전 구간(Migration→...→Retrieval Benchmark→Gold Query Set 정식
승인) 완료. 다음은 Pilot 범위를 4,107건 generated TSU로 확장하는 Human
Review 진행 여부 — 별도 작업 명령 대기.
```
