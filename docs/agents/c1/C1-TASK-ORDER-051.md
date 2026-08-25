# C1 Task Order 051 — HybridRetriever bible route가 file_scope를 무시하는 버그 수정 (TDD 게이팅)

**상태**: 발급됨 — 착수 가능
**우선순위**: P3 (버그는 실재하나 `USE_INVERTED_INDEX=true`일 때만 켜지는
옵트인 경로라 프로덕션 기본 경로엔 영향 없음)
**근거**: CUE가 코드를 직접 읽고 실제 버그로 확인, 실패 테스트까지 이미
작성·확인(red)해뒀다 — C1은 그 테스트를 통과시키는 최소 diff만 만들면 된다.

---

## 0. 지금까지 확인된 사실 (재조사하지 말고 이 결과를 출발점으로 삼을 것)

`core/hybrid_candidate_pipeline.py::HybridRetriever.retrieve()`
(107~135행)에서 라우트별 분기를 보면 exact/metadata/greek·hybrid 세 분기는
전부 `self.candidate_generator.search(..., source_files=file_scope, ...)`로
`file_scope`를 넘기는데, **`bible` 분기(107~121행)만 `file_scope`를 완전히
무시**한다:

```python
if plan.route == "bible" and self.bible_index is not None:
    seen: set[str] = set()
    candidate_tsu_ids = []
    for ref in parsed_query.scripture_refs:
        for tsu_id in self.bible_index.lookup_scripture_ref(ref):
            if tsu_id not in seen:
                seen.add(tsu_id)
                candidate_tsu_ids.append(tsu_id)
    candidates = [
        CandidateRef(tsu_id=tid, bm25_score=1.0) for tid in candidate_tsu_ids[:candidate_k]
    ]
```

`BibleIndex.lookup_scripture_ref()`는 tsu_id만 반환하고 source_file 정보를
갖고 있지 않다(`core/bible_index.py` 확인) — 그래서 스코프 필터링이 되려면
`self.tsu_by_id`(생성자에서 이미 받는 `dict[str, dict[str, Any]]`, 각
레코드에 `source_file` 키 있음, `tests/test_hybrid_candidate_pipeline.py`의
`FIXTURE_TSUS` 참고)로 tsu_id → source_file을 역참조해야 한다.

**CUE가 이미 작성한 실패 테스트** (`tests/test_hybrid_candidate_pipeline.py`,
`TestBibleRouteFileScope` 클래스, 파일 맨 아래 `TestHybridQueryProcessor`
바로 앞에 추가돼 있음):

```
tests/test_hybrid_candidate_pipeline.py::TestBibleRouteFileScope::test_bible_route_respects_file_scope FAILED
tests/test_hybrid_candidate_pipeline.py::TestBibleRouteFileScope::test_bible_route_file_scope_excludes_other_file FAILED
tests/test_hybrid_candidate_pipeline.py::TestBibleRouteFileScope::test_bible_route_file_scope_none_returns_both PASSED
```

세 번째 테스트가 이미 통과한다는 것은 fixture 데이터 자체(같은 "롬 8:28"
구절을 가리키지만 `source_file`이 다른 TSU 두 개)는 문제없이 세팅됐다는
뜻 — file_scope 미적용이라는 버그 자체만 잡으면 된다.

## 1. 목표

위 세 테스트가 모두 PASSED 되도록, **`HybridRetriever.retrieve()`의
bible 분기에만** 최소 diff를 넣는다.

## 2. 수정 범위 (여기만 건드릴 것)

- `core/hybrid_candidate_pipeline.py` — `retrieve()`의 `if plan.route ==
  "bible" ...` 분기(현재 107~121행 부근)에서만 수정. `file_scope`가
  주어졌을 때 `self.tsu_by_id.get(tid, {}).get("source_file")`가
  `file_scope` 안에 있는 tsu_id만 남기면 된다 — 다른 라우트들이 이미
  `source_files=file_scope`로 하는 것과 같은 "정확 일치 allowlist" 의미를
  그대로 따를 것 (docstring 82~84행 참고).
- `file_scope`가 `None`이면(스코프 없음) 기존처럼 전부 통과시켜야 한다 —
  `test_bible_route_file_scope_none_returns_both`가 이미 이걸 보장한다.

## 3. 하지 않을 것

- `tests/test_hybrid_candidate_pipeline.py`를 포함해 **테스트 파일은 절대
  수정하지 마라** — 이미 CUE가 작성·확인 완료했다. 테스트가 이상해
  보여도 먼저 질문할 것, 임의로 고치지 말 것.
- `core/bible_index.py`, `core/candidate_generator.py`, `core/retrieval.py`
  등 다른 파일은 건드리지 않는다.
- exact/metadata/greek·hybrid 등 다른 라우트 분기 로직 변경 금지 — 이미
  올바르게 동작 중.
- `USE_INVERTED_INDEX` 관련 설정이나 기본값 변경 금지 — 이번 범위 아님.
- git add/commit 금지.

## 4. 완료 조건

- [ ] `cd ~/DBMA && source ~/envs/dbma311/bin/activate` 후
      `pytest tests/test_hybrid_candidate_pipeline.py -v` 전체 실행 —
      37개 전부 PASSED (기존 35개 + 새 테스트 2개가 이제 통과로 바뀜)
- [ ] `git diff core/hybrid_candidate_pipeline.py`가 bible 분기 근처
      몇 줄짜리 diff인지 그대로 보고서에 붙여넣을 것 (실제 diff, 요약 금지)
- [ ] `pytest tests/` 전체 실행 결과도 붙여넣을 것 (다른 파일 회귀 없는지)
- [ ] 짧은 완료 보고만 (이 Task Order는 원인·설계 논의가 필요 없는 순수
      구현 작업이므로 보고서 별도 파일 불필요 — 채팅 응답에 diff만
      붙여넣으면 충분)

## 5. 완료 후

CUE가 diff를 직접 읽고 `pytest tests/test_hybrid_candidate_pipeline.py`로
독립 재검증한다.
