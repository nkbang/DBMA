// deno-fmt-ignore-file
# C1 Task Order 013 — 성경책별 임베딩 커버리지 리포트 구현

발급: CUE (2026-07-24)
대상: C1 (Cline 작업창 #1) — **반드시 새 Task/새 세션으로 시작**
성격: **구현 Task.** 아래 §2의 설계를 그대로 코드로 옮긴다. 설계를
다시 바꾸지 않는다 — 이미 CUE-사용자 간 합의된 표준이다.

---

## 1. 배경

사용자가 "성경책별 임베딩 정도 상황을 보고하는 기능"을 요청했다.
CUE가 검토한 결과, 업계 표준(Coverage Ratio + Staleness Detection +
Coverage Heatmap 조합, Pinecone/Weaviate/LlamaIndex의 ingestion
커버리지 리포트 패턴과 동일 철학)을 DBMA에 이미 존재하는 인프라 위에
얹는 방식으로 설계했다 — **신규 인프라 도입 없음**:

- `core.retrieval.RetrievalEngine.book_coverage()`(이미 존재,
  retrieval.py:1250) — book_id별 TSU 그룹핑을 이미 하고 있다.
- `core.retrieval.EmbeddingCache`(이미 존재, retrieval.py:575) —
  SHA256 해시 기반 캐시(`_hash_text()`, retrieval.py:594)로 "이
  텍스트가 이미 임베딩됐는가"를 조회할 수 있다.
- `core.config.EMBEDDING_DIMENSION`(=1024) — 임베딩 차원 검증 기준.
  오늘 세션에서 `core.embedder.embed()`가 과거에 차원 불일치를
  조용히 삼키던 버그가 있었음이 확인됐다(ADR-008 §1 재보정 기록) —
  같은 근본원인이 재발하지 않도록 이번 리포트는 "임베딩 존재 여부"
  뿐 아니라 "차원이 1024가 맞는가"도 함께 검증한다.

## 2. 설계 (그대로 구현)

### 2.1 신규 함수: `core/retrieval.py::RetrievalEngine.book_embedding_coverage()`

```python
def book_embedding_coverage(self, cache: EmbeddingCache) -> dict[str, dict]:
    """book_id별 (total_chunks, embedded_chunks, dimension_ok_chunks) 집계.
    book_coverage()와 동일 패턴(self.tsus 순회, read-only) — 새 코퍼스
    접근 경로 만들지 않는다."""
```

- `self.tsus`를 순회하며 book_id별로:
  - `total_chunks`: 해당 book_id를 가진 TSU 총 개수
  - `embedded_chunks`: `cache._hash_text(content)`로 캐시 파일
    존재 여부 확인(캐시 파일 열어서 `vector` 필드 존재 확인 —
    `EmbeddingCache.validate()`의 기존 로직과 동일 방식 재사용,
    새 검증 로직 새로 발명하지 말 것)
  - `dimension_ok_chunks`: 캐시된 vector의 `len(vector) ==
    EMBEDDING_DIMENSION`인 개수
- 반환: `{book_id: {"total": N, "embedded": N, "dimension_ok": N,
  "coverage_ratio": embedded/total}}`
- book_coverage()와 동일하게 **read-only**, 커버리지 0인 책은
  결과 dict에서 생략(누락 키 = 0으로 취급, book_coverage()의 계약과
  동일하게 유지)

### 2.2 UI: Dashboard 또는 Monitor 페이지에 리포트 표시

- `ui/pages/monitor.py`에 새 섹션 추가(개발자용 상세 정보라 Monitor가
  적합 — Dashboard는 사용자용 요약이라는 기존 설계 원칙,
  `ui/README.md`의 "Dashboard vs Monitor 분리" 참고)
- 66권 전체가 아니라 **coverage_ratio < 1.0인 책만** 목록으로 표시
  (전부 100%면 "전체 커버리지 정상" 한 줄만 표시 — 불필요한 정보
  나열 금지)
- 각 행: 책 이름, `embedded/total`, coverage_ratio(%), dimension_ok
  중 total과 다르면 "⚠️ 차원 불일치 N건" 경고 표시

### 2.3 하지 말 것

- `core/embedder.py`, `core/tsu_builder.py` 수정 금지 — 이번 Task는
  순수 리포트(read-only 집계) 기능이다. 임베딩을 다시 계산하거나
  고치는 로직은 범위 밖.
- `EmbeddingCache`, `book_coverage()`의 기존 코드/시그니처 변경 금지
  — 새 메서드만 추가한다.
- 캐시 파일을 직접 파싱하는 새 로직을 발명하지 말고, `EmbeddingCache.
  validate()`가 이미 하는 "JSON 열어서 vector/text 필드 확인" 패턴을
  그대로 재사용할 것(복붙 후 dimension 체크만 추가).

## 3. 테스트

- `tests/test_book_embedding_coverage.py` 신규
- 최소 케이스: (a) 전부 임베딩된 book, (b) 일부만 임베딩된 book,
  (c) 임베딩은 있으나 차원이 틀린 케이스, (d) TSU가 아예 없는 book_id
  질의 시 KeyError 대신 누락 처리
- 실제 캐시 파일(`cache/embeddings/*.json`)을 건드리지 말고
  tmp_path에 가짜 캐시 디렉터리를 만들어 테스트할 것

## 4. 완료 후

- 변경 파일 목록과 `pytest tests/test_book_embedding_coverage.py -q`
  실행 결과를 짧은 md로 남겨라(`docs/agents/c1/` 아래, 파일명 자유)
- 전체 회귀(`pytest tests/ -q`)도 실행해 기존 테스트가 깨지지
  않았는지 확인하고 결과를 같이 남길 것
- CUE 검토 요청 — CUE가 실제 코드 diff와 테스트 결과를 재검증한 뒤
  커밋한다(C1이 직접 커밋하지 않음)

## 5. 원칙 재확인

- "이미 존재합니다"라고 주장하기 전에 실제 파일을 열어 확인
  (Diagnosis rule)
- 파일 경로·함수명·개수를 문서화할 때는 반드시 실제 grep/read 결과에
  근거할 것(Path/structure documentation rule, Modelfile 참고) —
  존재를 확인 안 한 파일/함수를 산출물 문서에 적지 말 것
- 새 세션으로 시작 — 이 Task Order가 유일한 근거
