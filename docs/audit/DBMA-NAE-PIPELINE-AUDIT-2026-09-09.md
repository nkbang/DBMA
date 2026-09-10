# DBMA/NAE 파이프라인 실사 감사 보고서

- 작성일: 2026-09-09
- 감사 브랜치: `claude/dbma-nae-pipeline-audit-8e8224` (base `32f59c9`)
- 감사 방식: repository / config.yaml / 실제 산출물 / 실행 중인 서비스 / 전체 테스트 스위트 직접 확인
- 코드 변경: **없음** (read-only audit)
- 전제: 첨부된 "고도화 제안서"는 목표 방향으로만 취급하고, 근거로 사용하지 않음

---

## 0. 감사 근거 (Evidence Ledger)

| # | 증거 | 확인 방법 | 결과 |
|---|------|-----------|------|
| E1 | 전체 테스트 | `pytest tests/ -q` (venv `~/envs/dbma311`) | **2710 passed, 15 skipped, 78.6s** |
| E2 | 라이브 TSU 코퍼스 | `output/bench/tsu_dataset.jsonl` | 1,363 records, 3.4 MB |
| E3 | TSU manifest | `output/bench/tsu_manifest.json` | `tsu_count=1363`, `source_document_count=3`, `build_commit=478a2de` |
| E4 | 실제 source_file 분포 | jsonl 집계 | **1개 문서(매튜 풀 마태복음 EPUB)가 1,363건 전부** |
| E5 | Identity Registry | `data/제련완성본/registry/documents.json` | 3건 = PROCESSED 1 / EXCLUDED 2 |
| E6 | TSU 메타데이터 결측 | jsonl 집계 | `source_provenance` non-null **0/1363**, `nae_metadata` **0/1363**, `page` **0/1363**, `chapter` **0/1363**, `heading_path` 비어있지 않음 **0/1363**, `title` **0/1363** |
| E7 | verse_mapping 정밀도 | jsonl 집계 | book_id만 **1294/1363 (95.0%)**, chapter 이상 보유 **69건 (5.0%)** |
| E8 | Qdrant :6333 (config상 primary) | `curl /collections` | **무응답 — 컨테이너 미기동** |
| E9 | Qdrant :7333 (NAE) | `curl /collections` | green. `nae_ref_v1` **34,948 pts**, `nae_tsu_v1` **3,319 pts**, 1024-dim Cosine |
| E10 | Ollama | `curl /api/tags` | `bge-m3:latest`, `my-theology-bot-v2:latest` 등 11개 정상 |
| E11 | Qdrant 사용 여부(코어) | `grep -n qdrant core/retrieval.py` | **1202/1208행 2회뿐 — 저장만 하고 조회에 사용 안 함** |
| E12 | EPUB 서지 메타 | `ebooklib`로 원본 직접 판독 | title/creator/publisher/ISBN **원본에 존재** |
| E13 | 추출기 서지 지원 | `core/extractors.py` | `_extract_pdf_title_author`, `_extract_docx_title_author`만 존재. **EPUB 없음** |
| E14 | heading provider 등록 | `core/heading_provider.py:151-155` | md/markdown/txt/pdf만. **epub 미등록** |
| E15 | 청킹 품질 게이트 | `_chunks_meta.json` | `quality.passed=false`인데 `pipeline_state=INDEXED` |
| E16 | 검색 텔레메트리 DB | `output/bench/` 파일 목록 | `search_telemetry.sqlite3` **부재 (기록된 질의 0건)** |
| E17 | 하이브리드 경로 게이트 | `core/hybrid_candidate_pipeline.py:49` | `USE_INVERTED_INDEX` 미설정 → **기본 OFF** |
| E18 | nae_pd 모듈 게이트 | `config.yaml modules.nae_pd.enabled` | **false** |
| E19 | NAE TSU payload | Qdrant scroll | `review_status=verified`, `page=8`, `usage_permission=research`, `copyright_status=public_domain` **전부 보유** |
| E20 | Smith payload | Qdrant scroll | `page_start/page_end/volume/source_id` 보유. **review_status·copyright·usage 필드 없음**, OCR 품질 열화 육안 확인 |
| E21 | Citation 자료구조 | `core/retrieval.py:1852-1880` | 검수 상태·인용 허용 필드 **없음** |
| E22 | 인용 카드 UI | `ui/components/citation_card.py` | 저자/출처/문서/본문위치/자료유형 5종만. **검수·인용가능 없음** |

---

## 1. 실제 데이터 흐름도 (사실 기반)

```text
┌─ [A] DBMA Core 경로 — 실제 라이브 질의 경로 ────────────────────────┐
│                                                                      │
│  data/RAW/*.epub|pdf|docx|md|txt                                     │
│        │  core/extractors.py::extract_text_auto                      │
│        │    · title/author 추출: PDF·DOCX만 (E13)                    │
│        ▼                                                             │
│  [정제] core/processing.py::process_one_file                         │
│        │  noise_classifier / text_normalizer / repetition_detector   │
│        ▼                                                             │
│  data/제련완성본/<stem>.md  (+ frontmatter: source/type/lang/noise)   │
│        │                                                             │
│        ▼  core/text_splitter + chunking_optimizer (1200/120)         │
│  <stem>_chunks.txt  +  <stem>_chunks_meta.json                       │
│        │    · validate_chunks() / quality.passed → 기록만, 차단 안 함 │
│        ▼                                                             │
│  registry/documents.json  (identity_registry, pipeline_state)        │
│        │                                                             │
│        ▼  core/index_orchestrator.py::rebuild_tsu_index /            │
│           reconcile_pending  →  core/tsu_builder.py                  │
│  output/bench/tsu_dataset.jsonl   ← ★ 유일한 검색 대상 (E2)          │
│  output/bench/tsu_manifest.json   (dataset_sha256 = 캐시 무효화 키)  │
│        │                                                             │
│        ▼  ui/state/query_processor.py::get_shared_query_processor    │
│  core/retrieval.py::RetrievalEngine._load_corpus()                   │
│        │    · jsonl 전체를 프로세스 메모리에 적재                     │
│        ▼                                                             │
│  retrieve():                                                         │
│    STEP1  메타 필터(verse_mapping) → 95%가 book_id만이라 거의 무효과   │
│    STEP1b 파일 스코프(사용자 선택)                                    │
│    STEP2  BM25 — candidate_pool 전건 파이썬 루프 (ANN 아님)           │
│           무히트 시 candidate_pool[:candidate_k] 무순위 슬라이스      │
│    STEP3  벡터 — bge-m3 임베딩 + EmbeddingCache 조회 후 내적          │
│           (Qdrant 미사용 E11, 실패 시 in-memory TF-IDF 폴백)          │
│    STEP4  신학 스코어링 / STEP5 하이브리드 / STEP6 dedup / STEP7 top-k │
│        ▼                                                             │
│  ContextAssembler → CitationBuilder(Citation) → ResponsePackage      │
│        ▼                                                             │
│  core/generation.py::GenerationService (Ollama my-theology-bot-v2)   │
│        │  + _run_claim_guard(answer, candidates) → 경고만, 차단 없음  │
│        ▼                                                             │
│  ui/pages/chat.py → render_citation_card(저자/출처/문서/위치/유형)   │
└──────────────────────────────────────────────────────────────────────┘

┌─ [B] Smith 참고자료 경로 — 라이브, 보조 ─────────────────────────────┐
│  chat.py::_inject_smith_context                                      │
│   → NAE/smith_activation.should_activate_smith(정규식 의도 분류)      │
│   → NAE/reference_retrieval_adapter.search_reference(top_k=3)        │
│   → bge-m3 임베딩 → Qdrant :7333 / nae_ref_v1 (34,948 pts, E9)       │
│   → <reference> 블록으로 프롬프트에 주입 (TSU 하위 위계 명시)          │
│   ※ 실패는 전부 [] 반환으로 격리됨 — TSU 경로 무영향                  │
└──────────────────────────────────────────────────────────────────────┘

┌─ [C] NAE 공개신학 TSU 경로 — 존재하나 차단됨 ────────────────────────┐
│  NAE/corpus/tsu/{Dagg,Hiscox,Fuller_Vol01}/tsu.json                   │
│   → Qdrant :7333 / nae_tsu_v1 (3,319 pts, review_status·page 보유 E19)│
│   → NAE/retrieval_adapter.bridge_query()                             │
│   → core/module_registry 게이트: modules.nae_pd.enabled=false (E18)   │
│   → 호출처는 ui/pages/research.py 1곳뿐. chat.py는 호출하지 않음      │
│   ⇒ 질의 시 NaePdModuleDisabledError — 실질 비활성                    │
└──────────────────────────────────────────────────────────────────────┘

┌─ [D] 구축됐으나 기본 OFF인 경로 ─────────────────────────────────────┐
│  output/bench/tantivy_index + core/candidate_generator               │
│   → core/hybrid_candidate_pipeline.HybridQueryProcessor              │
│   → USE_INVERTED_INDEX 환경변수 필요, 기본 false (E17)                │
│   ※ SearchTelemetry는 이 경로에만 연결 → 기본 경로에서 질의 기록 0건  │
│  Qdrant :6333 / dbma_chunks, dbma_sermon → 컨테이너 미기동 (E8)       │
│  ChromaDB → legacy 보존, 조회 경로 없음 (config.yaml 주석 명시)       │
└──────────────────────────────────────────────────────────────────────┘
```

**핵심 사실 3가지**

1. 라이브 질의는 **JSONL 1개 파일에 대한 in-memory 선형 스캔**이다. 벡터 DB는 코어 검색에 관여하지 않는다(E11). `config.yaml`의 `vector_db.primary: "qdrant"`는 **[B]/[C] 경로에만 해당하는 서술이며 코어 경로에는 거짓**이다.
2. 현재 실사용 코퍼스는 **문서 1개, 1,363청크**다(E4). 시스템은 "3개 문서"를 보고하지만(E3) 나머지 2개는 EXCLUDED 상태의 소형 테스트 픽스처다.
3. **출처·위치·검수·인용가능 메타데이터를 완비한 코퍼스(nae_tsu_v1, E19)와, 라이브 질의가 실제로 읽는 코퍼스(tsu_dataset.jsonl, E6)가 완전히 분리되어 있다.** 이것이 이번 감사의 단일 최대 발견이다.

---

## 2. Pipeline Health Matrix

| 단계 | 상태 | 판정 근거 |
|------|------|-----------|
| **RAW 수집 / 식별** | HEALTHY | identity_registry가 file_hash·supersedes·pipeline_flags·retry_count까지 관리. `delete_raw_source`/휴지통/복원 경로 존재. 테스트 통과(E1) |
| **추출 (extract)** | PARTIAL | 8개 포맷 지원·OCR 분기·실패 격리(`extraction_failures.json`)는 정상. 다만 서지 메타(title/author)는 PDF·DOCX만(E13). 라이브 문서인 EPUB는 원본에 메타가 있는데도 전량 유실(E12) |
| **정제 (clean)** | HEALTHY | noise_classifier·repetition_detector·text_normalizer 동작, frontmatter에 noise_score/mode 기록. 산출물 실물 확인 |
| **청킹 (chunk)** | PARTIAL | 1200/120 규칙 준수, validate_chunks 존재. 그러나 `quality.passed=false`인 문서가 그대로 INDEXED로 승격됨(E15) — 게이트가 **자문(advisory)**일 뿐 강제되지 않음 |
| **구조/위치 부여** | RISKY | heading provider가 md/txt/pdf만 등록(E14). EPUB는 ATX 폴백으로 떨어지고 추출 마크다운에 ATX가 없어 `heading_path`가 **1,363건 전부 공백**(E6). verse_mapping도 95%가 book_id만(E7) → **답변에 표시할 "위치"가 사실상 존재하지 않음** |
| **인덱스 (index)** | PARTIAL | tsu_manifest의 dataset_sha256 기반 스테일 감지가 정확히 동작(ui/state/query_processor.py). 그러나 결과물은 ANN 인덱스가 아니라 평문 JSONL이며, 검색은 전건 스캔 |
| **검색 (query)** | RISKY | 정확도 자체는 하이브리드 스코어링으로 방어되나 ① 관련성 하한선 없음(무관 질의도 top-k 반환 — `chat.py:_LOW_CONFIDENCE_SCORE_THRESHOLD` 주석에 재현 사례 기록됨) ② BM25 무히트 시 **무순위 슬라이스**로 후보 생성 ③ O(N) 선형 스캔이라 코퍼스 증가에 대해 선형 열화 (코드 주석에 53k 코퍼스에서 45~55초 실측 기록) |
| **생성 (answer)** | PARTIAL | top-k만 프롬프트에 주입 — 전체 코퍼스 투입 없음(금지사항 준수 확인). ClaimGuard가 절대주장 탐지. 다만 ClaimGuard는 **경고·문구제안까지만** 하고 답변을 차단하지 않으며, 실패해도 답변은 그대로 사용됨(generation.py:124) |
| **인용/출처 표시** | RISKY | 카드 필드 5종 중 저자·출처·본문위치가 라이브 문서에서 **전부 공백**(E6) → 실제 화면에는 파일명만 남음. `Citation`에 **검수 상태·인용 가능 여부 필드 자체가 없음**(E21, E22) |
| **참고자료(Smith) 주입** | PARTIAL | 장애 격리·타임아웃·위계 명시는 잘 설계됨. 그러나 OCR 품질이 낮은 텍스트가 답변 근거로 들어가고(E20), 해당 payload에 검수·저작권 필드가 없어 **인용 가능 여부를 판단할 수 없음** |
| **NAE 공개신학 코퍼스** | UNKNOWN | 3,319 pts가 green 상태로 존재하고 메타데이터도 완비(E19)이나, 모듈이 disabled라 **실사용 검색 품질을 측정한 적이 없음**. ADR-030 감사 종결 기록은 데이터 품질에 대한 것이지 검색 품질에 대한 것이 아님 |
| **평가 / 관측** | RISKY | 벤치마크 스크립트·골든셋 문서·regression 비교 함수는 존재. 그러나 **텔레메트리 DB가 아예 생성되지 않음**(E16) — 기본 경로에 record_query 호출부가 없어 실제 질의가 한 건도 기록되지 않음. Monitor 탭은 빈 DB를 읽음 |
| **테스트 / 회귀** | HEALTHY | 2,710 pass / 78초(E1). 232개 테스트 파일. CI 워크플로 존재. **이 프로젝트의 최대 자산** |
| **거버넌스 / ADR** | HEALTHY | ADR-001~033, Architecture Freeze Rule, Evidence Before Promotion Rule이 문서와 실제 코드 주석에 일관되게 반영됨 |
| **설정 정합성** | RISKY | `config.yaml`이 코어 경로 사실과 불일치: `vector_db.primary: qdrant`(코어는 미사용, 게다가 :6333 미기동), `embedding.model: all-MiniLM-L6-v2 / dim 384`(실제는 bge-m3 1024-dim). 주석으로 "legacy/폴백 전용"이라 방어했으나 최상위 키 값 자체는 오해를 유발 |

**요약: HEALTHY 4 / PARTIAL 6 / RISKY 5 / UNKNOWN 1**

---

## 3. 증거 기반 Gap Analysis

### G1. 출처·위치 메타데이터가 라이브 코퍼스에서 100% 결측 — **P0**
- 증거: E6, E7, E12, E13, E14
- 사실: TSU 스키마에는 `title/author/page/chapter/source_provenance/structure.heading_path` 자리가 모두 **정의되어 있다**. 값만 비어 있다. 원본 EPUB에는 title·creator·publisher·ISBN이 실제로 들어 있다(E12).
- 원인은 3개로 분리됨:
  - G1-a 추출기에 EPUB 서지 판독기가 없음 (`extractors.py`에 pdf/docx용 함수만)
  - G1-b heading provider registry에 epub 미등록 (`heading_provider.py:151-155`)
  - G1-c registry의 title/author가 null이면 tsu_builder가 그대로 null을 전파 (설계상 "지어내지 않음" 원칙 — 올바른 동작이며, 상류를 고쳐야 함)
- 영향: 인용 카드의 5개 필드 중 3개가 항상 공백 → 사용자가 답변 근거를 원문에서 확인할 수단이 파일명뿐.

### G2. 검수 상태 / 인용 가능 여부를 표현할 자료구조가 코어에 없음 — **P0**
- 증거: E19(NAE엔 있음) vs E21·E22(코어엔 없음)
- 사실: `nae_tsu_v1` payload에는 `review_status=verified`, `usage_permission=research`, `copyright_status=public_domain`, `access_control`, `tsu_access`, `citation_policy`가 전부 존재한다. 코어 `Citation` 데이터클래스에는 이 개념이 **하나도 없다**.
- 영향: "이 문장을 설교에 인용해도 되는가"라는 DBMA의 본질적 질문에 시스템이 **구조적으로 답할 수 없다**.

### G3. 메타데이터 모델 이중화 — **P1**
- 증거: E6 vs E19
- 사실: 코어 TSU 스키마(`tsu_id/verse_mapping/content_quality/structure`)와 NAE TSU 스키마(`work_id/edition_id/page/paragraph/sentence/review_status`)가 서로 다른 세계다. `nae_metadata` 브리지 필드가 tsu_builder에 존재하나(E: tsu_builder.py:470) `ingest_nae_source.py`로 넣은 문서에만 채워지고, 실사용 0건.
- 영향: 통합 검색(v3 EvidenceUnit 계획)의 전제조건이 미충족. 단, `core/evidence_unit.py`와 `core/evidence_adapters/`가 이미 존재하므로 **설계 자산은 있음**.

### G4. 검색 확장성이 코퍼스 크기에 선형 종속 — **P1**
- 증거: E11, E17, `core/retrieval.py:1500~1520` 주석의 실측 기록(53k TSU에서 45~55초)
- 사실: 대체 경로(tantivy 역인덱스 + HybridQueryProcessor)가 이미 구현·테스트되어 있으나 기본 OFF다. 벡터 ANN(Qdrant)은 참고자료 경로에서만 쓰인다.
- 영향: 현재 1,363건에서는 문제없음. 문서 30~50개 규모로 늘면 즉시 체감 장애.

### G5. 품질 게이트가 강제되지 않음 — **P1**
- 증거: E15
- 사실: `quality.passed=false`(avg_noise 16.6, max_noise 100.0, dup 0.21)인 문서가 `pipeline_state=INDEXED`로 승격되어 현재 유일한 검색 대상이 되어 있다.
- 영향: 저품질 청크(EPUB 판권 페이지, 역자 소개 등 — 실제 첫 청크가 출판사 광고문임)가 검색 후보에 그대로 포함.

### G6. 질의 관측 데이터 부재 — **P1**
- 증거: E16, E17
- 사실: `SearchTelemetry` 구현체는 완성도가 높다(성공률/zero-hit률/CTR/캐시히트율/지연). 그런데 기본 질의 경로에 `record_query` 호출부가 없다. `record_query_latency`는 Streamlit session_state에만 남고 세션 종료 시 소멸.
- 영향: 개선 전후 비교의 기준선(baseline)을 만들 수 없다. 루프 엔지니어링 원칙("결과를 보고 수정한다")의 전제가 깨져 있다.

### G7. Smith 참고자료의 신뢰 등급 미표시 — **P1**
- 증거: E20
- 사실: 답변 프롬프트에 들어가는 Smith 텍스트가 OCR 열화 상태이고(`"opon stones to be tat upon Mount Ebal"`), payload에 검수/저작권 필드가 없다. 프롬프트에는 "보조 자료"라는 위계 문구가 붙지만, **UI 인용 카드에는 Smith 출처가 렌더링되지 않는다**(chat.py는 Smith를 컨텍스트에만 주입).
- 영향: 사용자가 답변 안의 특정 문장이 어디서 왔는지 모른 채 OCR 오독을 사실로 받아들일 수 있음.

### G8. config.yaml과 실제 구현의 문서적 불일치 — **P2**
- 증거: E8, E11
- 사실: `vector_db.primary: "qdrant"` + `url: http://localhost:6333`인데 해당 인스턴스는 미기동이고 코어는 조회하지 않는다. `embedding.model/dimension`도 실제(bge-m3/1024)와 다르다.
- 영향: 코드 변경 위험은 없으나, 신규 작업자·에이전트가 잘못된 전제로 설계할 위험. (실제로 config.yaml 주석에 2026-09-03의 동일 유형 혼동 사례가 기록되어 있음.)

### G9. NAE 코퍼스 검색 품질 미측정 — **P2 / UNKNOWN**
- 증거: E18, E19
- 사실: 3,319 TSU가 admitted 상태로 인덱싱까지 끝났으나 검색 품질 평가 기록이 없다. 메모리상 ADR-028은 Draft, ADR-030은 데이터 품질 종결이지 검색 품질 종결이 아니다.
- 영향: 모듈을 켤지 판단할 근거가 없다. **켜기 전에 평가가 선행되어야 한다**(금지사항: "평가 없는 모델/벡터 DB 교체").

---

## 4. Risk Register

| ID | 리스크 | 확률 | 영향 | 노출 | 완화 (최소 변경) |
|----|--------|------|------|------|------------------|
| R1 | **인용 불가 자료의 무자각 인용** — 검수/저작권 상태를 표시할 수 없어 사용자가 저작권 보호 자료를 설교에 그대로 인용 | 높음 | 치명 | **최우선** | P0-2: Citation에 필드 추가 + 값 없으면 "확인 필요" 명시 표시 |
| R2 | **근거 추적 불가** — 답변 각주가 파일명뿐이라 원문 대조 실패 | 확정(현재 발생 중) | 높음 | **최우선** | P0-1: EPUB 서지 판독 + P0-3: 위치 폴백 표기 |
| R3 | **OCR 오독의 사실화** — Smith 열화 텍스트가 출처 표시 없이 답변에 반영 | 중간 | 높음 | 높음 | P1-4: Smith 근거를 인용 카드에 별도 등급으로 노출 |
| R4 | **저품질 청크 오염** — passed=false 문서가 검색 후보에 상주 | 확정(현재 발생 중) | 중간 | 중간 | P1-3: 게이트를 차단이 아닌 **경고 배지 + 대시보드 노출**로 (데이터 삭제 금지) |
| R5 | **코퍼스 확대 시 지연 급증** — O(N) 선형 스캔 | 높음(문서 증가 시) | 높음 | 중간 | P1-1: 기존 tantivy 경로 A/B 실측 후 판단 (교체 아님) |
| R6 | **개선 효과 측정 불가** — 텔레메트리 미기록으로 baseline 부재 | 확정(현재 발생 중) | 높음 | 높음 | P1-2: 기본 경로에 record_query 연결 (읽기 전용 관측) |
| R7 | **무관 질의에 그럴듯한 답변** — 관련성 하한선 부재 | 중간 | 중간 | 중간 | 현행 soft caption 유지. 라벨 데이터 확보 전 임계값 강화 금지(feedback_avoid_risky_uncertain_design) |
| R8 | **설정 오해로 인한 잘못된 설계** — config.yaml 불일치 | 중간 | 중간 | 낮음 | P2-1: 주석·키 정합화 (동작 무변경) |
| R9 | **NAE 모듈 성급한 활성화** — 평가 없이 3,319 TSU를 검색 경로에 투입 | 중간 | 높음 | 중간 | P2-2: 평가 선행. 모듈 플래그는 감사 범위에서 **건드리지 않음** |
| R10 | **동시 편집 충돌** — C1과 동일 UI 파일 동시 수정 | 중간 | 중간 | 낮음 | 착수 전 `git diff` / `origin/dev/dbma-engine` 최신성 확인 (기존 확립된 규칙) |

---

## 5. 반드시 보존할 현재 자산 (Do-Not-Break List)

| 자산 | 위치 | 보존 이유 |
|------|------|-----------|
| **테스트 스위트 2,710건 / 78초** | `tests/` (232 파일) | 이 프로젝트의 신뢰 기반. 모든 보강은 이 스위트가 green을 유지하는 조건에서만 |
| **RetrievalEngine 단일 권위** | `core/retrieval.py` | ADR-001. 우회 경로 신설 금지 |
| **TSU additive-only 계약** | `core/tsu_builder.py` | 기존 필드 불변·신규 필드는 None 기본. 이 계약 덕분에 P0 보강이 **회귀 없이** 가능 |
| **Identity Registry** | `data/제련완성본/registry/documents.json` | file_hash / supersedes / pipeline_flags. 재처리 없이 상태 복원 가능한 유일한 근거 |
| **NAE 정본 코퍼스** | `NAE/corpus/tsu/` + `nae_tsu_v1` (3,319 pts) | ADR-030 FROZEN BASELINE. **재처리 금지**(HQ FINAL=ACCEPTED) |
| **nae_ref_v1 Smith 인덱스** | Qdrant :7333 (34,948 pts) | SPRINT34-SMITH-PHASEB 산출물. 재인덱싱 비용 큼 |
| **장애 격리 설계** | `reference_retrieval_adapter`, `_run_claim_guard` | 보조 경로 실패가 코어를 죽이지 않는 구조. 보강 시 이 패턴을 따를 것 |
| **dataset_sha256 스테일 감지** | `ui/state/query_processor.py` | SPRINT21-G Gap#1 수정분. 재발 방지 자산 |
| **ADR 체계 + Freeze Rule** | `docs/architecture/ADR-001~033` | 거버넌스 근간 |
| **원본 RAW 및 제련완성본 산출물** | `data/RAW`, `data/제련완성본` | 삭제·재처리 금지 (금지사항 명시) |
| **module_registry 게이트** | `core/module_registry.py` | nae_pd 격리 경계. 감사 중 상태 변경 없음 |

---

## 6. P0 / P1 / P2 최소 보강 계획

원칙: **전면 리팩터링 없음 · 데이터 삭제 없음 · 전체 코퍼스 재처리 없음 · 평가 없는 교체 없음.** 모든 항목은 additive-only 계약을 따르고, 값이 없으면 기존과 동일하게 동작한다(no-op).

### P0 — 근거 표시의 최소 성립 조건 (Sprint 1 범위)

| ID | 항목 | 변경 범위 | 성격 |
|----|------|-----------|------|
| P0-1 | `_extract_epub_title_author()` 추가 — ebooklib DC metadata(title/creator/publisher/ISBN) 판독 | `core/extractors.py` 1함수 + `extract_text_auto`의 epub 분기 2줄 | 추가. 실패 시 (None, None) — 기존 동작과 동일 |
| P0-2 | `Citation`에 `review_status` / `usage_permission` / `copyright_status` 3필드 추가 (기본 None), `CitationBuilder`가 TSU 메타에서 있으면 채움 | `core/retrieval.py` 데이터클래스 3줄 + 빌더 3줄 | 추가. 기존 필드 불변 |
| P0-3 | 인용 카드에 `검수 상태` / `인용 가능` 행 추가 + 값 부재 시 `확인 필요` 배지 | `ui/components/citation_card.py`, `ui/pages/chat.py` 호출부 | 추가. 기존 5행 렌더링 불변 |
| P0-4 | 위치 표기 폴백 체인: `heading_path → verse_mapping(chapter:verse) → page → 청크 순번(N/M)` | `ui/pages/chat.py` `text_location` 계산부 1곳 | 순수 표시 로직. 검색·스코어링 무영향 |

> P0-1은 **신규 처리 문서에만** 적용된다. 기존 매튜 풀 문서에 반영하려면 그 1개 문서만 `reindex_document()`로 재색인한다 — 전체 코퍼스 재처리가 아니다.

### P1 — 관측과 신뢰 등급

| ID | 항목 | 변경 범위 |
|----|------|-----------|
| P1-1 | tantivy/Hybrid 경로 A/B 실측(동일 질의 20건, 지연·top-5 일치율) 후 기본값 판단 | 스크립트만. `USE_INVERTED_INDEX` 기본값은 실측 후 별도 결정 |
| P1-2 | 기본 질의 경로에 `SearchTelemetry.record_query` 연결 — baseline 확보 | `ui/pages/chat.py`/`research.py` 각 1줄, try/except 격리 |
| P1-3 | `quality.passed=false` 문서를 Monitor/Library에 **경고 배지**로 노출 (차단·삭제 아님) | `ui/pages/monitor.py` 읽기 전용 추가 |
| P1-4 | Smith 근거를 인용 카드에 `참고자료(미검수·OCR)` 등급으로 별도 노출 | `ui/pages/chat.py` `_inject_smith_context` 반환값 활용 |
| P1-5 | EPUB heading provider 등록 (`EpubHeadingProvider`, spine/nav 기반) | `core/heading_provider.py` — PDF 어댑터와 동일 패턴 |

### P2 — 정합성과 장기 정리

| ID | 항목 |
|----|------|
| P2-1 | `config.yaml` 주석·키 정합화 (`vector_db.primary`의 적용 범위 명시, `embedding` 섹션을 legacy로 명확화). **동작 무변경** |
| P2-2 | NAE `nae_tsu_v1` 검색 품질 평가셋 설계 (활성화는 평가 결과 확인 후 별건) |
| P2-3 | `core/evidence_unit.py` 기반 코어/NAE 메타데이터 크로스워크 설계 문서화 (ADR 초안) |
| P2-4 | Qdrant :6333 dbma 인스턴스의 운영 방침 결정 (기동/폐기 — 현재 미기동 상태로 코드가 이를 참조하지 않음) |

---

## 7. Sprint 1 Backlog

> **Sprint 1 범위(사용자 지정, 확대 금지)**: 핵심 문서 3개에 대해 출처·위치·검수 상태·인용 가능 여부를 검색 결과와 답변 근거에 표시할 수 있는지 **검증**하고, **최소 보강안을 설계**한다.

### 대상 문서 3개 선정 근거

세 문서는 각각 **서로 다른 메타데이터 체제**를 대표하도록 골랐다. 하나씩 다 다르므로 3개로 전체 스펙트럼을 덮는다.

| # | 문서 | 경로 | 대표하는 체제 |
|---|------|------|---------------|
| D1 | 매튜 풀 청교도 성경주석 14 마태복음 (EPUB) | `data/RAW/` → `tsu_dataset.jsonl` (1,363 TSU) | **코어 라이브 경로**. 메타데이터 전량 결측 — 최악 케이스 |
| D2 | Hiscox, *The Standard Manual for Baptist Churches* | `NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json` (740 TSU) + `nae_tsu_v1` | **NAE 완비 경로**. page/paragraph/sentence/review_status/usage_permission 전부 보유 — 최선 케이스 |
| D3 | Smith's Bible Dictionary Vol.2 | `nae_ref_v1` (34,948 pts 중) | **참고자료 경로**. 위치(page_start/end)는 있으나 검수·저작권 없음 — 중간 케이스 |

### 티켓

| ID | 제목 | 산출물 | 완료 정의 |
|----|------|--------|-----------|
| **S1-01** | D1/D2/D3 4필드 실측 매트릭스 작성 | `docs/audit/SPRINT1-FIELD-MATRIX.md` | 문서×{출처,위치,검수,인용가능} 12칸이 `있음/없음/부분` + 각 칸의 **실제 값 또는 결측 증거**로 채워짐 |
| **S1-02** | 현행 UI 렌더링 실측 | 스크린샷 + 필드별 렌더 결과표 | D1 질의 1건을 Streamlit에서 실행해 인용 카드에 **실제로 무엇이 표시되는지** 기록. 코드 추정이 아닌 화면 근거 |
| **S1-03** | 4필드 표시 계약(Display Contract) 초안 | `docs/audit/SPRINT1-DISPLAY-CONTRACT.md` | 각 필드의 ① 데이터 출처 경로 ② 폴백 체인 ③ 값 부재 시 표기(`확인 필요`) ④ 절대 추측하지 않는다는 규칙을 명문화 |
| **S1-04** | P0-1 EPUB 서지 판독 설계 | 설계 섹션 + 함수 시그니처 | ebooklib DC 필드 → registry 필드 매핑표. **구현은 Sprint 2** |
| **S1-05** | P0-2 Citation 3필드 확장 설계 | 설계 섹션 + diff 스케치 | additive-only 확인, 기존 테스트 영향 분석(예상 0건) 포함 |
| **S1-06** | P0-4 위치 폴백 체인 설계 | 설계 섹션 | D1(청크순번)/D2(page·paragraph)/D3(page_start-end) 각각에 대해 폴백이 어느 단계에서 멈추는지 명시 |
| **S1-07** | Acceptance Test 초안 작성 (§8) | `tests/` 신규 파일 **초안만**, 미실행 | 아래 AT-1~AT-6이 테스트 함수 시그니처 수준으로 작성됨 |
| **S1-08** | Sprint 1 결과 보고 + Sprint 2 착수 판단 | `docs/audit/SPRINT1-REPORT.md` | 진행률·검증 결과·다음 조치 (CLAUDE.md 루프 엔지니어링 형식) |

### Sprint 1에서 **하지 않는 것**
- 코드 구현 (S1-04~06은 설계까지)
- `modules.nae_pd.enabled` 변경
- `USE_INVERTED_INDEX` 기본값 변경
- 코퍼스 재처리·재색인 (D1 재색인도 Sprint 2)
- Smith 인덱스 재구축

### 진행률 추적

```md
- [ ] S1-01 4필드 실측 매트릭스
- [ ] S1-02 현행 UI 렌더링 실측
- [ ] S1-03 표시 계약 초안
- [ ] S1-04 EPUB 서지 판독 설계
- [ ] S1-05 Citation 확장 설계
- [ ] S1-06 위치 폴백 체인 설계
- [ ] S1-07 Acceptance Test 초안
- [ ] S1-08 결과 보고
진행률: 0% (감사 완료 = Sprint 0 종료)
```

---

## 8. Acceptance Tests & Rollback Plan

### 8.1 Sprint 1 Acceptance Tests (설계 완료 판정)

Sprint 1은 설계 스프린트이므로 AT-1~AT-3은 **문서 검증**, AT-4~AT-6은 **Sprint 2 착수 조건인 테스트 초안**이다.

| ID | 대상 | 판정 기준 |
|----|------|-----------|
| **AT-1** | 매트릭스 완전성 | D1/D2/D3 × 4필드 = 12칸 전부가 실측 값 또는 결측 증거로 채워짐. "추정" 표기 0건 |
| **AT-2** | 폴백 체인 결정성 | 표시 계약의 폴백 체인이 D1/D2/D3 각각에 대해 **단일 결과**로 수렴함이 문서상 추적됨 |
| **AT-3** | 결측 정직성 | 값이 없는 필드에 대해 계약이 `확인 필요`를 반환하며, **어떤 경로에서도 값을 추측·생성하지 않음**이 명문화됨 |
| **AT-4** | (초안) 서지 판독 | `test_extract_epub_title_author_reads_dc_metadata` — D1 EPUB에서 title=`매튜 풀 청교도 성경주석 14 : 마태복음`, author=`매튜 풀` 반환 |
| **AT-5** | (초안) Citation 확장 무회귀 | `test_citation_new_fields_default_none` — 기존 TSU(3필드 부재)에서 Citation 생성 시 3필드가 None이고 나머지 필드는 **변경 전과 바이트 동일** |
| **AT-6** | (초안) 표시 폴백 | `test_text_location_fallback_chain` — heading_path 없음 + verse chapter 없음 + page 없음 → `청크 1/1363` 반환 |

### 8.2 회귀 게이트 (Sprint 2 이후 모든 변경에 적용)

```bash
~/envs/dbma311/bin/python -m pytest tests/ -q
```
- **기준선: 2710 passed, 15 skipped (2026-09-09 실측)**
- 통과 수가 2710 미만이거나 신규 fail이 1건이라도 있으면 **머지 금지**
- 신규 테스트 추가로 총계가 늘어나는 것은 정상

추가 게이트:
- `tsu_manifest.json`의 `dataset_sha256`이 의도치 않게 바뀌지 않았을 것 (재색인을 수반하지 않는 변경의 경우)
- `data/RAW`, `data/제련완성본`, `NAE/corpus/` 파일 수·크기 불변

### 8.3 Rollback Plan

Sprint 1은 문서만 생성하므로 **런타임 롤백 대상이 없다**. Sprint 2 이후를 위한 절차를 미리 고정한다.

| 계층 | 롤백 방법 | 소요 | 데이터 손실 |
|------|-----------|------|-------------|
| **L0 — 문서** | 해당 md 파일 revert | 즉시 | 없음 |
| **L1 — 코드** | 기능별 단일 커밋 원칙 → `git revert <sha>` | 분 단위 | 없음 |
| **L2 — UI 표시** | P0-3/P0-4는 표시 전용. revert 시 즉시 현행 카드로 복귀 | 즉시 | 없음 |
| **L3 — Citation 스키마** | additive-only이므로 revert 시 필드만 사라짐. TSU 데이터·인덱스 무영향 | 분 단위 | 없음 |
| **L4 — D1 재색인** | 사전에 `output/bench/tsu_dataset.jsonl` + `tsu_manifest.json`을 `workspace/snapshots/`에 타임스탬프 복사. 문제 시 파일 복원 후 앱 재시작(dataset_sha256 변경이 자동 감지되어 엔진 재생성) | 분 단위 | **없음 — RAW·제련완성본 원본 불변** |
| **L5 — 벡터 인덱스** | Sprint 1~2 범위에서 **변경 없음**. nae_ref_v1 / nae_tsu_v1 무접촉 | — | 없음 |

**롤백 트리거**
1. 회귀 스위트가 2710 pass 미만
2. 인용 카드에 **없는 값이 표시됨** (추측 발생 — 즉시 중단 사유)
3. 질의 지연이 기준선 대비 2배 초과
4. `documents.json` / `tsu_dataset.jsonl` 레코드 수가 의도와 다르게 변동

**스냅샷 선행 규칙**: L4 이상을 건드리는 작업은 착수 전 스냅샷 복사를 **먼저** 수행하고, 그 경로를 작업 보고서에 기록한다.

---

## 부록 A. 감사 중 확인된 "제안서와 현실의 차이" (참고)

| 흔한 가정 | 실제 |
|-----------|------|
| "Qdrant 기반 벡터 검색이 동작 중" | 코어 검색은 Qdrant를 **조회하지 않음**. Qdrant는 NAE 참고자료 경로 전용 |
| "임베딩은 all-MiniLM-L6-v2(384d)" | 실제는 bge-m3(1024d). config의 embedding 섹션은 legacy |
| "3개 문서가 인덱싱됨" | 실제 검색 가능 문서는 **1개** (나머지 2개는 EXCLUDED 픽스처) |
| "출처와 위치가 표시됨" | 표시 **컴포넌트는 있으나 데이터가 100% 결측** |
| "NAE 코퍼스가 검색에 통합됨" | `nae_pd` 모듈 **disabled**. Smith 참고자료만 라이브 |
| "품질 게이트가 저품질 문서를 막음" | `passed=false`도 **INDEXED로 승격됨** |
| "검색 품질이 모니터링됨" | 텔레메트리 DB가 **생성조차 되지 않음** |
| "Obsidian 연동" | 코드베이스에 **의존성 없음** — 핵심 의존성으로 가정하지 않아도 됨 (금지사항 자동 준수) |

## 부록 B. 재현 명령

```bash
# 회귀 기준선
~/envs/dbma311/bin/python -m pytest tests/ -q

# 라이브 코퍼스 메타데이터 결측 재현
python3 - <<'PY'
import json, collections
c = collections.Counter(); n = prov = page = head = 0
for line in open('output/bench/tsu_dataset.jsonl'):
    if not line.strip(): continue
    d = json.loads(line); n += 1
    if d.get('source_provenance'): prov += 1
    if d.get('page') is not None: page += 1
    if (d.get('structure') or {}).get('heading_path'): head += 1
    c[d.get('source_file')] += 1
print(f"total={n} provenance={prov} page={page} heading={head} sources={len(c)}")
PY

# 서비스 상태
curl -s http://localhost:6333/collections   # 미기동 예상
curl -s http://localhost:7333/collections   # nae_ref_v1 / nae_tsu_v1

# Qdrant 미사용 확인
grep -n 'qdrant' core/retrieval.py
```
