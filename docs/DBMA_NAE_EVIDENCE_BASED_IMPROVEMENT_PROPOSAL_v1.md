# DBMA/NAE Evidence-Based Improvement Proposal (Notch 3 — Planning Only)

- 작성일: 2026-09-10
- 성격: **개선 제안서.** 이 문서 작성 과정에서 코드·설정·데이터·인덱스·DB·프롬프트·UI를 수정하지 않았고, 실행·테스트·서비스 조작·환경변수/플래그 변경도 하지 않았다.
- 증거 기준: 본 세션에서 이미 작성된 **DBMA/NAE 1차 점검 보고서**(2026-09-09)와 **DBMA/NAE 2차 운영 검증 보고서(Notch 3)**(2026-09-09) 두 문서에서 실행·파일판독으로 확인된 사실만 사용한다. 두 보고서에서 UNKNOWN으로 표시된 항목은 개선 대상으로 확정하지 않는다.
- 인용 표기: `[1차 §x.y]` = 1차 점검 보고서 절, `[2차 Qn]` / `[2차 §…]` = 2차 검증 보고서 항목.
- **동반 문서**: `docs/DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md` — 본 제안의 요구·가정이 현재 파이프라인/코드/ADR/테스트와 충돌하는 지점을 Conflict Record로 등록. 아래 P0/P1의 실제 착수 판정은 Conflict Register의 Decision status를 따른다.

---

# Executive Summary

## 전면 재개발 대상이 아닌 이유

두 점검은 **작동하는 파이프라인**을 확인했다. `data/RAW` → 정제 → 청킹 → `tsu_dataset.jsonl`(1,363) → legacy `QueryProcessor`/`RetrievalEngine` → `ContextAssembler` → `CitationBuilder` → `GenerationService` 경로가 실제로 실행되며 [2차 §"기본 DBMA 검색 실행 결과"], 회귀 테스트 2,710건이 통과한다 [1차 §3.5]. Qdrant `nae_tsu_v1`(3,319 verified)·`nae_ref_v1`(34,948)은 green 상태이고 on-disk verified 건수와 정확히 대응한다 [2차 Q11]. Smith reference 주입 경로는 70~416 ms로 실동작한다 [2차 Q8]. ClaimGuard의 절대화 표현 탐지도 실동작한다 [2차 Q15]. 확인된 문제는 **국소적**이며(한국어 키워드 추출 1개 정규식, citation 필드 backfill 부재, 활성 경로 관측 부재, 생성 지연 원인 미규명), 각기 최소 변경으로 접근 가능하다.

## 확인된 핵심 문제

| ID | 한 줄 요약 | 등급 |
|----|-----------|------|
| PB-01 | 한국어 질의는 `_extract_keywords` 정규식(`[a-zA-Z]{3,}`)에서 `keywords=[]` → BM25 0 → 후보 풀이 코퍼스 앞 100건 슬라이스로 퇴화. 정확 문구 청크가 top-5에서 누락됨 | CONFIRMED |
| PB-02 | citation card에 실제 전달되는 값이 `source_file`+`relevance_score`뿐. `tsu_dataset.jsonl` 1,363건 전건 title/author/page/heading_path = null. 원본 EPUB에는 서지 정보 존재 | CONFIRMED (UI 렌더는 UNKNOWN) |
| PB-03 | 활성 legacy 경로에 질의/검색/생성 telemetry 지속 저장이 없음. `SearchTelemetry`는 비활성 hybrid 경로 전용 | CONFIRMED |
| PB-04 | UI 답변 생성이 관측 구간(Chat ≈23분) 내 미완료. citation card 화면 렌더도 그 때문에 미관측. **원인 UNKNOWN** | 관측 CONFIRMED / 원인 UNKNOWN |
| PB-05 | gold query 100건 중 현재 corpus와 완전일치 3건, `output/eval/*.jsonl` chunk ID 0/8 일치. 현재 corpus 기준 유효 품질 baseline 부재 | CONFIRMED |
| PB-06 | `DEFAULT_BENCH_DIR`이 cwd 상대 경로. 실행 위치에 따라 dataset/index/telemetry 경로가 달라질 수 있음 (재현성 위험으로 확인, 운영 오류로는 미확인) | CONFIRMED (코드) / 영향은 PROBABLE |
| PB-07 | ClaimGuard 예외 시 `RiskLevel.NONE` 반환하고 답변 계속 사용(fail-open). `absolute_claim_blocked=True`가 UI에서 실제 차단으로 이어지는지 UNKNOWN | fail-open CONFIRMED / UI 집행 UNKNOWN |
| PB-08 | `should_activate_smith()`가 일반 주석·성경참조 질의에도 True. 주입 텍스트에 OCR 열화 형태. Smith 결과는 citation card로 전달 안 됨 | CONFIRMED |
| PB-09 | `nae_ref_v1` 34,948건에 `review_status`/`usage_permission`/`copyright_status`/`citation_policy` 필드 자체가 없음. `nae_tsu_v1`은 `citation_policy` 전건 null | CONFIRMED |

## 보존할 핵심 자산

`registry/documents.json`의 `document_id`/`file_hash`/`pipeline_state`/`supersedes` 구조와 `core/index_orchestrator.py`의 문서 단위 reindex·superseded 제거 [1차 §2.1]; `tsu_dataset.jsonl`/`tantivy_index/`/`bible_index.sqlite3` 산출물; `core/retrieval.py`의 성경참조 파싱·metadata filter·bge-m3 스코어링·theological score·passage match·source tier bonus·dedup·document diversity; `ui/components/citation_card.py`+`CitationBuilder`/`Citation`; `core/claim_guard.py` 절대화 탐지; `nae_ref_v1` Smith 검색+주입; `nae_tsu_v1` verified 3,319+payload; 2,710 테스트·100 gold query·ClaimGuard goldset·CI·ADR·feature flag; 로컬 Ollama·bge-m3·Streamlit·Docker; top-k만 조립하는 컨텍스트 구조 [2차 Q4].

## 개선 제안의 원칙

**최소 변경**(질의-시점 로직 1개, 부가 sidecar 파일, 부가 로그 라인) · **활성 경로 우선**(legacy `QueryProcessor` 경로만 대상, `USE_INVERTED_INDEX`·`nae_pd` 활성화는 제안하지 않음) · **검증 우선**(모든 P0/P1은 feature flag 뒤에서 구현되고, 현재 corpus 기준 최소 eval subset으로 회귀 확인한 뒤에만 기본값 전환 검토).

---

# Evidence Baseline

## 사용한 확인된 사실 (CONFIRMED)

### 활성 경로 / 검색

- 활성 Chat 경로 = legacy `core.retrieval.QueryProcessor` + `RetrievalEngine`. `USE_INVERTED_INDEX` unset, `is_enabled()==False`, hybrid 경로 미실행 [2차 §"활성 경로 판정"].
- `_extract_keywords`: `re.findall(r'\b[a-zA-Z]{3,}\b', query.lower())` (`core/retrieval.py:470`). 한국어 질의 4건 실행 → `keywords=[]`; 영어 질의 → `keywords=['grace','forgiveness','matthew']` [2차 §"BM25가 0인 이유"].
- 문서 토크나이저는 한국어 처리: `_tokenize('구하라 그리하면 너희에게')` → `['구하','그리','너희']`. 질의 경로와 문서 경로가 다르다 [2차 동].
- `corpus loaded (engine.tsus): 1363`, `candidate_k=100`. BM25 무히트 시 `candidate_pool[:100]` 슬라이스가 실제 후보 풀 [2차 Q3].
- A1(한국어, 성경참조 없음): 후보 풀 = 코퍼스 인덱스 0..99, 반환 5건 모두 문서 앞부분(서문/총론) [2차 A1].
- A2(본문 실재 정확 문구 `구하라 그리하면…`): 해당 청크 `chunk_00280`이 **top-5에 없음**, 인덱스 87..98의 무관 5건 반환. zero-hit은 아님 [2차 A2].
- A3(성경참조 `MAT 6:9-13` 인식): `_metadata_filter()` 1363→16, `chunk_00280` 1위 반환 [2차 A3].
- 하이브리드 가중치 `0.25·BM25 + 0.20·vector + 0.30·theological + 0.20·PassageMatch + 0.05·SourceTierBonus` (`core/retrieval.py:1657`) [1차 §3.3].
- 전체 코퍼스는 LLM에 전달되지 않음. `llm_context_block` 2,324~5,033자 vs 데이터셋 3.4 MB [2차 Q4].

### citation / 메타데이터

- `tsu_dataset.jsonl` 1,363건 전건 집계: `title`/`author`/`page`/`chapter` non-null 0, `structure.heading_path` 비어있지 않음 0, `source_provenance` non-null 0, `nae_metadata` non-null 0 [1차 §3.4].
- citation card 실제 인자값(A3, k=3): `source_file`·`relevance_score`만 유효, `text_location`/`doc_type`/`author`/`citation_title` = None. 생성되는 meta 행 = `['문서']` 하나 [2차 Q6].
- `Citation` dataclass 필드: `citation_id, tsu_id, scripture_reference, source_title, source_author, document_id, content_excerpt, evidence_confidence, retrieval_score, source_file, language, source_type`. 검수 상태·인용 가능 여부·페이지 locator 필드 없음 [1차 §3.2, 2차 Q7].
- 원본 EPUB DC 메타데이터(ebooklib 직접 판독): `title='매튜 풀 청교도 성경주석 14 : 마태복음'`, `creator='매튜 풀'(aut)`, `publisher='크리스챤다이제스트'`, ISBN `978-89-447-8472-9`, `language='ko'`, `rights=[]` [1차 §3.4, 2차 Q7].
- `core/extractors.py`: `_extract_pdf_title_author()`(108), `_extract_docx_title_author()`(124), `extract_text_from_epub()`(159) — EPUB 서지 판독 함수 없음 [2차 Q7].
- `core/heading_provider.py:151-155`: `md`/`markdown`/`txt`/`pdf`만 등록. `core/tsu_builder.py:305` `if source_type == "pdf":`일 때만 assembler 경로. 정제본 `…_epub.md` ATX 헤딩 `grep -c '^#'` = 0 [2차 Q7].
- `verse_mapping` 키 조합: `(book_id,)` 1,294 / `(book_id,chapter,verse_start)` 50 / `(book_id,chapter,verse_end,verse_start)` 18 / `(book_id,chapter)` 1 [1차 §3.4]. chapter 없는 건은 `scripture_reference` = `'MAT ?:?'` [2차 Q7].
- **verse_mapping ↔ 본문 불일치 관측**: A1 #3 `chunk_00018` = `verse_mapping` `MAT 25:1-13`인데 본문은 마태복음 서론; A3 #4 `chunk_00261` = `MAT 6:14`로 매핑됐으나 본문은 주기도문 12절 해설 [2차 Q4/Q5].

### 관측성 / 실행 위치

- `SearchTelemetry.record_query()` 호출부 = `core/hybrid_candidate_pipeline.py:323` 1곳뿐, `USE_INVERTED_INDEX` 게이트. `SearchResultCache`도 동일 [2차 Q16].
- `record_query_latency()` → `st.session_state["query_latencies_ms"]`(상한 200), 디스크 미기록. `_record_result_click()`는 `telemetry_query_id` 부재로 legacy에서 즉시 반환 [2차 Q16].
- 6회 질의 후 `search_telemetry.sqlite3`·`search_cache.sqlite3`·`logs/` 전부 ABSENT. 지속 저장되는 것은 임베딩 캐시(+16)와 `chat_session_history.json`(사용자 턴 2건)뿐 [2차 Q16, D1, D2].
- `core/config.py:72` `DEFAULT_BENCH_DIR = _yaml_dirs.get("bench_dir","output/bench")` = cwd 상대. `DATA_DIR`은 `BASE_DIR` 절대 [2차 §"실행 위치 의존성"]. `DEFAULT_SEARCH_TELEMETRY_PATH` = `output/bench/search_telemetry.sqlite3` [1차 §3.3]. `config.yaml directories.logs_dir: "logs"` → `/Users/David/DBMA/logs` 디렉터리 부재 [1차 §3.5].

### 평가 자산

- 현재 corpus: `book_id` 집합 `['MAT']`, `source_file` 1개. gold query 100건 판정 FULL 3 / PARTIAL 10 / NONE 73 / 대조축 없음 14 [2차 Q13].
- `gold_queries.json` 스키마: `id, category, query, expected_books, expected_documents, expected_ranking_priority, notes`. TSU/document ID 직접 참조 필드 없음; `expected_books`만 대조 가능. `expected_documents`는 자연어 서술 [2차 Q13, V10].
- `output/eval/*.jsonl` chunk ID 현재 corpus 존재 0/8. 파일 간 스키마 상이 [2차 Q14].

### NAE 분리 / rights

- `NAE.retrieval_adapter.search()` / `bridge_query()` → `NaePdModuleDisabledError` (`modules.nae_pd.enabled=false`). 호출부 `ui/pages/research.py:566` 1곳, chat.py 미호출 [2차 Q9].
- `nae_tsu_v1` 3,319 전수: `review_status='verified'` 100%, `page` non-null 100%, `usage_permission='research'` 100%, `copyright_status='public_domain'` 100%, `citation_policy` = None 100%, `citation_policy_status`/`category_status` = `AUTHORITATIVE_SOURCE_MISSING` 100% [2차 Q10].
- `nae_ref_v1` 34,948 전수: `review_status`/`usage_permission`/`copyright_status`/`citation_policy` **필드 자체 부재** 100%; `page_start` null 1,146(3.3%); `content_type='reference_dictionary'` 100% [2차 Q10].
- on-disk 7,760 vs 인덱스 3,319 = `review_status=='verified'` 합계 3,319와 정확히 일치. 미색인 4,441 = generated 4,419 + rejected 22. `duplicate_of` 0건 [2차 Q11].
- `should_activate_smith()`: `모세는 누구인가` True, `매튜 풀 주석에서…` True, `마태복음 6:9-13 주기도문 해석` True [2차 Q8].
- Smith 주입 블록: `<reference>` 포함, 컨텍스트에 +1,720~+3,399자, 페이지 번호 포함, OCR 열화 텍스트(`Msuroiyott`, `BETHXEHEH`) [2차 Q8].
- Smith 항목을 `render_citation_card`로 전달하는 호출부 없음 [2차 Q8].

### ClaimGuard

- `_run_claim_guard` 실행: 절대화 표현 입력 → `RiskLevel.HIGH`, `matched_terms=['최초','유일','반드시',…]`, `absolute_claim_blocked=True` [2차 Q15].
- 예외 주입(인메모리) → `RiskLevel.NONE` 반환, 답변 계속 사용(fail-open) [2차 Q15].

### 회귀 기준선

- `pytest tests/ -q` → `2710 passed, 15 skipped` [1차 §3.5]. `test_query_enhancements_full_regression.py`에 `PytestReturnNotNoneWarning`(dict 반환) [1차 §3.5].
- 2차 무변경 확인: `tsu_dataset.jsonl`/`tsu_manifest.json`/`bible_index.sqlite3`/`registry/documents.json`/`config.yaml` SHA256 검증 전후 동일 [2차 §"수정 여부"].
- `tsu_manifest.json`: `dataset_sha256`/`registry_sha256`/`config_sha256`를 build에 결속 [1차 §3.3].

## PROBABLE

- PB-06의 **운영 영향**: cwd가 `/Users/David/DBMA`가 아닐 때 잘못된 경로를 읽거나 쓸 수 있음 — 코드 사실은 CONFIRMED이나 실제 그런 오류가 발생한 기록은 두 보고서에 없음 [2차 §"실행 위치 의존성", 1차 §5.3].
- PB-04의 **재현성**: Chat ≈23분 미완료는 수 회 관측이며, 검증자의 `curl` 1회 경합 가능성이 배제되지 않음 [2차 D-절, V2].

## UNKNOWN — 개선 대상으로 확정하지 않음 (보류)

| # | 항목 | 근거 |
|---|------|------|
| UK-1 | citation card / Smith 항목 / `absolute_claim_blocked`의 **실제 화면 동작** | 생성 미완료로 렌더 미관측 [2차 V1, V3, V4] |
| UK-2 | PB-04 지연의 원인 | 원인 분리 실험 미수행, 금지 범위 [2차 V2] |
| UK-3 | `USE_INVERTED_INDEX=true` 경로 동작, `tantivy_index/` 최신성 | 환경변수 변경 금지 [2차 V5] |
| UK-4 | `modules.nae_pd.enabled=true` 시 `bridge_query()` 결과·품질 | 플래그 변경 금지 [2차 V6] |
| UK-5 | `nae_tsu_v1` 미색인 4,441건의 처리 절차 | 추가 판독 필요 [2차 V9] |
| UK-6 | 2026-07-27~28 eval 실행 당시 corpus 구성 | 당시 스냅샷 없음 [2차 V11] |
| UK-7 | `dbma_qdrant`(:6333)·ChromaDB `chroma_db/` 내용 | 컨테이너 기동/조회 금지 [2차 V7, V8] |
| UK-8 | n8n 워크플로 활성 상태·control-plane 실가동 | 인증 미확보 [1차 U2/U3, 2차 V13] |
| UK-9 | 실사용자 질의 이력 존재 여부 | telemetry/history/logs 부재 [1차 U10] |
| UK-10 | 다중 문서·다중 포맷(특히 PDF heading provider) 실동작 | 현재 corpus가 단일 EPUB [1차 §5.5] |
| UK-11 | ADR-001~033 각 문서의 **내용** | 두 점검은 ADR 개수와 일부 번호만 확인, 본문 미판독 [1차 §1.2] |

## 본 제안서가 다루지 않는 미확인 영역

`.automation/`(8,277 파일) 내용, `scripts/` 97개의 실사용 여부, `docs/` 528개 최신성, `evidence/`·`archive/`·`workspace/` 내용, Qdrant 보안 구성, 원격 브랜치 diff, ADR 본문 [1차 U3·U9·U14·U15·U16·U17, §1.2].

---

# Improvement Principles and Guardrails

1. **기존 자산 보존.** 원본 EPUB, 정제 markdown, `tsu_dataset.jsonl`, `tantivy_index/`, `bible_index.sqlite3`, `nae_tsu_v1`, `nae_ref_v1`, registry, `output/eval/*` 를 삭제·덮어쓰기 하지 않는다. 신규 산출물은 additive(별도 파일)로만.
2. **No big-bang rewrite.** 대상은 `_extract_keywords` 1개 함수, `CitationBuilder`의 fill 로직, `QueryProcessor.process` 말미 1개 호출 등 국소 지점.
3. **No whole-corpus reprocessing by default.** 재추출·재OCR·재청킹·재임베딩·재색인을 기본 해법으로 제시하지 않는다. `tsu_manifest.json`의 3개 SHA가 변하지 않는 방식을 우선한다.
4. **No full-corpus LLM context.** top-k(현재 2~5) 조립 구조를 유지한다 [2차 Q4].
5. **Backward compatibility.** `Citation`/`CitationBuilder`/`ResponsePackage`/citation card의 공개 시그니처를 바꾸지 않는다. 새 필드는 optional·기본값 None. 새 동작은 전부 feature flag 뒤.
6. **Feature flags.** 신규 플래그는 `core/feature_flags.py` 또는 환경변수. **기본값 off = 현행 동작과 바이트 동일.** `USE_INVERTED_INDEX` / `modules.nae_pd.enabled`는 이 제안서에서 활성화 대상이 아니다.
7. **Snapshots and rollback.** 각 제안은 (a) 플래그 unset (b) 신규 파일 삭제 (c) `git revert` 중 하나로 즉시 원복 가능해야 한다.
8. **Privacy / rights-aware logging.** 로그에 원문 질의·검색 본문·사용자 식별자를 남기지 않는다. 저작권 자료(EPUB 본문, Smith 사전 텍스트)를 외부로 전송하지 않는다. **권리 상태가 authoritative source로 확인되지 않은 자료는 권리 필드를 단정하지 않는다**(프로젝트의 `AUTHORITATIVE_SOURCE_MISSING` 관례 준수).
9. **활성/비활성 경로 구분.** 제안은 legacy `QueryProcessor` 경로만 대상. hybrid·bridge 경로 항목은 전부 P2/Deferred.
10. **성능 원인 미단정.** PB-04에 대해 모델·VRAM·CPU·네트워크·프롬프트를 원인으로 지목하지 않는다. P0 조치는 "측정 가능하게 만드는 것"에 한정한다.

---

# Confirmed Problem Matrix

| Problem ID | 확인된 증거 | active path 영향 | data integrity 영향 | research / citation 영향 | user impact | severity | class |
|---|---|---|---|---|---|---|---|
| **PB-01** 한국어 질의 BM25=0 → 후보 풀 `pool[:100]` 퇴화 | `retrieval.py:470` 정규식; `_extract_keywords` 실행 4건 `[]`; A1 풀=0..99; A2 정확문구 청크 top-5 누락 [2차 Q3/A1/A2] | **직접.** 활성 경로에서 재현된 검색 실패 | 없음 (질의-시점) | **높음.** 근거 청크가 안 잡히면 인용도 불가 | 성경참조 없는 한국어 질의에서 무관 결과 상위 | 높음 | **P0** |
| **PB-02** citation 서지·locator 필드 결측 | `tsu_dataset.jsonl` 전건 null [1차 §3.4]; citation card 인자 `source_file`/score만 [2차 Q6]; EPUB엔 메타 존재 [2차 Q7] | **직접.** 출처 추적 신뢰성 훼손 | 없음 (backfill은 additive) | **높음.** 저자·서명·페이지 없이는 학술 인용 불가 | 근거 카드가 "문서" 한 줄만 표시 | 높음 | **P0** (서지 backfill) / locator·rights·UI는 조건부 → Conflict Register |
| **PB-03** 활성 경로 telemetry 지속 저장 부재 | `SearchTelemetry` hybrid 전용 [2차 Q16]; 6회 질의 후 telemetry/logs ABSENT | **직접.** 관측 부재로 오류 재현·판단 불가 | 없음 | 간접 | 장애 진단 불가(PB-04 포함) | 높음 | **P0** |
| **PB-04** UI 답변 생성 관측구간 미완료 | Chat ≈23분·Research ≈4~5분 미완료; `/api/generate` 120s 무응답 [2차 D-절] | **직접.** 현재 UI 사용을 실질적으로 막음 | 없음 | citation card 렌더 미관측 [2차 V1] | 답변 미출력 | 높음 | **P0** (계측 한정) / 원인·해법 Deferred |
| **PB-05** eval 자산 ↔ 현재 corpus 불일치 | gold FULL 3/100, eval chunk 0/8 [2차 Q13/Q14] | 없음 (eval 자산) | 없음 | **높음.** 품질 baseline 없음 | 개발/QA | 중 | **P1** (P0 측정의 선행) |
| **PB-06** `DEFAULT_BENCH_DIR` cwd 상대 | `config.py:72`; `DATA_DIR`만 절대 [2차 §실행위치] | **위험.** 잘못된 위치 실행 시 다른 dataset/index/log | **잠재적.** wrong-path write | 간접 | 재현성 위험(운영오류 미확인) | 중 | **P1** |
| **PB-07** ClaimGuard fail-open + UI 집행 UNKNOWN | 예외 시 `RiskLevel.NONE` 후 답변 사용 [2차 Q15]; UI 동작 미관측 [2차 V3] | **직접.** 가드 실패가 무경보 | 없음 | **중.** 절대화 주장 무검증 통과 가능 | 잠재 오정보 | 중 | **P1** / UI 집행 Deferred |
| **PB-08** Smith 과활성 + OCR 주입 + 미인용 | `should_activate_smith` A1/A3 True; OCR 텍스트 주입; citation 미전달 [2차 Q8] | **직접.** 무관 질의에도 OCR 노이즈가 LLM 컨텍스트에 | 없음 (읽기 전용) | **중.** 출처 불명 텍스트가 답변 근거에 | 답변 품질·신뢰 저하 | 중 | **P1** |
| **PB-09** NAE rights/citation_policy 필드 결측 | `nae_ref_v1` rights 필드 부재 100%; `nae_tsu_v1` `citation_policy` null 100% [2차 Q10] | 부분 (Smith 활성) | 없음 | **중.** 질의 시점 인용가능성·권리 판별 불가 | 간접 | 중 | **P1 / P2** (NAE governance 선행) |

---

# P0 Improvement Proposals

> 공통: 모든 P0는 (a) feature flag 뒤 (b) 기본값 off = 현행 바이트 동일 (c) `tsu_manifest.json` 3개 SHA 불변 (d) 회귀 `2710 passed` 유지 (e) 즉시 rollback. **본 세션에서 구현하지 않는다.** 착수 판정은 Conflict Register 참조.

## P0-1 — 한국어 인식 키워드 추출 (legacy 경로, 플래그 게이트)

1. **해결하려는 CONFIRMED 문제** — PB-01. 성경참조 없는 한국어 질의에서 `keywords=[]` → BM25 0 → 후보 풀 `candidate_pool[:100]` 고정, 정확 문구 청크 top-5 누락 [2차 Q3, A1, A2].
2. **Evidence** — `core/retrieval.py:470` 정규식; `_extract_keywords` 실행(KO 4건 `[]`, EN 정상); 문서측 `_tokenize`는 한국어 처리; A2 `chunk_00280` 누락, A3 1위 [2차 §BM25, A2/A3].
3. **최소 변경 설계** — `_extract_keywords()`가 `[]`를 반환할 때에 한해 문서 색인이 이미 쓰는 `_tokenize`를 질의에도 적용. 신규 사전·형태소기 도입 없음. 플래그 `RETRIEVAL_KOREAN_KEYWORDS`(기본 off). `_detect_scripture_refs`/`_detect_intent`/`_extract_themes` 불변.
4. **예상 변경 경로 / 파일** — `core/retrieval.py`(`_extract_keywords` 분기 ~10행), `core/feature_flags.py`.
5. **데이터 영향 / migration** — 없음. 질의-시점. 재색인·재청킹 없음.
6. **기존 기능 호환성** — 플래그 off = 반환값 바이트 동일. 영어 질의는 분기 미진입.
7. **feature flag / fallback** — `RETRIEVAL_KOREAN_KEYWORDS` 기본 `false`. `_tokenize` 예외 시 `[]` 폴백.
8. **acceptance tests** — KO-exact(`구하라 그리하면…` → `chunk_00280` top-5 진입) / KO-topic(BM25 non-zero>0) / EN(결과·점수 완전 동일) / scripture-ref(A3 1위 동일) 4분리 세트 + `2710 passed`.
9. **rollback plan** — 플래그 unset; 필요 시 `git revert`.
10. **privacy / rights impact** — 없음.
11. **latency / cost impact** — `_tokenize` 1회(µs). LLM/임베딩 호출 불변.
12. **dependencies and risks** — 승격(기본값 on)은 PB-05 eval subset 선행. keyword 변경 → 모든 한국어 질의의 하이브리드 랭킹(가중 0.25) 이동. `_tokenize` 2-gram ↔ BM25 문서통계 상호작용 미검증. → Conflict Register CON-001.
13. **out of scope** — `USE_INVERTED_INDEX`, hybrid, 형태소기 도입, 문서측 토크나이저 변경, `_extract_themes`/`_detect_intent` 수정.

## P0-2 — 서지 메타데이터 sidecar backfill (재처리 없음)

1. **해결하려는 CONFIRMED 문제** — PB-02의 서지 신원 부분. citation card가 `source_file`+score만 받음. `tsu_dataset.jsonl` 전건 title/author null. 원본 EPUB에 `title`/`creator` 존재 [1차 §3.4, 2차 Q6/Q7].
2. **Evidence** — 전건 집계 non-null 0 [1차 §3.4]; citation 실인자 None [2차 Q6]; ebooklib 판독으로 EPUB `title`/`creator='매튜 풀'`/`publisher` 확인, `rights=[]` [1차 §3.4]; `Citation`에 `source_title`/`source_author` 필드 이미 존재 [1차 §3.2].
3. **최소 변경 설계** — `output/bench/tsu_metadata_sidecar.json`(신규 additive), key=`document_id`, value=`{source_title, source_author, publisher, isbn, edition_year}`. **rights 필드는 넣지 않는다**(EPUB `rights=[]`이고 프로젝트 관례가 `AUTHORITATIVE_SOURCE_MISSING` — CON-012). 별도 빌더 스크립트(미실행). `CitationBuilder.build_citations()`는 TSU `title`/`author`가 null일 때만 sidecar로 `Citation.source_title`/`source_author` fill. `tsu_dataset.jsonl`·EPUB·정제 md 미수정. **locator(text_location)는 이 제안에서 다루지 않음** — `verse_mapping` ↔ 본문 불일치가 관측됨(CON-003).
4. **예상 변경 경로 / 파일** — 신규 `scripts/build_tsu_metadata_sidecar.py`(제안), `output/bench/tsu_metadata_sidecar.json`(생성물); 수정 `core/retrieval.py::CitationBuilder.build_citations`(~12행); 플래그 `CITATION_SIDECAR_FILL`(기본 off).
5. **데이터 영향 / migration** — additive 파일 1개. `dataset_sha256` 불변. migration 없음.
6. **기존 기능 호환성** — `Citation` 시그니처 불변(기존 필드에 값만). citation card는 값 truthy 시 행 렌더(현행 `if author:`). 플래그 off = 현행.
7. **feature flag / fallback** — `CITATION_SIDECAR_FILL` 기본 `false`. sidecar 부재·파싱 실패 시 무시.
8. **acceptance tests** — A3 citation 5건 flag on 시 `source_title`=EPUB title, `source_author`=`매튜 풀`; meta 행에 `저자`·`출처` 포함; `dataset_sha256` 불변; `2710 passed`(None 기대 테스트는 flag off 기준 유지, on 기준 신규 테스트).
9. **rollback plan** — 플래그 unset 또는 파일 삭제; 코드 `git revert`.
10. **privacy / rights impact** — 서지 메타(title/author/publisher/ISBN)만. EPUB 본문·Smith 텍스트 미포함. **권리 상태 단정 안 함**(CON-012). 외부 전송 없음.
11. **latency / cost impact** — dict 조회 O(1)×k. 파일 1회 로드·캐시.
12. **dependencies and risks** — EPUB DC 메타 정확성(EPUB 1종만 검증). `document_id` 조인 유일성(단일 문서에서 자명, 다중 문서 미검증). → CON-002, CON-010.
13. **out of scope** — EPUB 재추출, heading provider 신설, 재청킹, `tsu_dataset.jsonl` 직접 수정, `Citation` 필드 추가, PDF 경로, **페이지/heading/verse locator**, **rights 필드**.

## P0-3 — 활성 경로 비파괴 audit trail (플래그·프라이버시 준수)

1. **해결하려는 CONFIRMED 문제** — PB-03. legacy 경로에 관측 데이터 디스크 저장 부재 → 재현·회귀·PB-04 진단 불가 [2차 Q16].
2. **Evidence** — `SearchTelemetry` 호출부 1곳이 hybrid 게이트; `record_query_latency`→session_state; `_record_result_click` no-op; 6질의 후 telemetry/logs ABSENT [2차 Q16].
3. **최소 변경 설계** — `core/retrieval_audit.py`(신규 ~40행), `QueryProcessor.process()` 말미 append-only JSONL. 필드: `ts, query_sha256_salted, query_char_len, intent, scripture_ref_count, keyword_count, candidate_pool_size, bm25_nonzero_count, topk_scores, stage_ms{bm25,vector,theo,passage,total}, dataset_sha256, config_sha256, engine_kind, flag_state`. 경로는 **`BASE_DIR` 절대**. 플래그 `RETRIEVAL_AUDIT_LOG`(기본 off). 라이터 전체 `try/except`. → 경로 선택은 CON-004 참조.
4. **예상 변경 경로 / 파일** — 신규 `core/retrieval_audit.py`; `core/retrieval.py` 1개 호출; `core/feature_flags.py`.
5. **데이터 영향 / migration** — additive JSONL, 크기 회전(10MB×5). 기존 산출물 불변.
6. **기존 기능 호환성** — 플래그 off = 즉시 return. `ResponsePackage` 불변. `SearchTelemetry`와 별개 파일·스키마.
7. **feature flag / fallback** — `RETRIEVAL_AUDIT_LOG` 기본 `false`. 라이터 예외 → 로그 없이 계속.
8. **acceptance tests** — flag on + 6질의 → 6줄, 원문 질의 부재; flag off → 파일 미생성; 라이터 예외 주입 → 질의 정상; `os.chdir('/tmp')` 후에도 동일 파일; `2710 passed`.
9. **rollback plan** — 플래그 unset; 파일 삭제; `git revert`.
10. **privacy / rights impact** — 원문 질의·본문·식별자 미기록. salt는 비커밋 로컬 설정. 회전 상한 ≈50MB. disable=플래그.
11. **latency / cost impact** — sub-ms. LLM/임베딩 호출 불변.
12. **dependencies and risks** — `stage_ms` 세분화를 위해 `retrieve()`에 타이밍 포인트 추가 가능(계측, 로직 불변). 로그 분석 도구는 범위 밖. → CON-004, CON-009.
13. **out of scope** — 클릭/CTR telemetry, `SearchTelemetry` 활성화, 대시보드, 원격 수집, 원문 질의 저장.

## P0-4 — 생성·엔드투엔드 지연 계측 하니스 (측정 전용, 비파괴)

1. **해결하려는 CONFIRMED 문제** — PB-04. UI 생성 관측구간 미완료 → citation 렌더 미관측. **원인 UNKNOWN** → P0는 "분리 측정 가능하게" 한정 [2차 D-절, V2].
2. **Evidence** — Chat ≈23분·Research ≈4~5분; `/api/generate` 120s 무응답; llama-server 10~13% CPU; curl 경합 미배제; `research.py:277` "always run AI answer path" [2차 D-절].
3. **최소 변경 설계** — 독립 스크립트 `scripts/measure_generation_latency.py`(활성 코드 아님) + 프로토콜. 분리 항목: cold/warm load, retrieval-only, context assembly, first-token, total generation, UI render. 단일 테넌트. 부수로 Chat/Research 스피너에 경과시간+"생성 중" 표시와 클라이언트 hard timeout을 플래그(`UI_GENERATION_TIMEOUT_S`) 뒤에. → 스피너/timeout은 CON-005 참조.
4. **예상 변경 경로 / 파일** — 신규 `scripts/measure_generation_latency.py`; 선택 `ui/pages/chat.py`·`research.py` 스피너+timeout(~5행, 플래그).
5. **데이터 영향 / migration** — 없음.
6. **기존 기능 호환성** — 측정 스크립트는 프로덕션 경로 미변경. UI 플래그 off = 현행 무한 스피너.
7. **feature flag / fallback** — `UI_GENERATION_TIMEOUT_S` 미설정 = 현행. 설정 시 초과하면 안내+재시도(답변 폐기 아님).
8. **acceptance tests** — 스크립트가 load/retrieval/assembly/first-token/total/render 분리 표 산출, 재현; "first token latency" 수치 최초 생성; UI 플래그 on 시 timeout 경과 → 안내, 세션 유지; `2710 passed`.
9. **rollback plan** — 스크립트 삭제; UI 플래그 unset.
10. **privacy / rights impact** — 고정 공개 질의. 답변 본문 미저장, 시간·토큰수만.
11. **latency / cost impact** — 측정 실행이 GPU 1회 점유. 프로덕션 오버헤드 0.
12. **dependencies and risks** — 다른 부하 없는 상태에서만 유효 [2차 V2]. 하니스는 원인을 좁히기만 함 — 해법(모델·컨텍스트·양자화)은 전부 Deferred. → CON-005.
13. **out of scope** — 모델 교체, 양자화, `context_length`/VRAM 튜닝, LoRA/파인튜닝, 클라우드 호출, GPU 스케줄링.

---

# P1 Improvement Proposals

> P1은 PoC·비교 평가·feature flag가 선행되어야 하며, P0(특히 P0-3, PB-05 subset) 없이는 측정 불가. 설계 후보이며 승인 대상 아님.

## P1-1 — 현재 MAT 코퍼스용 최소 평가 subset + 평가 계약
- **해결**: PB-05 [2차 Q13/Q14]. **설계**: 기존 gold/eval 폐기 없이, MAT 대조 가능 subset(FULL 3 + PARTIAL 중 MAT 포함 + KO/EN/scripture 균형)만 추출. 판정축 = `expected_books ⊆ retrieved` AND 알려진 정답 청크 top-k 존재. run마다 `corpus_snapshot(dataset_sha256)`·`config_sha256`·`embedding_model`·`prompt_version`·`query_set_version` 계약 JSON. "coverage 없음"=`out_of_scope`(실패 아님). **PoC 선행**: subset이 P0-1 flag를 변별하는가. **flag/rollback**: 신규 파일만. **acceptance**: subset 15±건, 정답 축 명시, `out_of_scope` 규칙, run 1회=계약 JSON 1개, `2710 passed`. **risk**: 단일 문서라 통계적 힘 약함(회귀 확인용). → CON-007. **out of scope**: gold 확장, 다중 문서 eval, 모델 비교, 스키마 전면 통일.

## P1-2 — EPUB heading/locator provider (부분, PoC)
- **해결**: PB-02 잔여(페이지·heading). `heading_provider` EPUB 미등록, ATX 0 [2차 Q7]. **설계**: EPUB spine·nav(EPUB3)/NCX(EPUB2)에서 장 제목 트리 → `<stem>_headings.json` sidecar(additive) → `tsu_builder`가 EPUB일 때 `HeadingAssembler` 입력. **재청킹 없이** offset↔heading 매핑만. **PoC 선행**: 매튜 풀 EPUB nav가 장 경계를 담는지 육안 검증. **flag/rollback**: `EPUB_HEADING_PROVIDER`; sidecar 삭제. **acceptance**: `chunk_00280`에 `heading_path`="마태복음 > 6장" 수준; citation `text_location`이 파일명 대신 heading; **재빌드 전까지 `dataset_sha256` 불변**. **risk**: nav가 권 단위면 해상도 제한. 재빌드 시 `dataset_sha256` 변경 → P1-1 계약·`reindex_document` 동기. **out of scope**: 물리 페이지(EPUB에 없음), 전체 재청킹, PDF.

## P1-3 — Smith(`nae_ref_v1`) 활성 범위 축소 + 출처 표시
- **해결**: PB-08 [2차 Q8]. **설계**: (a) `should_activate_smith`를 인물/지명 사전형 질의로 좁히는 규칙을 플래그(`SMITH_ACTIVATION_STRICT`) 뒤에. (b) 주입 항목을 citation 목록에 **보조 출처**로 전달(`source_type="reference"`, 위계 하위 명시). (c) OCR 품질 경고 플래그. **OCR 재처리 안 함**. **PoC 선행**: strict 규칙을 질의 세트에 돌려 과활성/과소활성 측정. **flag/rollback**: `SMITH_ACTIVATION_STRICT` 기본 off. **acceptance**: strict on 시 `매튜 풀 주석에서…`·`마태복음 6:9-13…` → False, `모세는 누구인가` → True; citation에 Smith `reference` 타입 포함; `2710 passed`. **risk**: strict가 유효 질의 놓칠 수 있음(과소활성). citation에 넣으려면 위계 구분 필드가 없어 기존 필드 오버로드 필요(호환성). `nae_ref_v1`에 rights 필드 없음 → 채울 rights 없음. → CON-006. **out of scope**: Smith 일반 질의 확장(P2), OCR 재추출, `nae_ref_v1` 재색인.

## P1-4 — ClaimGuard fail-open 정책 옵션 비교 (결론 미도출)
- **해결**: PB-07 [2차 Q15]. **설계(비교만)**: (A) 현행 fail-open (B) fail-open + 감사 로그(P0-3 채널에 `claimguard_error`) (C) fail-soft: 예외 시 "자동 검증 실패" 배지(차단 아님). trade-off 표. 결론 없음. **flag/rollback**: `CLAIMGUARD_FAIL_POLICY` = `open`(기본)/`open_logged`/`soft`. **acceptance(옵션별)**: (B) 예외 주입 시 로그 1건, 답변 정상; (C) 예외 시 배지, 답변 유지. **risk**: `absolute_claim_blocked`의 **UI 집행이 UNKNOWN** [2차 V3] → (C)가 현행과 어떻게 다른지 확정 불가. UI 집행 확인 선행. → CON-008. **out of scope**: 절대화 주장 차단 정책 확정(Deferred), 탐지 규칙 변경, 인용/근거성 검증 신설.

## P1-5 — `DEFAULT_BENCH_DIR` 경로 앵커링
- **해결**: PB-06 [2차 §실행위치]. **설계**: 상대값이면 `BASE_DIR` 기준 해석(절대면 그대로). 안전을 위해 `BENCH_DIR_ANCHOR_BASE`(기본 off) 게이트, 한 스프린트 관찰 후 전환. **flag/rollback**: 플래그 unset = 현행 cwd 상대. **acceptance**: `os.chdir('/tmp')` 후 `DEFAULT_TSU_DATASET_PATH`가 `/Users/David/DBMA/output/bench/...`로 해석; `/Users/David/DBMA`에서 실행 시 불변; `2710 passed`. **risk**: cwd 상대에 의존하는 스크립트 존재 가능(미확인, [1차 U15]) → 플래그 점진 전환. 운영오류로 확인된 바 없음. → CON-011. **out of scope**: 다른 경로 상수 일괄 변경, 실행 래퍼.

---

# P2 / Deferred Proposals

| 항목 | 지금 하지 않는 이유 | 재검토 전 필요한 증거 |
|------|--------------------|----------------------|
| `USE_INVERTED_INDEX=true` / hybrid·tantivy 활성화 | 지시서 금지(#11). `tantivy_index/` 최신성 미검증 [2차 V5] | tantivy ↔ 현재 dataset 정합 증명 + P0-3 관측 + KO/EN/scripture A/B |
| `modules.nae_pd.enabled=true` / NAE bridge 활성화 | 지시서 금지(#11). 비활성 예외만 확인 [2차 Q9]. `nae_tsu_v1` `citation_policy` 전건 null [2차 Q10] | isolated read-only PoC + source separation 계약 + PB-09 해소 + bridge latency + HQ 승인 |
| 전체 corpus 재청킹·재임베딩·재색인 | 원칙 #3. `dataset_sha256` 변경 | 재처리로만 풀리는 확인 결함 + P1-1 계약으로 before/after |
| 새 vector DB / PostgreSQL / Qdrant·Chroma·Tantivy 전면 교체 | 지시서 금지(#4). Qdrant green, 검색 실동작 [2차 Q12] | 현행 스택의 확인된 한계 + PoC + 호환성 |
| 생성 모델 교체 / 양자화 / `context_length` 튜닝 | PB-04 원인 UNKNOWN [2차 V2]. 금지(#6·#12) | P0-4 하니스의 병목 단계 특정 |
| LoRA / 파인튜닝 | 금지(#6) | 프롬프트·검색 개선 소진 후 잔여 정량 결함 |
| 클라우드 Deep Audit / 대규모 클라우드 모델 자동 호출 | 금지(#6·#8). 저작권 자료 외부 전송 위험 | rights 분류 완료(PB-09) + 데이터 최소화 |
| Smith 일반 질의 확장 | 이미 과활성 [2차 Q8] | P1-3 측정 후, 일반 질의에서 품질 상승 근거 |
| ClaimGuard 최종 차단 정책 | `absolute_claim_blocked` UI 집행 UNKNOWN [2차 V3] | UI 집행 실동작 확인 + P1-4 비교 |
| 다중 문서 코퍼스 확장 | 현재 단일 MAT [1차 §5.5] | P0/P1 안정화 + 문서 추가 시 회귀 계약(P1-1) |
| `_record_result_click`/CTR telemetry | `ResponsePackage`에 `telemetry_query_id` 없음 [2차 Q16] | P0-3 채널 안정화 후 |
| n8n control-plane 개선 | 활성 상태 UNKNOWN [1차 U2] | 워크플로 활성 여부 + 실행 이력 |

---

# Integration Contract Review

> 각 경계: **현재 확인된 계약 / 깨질 수 있는 조건 / 최소 검증 방법 / 통합(변경)을 보류해야 하는 조건.** 상세 충돌은 `DBMA_NAE_PROPOSAL_CONFLICT_REGISTER_v1.md`.

## 1. DBMA legacy TSU ↔ CitationBuilder / UI
- **현재 계약**: `CitationBuilder.build_citations()` → `Citation(source_title, source_author, scripture_reference, source_file, evidence_confidence, retrieval_score, …)`. title/author 없으면 None, citation card는 truthy 필드만 렌더 → `['문서']` [2차 Q6/Q7].
- **깨질 수 있는 조건**: `Citation` 필드 추가 시 언팩·직렬화 테스트 파손; sidecar 오조인 시 오인용.
- **최소 검증**: P0-2 acceptance(A3 5건 서지, `dataset_sha256` 불변, `2710 passed`) + `document_id` 유일성.
- **보류 조건**: 다중 문서 `document_id` 충돌 관측; `Citation` 필드 추가 불가피.

## 2. DBMA legacy search ↔ Korean query parsing / BM25
- **현재 계약**: `_extract_keywords`(ASCII) → `bm25_score`. `[]`→0.0. 문서측 `_tokenize`(한국어). 두 경로 분리. BM25 가중 0.25 [2차 §BM25, 1차 §3.3].
- **깨질 수 있는 조건**: 질의 keyword 축 변경 → 모든 한국어 질의 랭킹 이동. `_detect_themes` 상호작용 미검증.
- **최소 검증**: P0-1 acceptance 4분리 + P1-1 subset 회귀.
- **보류 조건**: EN·scripture-ref 결과가 flag on/off로 달라짐; subset 변별력 없음.

## 3. DBMA active Chat ↔ NAE verified TSU
- **현재 계약**: **연결 없음.** chat.py는 bridge 미호출, `nae_pd` disabled, 호출 시 예외 [2차 Q9]. `nae_tsu_v1` `citation_policy` 전건 null [2차 Q10].
- **깨질 수 있는 조건**: bridge 활성 시 payload 스키마(`claim`/`source_text`/`work_id`) ↔ `CitationBuilder` 입력(`content`/`document_id`) 불일치; source separation 붕괴; `citation_policy` 부재로 인용 규칙 미결정.
- **최소 검증**: read-only isolated PoC(별도 컬렉션·플래그, 실답변 미주입) + 스키마 매핑 표 + rights/locator 선확보.
- **보류 조건**: 지시서 #11 — **무조건 보류**. PoC·계약·HQ 승인 전까지 `nae_pd.enabled=false`.

## 4. DBMA active Chat ↔ Smith reference injection
- **현재 계약**: `should_activate_smith` True → `search_reference`(타임아웃 5s×2, 실패 `[]`) → `<reference>` 블록 append(+1,720~3,399자). citation **미전달** [2차 Q8].
- **깨질 수 있는 조건**: 활성 규칙 축소 시 유효 인물/지명 질의 누락; citation에 넣을 때 위계 미구분 시 주 출처 오인; OCR 텍스트 인용.
- **최소 검증**: P1-3 acceptance(activate 매트릭스, `reference` 타입, 위계 라벨).
- **보류 조건**: strict가 recall 크게 저하; Smith가 품질 올린다는 근거 부재.

## 5. retrieval ↔ generation ↔ UI rendering
- **현재 계약**: Chat·Research 모두 `generate_answer()` 완료 후 렌더(`research.py:277`). retrieval 82~1,708 ms 완료되나 생성이 끝나야 검색결과·citation 렌더. 관측구간 내 미완료 → 렌더 UNKNOWN [2차 D-절, V1].
- **깨질 수 있는 조건**: 생성/렌더 분리는 UX-007 §4.1 의도와 충돌; 클라이언트 timeout이 진행 중 생성 폐기 위험(동시 생성).
- **최소 검증**: P0-4 하니스 단계 분리 + 스피너 경과/timeout(안내만, 폐기 아님).
- **보류 조건**: 렌더 분리(검색 우선 표시)는 별도 UX 결정 — 본 제안서 결론 없음.

## 6. current corpus ↔ gold queries / evaluation results
- **현재 계약**: `gold_queries.json`은 `expected_books`로만 대조(ID 없음). MAT 1종. FULL 3/100. `output/eval/*` 0/8. 스키마 상이 [2차 Q13/Q14].
- **깨질 수 있는 조건**: gold 100건 전량 실행 → 73 NONE이 실패로 오집계.
- **최소 검증**: P1-1(`out_of_scope`/`fail` 분리, 계약 JSON).
- **보류 조건**: subset이 P0-1을 변별 못하면 P0-1 기본값 전환 보류. 스키마 통일은 단계적.

## 7. process cwd ↔ bench / index / log paths
- **현재 계약**: `DEFAULT_BENCH_DIR` cwd 상대; `DATA_DIR` 절대. 검증 전부 `os.chdir` 후. **운영 오류 기록 없음** [2차 §실행위치].
- **깨질 수 있는 조건**: cron·CI·서브프로세스가 다른 cwd에서 호출 → 빈 dataset·엉뚱한 telemetry 위치.
- **최소 검증**: P1-5(`os.chdir('/tmp')` 후 `BASE_DIR` 해석).
- **보류 조건**: cwd 상대에 의존하는 스크립트 발견 시 플래그 유지.

## 8. ClaimGuard ↔ generation output / UI behavior
- **현재 계약**: `_run_claim_guard` → `ClaimGuardResult`. HIGH → `absolute_claim_blocked=True`. 예외 → `RiskLevel.NONE`, 답변 계속 [2차 Q15]. **UI 집행 UNKNOWN** [2차 V3].
- **깨질 수 있는 조건**: fail-soft 배지가 현행 UI의 기존 `absolute_claim_blocked` 처리와 이중/모순.
- **최소 검증**: 먼저 UI 집행 렌더 관측(생성 완료 조건), 그다음 P1-4 비교.
- **보류 조건**: UI 집행 UNKNOWN 동안 fail 정책 변경 보류. 차단 정책 Deferred.

---

# Recommended Validation Sequence

> 구현 순서가 아니라 **승인 전** 검증 순서. 각 단계 실패 시 다음으로 넘어가지 않는다.

## S0 — 결정적 재현
- **대상**: PB-01·PB-02·PB-04가 고정 corpus 스냅샷+고정 질의에서 재현되는가.
- **fixture**: 현재 `tsu_dataset.jsonl`(`dataset_sha256` 기록) + KO/EN/scripture 각 5건(FULL 3 gold + A1/A2/A3).
- **측정값**: 후보 풀 크기, BM25 non-zero 수, top-5 chunk ID, `stage_ms`; citation 인자 dict; 생성 first-token 유무.
- **통과 기준**: 2차 수치(A2 `chunk_00280` 누락, citation `['문서']`, 생성 미완료) 재현.
- **실패 시 결론**: 환경이 2차와 달라짐 → 증거 baseline 재확정 전까지 진행 불가.
- **다음 단계 금지 조건**: 재현 안 됨.

## S1 — 최소 eval subset (P1-1)
- **대상**: subset이 "검색 회귀"를 잡는가.
- **fixture**: MAT 대조 gold 13±건 + 정답 청크 매핑.
- **측정값**: 현행 legacy 경로 subset 점수(baseline).
- **통과 기준**: 각 건 정답 축 존재, `out_of_scope`/`fail` 규칙화.
- **실패 시 결론**: P0-1·P1-2 기본값 전환 무기한 보류(플래그 구현까지만).
- **다음 단계 금지 조건**: 변별력 미확인.

## S2 — 관측 채널(P0-3) + 지연 분리 측정(P0-4)
- **대상**: 단계별 수치 디스크 저장; 생성 지연이 어느 단계인가.
- **fixture**: S0 질의, 다른 부하 없는 상태.
- **측정값**: `retrieval_audit.jsonl` 필드 완전성·프라이버시; load/retrieval/assembly/first-token/total/render 분리 표.
- **통과 기준**: 6질의→6줄, 원문 없음; first-token 수치 존재.
- **실패 시 결론**: PB-04 원인 규명 불가 → 생성 관련 모든 P2 보류 유지.
- **다음 단계 금지 조건**: 라이터가 질의를 깨거나 원문을 남김.

## S3 — P0-1 flag A/B (S1 subset)
- **대상**: 한국어 키워드 보강이 KO 검색 개선 + EN·scripture 비회귀.
- **fixture**: S1 subset + P0-1 4분리 세트.
- **측정값**: flag on/off subset 점수, KO-exact top-5 진입, EN·scripture 동일성.
- **통과 기준**: KO-exact 개선 AND EN·scripture 완전 동일 AND subset 비회귀.
- **실패 시 결론**: flag opt-in 유지(기본값 off 영구) 또는 재설계.
- **다음 단계 금지 조건**: EN/scripture 회귀.

## S4 — P0-2 sidecar fill
- **대상**: 서지 backfill이 무결성 지키며 citation 완성.
- **fixture**: EPUB DC 메타 + registry + S0 질의.
- **측정값**: A3 citation 5건 `source_title`/`source_author`; `dataset_sha256`; 전체 테스트.
- **통과 기준**: 서지 채움 AND `dataset_sha256` 불변 AND `2710 passed` AND `document_id` 유일.
- **실패 시 결론**: sidecar 스키마·조인 재설계.
- **다음 단계 금지 조건**: `dataset_sha256` 변경 또는 오조인.

## S5 — P1 항목별 PoC
- P1-2: 매튜 풀 EPUB nav 추출 정확도 육안 검증.
- P1-3: activate 매트릭스 측정.
- P1-4: **먼저 UI 집행 여부 렌더 관측**(생성 완료 환경), 그다음 정책 비교.
- P1-5: `/tmp` 실행 테스트.
- 각 PoC 실패 시 해당 항목만 보류.

---

# First Candidate Vertical Slice

## 후보: **P0-2 (서지 메타데이터 sidecar backfill) — 단, 아래로 축소**

Conflict Register CON-003(verse_mapping ↔ 본문 불일치)·CON-012(EPUB `rights=[]` + 프로젝트 `AUTHORITATIVE_SOURCE_MISSING` 관례)에 따라, 첫 slice는 **`source_title` + `source_author` fill만** 포함한다. locator·rights·heading은 제외한다.

## 조건 충족 확인

| 조건 | 근거 |
|------|------|
| P0의 확인된 active-path 문제 | PB-02 서지 신원 부분 — citation card가 `['문서']` 한 줄만 [2차 Q6]. 활성 Chat 경로 재현 |
| 기존 corpus·index 삭제·전수 재처리 없음 | additive 파일 1개. `tsu_dataset.jsonl`·EPUB·index 불변, `dataset_sha256` 불변 |
| 기존 Chat 경로 기본값 보존 | `CITATION_SIDECAR_FILL` 기본 off = 현행 바이트 동일 |
| feature flag / fallback | 플래그 + sidecar 부재 시 현행 |
| acceptance·rollback 명확 | A3 5건 서지 채움 / `dataset_sha256` 불변 / `2710 passed`; rollback = 플래그 unset·파일 삭제 |
| 다른 대형 변경의 선행 조건 아님 | P0-1·P0-3·P0-4·bridge·hybrid와 독립 |
| 사용자 체감 개선 | 근거 카드에 **저자(매튜 풀)·서명**이 표시됨 |

## 이 slice가 포함하지 않는 것
- rights 필드(CON-012), 물리 페이지·heading_path(P1-2), `verse_mapping` 기반 locator(CON-003), `MAT ?:?` 개선
- 한국어 검색(P0-1), 관측(P0-3), 지연(P0-4)
- `Citation`/`ResponsePackage` 필드 추가, citation card 구조 변경
- NAE `nae_tsu_v1` 연결, Smith citation 전달, `tsu_dataset.jsonl` 재빌드

## 검증 게이트
S0(재현) → S4(sidecar fill, rights·locator 제외). S1~S3는 이 slice의 선행 조건 **아님**. `dataset_sha256` 불변·`2710 passed`가 회귀 방지선.

---

# Deferred Decisions

| 항목 | 재검토 트리거 |
|------|--------------|
| Qdrant/Chroma/Tantivy 전면 전환, 새 vector DB·PostgreSQL | 현행 스택의 확인된 한계 + PoC + 호환성 |
| NAE bridge 기본 활성화 | isolated PoC + source separation 계약 + PB-09 해소 + HQ 승인 |
| 전체 corpus 재청킹·재색인·재임베딩 | 재처리로만 풀리는 확인 결함 + P1-1 계약 |
| 생성 모델 교체 | P0-4 하니스의 병목 단계 특정 |
| LoRA/파인튜닝 | 위 + 정량 잔여 결함 |
| 클라우드 Deep Audit 자동화 | rights 분류 + 데이터 최소화·비전송 설계 |
| Smith 일반 질의 확장 | P1-3 측정 + 정량 근거 |
| ClaimGuard 절대화-주장 차단 정책 | UI 집행 확인 [2차 V3] + P1-4 비교 |
| `USE_INVERTED_INDEX=true` | tantivy 정합 증명 + P0-3 관측 + A/B |

---

# Final Recommendation

## 지금 시작할 최소 변경 1개
**P0-2 (축소판: `source_title`+`source_author` sidecar fill).** PB-02는 신학 연구 시스템의 핵심인 **출처 추적성**을 직접 훼손하는 확인된 결함이고, sidecar 방식은 `tsu_dataset.jsonl`·index·원본 불변(`dataset_sha256` 불변), 플래그 off 즉시 원복, 다른 대형 변경의 선행 조건 아님. 단 rights·locator는 CON-003/CON-012로 첫 slice에서 제외. **착수 전 S0 재현 + Conflict Register의 CON-002 검증 필요.**

## 지금 하지 말아야 할 변경
1. `USE_INVERTED_INDEX=true` / hybrid·tantivy 활성화
2. `modules.nae_pd.enabled=true` / NAE bridge 활성화
3. 전체 corpus 재청킹·재OCR·재임베딩·재색인
4. 생성 모델 교체·양자화·`context_length`/VRAM 튜닝·LoRA·파인튜닝 (PB-04 원인 UNKNOWN)
5. Qdrant/Chroma/Tantivy 교체, 새 vector DB·PostgreSQL
6. Smith 활성 범위 확대
7. ClaimGuard 절대화-주장 차단 정책 확정
8. `tsu_dataset.jsonl`·`nae_tsu_v1`·`nae_ref_v1`·`output/eval/*`·gold query 삭제·덮어쓰기
9. `Citation`/`ResponsePackage` 공개 필드 추가
10. 사용자 질의마다 전체 코퍼스를 LLM 컨텍스트에 투입
11. sidecar에 EPUB 권리 상태 단정 (CON-012)
12. `verse_mapping`을 검증 없이 표시 locator로 사용 (CON-003)

## 다음 개선 제안 전 반드시 확인해야 할 사실
1. **S0 재현**: 2차 수치가 현재 환경에서 재현되는가 (worktree ↔ live 코드 동일성 포함 [1차 §5.3]).
2. **PB-04 UI 집행**: 생성 완료 조건에서 citation card·Smith 항목·`absolute_claim_blocked`가 화면에서 실제로 어떻게 동작하는가 [2차 V1/V3/V4].
3. **P1-1 subset 변별력**: MAT 단일 corpus 기준 subset이 P0-1 flag를 유의미하게 구분하는가.
4. **NAE 미색인 4,441건**: 어느 파이프라인 단계가 필터했는지 [2차 V9].
5. **`_tokenize` ↔ BM25 문서 통계 상호작용**: 2-gram keyword가 하이브리드 랭킹을 어떻게 이동시키는가.
6. **ADR-001~033 본문**: retrieval·citation·telemetry·NAE 경계를 규율하는 ADR이 있는지 (두 점검은 미판독 [1차 §1.2]).

---

# 점검 증거로 확인되지 않은 가정

> 본 제안서가 암묵적으로 기대지만 1차·2차 점검에서 **직접 확인되지 않은** 사항. 이 가정이 깨지면 해당 제안의 재검토가 필요하다.

| # | 가정 | 관련 제안 |
|---|------|-----------|
| A-1 | worktree(`7984118`)의 코드가 구현 시점 live `/Users/David/DBMA` 코드와 동일 | 전체 |
| A-2 | 구현·검증 사이에 다른 세션이 `tsu_dataset.jsonl`·registry·Qdrant·`output/eval/*`를 변경하지 않음 | 전체 |
| A-3 | `nae_qdrant`·`dbma_n8n` 컨테이너·데이터가 안정 유지 | P0-2 rights, Integration §3·§4 |
| A-4 | EPUB DC 메타(title/creator/publisher/ISBN)가 인용에 정확·충분. EPUB **1종**만 확인 | P0-2, P1-2 |
| A-5 | `verse_mapping` chapter/verse가 신뢰 가능. 2차에서 본문 불일치 관측(A1 #3, A3 #4) [2차 Q4/Q5] | P0-2 locator, P1-2 |
| A-6 | Chat ≈23분 미완료가 **대표적** 상태이며 `curl` 경합 [2차 V2]·일시 자원상태 때문이 아님 | P0-4, Integration §5 |
| A-7 | `_extract_keywords`에 한국어 토큰을 넣어도 `_detect_intent`/`_extract_themes`/`_detect_scripture_refs`와 충돌 없음 | P0-1 |
| A-8 | 회귀 2,710건이 이 제안이 건드리는 경로를 실제 커버(커버리지 미측정) | P0-1, P0-2, P0-3 |
| A-9 | `RETRIEVAL_DOCUMENT_CAP=2`·dedup·diversity가 다중 문서에서도 단일 문서와 동일 동작 [1차 §5.5] | P1-1, Deferred |
| A-10 | `tantivy_index/`와 현재 `tsu_dataset.jsonl`이 동기 [2차 V5] | Deferred(hybrid) — P0/P1은 tantivy 미사용 |
| A-11 | sidecar `document_id` ↔ TSU `document_id` 조인이 1:1 (단일 문서 자명, 다중 문서 미검증) | P0-2 |
| A-12 | `feature_flags.py`/환경변수 플래그가 Streamlit 재기동 없이 프로세스 수준 일관 (플래그 추가 미실행). `get_shared_query_processor`는 `dataset_sha256` 변경 시만 재생성 [2차 §query→답변] | 전체 P0/P1 |
| A-13 | retrieval·citation·telemetry·NAE 경계를 규율하는 Approved ADR이 없거나, 있어도 본 제안과 충돌하지 않음 (ADR 본문 미판독 [1차 §1.2]) | 전체 |

---

*문서 끝. 본 제안서는 계획이며, 어떤 코드·설정·데이터·인덱스·서비스도 변경하지 않았다.*
