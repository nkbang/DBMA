# C1 Task Order 052 — open_or_build_index()가 stale 인덱스를 감지 못하는 버그 수정 (TDD 게이팅)

**상태**: 발급됨 — 착수 가능
**우선순위**: P2 (`C1-TASK-ORDER-050-REPORT.md` §5 Remaining Blockers #1 —
"영어 쿼리 결과 없음"의 근본원인. gold standard 96개 재실행이 이 수정을
전제조건으로 막혀있음)
**근거**: CUE가 코드를 직접 읽고 실제 버그로 확인, 실패 테스트까지 이미
작성·확인(red)해뒀다 — C1은 그 테스트를 통과시키는 최소 diff만 만들면 된다.

---

## 0. 지금까지 확인된 사실 (재조사하지 말고 이 결과를 출발점으로 삼을 것)

`core/candidate_generator.py::open_or_build_index()`(138~145행):

```python
def open_or_build_index(tsu_dataset_path: str | Path, index_dir: str | Path) -> "CandidateGenerator":
    index_dir = Path(index_dir)
    if not (index_dir / "meta.json").exists():
        build_index(tsu_dataset_path, index_dir)
    return CandidateGenerator(index_dir)
```

`meta.json` **파일 존재 여부만** 확인한다 — 인덱스 안 문서 수가 현재
`tsu_dataset_path`의 실제 레코드 수와 일치하는지는 전혀 확인하지 않는다.
`C1-TASK-ORDER-050-REPORT.md` §5(2026-08-21, 가장 최근 산출물)가 이로 인한
실제 사고를 기록해뒀다: BM25 인덱스(~80,000 docs)와 현재 `tsu_by_id`
(53,963 entries)가 어긋나 있어 영어 쿼리 결과가 0건이 나왔고("BM25가
반환한 tsu_id가 tsu_by_id에 없어 metadata 조회 실패 → score=0 → RRF
필터링"), 원인 규명 후 "BM25 인덱스 재빌드 또는 TSU 매니페스트 정합성
점검 필요 — Task Order 050 범위 밖"으로 후속 작업으로 넘겨진 상태다.
이후 커밋 어디에도 수정이 없다(CUE가 git log로 재확인 완료).

참고할 만한 기존 패턴(그대로 베끼라는 뜻은 아님, 설계 아이디어만):
`core/hybrid_candidate_pipeline.py:250`의 `core.bible_index.py::_row_count()`
+ `if not bible_path.exists() or _row_count(bible_path) == 0:` — 다만 이건
"파일이 비어있는지"만 보는 더 단순한 체크이고, 이번 버그는 "존재하고
비어있지도 않지만 **개수가 현재 데이터셋과 다른**" 경우라 그대로
재사용은 안 된다.

**CUE가 이미 작성한 실패 테스트** (`tests/test_candidate_generator.py`,
`TestOpenOrBuildIndexStaleness` 클래스, `TestBuildIndex` 바로 다음에
추가돼 있음):

```
tests/test_candidate_generator.py::TestOpenOrBuildIndexStaleness::test_stale_index_is_rebuilt_when_dataset_changes FAILED
tests/test_candidate_generator.py::TestOpenOrBuildIndexStaleness::test_matching_index_is_not_rebuilt_unnecessarily PASSED
```

두 번째 테스트가 이미 통과하는 건 지금은 애초에 아무것도 재빌드를 안 하기
때문(우연한 통과) — 수정 후에도 이 테스트가 계속 통과해야 한다는 게
핵심 제약이다 (§2 참고).

## 1. 목표

위 두 테스트가 모두 PASSED 되도록 `open_or_build_index()`에 최소 diff를
넣는다.

## 2. 수정 범위 (여기만 건드릴 것) — 성능 제약 반드시 준수

- `core/candidate_generator.py`의 `open_or_build_index()` 함수만 수정.
- **핵심 제약**: `C1-TASK-ORDER-033-REPORT.md` §2 실측치에 따르면 Tantivy
  100k 문서 색인이 61.87초, 300k가 195.37초 걸린다. `meta.json`이 존재할
  때마다 무조건 재빌드하는 방식으로 "고치면" 정확성 버그 하나를 고치는
  대신 프로덕션에서 매 프로세스 시작마다 몇 분씩 걸리는 훨씬 심각한
  성능 회귀를 새로 만드는 것이다 — 반드시 피할 것.
  `test_matching_index_is_not_rebuilt_unnecessarily`가 정확히 이 회귀를
  잡기 위한 테스트다: 데이터셋이 안 바뀌었으면 재빌드가 일어나지
  않아야 한다(`meta.json`의 mtime이 그대로 유지돼야 함).
- 구현 방식은 자유— 예를 들면: 현재 인덱스를 열어서 문서 수
  (`tantivy.Index.open(index_dir).searcher().num_docs`, 새 인스턴스를 또
  만들 필요 없이 확인만)를 세고, `tsu_dataset_path`의 실제 레코드 수(파일
  라인 수, `build_index()`가 이미 하는 것과 같은 방식으로 세면 됨)와
  비교해서 다르면 그때만 `build_index()`를 호출하는 식. 다른 접근이어도
  두 테스트만 통과하면 된다.

## 3. 하지 않을 것

- `tests/test_candidate_generator.py`를 포함해 **테스트 파일은 절대
  수정하지 마라** — 이미 CUE가 작성·확인 완료했다.
- `build_index()`, `CandidateGenerator` 클래스, `core/bible_index.py`,
  `core/hybrid_candidate_pipeline.py`, `core/index_orchestrator.py` 등
  다른 파일/함수는 건드리지 않는다 — `open_or_build_index()` 호출부는
  이미 5곳(`hybrid_candidate_pipeline.py` 1곳, `index_orchestrator.py`
  3곳)에서 시그니처 그대로 쓰고 있으므로 함수 시그니처(파라미터/반환
  타입)도 바꾸지 마라.
- 96개 book-level gold standard 재실행 — 이 Task Order 범위 아님(이
  버그가 그 재실행을 막고 있던 선행 조건일 뿐, 재실행 자체는 별도).
- git add/commit 금지.

## 4. 완료 조건

- [ ] `cd ~/DBMA && source ~/envs/dbma311/bin/activate` 후
      `pytest tests/test_candidate_generator.py -v` 전체 실행 — 19개
      전부 PASSED (기존 18개 + staleness 테스트 1개가 이제 통과로 바뀜)
- [ ] `git diff core/candidate_generator.py`가 `open_or_build_index()`
      근처 몇 줄짜리 diff인지 그대로 보고서에 붙여넣을 것 (실제 diff,
      요약 금지)
- [ ] `pytest tests/` 전체 실행 결과도 붙여넣을 것 (다른 파일 회귀
      없는지 — 특히 `test_hybrid_candidate_pipeline.py`,
      `test_index_orchestrator.py` 관련 있으면 확인)
- [ ] 짧은 완료 보고만 (순수 구현 작업, 별도 보고서 파일 불필요 — 채팅
      응답에 diff만 붙여넣으면 충분)

## 5. 완료 후

CUE가 diff를 직접 읽고 `pytest tests/test_candidate_generator.py`로
독립 재검증한다.
