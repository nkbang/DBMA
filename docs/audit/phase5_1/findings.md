# Phase 5.1 Forensic Findings — CUE-P0-FINAL-EVIDENCE-CLOSURE

범위: Read-only forensic review. 코드 수정·reset·restore·commit 없음.

---

## Q1/Q2/Q3 판정 요약 (근거는 `code-trace.md`)

| 질문 | 판정 |
|---|---|
| Q1 — evaluator가 `gold_tsu_ids`를 읽는가? | **FAIL** — `expected.expected_scriptures`/`required_concepts` 사용, `gold_tsu_ids`는 0회 참조 |
| Q2 — runner가 Qdrant 결과를 evaluator에 전달하는가? | **FAIL** — Qdrant 연결 코드 자체가 존재하지 않음(`_dummy_retrieval`만 존재) |
| Q3 — Metric 입력 공간이 동일한가? | **FAIL** — `retrieved_ids`=TSU-ID 공간, `relevant_ids`=자연어 성경구절 문자열 공간, 서로 다른 공간 |

## Confirmed Facts (직접 확인)

1. HEAD는 `d7152ec`(`commit.txt`), parent는 `7b76107`.
2. `git diff HEAD^ HEAD --stat`: `NAE/benchmark/` 5개 모듈 + 데이터셋 + 테스트 5종, 총 15개 파일, 2080줄 추가(`changed_files.txt`).
3. working tree에 **미커밋 변경**이 존재: `NAE/benchmark/{__init__,schema,loader}.py`, `datasets/benchmark_v1.jsonl`, 그리고 `tests/test_nae_benchmark_{schema,loader}.py`(`changed_files.txt`). 이 변경은 어느 commit에도 속하지 않는다 — working tree 상태일 뿐이다.
4. `pytest tests/test_nae_benchmark_*.py -v`: **92 passed**, 0 failed(`tests/pytest-output.txt`, 전체 출력 포함).
5. `evaluator.py`/`runner.py`는 미커밋 변경 목록에 없음 — `d7152ec` 커밋 시점 코드와 바이트 단위로 동일.
6. `gold_tsu_ids` 필드가 `schema.py`에 두 곳(68행 `BenchmarkExpected`, 118행 `BenchmarkItem`)에 독립적으로 정의되어 있음.
7. ADR-003/ADR-013 관련 grep 결과 위반 증거 없음(`adr-linkage.md`).

## 확인되지 않은 주장

- 미커밋 변경이 어느 시점, 어느 작업지시서에 대한 응답으로 작성되었는지는 git 이력만으로 확인 불가(working tree diff에는 타임스탬프나 지시서 참조가 남지 않음).
- `docs/agents/c1/C1-TASK-NAE-PHASE5-COMPLETE.md`가 이 uncommitted 변경의 완료 보고서인지 여부는 정황상 유력하나(파일명·시점·내용 일치도가 높음) 100% 확정할 근거는 없음 — 보고서 자체에 커밋 SHA나 diff 참조가 없기 때문.

## 구조적 결함 (코드로 확인됨)

- Q1/Q2/Q3 모두 FAIL — Phase 5.2를 위한 retrieval↔evaluation 연결이 설계 의도(`gold_tsu_ids`)와 실제 구현(`expected_scriptures`) 사이에서 완전히 단절되어 있다. 이 단절은 `d7152ec` 커밋 시점부터 지금까지 변하지 않았다.
- `gold_tsu_ids`의 이중 정의(schema.py 68행/118행) — 스키마 자체가 canonical 위치를 결정하지 않음.

## 다음 단계에 필요한 증거

- 미커밋 변경의 출처(어느 지시서·어느 세션)를 명확히 하는 것 — 이후 작업지시서 개정 시 "무엇을 기준으로 다시 쓸지"를 정하기 위해 필요.
- corpus/Qdrant point 실측 상태(`EMPTY_CONFIRMED`, 이전 리뷰 `CUE-PHASE5.0.5-EVIDENCE-REVIEW.md`에서 확인됨 — 이번 forensic review에서는 재확인하지 않음, 대상 범위 아님).
