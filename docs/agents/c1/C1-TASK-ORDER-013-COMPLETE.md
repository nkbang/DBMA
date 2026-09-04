# C1 Task Order 013 — 완료 보고서 (CUE 검수 후 정정본)

## 작업 요약

**제목:** 성경책별 임베딩 커버리지 리포트 기능 구현

**완료일:** 2026-07-24

**상태:** ✅ 완료 (신규 테스트 4 passed, 전체 회귀 재실행 완료 — 아래 참고)

**정정 사유(2026-07-24, CUE)**: C1이 작성한 원본 완료 보고서(§2.2)가
실제 코드와 불일치했다 — `st.metric`/`st.dataframe`/`st.progress`,
`threshold=0.95`, `engine`/`cache`를 인자로 받는 함수 시그니처를
서술했으나 실제 `ui/pages/monitor.py`에는 파라미터 없는 함수,
`st.markdown` bullet list, 기본값 `threshold=1.0`만 존재함(grep으로
직접 확인). 이 문서는 실제 코드를 다시 읽고 정정한 버전이다 — 코드
자체는 안전하고 정확했고(아래 §2 재검증 참고), 문제는 보고서 서술에만
있었다.

---

## 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `core/retrieval.py` | 신규 메서드 | `RetrievalEngine.book_embedding_coverage()` 추가 (retrieval.py:1268) |
| `ui/pages/monitor.py` | 신규 함수·호출 | `_render_embedding_coverage_report()` 추가(monitor.py:366) + `render_monitor_page()`에서 호출(monitor.py:58) |
| `tests/test_book_embedding_coverage.py` | 신규 파일 | 4개 테스트 케이스 |

---

## §2 — 구현 상세 (CUE가 실제 코드로 재확인)

### 2.1 `core/retrieval.py` — `book_embedding_coverage()`

```python
def book_embedding_coverage(
    self,
    cache: EmbeddingCache,
    threshold: float = 1.0,
) -> dict[str, dict]:
```

**실제 동작(코드 직접 확인)**:
- `self.tsus` 순회, book_id별 total/embedded/dimension_ok 집계 — `book_coverage()`와 동일 read-only 패턴
- `cache.lookup()` 호출 안 함 — `cache._hash_text(content)`로 해시를 직접 계산하고 `cache.cache_dir / f"{hash}.json"` 경로를 직접 구성해 파일 존재만 확인(CUE가 최초 계획 검토 시 `lookup()`의 embed_fn 트리거 위험을 지적해 이 방식으로 설계됨)
- 캐시 파일이 있으면 JSON을 열어 `vector` 필드 길이가 `EMBEDDING_DIMENSION`(1024)과 같은지 검증
- `coverage_ratio = embedded / total`, `coverage_ratio < threshold`(기본 1.0)인 책만 반환 dict에 포함
- 반환 형식: `{"GEN": {"total": 42, "embedded": 40, "dimension_ok": 39, "coverage_ratio": 0.952...}}`

**기존 코드 변경:** 없음 (신규 메서드만 추가, 확인됨)

**CUE 수정 1건**: docstring이 "cache.lookup()은 LRU order를 변경하므로
호출 안 함"이라 서술했으나, `EmbeddingCache`엔 LRU 메커니즘 자체가
없다(파일 기반 캐시 + hit/miss 카운터뿐) — 진짜 위험은 "embed_fn 호출로
새 캐시 파일이 쓰여지는 부작용"이었다. docstring을 정확한 근거로
수정함(CUE, retrieval.py:1278 부근).

### 2.2 `ui/pages/monitor.py` — 커버리지 리포트 (실제 코드, 이전 보고서와 다름)

```python
def _render_embedding_coverage_report() -> None:
    """book_embedding_coverage() 기반: 커버리지 미달 책만 보여주는 리포트."""
```

**실제 동작(파라미터 없음 — 이전 보고서의 `(engine, cache)` 시그니처
서술은 오류였음)**:
- 함수 내부에서 직접 `RetrievalEngine(DEFAULT_TSU_DATASET_PATH)`와
  `EmbeddingCache(...)`를 생성(호출부에서 주입하지 않음)
- 예외 발생 시 `st.warning("커버리지 데이터를 로드할 수 없습니다.")`로
  폴백
- 커버리지 미달 책이 하나도 없으면 `st.info("📚 모든 책의 임베딩
  커버리지가 100%입니다.")`
- 미달 책이 있으면 `st.markdown()`으로 책별 한 줄씩 bullet list 출력
  (`- **GEN**: 40/42 chunks (95.2%) — dimension_ok: 39` 형식) —
  `st.metric`/`st.dataframe`/`st.progress`는 사용되지 않음
- `render_monitor_page()`에서 "임베딩 커버리지 리포트" 섹션으로 호출됨
  (monitor.py:56-58)

**기존 코드 변경:** 없음(신규 함수·신규 섹션 호출 추가만)

**참고(사소, 블로킹 아님)**: `book_embedding_coverage(cache)`를 기본
`threshold=1.0`으로 호출하므로 반환값이 이미 미달 책만 담고 있는데,
그 위에서 `coverage_ratio < 1.0` 재필터를 한 번 더 한다 — 결과에는
영향 없는 중복 코드. 또한 페이지를 열 때마다 `RetrievalEngine`을 새로
생성해 TSU 데이터셋(현재 52,064건)을 매번 다시 로드함 — 정확성 문제는
아니지만, 세션 공유 인스턴스(`ui/state/query_processor.py`의 패턴)를
쓰면 더 가볍다. 이번 Task Order 범위 밖이라 별도 후속 과제로 남김.

### 2.3 `tests/test_book_embedding_coverage.py` — 4개 테스트 케이스

| 케이스 | 설명 | CUE 직접 재실행 |
|--------|------|--------|
| `test_all_books_full_coverage` | 모든 chunk 임베딩 → 결과 empty | ✅ PASSED |
| `test_partial_embedding` | 일부만 임베딩 → coverage_ratio < 1.0 | ✅ PASSED |
| `test_empty_cache_returns_zero_coverage` | 캐시 비어있음 → coverage_ratio == 0.0 | ✅ PASSED |
| `test_dimension_validation` | dimension != 1024 → dimension_ok 카운트 제외 | ✅ PASSED |

`pytest tests/test_book_embedding_coverage.py -q` → `4 passed in 0.04s`
(CUE가 직접 재실행해 확인, 원본 보고서 수치와 일치)

**Task Order §3의 케이스 (d)("TSU가 아예 없는 book_id 질의 시 누락
처리")는 정확히 그 형태로 테스트되지 않고, 대신 "캐시가 비어있는 경우"
테스트로 대체됨** — 반환값이 일반 dict라 없는 키는 어차피 `.get()`
등에서 자연히 누락 처리되므로(기존 `book_coverage()`와 동일 계약)
실질적 위험은 낮음. CUE가 승인.

---

## §3 — 회귀 테스트 (CUE 재실행 결과)

**2026-07-24 CUE 직접 실행:** `pytest tests/ --tb=short` → **734 passed, 0 failed, 11 warnings**(기존 경고)

소요 시간: 145.62s (2분 25초)

## §3.1 — 드라이 런 결과

`book_embedding_coverage()` 메서드 실제 실행 검증:
- 캐시 파일이 있는 경우: coverage_ratio 계산 정확
- 캐시 파일이 없는 경우: coverage_ratio == 0.0
- TSU가 없는 book_id: 결과에 포함되지 않음 (정상 동작)

---

## §4 — 하지 않은 변경 (제약 준수, CUE 확인)

| 파일 | 상태 |
|------|------|
| `core/embedder.py` | ✅ 수정 금지 — 미변경 확인 |
| `core/tsu_builder.py` | ✅ 수정 금지 — 미변경 확인 |
| `EmbeddingCache`, `book_coverage()` 기존 코드 | ✅ 변경 금지 — 미변경 확인 |
| `cache/embeddings/` 실제 파일 | ✅ 건드리지 않음 — `cache.lookup()`/`embed_fn` 미호출 확인 |

---

## §5 — CUE 검토 결론

- 코드 자체: **안전, 정확, 승인** — read-only 계약 준수 확인, 테스트
  직접 재실행 통과.
- docstring 오류 1건(LRU 관련 근거 오류) CUE가 직접 수정.
- 완료 보고서 서술과 실제 코드 불일치 — 이 문서로 정정.
- 커밋은 CUE가 진행(C1은 직접 커밋하지 않음, Task Order 원칙 준수 확인).
