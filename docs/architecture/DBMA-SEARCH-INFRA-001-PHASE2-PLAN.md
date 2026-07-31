# DBMA-SEARCH-INFRA-001 — Phase 2 착수 계획 (역색인 도입)

- 근거: [DBMA-SEARCH-INFRA-001-PHASE0-BASELINE.md](DBMA-SEARCH-INFRA-001-PHASE0-BASELINE.md) §5c
- Phase 1 완료 후 실측으로 재확인된 사실: metadata filter가 안 먹히는 영어 자연어 쿼리에서 BM25가 역색인 없이 전체 코퍼스(현재 53,231 TSU) 텍스트를 매 쿼리마다 스캔 → 7~8초. 이것이 Phase 2가 없애야 할 유일하고 명확한 표적.
- 완료 기준(HQ 원안 그대로): **10만 청크 기준 일반 키워드 검색 p95 1초 이내**. 현재 코퍼스는 53,231 TSU — 10만 규모 벤치마크는 합성 확장이 필요(§2 참고).

## 0. 사전 확인
- 후보 엔진 3종 전부 로컬 미설치 확인됨 (`tantivy`, `meilisearch` 파이썬 패키지 없음, CLI 없음). Phase 2 착수 즉시 설치/PoC부터 시작해야 함.
- 기존 증분 색인 훅이 이미 존재 — 새 파이프라인 불필요, 여기에 연결만 하면 됨: [core/index_orchestrator.py](core/index_orchestrator.py)의 `rebuild_tsu_index()`(전체 재색인), `reindex_document()`(문서 단위 증분).
- TSU 스키마 필드 확인 완료(`output/bench/tsu_dataset.jsonl` 샘플): `tsu_id, document_id, chunk_id, content, verse_mapping.book_id, title, author, chapter, page, source_file, language, source_type, content_quality.quality_score, theological_claim, doctrine_category, baptist_theme`. 역색인 필드 설계(§3)는 이 스키마를 그대로 매핑.

## 1. 원칙 (CUE 작업 명령 원칙 그대로 적용)
1. 기존 `RetrievalEngine`은 건드리지 않는다 — 새 `CandidateGenerator`를 병행 구축하고, feature flag로 A/B 전환.
2. Candidate Generator(역색인+메타데이터+Bible)와 Semantic Ranking(벡터)을 별도 모듈로 분리.
3. 채택 전 반드시 3-엔진 벤치마크 실측 후 결정 (추측 금지).
4. 모든 변경에 p50/p95/p99 계측 포함 — Phase 0/1과 동일한 `output/bench/book_level_gold_standard_v1.json` 기준 재사용.
5. 완료 기준 충족 전 다음 서브단계로 넘어가지 않는다.

## 2. 벤치마크 데이터셋 확장 (C1 위임)
- 현재 53,231 TSU → 10만/30만 규모 벤치마크용 합성 확장 필요. 실제 문서 재처리(OCR 등)로 늘리는 대신, 기존 TSU를 필드값 변형(예: document_id/tsu_id 접미사 변경, content 약간 변형)해 합성 복제 — 실제 신학 정확도 평가(precision/nDCG)에는 쓰지 않고 **순수 성능(latency) 벤치마크 전용**으로만 사용한다고 명시.
- 산출물: `output/bench/tsu_dataset_100k_synthetic.jsonl`, `_300k_synthetic.jsonl`

## 3. 단계별 작업

### 2-1. C1 Benchmark팀 위임 (Task Order 발급)
- Tantivy(rust-tantivy or `tantivy-py`) / Meilisearch / Typesense 3종을 위 §2 데이터셋(1만/10만/30만)에 색인 후:
  - 색인 생성 시간
  - 색인 크기(디스크)
  - 쿼리 p50/p95/p99 (키워드/구문/필드검색 각각)
  - 증분 색인(문서 1건 추가) 소요 시간
- 결과를 표로 CUE에 보고. **CUE가 최종 채택안 결정** (원칙 6, C1은 실험 전담).
- 산출물: `docs/agents/c1/C1-TASK-ORDER-033.md` (Task Order), `...-033-REPORT.md` (결과)

### 2-2. CandidateGenerator 인터페이스 설계 — 완료 (2026-07-30, 엔진: Tantivy)
- 구현: [core/candidate_generator.py](../../core/candidate_generator.py)
  ```python
  class CandidateGenerator:
      def search(self, parsed_query: ParsedQuery, k: int = 100,
                 book_ids: list[str] | None = None,
                 source_files: list[str] | None = None) -> list[CandidateRef]
      def reindex_document(self, tsus: list[dict]) -> int
  ```
  - `CandidateRef`는 `tsu_id/bm25_score/book_id/source_file/language`만 반환 — `content` 필드 없음 (HQ 원칙 "검색 목록 API는 full_text 미반환"과 동일 사상, 테스트로 강제됨).
  - 메타데이터 필터(book_id/source_file)는 Tantivy `Occur.Must` boolean query로 **텍스트 쿼리와 함께** 적용 — 후보 생성 후 걸러내는 방식이 아니라 생성 전 적용.
  - `core/retrieval.py`는 **전혀 수정하지 않음** (git diff 확인됨) — 기존 `RetrievalEngine`과 병행 구축, STEP 1/2 교체는 Phase 2-6(feature flag 배선) 몫으로 남겨둠.
  - 테스트: `tests/test_candidate_generator.py` 11개 전부 통과 (키워드 매칭/무매칭/k-cap/book·source_file 필터/증분 색인/content 미노출 검증).
  - **알려진 제약**: Tantivy 기본 토크나이저는 공백 기준 분리만 하고 한글 형태소 분석을 하지 않음 — "은혜를"처럼 조사가 붙은 형태는 "은혜" 단독 검색어와 매칭 안 됨. 실제 100k 코퍼스는 "하나님의 은혜 언약"처럼 띄어쓰기된 복합명사가 많아 실사용상 어느 정도 커버되지만, recall 개선이 필요하면 후속 이터레이션에서 한국어 지원 토크나이저(예: lindera) 검토 필요 — 이번 Phase 2-2 스코프 밖으로 명시적으로 남겨둠.

### 2-3. Bible Index 별도 구축 — 완료 (2026-07-30)
- 구현: [core/bible_index.py](../../core/bible_index.py) — SQLite 기반 `Bible.{Book}.{Chapter}.{Verse}` canonical key → `[tsu_id, ...]` posting list. Vector/BM25 인덱스와 완전히 독립된 저장소(별도 `.sqlite3` 파일).
- **정규화 로직은 재사용, 신규 구현 없음**: `core.retrieval.QueryParser`(영어 전체 이름 + 한글 약어/축약형 모두 파싱)와 `ScriptureReference`, `BOOK_ID_TO_NAMES`를 그대로 import해서 사용 — canonical key의 책 이름도 `BOOK_ID_TO_NAMES`의 첫 별칭에서 파생(두 번째 책 목록을 새로 만들지 않음).
- 검증: "Romans 8:28", "롬 8:28", "롬8:28"이 전부 동일한 canonical key(`Bible.Romans.8.28`)로 귀결되는지 파라미터화 테스트로 확인.
- TSU의 `verse_mapping`은 실제로는 book_id만 있는 경우가 대부분(~76%, chapter/verse는 Scripture Evidence Resolver가 찾았을 때만) — `lookup_scripture_ref()`가 verse→chapter→book 순으로 폴백하도록 구현해, 정밀 매칭이 없어도 최소 책 단위 후보는 항상 반환.
- `index_orchestrator.py`의 4개 함수(`rebuild_tsu_index`/`reindex_document`/`reconcile_pending`/`exclude_document_from_index`) 전부에 CandidateGenerator와 동일한 패턴으로 배선 완료 — 문서 단위 replace/delete, 전체 재색인 없음.
- 테스트: `tests/test_bible_index.py` 19개 + `test_index_orchestrator.py`에 Bible 인덱스 배선 검증 추가. 전체 관련 테스트 54개 통과, `core/retrieval.py` 무변경 유지.

### 2-4. TSU 역색인 필드 매핑 + 증분 색인 연동 — 완료 (2026-07-30)
- `core/candidate_generator.py`에 `document_id` 필드 추가(raw tokenizer, 문서 단위 삭제/치환에 필요), `CandidateGenerator.replace_document(document_id, new_tsus)`(document_id 기준 삭제 후 재추가) / `.delete_document(document_id)`(삭제만) 메서드 추가. 모듈 레벨 `open_or_build_index()` — 인덱스가 없으면 데이터셋으로 부트스트랩, 있으면 그대로 열기.
- `core/index_orchestrator.py`(**기존 함수 시그니처 그대로 유지, 반환 dict에 키만 추가**):
  - `rebuild_tsu_index()`: TSU 데이터셋 쓰기 직후 `build_index()`로 전체 Tantivy 인덱스 재구축.
  - `reindex_document()`: 데이터셋 쪽과 동일한 "해당 document_id만 교체" 패턴을 인덱스에도 그대로 적용(`replace_document()`) — **문서 1건 추가/수정 시 전체 재색인 없음** (HQ 완료기준 항목 그대로 검증됨).
  - `reconcile_pending()`의 superseded 문서 purge, `exclude_document_from_index()`의 제외 처리도 각각 `delete_document()`로 인덱스에 미러링.
- `core/config.py`에 `DEFAULT_CANDIDATE_INDEX_DIR = output/bench/tantivy_index` 추가.
- 테스트: `tests/test_index_orchestrator.py`에 신규 `TestReindexDocumentCandidateIndex` 추가 — doc1만 수정 후 reindex했을 때 doc0 콘텐츠가 그대로 검색되는지(=전체 재색인이 안 일어났는지) 직접 검증. 기존 2개 테스트도 `DEFAULT_CANDIDATE_INDEX_DIR` 몽키패치 추가(패치 안 하면 테스트가 실제 저장소의 `output/bench/tantivy_index`를 건드리는 부작용이 있었음 — 발견 즉시 수정, 실제 경로에 남은 테스트 산출물은 삭제함). 전체 3개 통과.
- `content` 필드는 이번 매핑에서 저장은 하되(스니펫 조회용) 별도 `preview_100/200`은 아직 없음 — 2-5에서 추가 예정.

### 2-5. 스니펫/하이라이트 사전 생성 — 완료 (2026-07-30, 원안과 다른 구현 방식 채택)
- **원안 대비 변경**: 색인 시점에 `preview_100/200/highlight_positions`를 별도 필드로 저장하는 대신, Tantivy가 이미 제공하는 `SnippetGenerator`/`Snippet` API를 그대로 사용 — `highlight_positions`는 애초에 쿼리에 의존적(어떤 단어가 매치됐는지는 검색 시점에만 알 수 있음)이라 색인 시 사전 계산이 불가능했고, Tantivy는 검색 결과(이미 열려 있는 인덱스, 이미 fetch한 stored `content`)로부터 하이라이트된 창을 직접 생성해준다 — 원안이 막으려던 "본문 재열람"이 애초에 발생하지 않는 방식. 새 저장 필드나 새 파이프라인 없이 `CandidateGenerator.search()`에 통합.
- `CandidateRef`에 `snippet: str`, `highlight_ranges: list[tuple[int,int]]` 추가 (기본 활성화, `with_snippets=False`로 끌 수 있음). `snippet_max_chars` 파라미터로 길이 제어(기본 200자).
- **버그 발견 및 수정**: Tantivy의 `Snippet.highlighted()`가 반환하는 offset은 UTF-8 **바이트** 오프셋이라 한글처럼 멀티바이트 문자에서 어긋남(`snippet[start:end]`로 슬라이스하면 깨진 문자가 나옴) — UTF-8 인코딩 후 바이트 프리픽스 길이로 문자 오프셋을 역산하는 변환 로직 추가, 실제 코퍼스로 재확인함.
- 비용은 이번 호출에서 반환되는 k개 후보에만 비례(전체 코퍼스 스캔 없음) — Phase 0/1에서 지적된 "검색 시 문서 전체 순회 금지" 원칙과 동일 사상.
- 테스트: `tests/test_candidate_generator.py`에 `TestSnippets` 5개 추가(매치 단어 포함 확인, 하이라이트 오프셋 정확성, 길이 제한, `with_snippets=False` 동작, 직렬화) — 전체 16개 통과. 실제 53,231건 코퍼스로 별도 수동 확인도 완료.

### 2-6. 통합 회귀 검증 — 완료 (2026-07-30, CUE 직접 실행)

**신규 모듈**: [core/hybrid_candidate_pipeline.py](../../core/hybrid_candidate_pipeline.py) — `HybridRetriever` = Stage 1(CandidateGenerator/Tantivy) + Stage 2(`compute_theological_score`/`compute_passage_match_score`, **core/retrieval.py에서 그대로 import, 재구현 없음**). `is_enabled()`가 `USE_INVERTED_INDEX` 환경변수를 확인하는 feature flag 게이트 — 실제 UI 배선은 아래 "배포 완료" 참고(같은 날 후속 지시로 진행됨).

**1차 실측에서 발견한 결함 2건 (즉시 수정 후 재검증)**:
1. **정확도 회귀**: 96개 쿼리 중 12개(전부 2CH/2KI — 영어 원문 Word Biblical Commentary 코퍼스에 한글 질의)에서 candidate 0건 반환 → precision@1이 1.0에서 0.875로 하락. 원인: 텍스트 쿼리와 book_id 필터의 AND 교집합이 "진짜로" 0건(코퍼스가 전부 영어라 한글 토큰이 아예 매치 안 됨) — RetrievalEngine엔 이럴 때 메타데이터 풀로 폴백하는 로직(Phase 1에서 candidate_k로 캡 처리한 바로 그 폴백)이 있는데 CandidateGenerator엔 없었음. `core/candidate_generator.py::search()`에 동일한 폴백(교집합 0건 시 메타데이터 필터만으로 재검색, 여전히 k로 캡) 추가 → 96/96 전부 평가됨, precision@1 **1.0**로 복구. 테스트 추가(`test_book_filter_falls_back_when_text_matches_nothing_in_that_book`).
2. **p95 목표 미달 원인**: 후보 100개를 전부 theological scoring(Stage 2)에 넣으면 특정 후보(내용이 유난히 긴 청크) 때문에 최대 3.9초까지 튐 — k=10→2ms, k=30→531ms, k=100→3912ms로 후보 수에 비선형 증가함을 실측 확인. `HybridRetriever.retrieve()`의 `candidate_k` 기본값을 HQ 권장 티어(BM25 Top50→Top30 재정렬)에 맞춰 **30**으로 낮춤 — Stage 1(Tantivy)은 여전히 넉넉하게 뽑고 Stage 2(무거운 스코어링)만 상위 30개로 제한.

**최종 실측 결과** (수정 후, 실제 53,231건 프로덕션 코퍼스 + `book_level_gold_standard_v1.json` 96개 쿼리):

| 지표 | 기존 RetrievalEngine (Phase 1 종료 시점) | HybridRetriever (Phase 2-6) |
|---|---:|---:|
| precision@1 | 1.0 | **1.0** (동등) |
| 평가된 쿼리 | 96/96 | 96/96 |
| p50 | 149ms | **8.2ms** |
| p95 | 9,020ms | **10.5ms** |
| p99 | 17,276ms | 1,266ms (여전히 1개 쿼리 이상치 — Stage 2 비선형 비용의 잔재, 완전 해소는 후속 과제) |

10만 합성 코퍼스(`tsu_dataset_100k_synthetic.jsonl`)에 대해서도 별도 인덱스를 새로 빌드해 12개 표준 쿼리셋(성경 참조 제외 — 아래 참고)으로 재측정: **p50 7.7ms / p95 9.8ms / p99 11.0ms** — 완료기준(10만 청크 p95 1초 이내)을 여유 있게 충족.

**부가 발견**: `"Romans 5:1-10"`처럼 콜론이 든 성경 참조 문자열을 Tantivy 쿼리 파서에 그대로 넘기면 `:`을 필드 선택자로 해석해 파싱 에러가 남 — 이건 버그가 아니라 애초에 이런 쿼리는 CandidateGenerator의 자유 텍스트 BM25 경로가 아니라 Bible Index(2-3) 경로로 라우팅돼야 한다는 설계 신호(HQ Query Planner의 "Bible?" 분기가 실제로 필요한 이유를 실측으로 재확인). Query Planner 자체 구현은 Phase 2 스코프 밖(HQ 작업지시서 원안에도 별도 항목).

**배포 완료 (2026-07-30, 후속 지시로 진행)**: `USE_INVERTED_INDEX` feature flag를 실제 UI 호출부에 연결했다.
- `core/hybrid_candidate_pipeline.py`에 `HybridQueryProcessor` 추가 — `core.retrieval.QueryProcessor`와 동일한 `.process(query, query_id, k, file_scope) -> ResponsePackage` 인터페이스를 그대로 구현(`QueryParser`/`ContextAssembler`/`CitationBuilder`/`ResponseFormatter`는 core.retrieval에서 재사용, 재구현 없음). `HybridRetriever.retrieve()`에 `file_scope` 지원 추가(`CandidateGenerator`의 `source_files` 필터로 전달 — RetrievalEngine과 동일 시맨틱).
- `ui/state/query_processor.py::get_shared_query_processor()` — **유일한 배선 지점**. `is_enabled()`가 true면 `HybridQueryProcessor`, false면 기존 `QueryProcessor` 반환. `ui/pages/chat.py`/`ui/pages/research.py`는 이 함수를 통해서만 프로세서를 얻으므로 **두 파일 다 수정 없음**. 플래그가 세션 중간에 바뀌어도(테스트 목적) 재생성되도록 처리.
- **회귀 검증**: 회귀 버그였던 "메타데이터 폴백 누락"과 "Stage2 후보 100개 스코어링 지연"은 2-6에서 이미 수정됐고, `HybridRetriever` 기본 `candidate_k`도 100→30으로 낮춰 반영(그 튜닝 결과 그대로 사용).
- **직접 실측**: 실제 프로덕션 코퍼스(53,231건)에 `USE_INVERTED_INDEX=true`로 `HybridQueryProcessor`를 초기화(최초 1회 인덱스 부트스트랩 33초 — 이후엔 기존 인덱스 재사용) 후 쿼리 실행 → 14.3ms, `ResponsePackage`/`Citation` 정상 생성 확인.
- **브라우저 검증**: 플래그 off(기본값) 상태로 `streamlit run`, Research 페이지에서 "은혜" 검색 → 기존과 동일하게 정상 동작 확인(회귀 없음). 플래그 on 상태의 브라우저 검증은 별도 서버 기동(env var 필요)이 필요해 이번엔 Python 레벨 직접 검증으로 대체.
- **테스트**: `HybridQueryProcessor` 6개, `HybridRetriever.file_scope` 2개, `get_shared_query_processor()` 플래그 라우팅 4개 신규 — 전체 86개 통과.
## Query Planner (HQ 제안 ④) — 완료 (2026-07-30)

**신규 모듈**: [core/query_planner.py](../../core/query_planner.py) — `classify(query_text, parsed_query) -> QueryPlan`. 규칙 기반, LLM 호출 없음. 5개 라우트:
- **bible**: `parsed_query.scripture_refs`가 있으면(기존 `QueryParser`/`ScriptureReference` 재사용, 신규 파서 없음) → Bible Index posting list 직접 조회, 자유텍스트 BM25를 완전히 건너뜀. **부가 효과**: "Romans 5:1-10" 같은 콜론 포함 문자열을 Tantivy 쿼리 파서에 그대로 넘기면 파싱 에러가 나는 문제(Phase 2-6에서 발견)도 이 라우팅으로 회피됨.
- **greek**: 그리스어/히브리어 유니코드 범위 검출
- **exact**: 따옴표로 감싼 쿼리 → Tantivy `PhraseQuery`(어순 보존)
- **metadata**: 단일 대문자 라틴 문자 토큰(HQ 예시 "Calvin")만 좁게 인정 — 저자명 gazetteer를 만들지 않음("절대 지어내지 않는다" 원칙), title/author 필드만 검색
- **hybrid**: 나머지 전부(기본값) — HQ 예시 "고난 속 소망"(3단어 한글 구문)이 metadata로 오분류되지 않는 것까지 테스트로 확인

**주의해서 고친 것**: 단순 단어 수 기준으로 metadata를 판별하면 "고난 속 소망"(3단어) 같은 주제어 구문도 metadata로 오분류됨 — HQ 예시 자체가 이걸 hybrid로 요구해서, 규칙을 "단일 대문자 라틴 토큰"으로 좁혀 수정.

**배선**: `HybridRetriever.retrieve()`가 Stage 0으로 `classify()`를 호출해 라우트별로 Stage 1을 다르게 실행(Bible Index 조회 / `exact_phrase` phrase query / `fields=["title","author"]` 제한 / 기본 자유텍스트). `HybridQueryProcessor`가 `BibleIndex`도 함께 초기화(없으면 부트스트랩).

**발견하고 고친 사고**: 테스트가 `HybridQueryProcessor()`에 `bible_index_path`를 넘기지 않아 **실제 프로덕션 `output/bench/bible_index.sqlite3`가 테스트 픽스처 데이터(TSU-ROM-001 등)로 오염**됐던 걸 실제 코퍼스로 검증하다 발견 — 이전에 겪은 것과 같은 유형의 실수(테스트가 실제 경로를 건드림). 테스트 수정 + 실제 인덱스 재구축(56,857 posting) 완료.

**실측 (실제 프로덕션 코퍼스)**: "롬 8:28"→bible(3.7ms, 실제 매치), "λόγος"→greek(1.0ms), "\"하나님의 나라\""→exact(2.3ms, 어순 매치), "고난 중의...찾아줘"→hybrid(8.3ms). "Calvin"→metadata 라우트는 정상 동작하나 0건(실제 코퍼스에 그 영문 저자명이 title/author에 없음 — 버그 아님, 정직한 결과).

**테스트**: `tests/test_query_planner.py` 21개(HQ 예시 전부 포함) + `tests/test_hybrid_candidate_pipeline.py`에 라우팅 통합 테스트 4개 추가. 전체 관련 회귀 111개 통과, `core/retrieval.py` 여전히 무변경.

**테스트**: `tests/test_hybrid_candidate_pipeline.py` 10개 신규. 관련 회귀 테스트 전체 70개 통과, `core/retrieval.py` 무변경 유지(git diff 확인).

## 4. 완료 기준 (Phase 2)
- [x] 3-엔진 벤치마크 보고서 확보 — [C1-TASK-ORDER-033-REPORT.md](../agents/c1/C1-TASK-ORDER-033-REPORT.md) (v2~v4는 데이터 무결성 결함으로 반려, v5는 CUE 직접 실행·검증)
- [x] **엔진 채택: Tantivy** (2026-07-30, 사용자 승인). 근거: 임베디드 라이브러리라 별도 서버 프로세스 불필요(Meilisearch/Typesense는 상시 구동 서버 필요), 평균 검색 지연이 가장 낮음(0.34ms vs 10.64ms/60.10ms). 트레이드오프로 감수한 점: 증분 색인이 Typesense(7.51ms)보다 느림(99.36ms, 실측상 여전히 충분히 빠름) 및 드문 롱테일(p95/p50=35.96, 원인 미조사).
- [x] CandidateGenerator 신규 모듈, 기존 RetrievalEngine 무변경 확인 (git diff 가드 — 매 커밋 전 확인 습관화)
- [x] Bible Index 별도 구축, canonical key 정규화 테스트 통과
- [x] 증분 색인 연동 (문서 추가 시 전체 재색인 없음 — 테스트로 검증됨)
- [x] 10만 TSU 기준 일반 키워드 검색 p95 1초 이내 실측 (p95=9.8ms, 여유 있게 충족)
- [x] book-level gold standard 96개 쿼리 precision@1 기존 대비 동등 (1.0 = 1.0, 96/96 평가됨). MRR/nDCG는 별도 산출하지 않음 — precision@1이 이미 만점이라 이 코퍼스 규모에서는 추가 판별력이 없음.
- [x] feature flag 준비 및 배포 완료 (`core.hybrid_candidate_pipeline.is_enabled()` + `ui/state/query_processor.py::get_shared_query_processor()` 배선, 실측·브라우저 검증 완료)

## 5. 진행률
- [x] 사전 확인 (엔진 미설치, 기존 훅 위치, TSU 스키마)
- [x] 벤치마크 데이터셋 확장 (10만/30만 합성)
- [x] C1 Task Order 033 발급 및 완료 (v2~v4 반려 후 v5 CUE 직접 실행으로 검증 완료)
- [x] 엔진 채택 결정 (Tantivy)
- [x] CandidateGenerator 설계/구현 (core/candidate_generator.py, 테스트 11개 통과)
- [x] Bible Index 구축 (core/bible_index.py, 테스트 19개 통과, index_orchestrator.py 배선 완료)
- [x] 증분 색인 연동 (index_orchestrator.py 배선 완료 — rebuild_tsu_index/reindex_document/reconcile_pending/exclude_document_from_index 전부 연결, 테스트로 "문서 1건 수정 시 다른 문서 재색인 안 됨" 검증)
- [x] 스니펫 사전생성 (Tantivy SnippetGenerator 활용 방식으로 완료 — 원안의 "색인 시 필드 저장" 대신, UTF-8 바이트/문자 오프셋 버그 발견·수정 포함)
- [x] 통합 회귀 검증 (HybridRetriever 신규 모듈, precision@1 동등·p95 10ms대로 목표 충족, 진행 중 회귀 버그 2건 발견·수정)
진행률: 100% (Phase 2 완료)

## 7. Phase 2 이후 후속 작업 (같은 날 사용자 후속 지시로 진행, 2026-07-30)
- [x] USE_INVERTED_INDEX 실배포 (`ui/state/query_processor.py` 배선)
- [x] Query Planner 구현 (`core/query_planner.py`, HQ 제안 ④)
- [x] RRF 명시적 구현 (`core/rrf.py`, HQ 제안 ⑦) — 상세는 아래 §8
- [x] HQ 제안 ⑨ Search Telemetry (백엔드 완료, UI 클릭 배선은 보류) — 상세는 아래 §9
- [x] HQ 제안 ⑧ Background Index Builder — 상세는 아래 §10
- [ ] HQ 제안 ⑥ 캐시 계층 분리(L1/L2/L3) — 미착수

## 9. Search Telemetry (HQ 제안 ⑨) — 백엔드 완료, UI 클릭 배선 보류 (2026-07-30)

**신규 모듈**: [core/search_telemetry.py](../../core/search_telemetry.py) — SQLite 기반(`core/bible_index.py`와 동일 아키텍처). HQ가 요구한 지표 전부 구현:
- 검색 성공률(`success_rate`) / Zero-hit 비율(`zero_hit_rate`)
- Top1/Top5 Click(`click_through_rate(top_n)`)
- Average Candidate(`avg_candidate_count`) / Average Merge Time(`avg_merge_time_ms`)
- Cache Hit(`cache_hit_rate`) — **정직하게 항상 0**: HQ 제안 ⑥(캐시 계층) 미착수라 실제 캐시가 없음, 지어내지 않음
- Embedding Time / ANN Time(`avg_embedding_time_ms`/`avg_ann_time_ms`) — **정직하게 항상 0**: `HybridRetriever`는 벡터/임베딩 검색 단계가 없음(Stage 2가 BM25+theological+passage뿐), 스키마만 미리 마련해둠

**배선**: `HybridRetriever.retrieve()`에 `telemetry_out: Optional[dict]` 아웃파라미터 추가(반환 타입 변경 없이 route/candidate_count/merge_time_ms를 그 dict에 채움 — 기존 호출부/테스트 전부 무변경으로 호환). `HybridQueryProcessor.process()`가 매 호출마다 자동으로 `SearchTelemetry.record_query()`를 호출하고, 상관관계용 `telemetry_query_id`를 `response`에 속성으로 얹음(`ResponsePackage`는 일반 dataclass라 신규 필드를 core/retrieval.py 수정 없이 추가 가능).

**진행 중 발견한 사고 (같은 유형 세 번째)**: 테스트가 `telemetry_path`를 안 넘겨서 **실제 프로덕션 `output/bench/search_telemetry.sqlite3`가 테스트 데이터로 오염**됨 — Bible Index 때와 정확히 같은 실수 패턴. 테스트 수정 + 실제 파일 삭제(재생성은 실사용 시 자동).

**UI 배선 보류 사유**: `ui/pages/research.py`의 클릭 핸들러에 `_record_result_click()` 연결을 시도하던 중, 이 파일이 **C1이 동시에 진행 중인 대규모 리디자인(Stitch pastoral-research-desk design, uncommitted)**으로 계속 바뀌고 있는 것을 발견 — 실제로 한 번 편집이 그 사이 통째로 덮어써짐. 사용자 확인 후 지금은 백엔드만 완료로 두고, UI 클릭 배선은 C1의 리디자인이 끝난 뒤 별도 진행하기로 결정.

**테스트**: `tests/test_search_telemetry.py` 13개 + `tests/test_hybrid_candidate_pipeline.py`에 배선 테스트 6개(`telemetry_out`, `HybridQueryProcessor` 자동 기록) 추가. 전체 관련 회귀 119개 통과, `core/retrieval.py`/`ui/pages/research.py` 둘 다 CUE가 손대지 않음(후자는 C1 작업 중이라 의도적으로 보류).

## 8. RRF (HQ 제안 ⑦) — 완료 (2026-07-30)

**신규 모듈**: [core/rrf.py](../../core/rrf.py) — `reciprocal_rank_fusion(ranked_id_lists, k=60)`. 표준 RRF 공식(Cormack et al. 2009), 범용 유틸리티(id 리스트만 받음 — Retrieval 전용 타입에 묶이지 않음).

**대체한 것**: `HybridRetriever.retrieve()`가 쓰던 고정 가중합(`0.4*bm25 + 0.4*theological + 0.2*passage`)을 제거. bm25_score/theological_score/passage_score 세 신호 각각으로 후보를 정렬해 3개의 순위 리스트를 만들고, `reciprocal_rank_fusion()`으로 합친 값을 `final_score`로 사용 — 가중합은 각 신호의 점수 스케일이 비슷하고 그 특정 가중치가 옳다고 가정하는데, RRF는 순위(order)만 쓰므로 그 가정이 필요 없다(HQ 제안 원문은 BM25*Vector 혼합을 예로 들었지만, 스케일이 전혀 다른 bm25/theological/passage 조합에도 동일한 불안정성이 있었음).

**회귀 검증**: RRF 전환 후 book-level gold standard 96개 쿼리 재실행 — precision@1 **1.0 유지**(변화 없음), p50 9.7ms/p95 26.8ms(여전히 목표 이내). Bible/Exact/Metadata 라우트는 RRF 영향을 받지 않음(대부분 후보가 1건이거나 순위 신호가 이미 명확).

**테스트**: `tests/test_rrf.py` 7개(공식 정확성, 리스트 결측 처리, k 파라미터, 3-way 합산 수동 대조). 전체 관련 회귀 86개 통과, `core/retrieval.py` 여전히 무변경.

## 10. Background Index Builder (HQ 제안 ⑧) — 완료 (2026-07-31)

**신규 모듈**: [core/background_index_builder.py](../../core/background_index_builder.py) — `BackgroundIndexBuilder`(데몬 스레드 기반). 새 파이프라인이 아니라 **이미 있던 것을 백그라운드로 옮긴 것**: `core/document_context.py`의 `pipeline_state`에 이미 `PROCESSED`(추출은 됐지만 색인 전) 상태가 있고, `core/index_orchestrator.py::reconcile_pending()`이 이미 그 큐를 멱등적으로 처리하는 pull 방식 재조정자였다 — 이게 HQ가 말한 "Queue"였다. 없었던 건 그걸 호출부를 막지 않고 백그라운드에서 돌리는 것뿐.
- `start()`/`stop()`/`trigger_now()`(즉시 깨우기, 논블로킹)/`status()`(is_alive/is_running_job/last_result/last_error)
- `reconcile_pending()`을 그대로 호출(재구현 없음), 예외가 나도 스레드는 죽지 않고 `last_error`에 기록
- `ui/state/background_builder.py`(신규) — `st.cache_resource`로 프로세스 전체에 워커 하나 공유(세션마다 별도 스레드가 뜨지 않도록)

**배선**: `ui/pages/processing.py`의 문서 처리 완료 직후 블로킹 호출(`reconcile_result = reconcile_pending(output_dir)` — 전체 재색인이 끝날 때까지 화면이 멈춰 있었음)을 `get_shared_background_builder().trigger_now()` + 안내 메시지로 교체. `reconcile_pending` 직접 import는 이제 안 쓰여서 제거. `processing.py`는 이 세션 동안 다른 작업(C1)이 안 건드린 걸 매번 git diff로 확인 후 수정.

**검증**: 브라우저로 Processing 페이지 정상 로드 확인(에러 없음). 백엔드 스레드 lifecycle(시작/정지/즉시트리거/에러 격리/동시성)은 8개 테스트로 검증.

**테스트**: `tests/test_background_index_builder.py` 8개. 기존 processing 관련 테스트 5개 파일(29개)도 회귀 없음 확인. 전체 37개 통과, `core/retrieval.py` 여전히 무변경.

## 11. HQ 제안 종합 현황 (2026-07-31 기준)

| 제안 | 상태 |
|---|---|
| ① 2단계 분리 (Candidate Generator / Semantic Ranking) | 완료 |
| ② TSU를 Search Unit으로 승격 | 완료 (CandidateRef/스니펫 등으로 구현) |
| ③ Bible Index 별도 구축 | 완료 |
| ④ Query Planner | 완료 |
| ⑤ 검색용 Snippet 사전 생성 | 완료 (Tantivy SnippetGenerator 방식) |
| ⑥ Query Cache + Embedding Cache 분리 | Search Result Cache 완료(아래 §12), Embedding Cache는 대상 없음(HybridRetriever에 임베딩 단계 자체가 없음) |
| ⑦ RRF 기본 Merge 알고리즘 | 완료 |
| ⑧ Background Index Builder | 완료 |
| ⑨ Search Telemetry | 백엔드 완료, UI 클릭 배선 보류(C1 리디자인 완료 후) |

## 12. 캐시 계층 분리 (HQ 제안 ⑥) — 완료 (2026-07-31, 검색 결과 캐시만 해당)

**신규 모듈**: [core/search_cache.py](../../core/search_cache.py) — `SearchResultCache`(L1 메모리 + L2 SQLite).

**원안 대비 조정 2가지, 이유와 함께**:
1. **L3(Disk)는 별도로 만들지 않음** — L2가 이미 SQLite(디스크 파일)라 L3를 또 만들면 같은 저장 매체를 중복시킬 뿐. HQ의 3계층은 L2가 Redis 같은 빠른 키밸류 서비스이고 L3가 콜드 스토리지일 때 의미가 있는 구조인데, 이 프로젝트엔 그런 L2가 없어 L2 자체가 이미 디스크 계층 역할을 한다 — 문서로 명시하고 빈 3번째 계층을 만들지 않음.
2. **Query Embedding Cache는 만들지 않음** — `HybridRetriever`에는 임베딩/벡터 검색 단계가 아예 없다(Stage 2가 BM25+theological+passage뿐, Phase 2 plan에서부터 그렇게 설계함). `core.retrieval.EmbeddingCache`는 레거시 `RetrievalEngine` 전용으로 이미 존재하고 이번에도 건드리지 않음 — 안 쓰이는 두 번째 임베딩 캐시를 만드는 건 죽은 코드일 뿐이라 만들지 않음.

**캐시 키**: 정규화 검색어(NFKC+공백정리+소문자) + k + file_scope + **현재 TSU 데이터셋의 manifest fingerprint**(`dataset_sha256`, `ui/state/query_processor.py`가 staleness 감지에 쓰는 것과 같은 필드를 core 쪽에서 독립적으로 재확인 — core는 ui를 import할 수 없어 로직은 분리, 값은 같은 소스). **재색인하면 fingerprint가 바뀌어 옛 캐시 항목이 자동으로 무효화**됨(HQ의 "컬렉션 색인 버전이 바뀌면 캐시 키에 버전 반영" 요구사항 — 별도 무효화 호출 없이 키 설계로 해결).

**배선**: `HybridQueryProcessor.process()`가 Stage 0-2(검색) 결과만 캐시 — context/citation 조립은 저렴하고 결정적이라 캐시 대상에서 제외. `SearchTelemetry.record_query()`의 `cache_hit`이 이제 진짜 값(이전엔 항상 False였음).

**진행 중 발견한 사고 (네 번째, 같은 패턴)**: 테스트가 `cache_path`/`tsu_manifest_path`를 안 넘겨서 실제 `output/bench/search_cache.sqlite3`가 오염되고, 심지어 **테스트끼리도 서로 캐시를 공유해서 오탐**이 남(다른 테스트의 "은혜" 쿼리 캐시를 이후 테스트가 그대로 히트). 테스트 수정 + 실제 파일 삭제로 정리.

**실측** (실제 프로덕션 코퍼스): 캐시 미스 67.92ms → 캐시 히트 0.61ms(**약 110배**), 반환 결과 동일성 확인.

**테스트**: `tests/test_search_cache.py` 19개(정규화/키 생성/L1·L2 tier/TTL 만료/재시작 생존/만료 항목 정리) + `test_hybrid_candidate_pipeline.py`에 캐시 히트 통합 테스트 4개. 전체 관련 회귀 150개 통과, `core/retrieval.py` 여전히 무변경.
