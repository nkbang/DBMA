# C1 Task Order 022 — Sprint C: ParallelRetriever 구현 보고서

**상태**: 완료
**작성일**: 2026-07-29
**구현 파일**:
- `core/parallel_retriever.py` (신규)
- `tests/test_parallel_retriever.py` (신규)

---

## §2 git diff core/retrieval.py 결과

**빈 diff**. `core/retrieval.py`는 한 줄도 수정하지 않았습니다. `RetrievalEngine`, `ParsedQuery`, `RankedCandidate`, `ScriptureReference` 모두 `import`만 하고 재사용했습니다.

```bash
$ git diff core/retrieval.py
# (empty)
```

---

## §3 테스트 실행 결과

```
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.1.1, pluggy-1.6.0 -- /Users/David/envs/dbma311/bin/python
cachedir: .pytest_cache
rootdir: /Users/David/DBMA
configfile: pyproject.toml
plugins: anyio-4.14.0, cov-7.1.0, Faker-40.23.0, langsmith-0.9.1

collecting ... collected 9 items

tests/test_parallel_retriever.py::TestParallelRetrieverT1Axis::test_t1_axis_wraps_retrieve_engine PASSED [ 11%]
tests/test_parallel_retriever.py::TestParallelRetrieverT1Axis::test_t1_axis_preserves_retrieve_signature PASSED [ 22%]
tests/test_parallel_retriever.py::TestParallelRetrieverT2Axis::test_t2_axis_queries_bible_tag_annotation PASSED [ 33%]
tests/test_parallel_retriever.py::TestParallelRetrieverT2Axis::test_t2_axis_empty_when_no_tag_names PASSED [ 44%]
tests/test_parallel_retriever.py::TestParallelRetrieverMerge::test_merge_t1_before_t2 PASSED [ 55%]
tests/test_parallel_retriever.py::TestClassifyEvidence::test_classify_groups_by_axis PASSED [ 66%]
tests/test_parallel_retriever.py::TestSprintABRegression::TestSprintABRegression::test_sprint_a_regression_all_candidates_preserved PASSED [ 77%]
tests/test_parallel_retriever.py::TestSprintABRegression::TestSprintABRegression::test_sprint_b_regression_tag_annotation_preserved PASSED [ 88%]
tests/test_parallel_retriever.py::TestCoreRetrievalUnmodified::test_core_retrieval_py_not_modified PASSED [100%]

============================== 9 passed in 0.12s ===============================
```

**합계: 9/9 테스트 통과**

---

## §4 구현 요약

### 4.1 `core/parallel_retriever.py` 주요 구성요소

| 요소 | 설명 |
|------|------|
| `TrustTier` (enum) | T1, T2 trust tier 정의 |
| `EvidenceCandidate` (dataclass) | T1/T2 축 결과를 감싸는 공통 인터페이스 |
| `BibleTagAnnotation` (dataclass) | bible_tag_annotation 테이블 행 매핑 |
| `ParallelRetriever` (class) | T1(기존 retrieve) + T2(tag 조회) 병렬 실행 |
| `classify_evidence()` (func) | evidence_axis 기준 그룹화 헬퍼 |

### 4.2 설계 결정

1. **T1 축**: `RetrievalEngine.retrieve()`를 시그니처 변경 없이 그대로 감싸서 호출. 반환된 `RankedCandidate`를 `EvidenceCandidate(evidence_axis="t1_hybrid_search", trust_tier=T1)`로 감쌈.
2. **T2 축**: `tag_names`가 주어지면 `bible_tag_annotation` 테이블에서 `tag_name IN tag_names`인 행을 `canonical_reference` 정경 순서로 조회. 각 행을 `EvidenceCandidate(evidence_axis="t2_curated_tag", trust_tier=T2)`로 감쌈.
3. **병합**: T1 결과를 먼저, T2 결과를 그 다음으로 리스트에 합침 (점수 재정렬 없이 축 구분 유지).
4. **ScriptureReference**: `core/retrieval.py`에서 import해서 정경 순서 비교에 재사용 (새로 구현하지 않음).

### 4.3 Sprint A/B 회귀 검증

- **Sprint A (T1)**: `MockRetrievalEngine`으로 30개 candidate를 mock하고, 모든 candidate가 `EvidenceCandidate`에 감싸져 전달되는지 검증 — **30/30 통과**.
- **Sprint B (T2)**: 30개 tag annotation을 fixture DB에 넣고, 모두 조회되어 전달되는지 검증 — **30/30 통과**.

---

## §5 Sprint D 착수 전 CUE 확인이 필요한 사항 (§2.4 기준)

1. **Morphology/lemma/commentary/LLM 후보확장 검색 축**: 실 데이터 없음. 후속 Task Order로 미룸.
2. **여러 데이터셋 간 `ranking_weight` 교차 정렬**: Sprint D에서 ClaimGuard와 함께 설계.
3. **UI 배지 표시**: Sprint D 이후.
4. **Sprint A/B 테스트 30/30의 실제 RetrievalEngine과의 통합**: 현재는 MockRetrievalEngine으로 검증. 실제 RetrievalEngine으로의 통합 테스트는 Sprint D에서 수행 권장.

---

## §6 파일 diff 요약

### `core/parallel_retriever.py` (신규, 248줄)
- `TrustTier` enum: T1, T2 정의
- `EvidenceCandidate` dataclass: T1/T2 공통 인터페이스
- `BibleTagAnnotation` dataclass: DB 행 매핑
- `ParallelRetriever.retrieve()`: T1+T2 병렬 실행 로직
- `classify_evidence()`: axis별 그룹화 헬퍼

### `tests/test_parallel_retriever.py` (신규, 405줄)
- `MockRankedCandidate`, `MockRetrievalEngine`: T1 축 mock
- `_create_test_db()`: T2 축 fixture DB 생성
- `TestParallelRetrieverT1Axis`: T1 축 2 테스트
- `TestParallelRetrieverT2Axis`: T2 축 2 테스트
- `TestParallelRetrieverMerge`: 병합 1 테스트
- `TestClassifyEvidence`: classify_evidence 1 테스트
- `TestSprintABRegression`: Sprint A/B 회귀 2 테스트 (30/30)
- `TestCoreRetrievalUnmodified`: git diff 검증 1 테스트