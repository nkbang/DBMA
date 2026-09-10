# DBMA/NAE 1차 점검 보고서

- 작성일: 2026-09-09
- 점검 대상: DBMA/NAE repository 및 로컬 실행 환경
- 점검 위치: `/Users/David/DBMA/.claude/worktrees/confident-dewdney-a10c0e` (worktree), 데이터는 `/Users/David/DBMA/`
- 브랜치 / 커밋: `claude/dbma-nae-pipeline-audit-8e8224` / `7984118` (2026-09-09)
- 코드 변경: 없음
- 두 비교 기준 문서(고도화 제안서, Sprint 0 감사)는 **점검 항목을 정하는 용도로만** 사용했고, 그 서술을 사실로 채택하지 않았다
- 본 보고서에는 판정·개선 방안·계획을 포함하지 않는다

---

## 1. Repository Inventory

### 1.1 규모

| 항목 | 수치 | 확인 명령 |
|------|------|-----------|
| Git 추적 파일 | 9,911개 | `git ls-files \| wc -l` |
| 작업 트리 용량 | 423 MB | `du -sh .` |
| Python LOC (tests) | 37,855 | `git ls-files 'tests/*.py' \| xargs wc -l` |
| Python LOC (scripts) | 24,143 | 〃 |
| Python LOC (core) | 18,357 | 〃 |
| Python LOC (NAE) | 11,721 | 〃 |
| Python LOC (ui) | 8,994 | 〃 |

### 1.2 최상위 디렉터리별 추적 파일 수

| 디렉터리 | 파일 수 | 내용 |
|----------|--------:|------|
| `.automation/` | 8,277 | n8n control-plane. 하위 `evidence/` 8,091, `night-shift/` 64, `requests/` 39, `tasks/` 35, `audit/` 22, `control-plane/` 16, `workflows/` 4 |
| `docs/` | 528 | ADR 33건(`docs/architecture/ADR-001`~`ADR-033`), UX 계획서, 파이프라인·상태 문서 |
| `NAE/` | 362 | `review/` 132, `corpus/` 110, `pipeline/` 78, `benchmark/` 18, `collectors/` 9, `authority/` 5 |
| `tests/` | 244 | 테스트 파일 232개 + 픽스처 |
| `scripts/` | 144 | `.py` 97개 |
| `evidence/` | 104 | `gate2/`, `phase5_1_contract/`, `phase5_1_remediation/`, `phase5_1_remediation_004/`, `phase5_2/` |
| `core/` | 73 | 아래 1.3 |
| `resources/` | 34 | |
| `ui/` | 31 | `pages/` 13, `components/` 8, `state/`, `theme/` |
| `sermon_corpus/` | 27 | |
| `archive/` | 10 | `archive/legacy/` (ADR-003에 따라 격리된 legacy 경로) |
| `workspace/` | 9 | `experiments/ inbox/ logs/ reports/ snapshots/ staging/` — `snapshots/`는 `.gitkeep` 1개뿐 |

### 1.3 `core/` 모듈 목록 (49개 `.py` + 3개 패키지)

```
추출·정제  extractors.py  text_normalizer.py  noise_classifier.py
           repetition_detector.py  raw_hygiene.py  frontmatter_detector.py
           date_extractor.py  multi_doc_splitter.py  extraction_failures.py
구조       heading_extractor.py  heading_provider.py  heading_constants.py
           pdf_structure_detector.py  semantic_boundary_detector.py
           document_context.py  document_detail.py
청킹       text_splitter.py  chunking_optimizer.py  hierarchical_chunk_builder.py
식별·색인  identity_registry.py  document_identity.py  index_orchestrator.py
           tsu_builder.py  background_index_builder.py  bible_index.py
           candidate_generator.py
검색       retrieval.py (2,271행)  hybrid_candidate_pipeline.py  rrf.py
           parallel_retriever.py  query_planner.py  query_enhancements.py
           search_cache.py  search_telemetry.py  embedder.py
생성·검증  generation.py  claim_guard.py
데이터모델 evidence_unit.py  dataset_registry.py  canonical_constants.py
           tag_ingest_validator.py  review_disposition_v2.py
운영       config.py  files.py  processing.py  utils.py  init.py
           module_registry.py  feature_flags.py  runtime_state.py
           execution_context.py  research_workspace.py  reading_session.py
패키지     dataset_adapters/  evidence_adapters/  evaluation/  sermon/  tli/
```

### 1.4 `ui/` 페이지 (11개 탭)

`ui/app.py:419-425` 등록 순서 — Dashboard, Library, Processing, Research, AI에게 질문(chat), 설교 연구, 설교문 작성, 그 외 `sermon_review.py`, `monitor.py`, `onboarding.py`, `help.py`.

### 1.5 런타임 환경 (venv `~/envs/dbma311`, Python 3.11.15)

| 패키지 | 버전 |
|--------|------|
| streamlit | 1.58.0 |
| docling | 2.106.0 |
| sentence-transformers | 5.5.1 |
| pymupdf | 1.27.2.3 |
| ebooklib | 0.20 |
| qdrant-client | 1.18.0 |
| tantivy | 0.26.0 |
| chromadb | 1.5.9 |
| ollama | 0.6.2 |
| pydantic | 2.13.4 |
| pytest | 9.1.1 |
| **llama-index-core** | **NOT INSTALLED** |

`grep -rn "llama_index" --include='*.py' core/ ui/ NAE/ scripts/` 결과 **0건**. `requirements*.txt`에도 llama-index 항목 없음. (`CLAUDE.md`의 "RAG 스택: LlamaIndex" 서술과 설치·임포트 실측이 일치하지 않음 — 사실만 기록)

### 1.6 컨테이너 / 서비스

| 이름 | 이미지 | 상태 | 포트 |
|------|--------|------|------|
| `nae_qdrant` | qdrant/qdrant:latest | **Up 2 weeks** | 7333→6333, 7334→6334 |
| `dbma_n8n` | n8nio/n8n:latest | **Up 2 weeks** | 5678 (`/healthz` → `{"status":"ok"}`) |
| `open-webui` | ghcr.io/open-webui/open-webui:main | Up 2 weeks (healthy) | 3000→8080 |
| `dbma_qdrant` | qdrant/qdrant:latest | **Exited (143) 6 weeks ago** | 6333 (미개방) |
| `typesense-bench` | — | Exited (255) 2 weeks ago | — |
| `meilisearch-bench` | — | Exited (137) 5 weeks ago | — |
| `qdrant` | — | Exited (255) 2 weeks ago | — |

Ollama: 로컬 프로세스로 기동 중(`ollama serve` + `llama-server`). 모델 11개 —
`bge-m3:latest`, `my-theology-bot-v2:latest`, `llama3.1:8b`, `qwen3:32b`, `qwen3.8:27b`,
`qwen3.6:35b`, `qwen3.6:35b-DBMAcode`, `qwen3.6:35b-DBMAcode-Cline`,
`dbma-planner-r1-q6:70b`, `mxbai-embed-large:latest`, `nomic-embed-text:latest`.

Streamlit 프로세스: **미기동** (`ps aux | grep streamlit` 0건).

### 1.7 데이터 인벤토리

**로컬 파일 (`/Users/David/DBMA/data/`)**

| 경로 | 내용 |
|------|------|
| `data/RAW/` | EPUB 1개(매튜 풀 청교도 성경주석 14 마태복음, 14.7 MB) + `설교_분리/` (빈 디렉터리, 0 파일) |
| `data/제련완성본/` | 정제본 `.md` 1개(1.81 MB), `_chunks.txt` 1개(2.16 MB), `_chunks_meta.json` 1개, 원본 복사본 1개, `THEOLOGY_OF_GRACE.txt`, `은혜에_의한_구원_설교.md`, `registry/` |
| `data/제련완성본/registry/` | `documents.json`, `documents.json.lock`, `extraction_failures.json` |
| `data/beta_corpus/` | 12개 PDF (`bible_study/` 8, `commentaries/` 4) |
| `data/nae/` | 7 파일 |
| `data/sermon_corpus/` | 7 파일 |
| `data/bible/` | 2 파일 |
| `data/inbox/`, `data/normalized/` | 각 1 파일 |
| `data/processed/` | **0 파일** |
| `data/chat_session_history.json` | **부재** |

**색인 산출물 (`/Users/David/DBMA/output/bench/`)**

| 파일 | 크기 / 값 |
|------|-----------|
| `tsu_dataset.jsonl` | 3,414,842 bytes / **1,363 레코드** |
| `tsu_manifest.json` | 598 bytes |
| `bible_index.sqlite3` | 339,968 bytes |
| `tantivy_index/` | 65개 항목 |
| `tsu_dataset.jsonl.lock` | 0 bytes |
| `search_telemetry.sqlite3` | **부재** |

**평가 산출물 (`/Users/David/DBMA/output/eval/`)**

| 파일 | 최종 수정 |
|------|-----------|
| `test_run_001_eval.jsonl` | 2026-07-27 01:07 |
| `test_run_002_eval.jsonl` | 2026-07-27 01:18 |
| `baseline_002_sermon_eval.jsonl` | 2026-07-27 19:05 |
| `beta_llama31_8b_20260728T135719_sermon_eval.jsonl` | 2026-07-28 14:04 |
| `goldexp_001_worksheet.json` | 2026-07-27 20:10 |

**NAE 코퍼스 (on-disk, `NAE/corpus/tsu/`)**

| 저작 | `tsu.json` 레코드 수 |
|------|---------------------:|
| `Dagg_Church_Order` | 3,377 |
| `Fuller_Complete_Works_Vol01` | 3,643 |
| `Hiscox_Standard_Manual` | 740 |
| 그 외 | `_batch*_promotion_backup_*` / `_promotion_backup_*` 백업 디렉터리 다수, `tsu_id_state.json` |

`NAE/corpus/` 하위: `canonical/`(PBC1765, PBC1742, SLBC1689), `quarantine/`(PBC1765), `embeddings/`, `manifests/`, `reports/`.
`NAE/governance/corpus_admissions.jsonl`: **14행**.
`NAE/authority/works.yaml`: `works: []` (빈 상태, 주석에 ADR-021 SS4 Option C 명시). `NAE/authority/legacy_snapshot/` 별도 존재.

**벡터 인덱스 (Qdrant `localhost:7333`)**

| 컬렉션 | points | status | 벡터 |
|--------|-------:|--------|------|
| `nae_ref_v1` | **34,948** | green | 1024-dim, Cosine |
| `nae_tsu_v1` | **3,319** | green | 1024-dim, Cosine |

`nae_tsu_v1` 소스별 exact count:

| identifier | count |
|------------|------:|
| `Dagg_Church_Order` | 2,958 |
| `Hiscox_Standard_Manual` | 361 |
| `Fuller_Complete_Works_Vol01` | **0** |
| 합계 | 3,319 (컬렉션 총계와 일치) |

`nae_ref_v1` 소스별 exact count:

| source_id | count |
|-----------|------:|
| `BAP-REF-SMITH-VOL01` | 8,841 |
| `BAP-REF-SMITH-VOL02` | 8,391 |
| `BAP-REF-SMITH-VOL03` | 8,184 |
| `BAP-REF-SMITH-VOL04` | 9,532 |
| 합계 | 34,948 (컬렉션 총계와 일치) |

---

## 2. Actual Data Flow Map

아래는 코드 판독과 산출물 실측으로 확인한 **현재 연결 상태**다. 점선은 코드에 존재하나 현재 실행 조건이 충족되지 않아 흐르지 않는 경로다.

### 2.1 적재 → 색인 (Ingestion)

```text
data/RAW/<파일>
   │
   │ core/files.py · core/processing.py::process_one_file()
   │   ├ core/extractors.py::extract_text_auto()
   │   │    · .pdf → _extract_pdf_title_author() 로 title/author 판독
   │   │    · .docx → _extract_docx_title_author()
   │   │    · .epub → extract_text_from_epub()  (서지 판독 함수 없음)
   │   ├ core/noise_classifier.py · core/text_normalizer.py
   │   │  core/repetition_detector.py
   │   └ core/processing.py::validate_chunks() → ChunkValidationResult
   ▼
data/제련완성본/<stem>.md            ← YAML frontmatter:
data/제련완성본/<stem>_chunks.txt        source / source_type / language
data/제련완성본/<stem>_chunks_meta.json  created_at / noise_score / noise_mode
   │
   │ core/identity_registry.py (registry_lock 으로 직렬화)
   ▼
data/제련완성본/registry/documents.json
   · document_id / file_hash / ingest_status / pipeline_state
   · pipeline_flags{ingested,copied,extracted,cleaned,chunked,
                    output_generated,verified}
   · superseded_by / supersedes / retry_count / max_retries
   │
   │ core/index_orchestrator.py
   │   rebuild_tsu_index() | reindex_document(document_id) | reconcile_pending()
   │   └ core/tsu_builder.py::build_tsu_records()
   │        · source_type == "pdf" → get_registry().resolve("pdf")
   │                                 + HeadingAssembler().assign()
   │        · 그 외            → HeadingStack().apply_chunk()   (ATX 기반)
   │        · registry 에 source_tier 키가 있을 때만 source_provenance 생성
   │        · registry 에 nae_theological_position 키가 있을 때만 nae_metadata 생성
   ▼
output/bench/tsu_dataset.jsonl   (1,363 레코드)
output/bench/tsu_manifest.json   (dataset_sha256 / registry_sha256 / config_sha256)
   │
   ├─ core/candidate_generator.py::open_or_build_index()
   │     → output/bench/tantivy_index/   (replace_document 로 문서 단위 교체)
   └─ core/bible_index.py::build_index() / BibleIndex.replace_document()
         → output/bench/bible_index.sqlite3
```

`reindex_document()`는 `tsu_dataset.jsonl`·`tantivy_index`·`bible_index.sqlite3` 세 곳 모두에서
해당 `document_id` 행만 교체한다. `reconcile_pending()`은 `pipeline_state == "PROCESSED"` 문서를
색인하고 `INDEXED`로 전진시키며, `superseded_by`가 설정된 문서의 TSU 레코드를 데이터셋에서 제거한다.

### 2.2 질의 → 답변 (Query, 라이브 경로)

```text
ui/pages/chat.py::_handle_user_message()
   │
   │ ui/state/query_processor.py::get_shared_query_processor()
   │   · tsu_manifest.json 의 dataset_sha256 을 매 호출 비교 → 변경 시 재생성
   │   · engine_kind = session_state 우선, 없으면 hybrid_candidate_pipeline.is_enabled()
   │   · is_enabled() = os.environ["USE_INVERTED_INDEX"] == "true"  (기본 미설정)
   ▼
core/retrieval.py::QueryProcessor.process(question, k)
   │
   ├ QueryParser.parse()
   │    _detect_intent / _extract_scripture_refs / _extract_themes
   │    _extract_keywords / _detect_books_standalone / _resolve_book_name
   │
   ├ RetrievalEngine.retrieve(parsed_query, k_output, embedding_cache, file_scope)
   │    STEP 1  _metadata_filter()          verse_mapping 기준
   │    STEP 1b file_scope 필터              chat.py "단일/다중 파일" 선택
   │    STEP 2  bm25_score()                candidate_pool 전건 루프
   │            무히트 시 candidate_pool[:candidate_k] 슬라이스
   │    STEP 3  core/embedder.py::get_embedder() → bge-m3 인코딩
   │            EmbeddingCache.lookup() 후 정규화 벡터 내적
   │            예외 시 _ensure_tfidf_index() → TfidfVectorizer 코사인
   │    STEP 4  compute_theological_score()
   │            _scripture_alignment_score / _thematic_relevance_score
   │            _sermon_usability_score / compute_passage_match_score
   │            compute_source_tier_bonus / compute_content_quality_factor
   │    STEP 5  하이브리드 가중합
   │            0.25*BM25 + 0.20*vector + 0.30*theological
   │            + 0.20*PassageMatch + 0.05*SourceTierBonus
   │    STEP 6  _deduplicate() / _apply_document_diversity()
   │    STEP 7  top-k
   │
   ├ ContextAssembler.assemble() → <context id="{tsu_id}" score="{f}">…</context>
   ├ CitationBuilder.build_citations() → Citation(citation_id, tsu_id,
   │      scripture_reference, source_title, source_author, document_id,
   │      content_excerpt, evidence_confidence, retrieval_score,
   │      source_file, language, source_type)
   └ ResponseFormatter.format() → ResponsePackage(+ PerformanceMetrics)
   │
   ▼
ui/pages/chat.py::_inject_smith_context()
   │  NAE/smith_activation.py::should_activate_smith(query)   (정규식 의도 분류)
   │  → True 이면 rewrite_query_for_smith()
   │  → NAE/reference_retrieval_adapter.py::search_reference(q, top_k=3)
   │       ollama bge-m3 임베딩(타임아웃 5.0s)
   │       → Qdrant :7333 / nae_ref_v1 (타임아웃 5.0s)
   │       → 실패·타임아웃·malformed 전부 [] 반환
   │  → "smith" 포함 항목만 필터 → <reference> 블록 + 위계 안내문을 컨텍스트에 append
   ▼
core/generation.py::GenerationService.generate()
   │  ollama my-theology-bot-v2:latest
   │  _external_source_directive(candidates)
   │      candidates 중 source_provenance 가 있는 것이 하나라도 있을 때만 지시문 추가
   │  _run_claim_guard(answer, response)
   │      core/claim_guard.py::ClaimGuard → ClaimGuardResult
   │      (risk_level / matched_terms / scope_qualifier_required /
   │       absolute_claim_blocked / suggested_wording)
   │      예외 발생 시 RiskLevel.NONE 결과를 반환하고 답변은 그대로 사용
   ▼
ui/pages/chat.py
   │  ui/components/citation_card.py::render_citation_card(
   │      source_file, text_location, doc_type, author,
   │      citation_title, relevance_score, …)
   │    · text_location = structure.heading_path 를 " > " 로 결합
   │    · author/title  = Citation.source_author / Citation.source_title
   │  ui/state/query_processor.py::record_query_latency(total_ms)
   │      → st.session_state["query_latencies_ms"] (최대 200건, 디스크 미기록)
   ▼
답변 + 근거 카드
```

### 2.3 실행 조건이 충족되지 않은 경로 (코드 존재)

```text
[a] 역인덱스 하이브리드 경로
    core/hybrid_candidate_pipeline.py::HybridQueryProcessor / HybridRetriever
      ← core/candidate_generator.py (tantivy) + core/query_planner.py + core/rrf.py
      게이트: is_enabled() == os.environ.get("USE_INVERTED_INDEX","false")=="true"
      현재 환경변수 미설정
      · core/search_telemetry.py::SearchTelemetry.record_query() 는
        이 경로(hybrid_candidate_pipeline.py:323)에서만 호출됨

[b] NAE 공개신학 TSU 브리지
    NAE/retrieval_adapter.py::search() / bridge_query()
      게이트: core/module_registry.py ← config.yaml modules.nae_pd.enabled: false
      비활성 시 NaePdModuleDisabledError
      호출처: ui/pages/research.py:566 (chat.py 는 호출하지 않음)

[c] DBMA 자체 Qdrant
    config.yaml vector_db.qdrant.url: http://localhost:6333
      컨테이너 dbma_qdrant = Exited (143), 포트 미개방
      core/retrieval.py 에서 qdrant 문자열은 1202행(파라미터 기본값)과
      1208행(self.qdrant_url 대입) 두 곳뿐 — 조회 호출 없음

[d] ChromaDB
    config.yaml vector_db.chroma.* 존재, chromadb 1.5.9 설치됨
      config.yaml 주석에 "legacy corpus history로만 보존되며,
      현재 검색 경로에서 쿼리되지 않습니다" 명시

[e] EvidenceUnit 계열
    core/evidence_unit.py::EvidenceUnit 및 하위 모델
      임포트하는 곳: core/evidence_adapters/base.py,
                     devonthink_fixture_adapter.py, notion_fixture_adapter.py
      core/retrieval.py · core/generation.py · ui/ 에서의 임포트 0건

[f] n8n control-plane
    .automation/control-plane/*.py (control_plane, executor_dispatch,
      n8n_gateway, evidence_collector, policy_enforcement, heartbeat 등)
    .automation/workflows/*.json (phase-e.json 외 3건)
    컨테이너 dbma_n8n 기동 중(/healthz ok), 워크플로 활성 상태는 §4 참조
```

---

## 3. 확인한 증거

### 3.1 파일 경로

| 경로 | 확인 내용 |
|------|-----------|
| `config.yaml` | 단일 설정 소스. §3.3 참조 |
| `dbma_ui.py` | `from ui.app import main` 만 수행하는 thin launcher |
| `ui/app.py:419-425` | 탭 → 렌더 함수 매핑 |
| `ui/pages/chat.py:46` | `from NAE.smith_activation import should_activate_smith, rewrite_query_for_smith` |
| `ui/pages/chat.py:352` | `from NAE.reference_retrieval_adapter import search_reference` |
| `ui/pages/chat.py:770` | `render_citation_card(...)` 호출 |
| `ui/pages/research.py:566` | `from NAE.retrieval_adapter import bridge_query, NaePdModuleDisabledError` |
| `ui/state/query_processor.py:30` | `from core.hybrid_candidate_pipeline import HybridQueryProcessor, is_enabled` |
| `core/retrieval.py:1202,1208` | `qdrant_url` 파라미터·대입 (조회 호출 없음) |
| `core/retrieval.py:1243` | `_load_corpus()` — jsonl 을 `self.tsus` 에 적재 |
| `core/heading_provider.py:151-155` | `register("md"/"markdown"/"txt", MarkdownProvider)`, `register("pdf", PdfHeadingProvider)` |
| `core/tsu_builder.py:450,459` | `record["source_provenance"] = {...}` / `= None` |
| `core/tsu_builder.py:470,477` | `record["nae_metadata"] = {...}` / `= None` |
| `core/extractors.py:108,124` | `_extract_pdf_title_author()`, `_extract_docx_title_author()` |
| `core/extractors.py:159` | `extract_text_from_epub()` |
| `core/index_orchestrator.py:49,101,174,280,374,473,498` | `rebuild_tsu_index` / `reindex_document` / `reconcile_pending` / `exclude_document_from_index` / `delete_raw_source` / `list_trashed_raw_files` / `restore_raw_source` |
| `core/hybrid_candidate_pipeline.py:49` | `is_enabled()` |
| `core/hybrid_candidate_pipeline.py:323` | `self.telemetry.record_query(...)` |
| `core/evidence_unit.py` | `EvidenceUnit` 및 하위 모델 정의 |
| `NAE/governance/corpus_admissions.jsonl` | 14행. 각 행에 `source_id`/`authority_class`/`track`/`decided_by`/`date`/`evidence_refs` |
| `NAE/authority/works.yaml` | `works: []` |
| `tests/gold_queries.json` | `total_queries: 100`, 7개 범주 |
| `tests/goldsets/claim_guard_goldset_v1.jsonl` | ClaimGuard 골드셋 |
| `docs/architecture/ADR-001` ~ `ADR-033` | ADR 33건 |
| `workspace/snapshots/` | `.gitkeep` 1개만 존재 |
| `data/제련완성본/registry/documents.json` | 문서 3건 |
| `output/bench/tsu_manifest.json` | 아래 3.3 |

### 3.2 함수 / 클래스명

| 영역 | 이름 |
|------|------|
| 질의 파싱 | `QueryParser.parse` · `_detect_intent` · `_extract_scripture_refs` · `_extract_themes` · `_extract_keywords` · `_detect_books_standalone` · `_resolve_book_name` |
| 검색 | `RetrievalEngine.__init__/_load_corpus/_build_tfidf_index/_ensure_tfidf_index/retrieve/_metadata_filter/_deduplicate/_apply_document_diversity/list_source_files/book_coverage/book_embedding_coverage` |
| 스코어링 | `bm25_score` · `TfidfVectorizer` · `compute_passage_match_score` · `compute_source_tier_bonus` · `compute_content_quality_factor` · `compute_theological_score` · `_scripture_alignment_score` · `_thematic_relevance_score` · `_sermon_usability_score` |
| 조립·인용 | `ContextAssembler.assemble` · `Citation` · `CitationBuilder.build_citations` · `ResponseFormatter.format` · `ResponsePackage` · `RankedCandidate` · `ParsedQuery` · `ScriptureReference` · `PerformanceMetrics` |
| 캐시 | `EmbeddingCache.lookup/insert/batch_insert/get_hit_rate/validate/rebuild` |
| 생성·검증 | `GenerationService` · `_run_claim_guard` · `_external_source_directive` · `_format_sermon_context` · `ClaimGuard` · `ClaimGuardResult` · `RiskLevel` |
| 처리 | `process_one_file` · `process_batch` · `validate_chunks` · `ChunkValidationResult` · `build_converter` · `build_splitter` · `detect_language` · `save_md_with_language` · `save_chunks` · `get_processed_files` · `mark_processed` |
| 색인 | `build_tsu_records` · `write_tsu_dataset` · `write_manifest` · `open_or_build_index` · `CandidateGenerator.replace_document` · `BibleIndex.add_tsus/replace_document/delete_document/lookup/lookup_scripture_ref` · `keys_for_scripture_ref` · `canonical_key` |
| 하이브리드 | `HybridQueryProcessor` · `HybridRetriever` · `is_enabled` · `SearchTelemetry.record_query/record_click/summary/zero_hit_rate/click_through_rate` · `open_telemetry` |
| NAE | `should_activate_smith` · `rewrite_query_for_smith` · `search_reference` · `ReferenceRetrievalError` · `EmbeddingTimeoutError` · `QdrantConnectionError` · `bridge_query` · `NaePdModuleDisabledError` |
| 데이터모델 | `EvidenceUnit` · `EvidenceLocation` · `EvidenceContent` · `EvidenceProvenance` · `EvidenceRights` · `EvidenceQuality` · `EvidenceAnnotations` · `EvidenceTrust` · `CorpusType` · `LicenseStatus` · `DisplayPolicy` · `ExportPolicy` · `ExtractionStatus` · `CitationReadiness` · `TrustTier` · `LicensePolicy` |
| 평가 | `judge_groundedness` · `JUDGE_PROMPT_VERSION` · `run_benchmark_integration` · `compare_with_regression` |
| UI | `render_citation_card` · `get_shared_query_processor` · `record_query_latency` · `_current_dataset_fingerprint` · `_inject_smith_context` · `_format_smith_context` |

### 3.3 설정값

**`config.yaml`**

| 키 | 값 |
|----|----|
| `app.version` | `1.3.0` |
| `directories.raw_dir` | `data/RAW` |
| `directories.output_dir` | `data/제련완성본` |
| `directories.bench_dir` | `output/bench` |
| `directories.logs_dir` | `logs` |
| `chunking.default_size` / `default_overlap` | `1200` / `120` |
| `chunking.min_chunk_size` / `max_chunk_size` | `80` / `5000` |
| `vector_db.primary` | `qdrant` |
| `vector_db.qdrant.url` | `http://localhost:6333` |
| `vector_db.qdrant.collections` | `sermon: dbma_sermon`, `chunks: dbma_chunks` |
| `vector_db.chroma.collection_name` / `persist_directory` | `dbmar_docs` / `chroma_db` |
| `embedding.model` / `dimension` | `all-MiniLM-L6-v2` / `384` |
| `ollama.default_embed_model` | `bge-m3:latest` |
| `ollama.default_gen_model` | `my-theology-bot-v2:latest` |
| `rag.top_k` / `default_temperature` | `4` / `0.2` |
| `rag.min_length` / `max_noise` | `80` / `70.0` |
| `rag.chunk_size` / `chunk_overlap` | `1200` / `120` |
| `maintenance.trash_retention_days` | `30` |
| `modules.nae_pd.enabled` | **`false`** |
| `modules.nae_pd.corpus_root` | `NAE/corpus/tsu` |
| `modules.nae_pd.index_collection` | `nae_tsu_v1` |

**`core/config.py` 파생 상수**

| 이름 | 해석 결과 |
|------|-----------|
| `DEFAULT_TSU_DATASET_PATH` | `output/bench/tsu_dataset.jsonl` |
| `DEFAULT_SEARCH_TELEMETRY_PATH` | `output/bench/search_telemetry.sqlite3` |
| `DEFAULT_REGISTRY_PATH` | `data/제련완성본/registry/documents.json` |
| `RETRIEVAL_DOCUMENT_CAP` | `2` (`rag.document_cap` 미정의 → 기본값) |

**코드 내 상수**

| 위치 | 값 |
|------|----|
| `core/feature_flags.py` | `SPRINT2_FEATURES = True` |
| `core/hybrid_candidate_pipeline.py:49` | `USE_INVERTED_INDEX` 기본 `"false"` — 현재 셸에 미설정 |
| `ui/pages/chat.py:58` | `_SCOPE_K = {"단일 파일":3, "다중 파일":5, "전체 파일":5}` |
| `ui/pages/chat.py:65-66` | `_HISTORY_MAX_TURNS = 3`, `_HISTORY_MAX_CHARS_PER_MESSAGE = 300` |
| `ui/pages/chat.py:80` | `_LOW_CONFIDENCE_SCORE_THRESHOLD = 0.45` |
| `NAE/reference_retrieval_adapter.py:31-32` | `_EMBEDDING_TIMEOUT_S = 5.0`, `_QDRANT_TIMEOUT_S = 5.0` |
| `NAE/retrieval_adapter.py:30-31` | `_HARD_TIMEOUT_MS = 3000`, `_WARN_THRESHOLD_MS = 1500` |
| `core/retrieval.py:1657` | 하이브리드 가중치 `0.25 / 0.20 / 0.30 / 0.20 / 0.05` |

**`output/bench/tsu_manifest.json`**

```json
{"generated_at":"2026-09-07T23:35:51","tsu_count":1363,"source_document_count":3,
 "build_commit":"478a2de3cb4a9e9913226ff235e483adf4aa80ff",
 "builder_script":"scripts/build_tsu_dataset.py",
 "registry_path":"data/제련완성본/registry/documents.json",
 "registry_sha256":"2c4d6e39…","dataset_sha256":"fc9705c8…",
 "dataset_records":1363,"config_file":"config.yaml","config_sha256":"f664eda6…"}
```

**registry 실제 내용 (`documents.json`, 3건)**

| document_id (앞 12자) | source_file | ingest_status | pipeline_state |
|---|---|---|---|
| `c6618c640f79` | 매튜 풀 청교도 성경주석 14  마태복음 (매튜 풀).epub | `PROCESSED` | `INDEXED` |
| `f1822d8ee752` | THEOLOGY_OF_GRACE.txt | `EXCLUDED` | — |
| `7d95e9df3cf6` | 은혜에_의한_구원_설교.md | `EXCLUDED` | — |

PROCESSED 문서 레코드의 값: `chunk_count: 1363`, `language: "ko"`, `noise_score: 38.5`,
`noise_mode: "rich_text"`, `source_type: "epub"`, `is_ocr: false`, `doc_type: "주석"`,
`book/chapter/page/title/author: null`, `superseded_by/supersedes: null`,
`pipeline_flags` 7개 항목 모두 `true`.

`<stem>_chunks_meta.json`: `chunks: 1363`, `chunk_size: 1200`, `chunk_overlap: 120`,
`quality: {avg_noise: 16.632…, max_noise: 100.0, avg_dup: 0.2068, short_ratio: 0.0323, passed: false}`.

### 3.4 실행 명령과 그 출력

| 명령 | 출력 |
|------|------|
| `~/envs/dbma311/bin/python -m pytest tests/ -q` | `2710 passed, 15 skipped, 16 warnings in 78.63s` |
| `~/envs/dbma311/bin/python -V` | `Python 3.11.15` |
| `git ls-files \| wc -l` | `9911` |
| `git log -1 --format='%H %ad %s' --date=short` | `7984118 2026-09-09 docs: add evidence-based DBMA/NAE pipeline audit (Sprint 0)` |
| `wc -l output/bench/tsu_dataset.jsonl` | `1363` |
| `curl -s http://localhost:6333/collections` | 무응답 (연결 실패) |
| `curl -s http://localhost:7333/collections` | `{"result":{"collections":[{"name":"nae_ref_v1"},{"name":"nae_tsu_v1"}]},"status":"ok"}` |
| `curl -s http://localhost:5678/healthz` | `{"status":"ok"}` |
| `curl -s http://localhost:5678/api/v1/workflows -H "X-N8N-API-KEY: …"` | `{"message":"unauthorized"}` |
| `curl -s http://localhost:11434/api/tags` | 모델 11개 |
| `docker ps -a` | §1.6 표 |
| `grep -n 'qdrant' core/retrieval.py` | 2행(`1202`, `1208`)만 일치 |
| `grep -rn "llama_index" --include='*.py' core/ ui/ NAE/ scripts/` | 0건 |
| `grep -rEn 'anthropic\|openai\|gemini\|google.generativeai' --include='*.py' core/ ui/ scripts/ NAE/` | 0건 |
| `grep -rn "chunk_version\|is_active\|valid_from\|supersedes_chunk" --include='*.py' core/` | 0건 |
| `ebooklib` 로 `data/RAW/…epub` DC 메타 판독 | `title=('매튜 풀 청교도 성경주석 14 : 마태복음',)`, `creator=('매튜 풀', role=aut)`, `publisher=('크리스챤다이제스트',)`, `identifier` 에 ISBN `978-89-447-8472-9`, `language=('ko',)`, `rights=[]` |

**`tsu_dataset.jsonl` 1,363건 집계 (Python 스크립트로 전건 순회)**

| 항목 | 값 |
|------|----|
| 고유 `source_file` | **1개** (매튜 풀 EPUB) |
| `source_provenance` non-null | 0 |
| `nae_metadata` non-null | 0 |
| `page` non-null | 0 |
| `chapter` non-null | 0 |
| `title` non-null | 0 |
| `structure.heading_path` 비어있지 않음 | 0 |
| `content_quality.noise_type` 분포 | `NORMAL_CONTENT` 1,250 / `ORIGINAL_LANGUAGE` 108 / `OCR_FRAGMENT` 5 |
| `verse_mapping` 키 조합 | `(book_id,)` 1,294 / `(book_id, chapter, verse_start)` 50 / `(book_id, chapter, verse_end, verse_start)` 18 / `(book_id, chapter)` 1 |

**TSU 레코드 스키마 (첫 레코드 실물)**

`tsu_id`, `document_id`, `chunk_id`, `content`, `verse_mapping`, `themes`, `title`, `author`,
`chapter`, `page`, `source_file`, `language`, `source_type`,
`content_quality{noise_type,quality_score,section_type}`,
`structure{heading_path,heading_depth,heading_confidence,heading_source}`,
`theological_claim`, `doctrine_category`, `baptist_theme`, `source_provenance`, `nae_metadata`

**`nae_tsu_v1` payload 키 (Qdrant scroll 1건)**

`access_control`, `author`, `author_id`, `book`, `canonical_version`, `category`,
`category_status`, `citation_policy`, `citation_policy_status`, `citation_score`,
`citations`, `claim`, `collector_version`, `copyright_status`, `doctrine`, `duplicate_of`,
`edition_id`, `evidence_score`, `identifier`, `llm_score`, `metadata_provenance`,
`metadata_schema_version`, `overall_score`, `page`, `paragraph`, `parser_score`,
`publication_year`, `review_status`, `scriptures`, `sentence`, `source_id`,
`source_identifier`, `source_text`, `source_type`, `tsu_access`, `tsu_id`,
`tsu_schema_version`, `usage_permission`, `volume_id`, `work_id`
— 샘플 값: `review_status="verified"`, `page=8`, `usage_permission="research"`,
`copyright_status="public_domain"`

**`nae_ref_v1` payload 키 (Qdrant scroll 1건)**

`chunk_index`, `text`, `identifier`, `source_id`, `volume`, `page_start`, `page_end`,
`heading_context`, `content_type`
— 샘플 값: `source_id="BAP-REF-SMITH-VOL02"`, `page_start=191`, `page_end=193`,
`content_type="reference_dictionary"`

**`NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json` 첫 레코드 키**

`id`, `tsu_schema_version`, `book`, `author`, `identifier`, `source_identifier`,
`collector_version`, `canonical_version`, `page`, `paragraph`, `sentence`, `source_text`,
`claim`, `doctrine`, `scriptures`, `citations`, `confidence`, `extraction_method`,
`review_status`, `model`, `source_id`, `author_id`, `work_id`, `edition_id`,
`publication_year`, `source_type`, `copyright_status`, `usage_permission`,
`access_control`, `volume_id`, `tsu_access`, `category`, `category_status`,
`citation_policy`, `citation_policy_status`, `metadata_schema_version`,
`metadata_provenance`
— 샘플 값: `page=12`, `paragraph=35`, `sentence=1`, `review_status="generated"`,
`category_status="AUTHORITATIVE_SOURCE_MISSING"`, `citation_policy=null`

### 3.5 테스트 / 로그

**테스트**

- 전체 스위트 실행 결과: **`2710 passed, 15 skipped, 16 warnings in 78.63s`** (2026-09-09, `~/envs/dbma311`)
- 테스트 파일 232개
- 경고 유형: `PytestReturnNotNoneWarning` — `tests/test_query_enhancements_full_regression.py` 의 여러 테스트가 `None` 대신 `dict` 를 반환
- 골드셋: `tests/gold_queries.json` (`version 1.0.0`, `created 2026-07-10`, `total_queries 100`; 범주별 `book_reference` 15, `theme` 15, `doctrine` 12, `original_language` 8, `historical` 10, `mission_pastoral` 8 …), `tests/goldsets/claim_guard_goldset_v1.jsonl`
- CI: `.github/workflows/ci.yml`, `.github/workflows/update-docs.yml`

**로그**

- `config.yaml` 의 `directories.logs_dir: "logs"` 가 가리키는 `/Users/David/DBMA/logs` — **디렉터리 부재** (`ls: No such file or directory`)
- `/Users/David/DBMA/output/bench/search_telemetry.sqlite3` — **부재**
- `/Users/David/DBMA/data/chat_session_history.json` — **부재**
- `workspace/logs/` — 존재하나 추적 파일은 `.gitkeep` 계열
- 남아 있는 실행 기록: `/Users/David/DBMA/output/eval/*.jsonl` 5개 (최신 2026-07-28)
  - `test_run_002_eval.jsonl` 첫 레코드: `run_id="test_run_002"`, `query_id="BK001"`,
    `question="Romans 8:28"`, `retrieved_chunk_ids=["TSU-ROM-d02a5e70…_chunk_00293"]`,
    `groundedness=0.0`, `judge_model="dbma-planner-r1-q6:70b"`,
    `judge_prompt_version="v1"`, `timestamp="2026-07-27T06:11:37…"`,
    `groundedness_rationale="답변은 검색된 청크와 무관하며 Romans 8:28에 대한 정보가 청크에 존재하지 않습니다."`
  - 이 레코드가 참조하는 `TSU-ROM-…` 문서는 현재 `tsu_dataset.jsonl`(매튜 풀 단일 문서)에 존재하지 않음
- `.automation/evidence/` — 8,091개 파일 (`ADR-021-PILOT-*.jsonl`, `CONTROL-PLANE-PILOT-*.jsonl`,
  `ADR-022-PHASE-E-INDEPENDENT-VERIFICATION.md` 등)

---

## 4. UNKNOWN으로 남긴 항목

| # | 항목 | UNKNOWN인 이유 |
|---|------|----------------|
| U1 | 실행 중인 Streamlit UI의 실제 화면 출력 | Streamlit 프로세스 미기동. 본 점검에서 앱을 기동하지 않았으므로 인용 카드·탭이 실제로 무엇을 렌더링하는지 화면으로 확인하지 못함. §2의 UI 서술은 전부 코드 판독 결과 |
| U2 | n8n 워크플로의 활성/비활성 상태 및 최근 실행 이력 | `dbma_n8n` 컨테이너는 기동 중이고 `/healthz`는 ok이나, `docker-compose.yml`에 기재된 `N8N_API_KEY` 값으로 `/api/v1/workflows` 호출 시 `{"message":"unauthorized"}`. 인증 없이 확인 불가하며, 자격증명을 새로 만들거나 UI에 로그인하는 행위는 점검 범위를 벗어남 |
| U3 | `.automation/` 8,277개 파일의 내용과 control-plane 실제 가동 여부 | 파일 수·디렉터리 구조·모듈명만 확인. 8,091개 evidence 파일의 내용은 미판독. control-plane 코드가 실제로 실행된 적이 있는지, 언제 마지막으로 실행됐는지 확인하지 못함 |
| U4 | `dbma_qdrant`(:6333) 볼륨에 남아 있는 데이터 | 컨테이너가 `Exited (143)` 상태. 기동은 점검 범위 밖의 상태 변경이므로 `qdrant_storage` 볼륨의 컬렉션·포인트 수 미확인 |
| U5 | ChromaDB `chroma_db/` 의 실제 내용 | `chromadb 1.5.9` 설치 확인, `config.yaml`에 설정 존재. 디렉터리 실물과 컬렉션 내용은 미확인 |
| U6 | `nae_tsu_v1` / `nae_ref_v1` payload의 전체 분포 | 각 컬렉션에서 scroll 1건씩만 판독. 소스별 exact count는 확인했으나(§1.7), `review_status`·`page`·`usage_permission` 등 필드가 **전체 포인트에서** 어떤 분포를 갖는지는 미측정 |
| U7 | `NAE/corpus/tsu/` on-disk 7,760건과 `nae_tsu_v1` 3,319건의 차이 내역 | 소스별 count는 확인(Dagg 3,377→2,958 / Hiscox 740→361 / Fuller 3,643→0). 각 차이가 어떤 레코드에 해당하는지, 어떤 절차로 걸러졌는지는 `NAE/review/`·`NAE/governance/` 판독이 더 필요하며 이번 범위에서 수행하지 않음 |
| U8 | `data/nae/`(7) `data/sermon_corpus/`(7) `data/bible/`(2) `data/inbox/`(1) `data/normalized/`(1) `sermon_corpus/`(27 tracked) 의 내용 | 파일 수만 확인. 개별 파일 내용 및 어떤 코드 경로가 이들을 읽는지 미추적 |
| U9 | `evidence/`(104) 및 `analysis/`, `_c1_test/`, `archive/` 의 내용 | 디렉터리 목록만 확인 |
| U10 | 실제 사용자 질의 이력 | `search_telemetry.sqlite3`·`chat_session_history.json`·`logs/` 모두 부재. 이 설치본에서 실제 질의가 수행된 적이 있는지 판단할 근거가 없음 |
| U11 | `output/eval/` 5개 파일 전체 내용 및 당시 코퍼스 구성 | `test_run_002_eval.jsonl` 첫 레코드만 판독. 5개 파일의 전 레코드와, 2026-07-27~28 시점의 `tsu_dataset.jsonl` 구성은 확인하지 못함(당시 스냅샷 없음) |
| U12 | `USE_INVERTED_INDEX=true` 로 켰을 때의 동작 | 환경변수를 설정해 실행하는 것은 상태 변경이므로 수행하지 않음. `tantivy_index/`(65개 항목)가 현재 `tsu_dataset.jsonl`과 동기 상태인지도 미검증 |
| U13 | `modules.nae_pd.enabled=true` 일 때의 `bridge_query()` 동작 | 설정 변경을 수반하므로 미수행 |
| U14 | Qdrant 인증·네트워크 노출 설정 | `nae_qdrant`가 `0.0.0.0:7333` 으로 바인딩된 것은 `docker ps` 로 확인. API key 설정 여부 등 보안 구성은 컨테이너 환경변수·설정 파일 미판독으로 UNKNOWN |
| U15 | `scripts/` 97개 스크립트 중 실제로 사용되는 것과 일회성 산출물의 구분 | 파일명·일부 docstring만 확인 |
| U16 | `docs/` 528개 문서의 최신성 | ADR 목록과 일부 파일명만 확인. 각 문서가 현재 코드 상태를 반영하는지 대조하지 않음 |
| U17 | `nas/` 원격(`nas/dev/dbma-engine` 등)과 `origin/` 의 차이 | `git branch -r` 목록만 확인. fetch·diff 미수행 |

---

## 5. 점검 범위의 한계

1. **읽기 전용 점검이다.** 코드·설정·데이터를 일절 변경하지 않았고, 서비스 기동/중지, 환경변수 설정, 모듈 플래그 변경, 컨테이너 시작을 수행하지 않았다. 따라서 "현재 상태에서 관측되는 사실"만 담고 있으며, 조건을 바꿨을 때의 동작(U12·U13)은 범위 밖이다.

2. **UI를 실행하지 않았다.** §2의 UI 흐름과 §3의 UI 관련 증거는 전부 **코드 판독** 결과다. 화면에 실제로 무엇이 출력되는지는 확인하지 않았다(U1). 코드 경로와 렌더 결과가 다를 가능성을 배제하지 못한다.

3. **worktree에서 점검했다.** 작업 위치는 `/Users/David/DBMA/.claude/worktrees/confident-dewdney-a10c0e` 이고, `data/`·`output/`·`logs/` 는 `.gitignore` 대상이라 worktree에 없다. 이 경로들은 원본 체크아웃 `/Users/David/DBMA/` 의 실물을 절대경로로 읽었다. 두 위치의 코드가 동일하다는 것은 worktree 생성 시점(`7984118`) 기준이며, 그 이후 원본 체크아웃에서 코드가 변경됐을 가능성은 검증하지 않았다.

4. **단일 시점의 스냅샷이다.** 모든 수치는 2026-09-09 기준이다. `tsu_dataset.jsonl`은 2026-09-07 23:35 생성분이고, Qdrant 컨테이너는 "Up 2 weeks" 상태다. 점검 중 다른 세션이 데이터를 변경했다면 반영되지 않는다.

5. **코퍼스가 문서 1건 규모다.** `tsu_dataset.jsonl`의 고유 `source_file`이 1개이므로, 다중 문서·다중 포맷 상황에서만 드러나는 동작(문서 간 중복 제거, `RETRIEVAL_DOCUMENT_CAP=2`의 실효, 파일 스코프 선택, PDF heading provider 경로)은 이 점검에서 관측되지 않았다. PDF 경로(`PdfHeadingProvider`)는 코드로만 확인했고 실제 산출물로 확인하지 못했다.

6. **전건 판독이 아니다.** `tsu_dataset.jsonl` 1,363건은 전건 순회 집계했으나, Qdrant 38,267 포인트(34,948 + 3,319)는 scroll 1건씩 + 소스별 count 쿼리만 수행했다. `.automation/evidence/` 8,091개, `docs/` 528개, `scripts/` 97개는 목록 수준에서만 확인했다.

7. **인증이 필요한 대상은 확인하지 못했다.** n8n API(U2)가 이에 해당한다. 새 자격증명을 만들거나 UI에 로그인하는 것은 점검이 아니라 상태 변경·접근 행위라고 보아 수행하지 않았다.

8. **두 비교 기준 문서를 사실 근거로 쓰지 않았다.** 고도화 제안서와 Sprint 0 감사는 "무엇을 확인할지" 목록을 뽑는 데만 사용했다. 두 문서에 서술된 내용 중 이번 점검에서 직접 재확인하지 못한 것은 본 보고서에 싣지 않았다.

9. **성능·품질을 측정하지 않았다.** 질의 지연, 검색 정확도, 답변 근거성을 측정하는 실행(예: `scripts/run_rag_eval.py`)은 수행하지 않았다. `output/eval/`의 기존 기록은 2026-07-27~28 것이며 현재 코퍼스와 대응하지 않는다(§3.5).

10. **판정·권고를 포함하지 않는다.** 지시에 따라 상태 등급, 원인 분석, 개선 방안, 우선순위, 계획을 일절 담지 않았다. §3의 집계 수치(예: 특정 필드의 non-null 0건)는 관측 사실이며 평가가 아니다.
