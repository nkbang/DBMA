# DBMA State

## 버전 상태
**DBMA v1.3.0 — Architecture Consolidation Release** (Research Grade /
Production Candidate). 버전·Authority 정의는
`docs/architecture/DBMA-Version-Authority-v1.md`가 단일 기준이다.

```
Release State:  v1.3.0 RC READY
Development:    FROZEN
Next:           GA validation / tag preparation
```

## 현재 상태
DBMA는 신학 문서 전용 TSU 기반 Theological Retrieval System이다.
SPRINT17~19에서 Retrieval/Evidence/Citation 계층이 구조적으로 완성되었고,
SPRINT20에서 그 위에 Metadata Lineage, Configuration/Environment/Logging
Authority, Application Entry Point 정합성을 확보했다.
SPRINT20-I(Architecture Consolidation)에서 Processing/Identity/Index/TSU
Builder/Retrieval/Embedding Authority를 확정하고 TSU Builder를 core로
이동했으며, Legacy(`dbma.py` + Chroma/Qdrant island + md_manager)를
`archive/legacy/`로 분리 완료했다. v1.3.0으로 태그·검증되었다.

**[2026-07-22 갱신] 이 문서는 SPRINT27-D 이후 장기간 갱신이 밀려 실제
코드 상태와 어긋나 있었다 — 실제로는 SPRINT33-D까지 진행되었다.**
아래 "SPRINT28~33-D 진행 내역"과 "SPRINT 외 병행 작업"을 반드시 함께
읽을 것.

**[2026-07-30 갱신] SPRINT33-D 이후 이 문서가 다시 갱신되지 않은 채
DBMA-SEARCH-INFRA-001(Logos식 Hybrid Retrieval 인프라, Phase 0~2)이
진행·완료되었다 — 아래 "DBMA-SEARCH-INFRA-001 진행 내역" 섹션을 반드시
함께 읽을 것. SPRINT 번호 체계 밖의 별도 프로젝트 트랙이다.**

**[2026-07-31 갱신] DBMA-UX-001~003 트랙(Stitch 프로토타입 → 브랜드/UI
정정 → Sample Library) 완료. `docs/DBMA-UX-001-EXECUTION-PLAN.md`(진행률
100%), `docs/DBMA-UX-002-IMPLEMENTATION-PLAN.md`,
`docs/DBMA-UX-003-SAMPLE-LIBRARY-PLAN.md` 참고. 라이브 `ui/` 코드의 기술
용어 노출(RAG/벡터DB/임베딩/청킹 등) 9건을 발견·수정했고, Library에
"기본 자료(읽기 전용)" Sample Library를 실제 파이프라인으로 구현했다
(`core/config.py::DEFAULT_SAMPLE_LIBRARY_PATH`,
`scripts/seed_sample_library.py`). Core 스키마(`identity_registry.py`)는
변경하지 않았다 — side-file 방식. "보기"/"복사하여 내 자료로" 두 버튼
모두 실 브라우저 클릭으로 최종 검증함(문서 수 112→113 증가 확인, 이후
테스트 산출물 정리). C1 Task Order 035 Architecture Review: GO with
caveats.**

**[2026-07-31 갱신 #2] DBMA-UX-004(P1 화면 점검) 완료,
`docs/DBMA-UX-004-P1-SCREENS-PLAN.md` 참고. 연구하기(`research.py`)
화면을 실 데이터로 브라우저 검색까지 돌려보고서야 발견된 위반 다수
수정 — `RRF {score}`/`Hybrid·BM25·Vector·RRF` 알고리즘 노출(관리자
게이트 처리), `TSU` 라벨, `ROM` 등 원시 성경책 코드, `EXEGESIS` 등
영어 intent enum, "쿼리" 차용어 전반. **1차 grep 감사(리터럴 문자열만
검색)로는 f-string 동적 조합 문자열을 못 잡는다는 것이 이번 교훈** —
향후 UX 감사는 grep 이후 반드시 실 데이터로 브라우저 검증 필요.
"자료 읽기"(문서 본문 전체를 읽는 화면) 자체가 라이브 앱에 없다는
진짜 기능 공백도 발견 — `docs/DBMA-UX-005-DOCUMENT-READING-PLAN.md`로
분리 발행, 착수 전 HQ 결정(옵션 A/B) 대기 중.**

**[2026-07-31 갱신 #3] HQ 지시로 DBMA-UX-006(독립 재감사) →
DBMA-UX-007(Implementation Specification) 발행. Gate 체계 도입:
Gate 1~5(Audit/Product Identity/IA/Visual Direction/Architecture Safety)
PASS, **Gate 6(Implementation Specification) PASS**(`docs/DBMA-UX-007-IMPLEMENTATION-SPEC.md`),
**HQ 승인 대기 → C1 Implementation BLOCKED**. 읽기 화면은 "document
viewer"가 아니라 "research workspace"로 확정(본문+연구+행동 3영역).
"기술적 leakage 금지"를 UX invariant로 명문화 — `chat.py`의
`신뢰도(final_score)`/`근거 신뢰도(citation)` 원시 노출이 미해결 위반으로
공식 기록됨, §11 용어집으로 향후 위반 판정 기준 고정. mockup.html은
"시각 참조"로만 쓰고 구현 권한은 스펙 문서에 있음을 명시.**

**[2026-07-31 갱신 #4] HQ가 DBMA-UX-007 승인. §12 CUE/C1 경계 원칙에
따라 구현을 한 번에 넘기지 않고 스펙 §15 순서대로 단계 발급 시작 —
[C1 Task Order 039](agents/c1/C1-TASK-ORDER-039.md)(Phase 1: 기술적
leakage 제거 + 인용·출처 공용 컴포넌트) 발급. `chat.py`의
`신뢰도(final_score)`/`근거 신뢰도(citation)` 원시 노출이 이번 Phase의
1순위 수정 대상. Phase 2(홈 화면)는 Phase 1 완료·CUE 검토 후 발급 예정.**

---

## 아키텍처 결정 (ADR)

- `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` (accepted):
  `core/retrieval.py::RetrievalEngine`/`QueryProcessor`가 유일한 Retrieval
  Engine Authority. `dbma.py`의 인라인 RAG(`query_rag` 등)는 폐기 대상.
- 공식 실행 진입점: `dbma_ui.py` → `ui/app.py` (SPRINT20-G2에서 README/
  `.github/instructions/*` 문서 정렬 완료).
- `docs/architecture/ADR-006-Heading-Provider-Registry.md` (accepted):
  헤딩 감지를 소스 타입별 Provider로 분리(`core/heading_provider.py`).
- `docs/architecture/ADR-007-Semantic-Boundary-Detector.md` +
  Amendment A (accepted): Boundary Score 모델과 D5(recovery/semantic/
  outlier) 3축 품질 지표, Hierarchical Chunk Builder 설계 근거.
- `docs/architecture/ADR-008-Semantic-Chunking-Production-Path.md`
  (accepted, 프로덕션 전환 경로는 미실행): 현재 `chunking_optimizer.py`
  대신 Hierarchical Chunk Builder로 전환하는 조건과 절차.
- `docs/architecture/ADR-009-SIL-Theology-Engine.md` (**완료**, commit
  `0324dca`, 2026-07-22 — 이전 "구조만 확정" 기재는 stale, 이후 갱신
  누락돼 있었음): 사용자가 신학 전통(개혁파 침례교, 1689 런던신앙고백
  계열)과 `doctrine_category`(7개)/`baptist_theme`(10개) 최종 어휘를
  직접 확정. `core/sermon/doctrine_vocabulary.py`(승인 어휘 상수),
  `core/sermon/doctrine_filter.py`(`check()` — 사후 실행, 생성 차단
  없음, 점수화 금지, 저신뢰도는 "(확실하지 않음)" 노출, 승인 어휘 밖
  범주는 필터링, Ollama 실패해도 raise 안 함)로 구현되고
  `ui/pages/sermon_draft.py`에 개요 생성 직후 자동 실행·경고 배너로
  연결됨. 테스트 10건 신규(`tests/test_doctrine_filter.py`), 당시
  회귀 612 passed.
- `docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md`
  (구조 확정 — 미확정 항목 2건 중 1건 해결(2026-07-29, 골든셋 3→7건
  확대), 나머지 1건(`question_answering_quality` reference-free
  재정의)은 **David 결정으로 Phase 4 착수 시점까지 명시적 보류**,
  2026-07-29): LLM-as-judge pointwise 평가 인프라(`core/evaluation/`).
- `docs/architecture/ADR-011-Header-Footer-Repetition-Detector.md`
  (완료/보류 확정, 2026-07-23): 한글 PDF 주석서(Profile B)의 반복
  러닝헤더 문제 — `RepetitionTracker`(`core/repetition_detector.py`)
  구현 + 단위테스트 6건 통과, `noise_classifier.py`/
  `semantic_boundary_detector.py` 연결 후 Beta corpus 실측까지 완료.
  결과: 효과 0(delta=0) 확인 — 이 corpus엔 candidate 스트림에 살아남는
  running header가 없어 프로덕션 반영은 보류(추가 조치 불필요, 코드는
  향후 재평가용으로 유지). 상세: 문서 본문 Next Steps(160~208행) 참고.

---

## SPRINT28~33-D 진행 내역 (2026-07-22, 뒤늦게 기록)

STATE.md가 SPRINT27-D에서 멈춰 있는 동안 실제로는 아래까지 진행되어
있었다 — 전부 완료 상태이며, 코드 변경은 각 스프린트 주석([SPRINT28-B]
등)과 `docs/SPRINT33-*.md`에서 확인 가능하다.

- **SPRINT28** — 청크 단위 noise 분류기, front-matter 감지 버그 수정,
  PDF PAGE_BREAK_MARKER 보존, RetrievalEngine TF-IDF fallback 지연 빌드.
- **SPRINT29** — 청킹 파라미터를 `core/config.py` 단일 소스로 정리(SSOT),
  경계 기반 chunk overlap 적용, 헤딩 골격(`heading_extractor.py`, "honest
  empty" 원칙).
- **SPRINT30** — 적응형 PDF 헤딩 감지기(`core/pdf_structure_detector.py`)
  실측·설계·구현.
- **SPRINT31** — Heading Provider Registry 아키텍처 확정(ADR-006),
  HeadingAssembler 커서 매칭(정확 일치 → bounded-lookahead 복구),
  PDF span geometry 수집/연결, 과도기 어댑터 제거.
- **SPRINT32** — PdfHeadingProvider를 `tsu_builder.py`에 실제 연결(PDF
  한정, ADR-006 Option 1), HeadingAssembler word-boundary 매칭 버그 수정.
- **SPRINT33-A** — SPRINT31~32 경계/청킹 파이프라인 감사(코드 변경 없음).
- **SPRINT33-B** — `core/semantic_boundary_detector.py`(Boundary Score
  모델, dormant/shadow) 설계·구현. ADR-007.
- **SPRINT33-C** — Boundary Score 모델 shadow 검증·보정(휴리스틱 피처
  4종 추가: Paragraph/TinyFragmentPenalty/SentenceBoundaryConfidence/
  ScriptureReferenceBoundary, 가중치 보정, shadow-vs-production delta 측정).
- **SPRINT33-D** — Hierarchical Chunk Builder 프로토타입
  (`core/hierarchical_chunk_builder.py`, ADR-007 Amendment A) 구현 및
  D5 3축 정식 평가 완료. ADR-008의 제안 2(Level 3 Hard Fallback,
  2026-07-22 완료)/3(임베딩 6번째 feature)/4(버그 수정)까지 모두
  완료(commit `08d542a`). **상태: 프로토타입 완결 — 프로덕션(`chunking_
  optimizer.py`) 전환은 데이터 갖춰졌으나 HQ 결정 대기로 보류(2026-07-22).**
  - 이 과정에서 `split_sentences_mixed()`의 줄바꿈 의존 버그를 발견 →
    `docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`로 분리 추적.
    하위 결함 B는 `_merge_sentence_fragments()` word-safe hard slice로
    수정 완료(over-cap 비율 4.6%→0.5%, commit `c513bad`). **근본 수정
    (a)도 완료됨**(`_split_line_on_sentence_end()` 신설로 문장부호 기준
    분할 추가, commit `d45caed`, 2026-07-21 — 애초 제안한 "`split_
    sentences()`로 위임" 방식은 아니었지만 동일 목적 달성. 잔여
    over-cap은 0.2%(40건)로, 이는 Axis 3 unsplittable outlier — 별개
    문제로 Hierarchical Chunk Builder 쪽에서 계속 추적). **[2026-07-22
    정정] 이 항목은 한때 "미착수"로 잘못 기재됐었다 — Preflight 문서의
    갱신 지연분을 그대로 옮겨적은 것이 원인, git 로그 재대조로 확인.**

---

## SPRINT 외 병행 작업 (2026-07-21~22)

번호가 매겨진 스프린트 트랙과 별개로, 별도 설계 문서
(`docs/LOCAL_MODEL_SERMON_ALGORITHM_DESIGN.md`) 하에 진행된 작업.
commit `08e5704`/`8f40ea0`/`3dde0fd`/`21f80a1` (dev/dbma-engine push 완료).

- 설교문 생성 파이프라인: Logos Print/Export 자료 인제스트 스크립트
  (`scripts/ingest_logos_export.py`), TSU `source_provenance` additive
  필드, 하이브리드 검색에 PassageMatch·SourceTierBonus 항목 추가
  (`core/retrieval.py`).
- 한국어 출력 순도: 로컬 생성 모델(`my-theology-bot:latest`,
  llama3.3:70b Q4_K_M)에서 실측된 CJK 이웃 언어/태국어 혼입 현상 —
  temperature와 무관하게 재현되는 모델 자체 결함으로 확인, 재시도 2회
  + 최종 sanitize 백스톱으로 대응(`core/generation.py`).
- 대시보드: "정리된 자료"/"유형별 문서" 카운트 불일치(74 vs 124) 수정 —
  `_get_effective_documents()`로 두 카드가 같은 모집단(chunk_count>0·
  ingest_status=PROCESSED·superseded_by 없음)을 공유하도록 통일, registry의
  superseded 이력 48건 정리, 유형별 수량사(권/건) 적용.
- Streamlit dev server가 harness 할당 포트로 바인딩되지 않던 문제 수정
  (`.claude/launch.json`, autoPort).

**다음 조치**: 없음(각 항목 실측 검증 완료) — Logos 인제스트는 실제
Logos 자료·manifest 준비가 있어야 다음 단계로 진행 가능.

---

## 프로젝트 진행률

전체 진행률(SPRINT20-I Architecture Consolidation 기준): 100% —
단, 이는 v1.3.0 태그 시점 스코프일 뿐이며 이후 SPRINT28~33-D(청킹
품질 고도화, 위 §SPRINT28~33-D 참고)가 별도로 진행 중/완료되었다.
"100%"는 v1.3.0 스코프 완료를 뜻하지 프로젝트 전체 종료를 뜻하지 않는다.

### 세부 진행 (SPRINT20-I 완료, v1.3.0 스코프)
- Retrieval Engine 단일화 (ADR-001): 100%
- Citation Layer / Metadata Propagation: 100%
- Configuration / Execution Env / Logging Authority: 100%
- Index/TSU Builder Authority (core/index_orchestrator.py, core/tsu_builder.py): 100%
- Registry Path Authority (DEFAULT_REGISTRY_PATH): 100%
- Legacy Archive (dbma.py + search/ingest/qdrant_init + md_manager → archive/legacy): 100%
- Retrieval Document Diversity (RETRIEVAL_DOCUMENT_CAP): 100%
- Legacy Vector Store 정책 (ADR-003 Finalization): 100%
- Release: v1.3.0 태그 + chapter-level benchmark PASS + beta validation: 100%

---

## v1.3.0 릴리스 상태

```
Version:   v1.3.0 (tag 07ec084) + post-release stabilization (SPRINT28~33-D 반영)
HEAD:      afbb1be (origin/dev/dbma-engine 동기화, 2026-07-29 — Task Order
           016(Hierarchical Chunk Builder Axis 2, Option A/B/C-1 전부
           실측 기각·종료)·골든셋 gold-4~7 확장·Task Order 017
           (DocumentContext Registry Schema Parity 구현)·Task Order 018
           (doc_type을 core/processing.py PROCESS/SKIP 경로에 실제 배선)·
           Task Order 019(기존 등록 문서 doc_type 백필 스크립트)·
           STATE.md/ADR-009/ADR-010 stale 항목 정정·ADR-010 잔여
           결정 항목 Phase 4까지 보류 확정, 전부 push 완료)
Tests:     1,151개 수집 확인(tests/ 스코프, 2026-07-30 재확인 — 이전 기재
           "852개"/"1,114개"는 같은 날 세션 중간 시점 값으로 이미 stale,
           DBMA-SEARCH-INFRA-001 Phase 2 + Query Planner에서 추가된 테스트
           반영 안 돼 있었음). 전체 1,151개 일괄 실행은 비용 커서 보류 —
           DBMA-SEARCH-INFRA-001 관련 범위(candidate_generator/bible_index/
           hybrid_candidate_pipeline/query_planner/index_orchestrator/
           retrieval 일부)는 이번 세션에서 개별 확인 시마다 통과 확인됨
           (111개). output/SPRINT5_ENGINEERING_VALIDATION/
           stress_test.py에서 무관한 collection error 1건 있음(사전부터
           존재, 이번 세션 원인 아님, 미조사). 전체 스위트 공식 재실행은
           GA 검토 전 별도로 권장.
Runtime:   APP_VERSION 1.3.0 / embed bge-m3:latest / gen my-theology-bot:latest
           (llama3.3:70b Q4_K_M) / cap 2
Status:    STABLE — GA 검토 단계 (변동 없음)
```

완료된 post-release 안정화:
- UI 수정: st.rerun 콜백, 임베딩 % 표시, 마지막 처리, 버전/임베딩 라벨 authority화
- Ollama HTTP 500: char/token 4→2 (다국어 oversized 차단)
- Orphan cleanup: data/rag_index, 빈 backup 폴더, md_manager archive
- Benchmark evidence: output/bench/chapter_level_result_v1.3.0_cap2.json

## DBMA-SEARCH-INFRA-001 진행 내역 (2026-07-30)

HQ 작업지시서("Logos식 초고속 하이브리드 검색 엔진 도입") 기반, `docs/architecture/`
아래 계획 문서 3건 참고:
- `DBMA-SEARCH-INFRA-001-PHASE0-BASELINE.md` — 현황 진단
- `DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md` — Phase 2 착수 계획 (진행률 100%)
- `C1-TASK-ORDER-033-REPORT.md`(`docs/agents/c1/`) — 엔진 벤치마크 v5(CUE 직접 실행·검증)

**Phase 0 (현황 진단)**: 기존 `RetrievalEngine.retrieve()`가 metadata filter 실패 시
BM25가 역색인 없이 전체 코퍼스(53,231 TSU)를 스캔 → 7~8초. Qdrant는 실제로
연결된 적이 없었음(파라미터만 받고 미사용, 전량 인메모리 BM25/TF-IDF)도 확인.

**Phase 1 (긴급 패치)**: BM25 완전 미스 시 폴백이 `candidate_k` 캡을 무시하고
전체 후보 풀을 theological scoring에 넘기던 버그 수정(`core/retrieval.py`) —
p50 385ms→149ms, p95 14.7s→9.0s, p99 54.6s→17.3s. `core/retrieval.py`는 이
한 건의 최소 패치 외에는 이후 전부 무변경 유지.

**Phase 2 (역색인 인프라 도입, 완료)**:
- 2-1: Tantivy/Meilisearch/Typesense 벤치마크 → **Tantivy 채택**(임베디드,
  평균 지연 최저). C1이 Task Order 033을 4차례(v2~v4) 데이터 무결성 결함으로
  반려당한 뒤 CUE가 직접 인수해 실행·검증(v5) — 상세는
  `feedback_c1_stale_status_reports.md` 메모리 #9/#10 참고.
- 2-2: `core/candidate_generator.py` — Tantivy 기반 `CandidateGenerator`
  (BM25 + 메타데이터 사전필터, id+score만 반환·full_text 미포함)
- 2-3: `core/bible_index.py` — SQLite 기반 `Bible.{Book}.{Chapter}.{Verse}`
  posting list, Vector 인덱스와 독립. 기존 `QueryParser`/`ScriptureReference`
  정규화 재사용(신규 파서 없음)
- 2-4: `core/index_orchestrator.py`의 4개 함수(rebuild_tsu_index/
  reindex_document/reconcile_pending/exclude_document_from_index) 전부에
  candidate index + Bible index 배선 — 문서 1건 수정 시 전체 재색인 없음
- 2-5: 스니펫 — 별도 preview 필드 저장 대신 Tantivy 내장 `SnippetGenerator`
  활용(UTF-8 바이트/문자 오프셋 버그 발견·수정 포함)
- 2-6: `core/hybrid_candidate_pipeline.py`(`HybridRetriever`) — Stage1
  CandidateGenerator + Stage2는 `core/retrieval.py`의 기존 스코어링 함수
  그대로 재사용(재구현 없음). 통합 검증 중 회귀 버그 2건 발견·수정
  (메타데이터 폴백 누락으로 12/96 쿼리 dead-end, Stage2 후보 100개 스코어링
  시 특정 청크로 인한 비선형 지연) 후 최종 실측:

| 지표 | 기존 RetrievalEngine | HybridRetriever |
|---|---:|---:|
| precision@1 (96쿼리) | 1.0 | 1.0 |
| p50 | 149ms | 8.2ms |
| p95 | 9,020ms | 10.5ms |

  10만 합성 코퍼스 별도 측정: p95 9.8ms(완료기준 1초 이내 충족).

**[2026-07-30 추가 진행] USE_INVERTED_INDEX 실배포 + Query Planner 구현 완료**:
- `ui/state/query_processor.py::get_shared_query_processor()`에 배선 완료 —
  `chat.py`/`research.py`는 무변경(이 함수 하나만 통과). 플래그 true면
  `HybridQueryProcessor` 반환.
- `core/query_planner.py`(신규) — 규칙 기반 5-way 라우팅(bible/greek/exact/
  metadata/hybrid), LLM 미사용. `HybridRetriever.retrieve()`가 Stage 0으로
  호출해 Bible Index 직접조회/PhraseQuery/title-author 한정 검색으로 분기.
- 진행 중 실제 프로덕션 `output/bench/bible_index.sqlite3`가 테스트 픽스처로
  오염된 걸 발견·수정(테스트가 경로 인자 하나를 안 넘겨서 발생 — 재발 방지로
  테스트 수정 + 실제 인덱스 재구축 56,857 postings).
- `core/retrieval.py`는 시종 무변경 유지.

**RRF (HQ 제안 ⑦) 구현**: `core/rrf.py`(신규, 범용 유틸) — `HybridRetriever`의
고정 가중합(0.4*bm25+0.4*theological+0.2*passage)을 3-신호 순위 기반 RRF로
교체. book-level gold standard 재실행으로 precision@1 1.0 유지 확인(회귀 없음).

**Search Telemetry (HQ 제안 ⑨) 구현 — 백엔드만, UI 클릭 배선 보류**:
`core/search_telemetry.py`(신규, SQLite) — 성공률/Zero-hit/Top1·5 Click/
Average Candidate/Merge Time/Cache Hit/Embedding·ANN Time 전부 구현(캐시·
임베딩·ANN은 아직 그 단계 자체가 없어 정직하게 항상 0). `HybridQueryProcessor`가
매 쿼리 자동 기록. **UI(`ui/pages/research.py`) 클릭 배선은 보류** —
연결 시도 중 이 파일이 C1이 동시에 진행 중인 대규모 Stitch 리디자인
(uncommitted, 계속 변경 중)으로 실제로 한 번 편집이 덮어써진 것을 발견,
사용자 확인 후 C1 작업 완료 후로 미룸.

**Background Index Builder (HQ 제안 ⑧) 구현 (2026-07-31)**: `core/background_index_builder.py`
(신규, 데몬 스레드) — 새 파이프라인이 아니라 이미 있던 `pipeline_state=PROCESSED`
큐 + `reconcile_pending()`(멱등적 pull 재조정자)을 블로킹 호출 대신 백그라운드
스레드로 옮긴 것. `ui/pages/processing.py`의 블로킹 호출 1곳을
`trigger_now()`(논블로킹)로 교체 — 수정 전 매번 git diff로 C1이 안 건드린
파일인지 확인함(research.py 사고 이후 습관화).

**캐시 계층 분리 (HQ 제안 ⑥) 구현 (2026-07-31)**: `core/search_cache.py`
(신규) — `SearchResultCache`(L1 메모리 + L2 SQLite). L3(Disk)는 별도로
안 만듦(L2가 이미 디스크라 중복), Query Embedding Cache도 안 만듦
(HybridRetriever엔 임베딩 단계 자체가 없음) — 둘 다 이유를 문서에 명시.
캐시 키에 TSU manifest fingerprint 포함 → 재색인하면 자동 무효화.
실측: 캐시 히트 시 67.92ms→0.61ms(약 110배). 이번에도 테스트가 실제
경로를 오염시킨 사고 발생(네 번째, 같은 패턴) — 수정 완료.

**범위 경계 (의도적으로 안 한 것)**: HQ 제안 ①~⑨ 전부 착수 완료(⑨는 백엔드만,
UI 클릭 배선은 C1 리디자인 완료 후 보류). 남은 것은 그 UI 배선 하나뿐.

**테스트**: 이 트랙에서 신규 파일 5개(`test_candidate_generator.py`,
`test_bible_index.py`, `test_hybrid_candidate_pipeline.py`, `test_query_planner.py`
+ `test_index_orchestrator.py`/`test_shared_query_processor.py` 확장) 약 100여 건
추가. 전체 스위트는 1,114개+ 수집(2026-07-30 재확인, 아래
"Tests:" 줄도 함께 갱신).

## 잔여 (비blocker, 향후)
- monitor.py 정적 하드코딩 값(메모리 72% 등) → 실시간화 (P3)
- GA 선언 여부 판단 (안정화 기간 후)
- [x] **[2026-07-27, 완전 해결]** TSU `verse_mapping`의 book_id/chapter
  조합 불일치 — Fix A 구현(`core/tsu_builder.py`) + 전체 재빌드 완료,
  재측정 결과 불일치 8,391건(64.88%) → 0건(0.00%). 상세:
  `docs/PREFLIGHT-tsu-verse-mapping-book-chapter-mismatch.md`
- **[2026-07-27 신규]** DBMA-SEQ(ADR-012) `sermon_judge.py`
  groundedness 첫 실측 — `scripts/run_sermon_eval.py` 신설, 실제
  경로로 3건 실행 결과 평균 5.00/5(전부 만점, 판별력 확인 필요).
  상세: `docs/DBMA-SEQ-Phase1-Groundedness-Baseline-2026-07-27.md`
- **[2026-07-27 결정 → 2026-07-29 완료]** 골든셋 라벨링 담당/일정 확정
  — 담당: David 본인 직접 채점. ADR-010(RAG)/ADR-012(설교) 골든셋을
  3건→7건으로 **동시 확장 완료**(gold-4~7/SEQ004~007). RAG 축은
  judge·사람 4건 전부 완전 일치, 설교 축은 judge가 사람보다 최대 1점
  관대한 경향 확인 — "전부 만점" 판별력 우려 해소. 반영: `tests/
  fixtures/rag_eval_golden_set.json`(RAG), `docs/DBMA-SEQ-Phase1-
  Groundedness-Baseline-2026-07-27.md`(설교, "확장" 절).

---

## 현재 작업 원칙

- 한 번에 하나씩 고친다.
- 변경 후 바로 검증한다.
- 로그를 남긴다.
- 문서화는 md 파일로 한다.
- 추측보다 실행 결과를 본다.

---

## 상태 기록 규칙

상태는 아래 형식으로 남긴다.

```md
- 날짜:
- 작업명:
- 대상 파일:
- 상태:
- 결과:
- 다음 조치:
```

---

## 최근 상태

### 문서 정합성 점검 및 정정 (2026-07-20)
- 상태: 완료
- 설명: HQ 제기 "dbma.py 제거 적절성" 질의를 계기로 문서 전수 점검 수행.
  `dbma.py`는 이미 SPRINT20-I-D(commit `ce6b05a`, 2026-07-17)에서
  `archive/legacy/`로 이동 완료된 상태였으나, `CLAUDE.md`와
  `docs/architecture/DBMA-Legacy-Code-Removal-Plan-v1.md`가 이를 반영하지
  못하고 "제거 계획 진행 중"으로 서술 중이었음을 확인해 정정. 존재하지 않는
  `dbma_rag.py`(commit `94ed8cf`에서 이미 삭제됨) 오기재도 `CLAUDE.md`와
  그 생성 템플릿(`scripts/create_docs.py`)에서 함께 제거. ChromaDB/Qdrant
  레거시 벡터스토어는 ADR-003(Finalization)에 따라 폐기 대상이 아니라 KEEP
  확정 상태임을 재확인(`chroma_db/`, `dbma_qdrant_storage` 실물 존재 확인
  완료). `docs/architecture/DBMA-Architecture-Map-v2.md`,
  `DBMA-Module-Responsibility-v2.md`는 `status: current`를 단 채 SPRINT16
  시점(레거시 archive 이전) 상태를 서술하고 있어 STATE.md와 모순되는 것을
  발견, 본문 재작성 없이 frontmatter status를 `superseded`로 변경하고 상단에
  경고 문구 추가.
- 커밋: `35b8e94`(CLAUDE.md/Plan v1), `8f6b314`(create_docs.py),
  `38e813d`(Architecture-Map-v2/Module-Responsibility-v2) — `dev/dbma-engine`에
  push 완료.
- 다음 조치: 없음.

### Citation Layer (SPRINT20-B/E)
- 상태: 완료
- 설명: `CitationBuilder`가 `list[str]` 대신 구조화된 `Citation` 객체를 생성하고,
  `ResponsePackage.citations` → `GenerationResult.citations`까지 손실 없이
  전달된다. `source_file`/`language`/`source_type`이 registry→TSU→Citation
  전 구간에서 100% coverage로 propagate됨을 1,500개 gold query로 확인했다.
- 다음 조치: 없음(SPRINT20-F 이후 후속 품질 개선은 별도 스프린트로 분리).

### Research Workspace Layer — 첫 번째 Memory Layer (SPRINT27-B/C)
- 상태: 완료
- 설명: `core/research_workspace.py`를 기존 5개 Authority(Processing/Identity/
  TSU/Retrieval/Generation)와 나란한 독립 6번째 레이어로 신설
  (`docs/architecture/ADR-004-Research-Workspace-Layer.md`). 검색 세션을
  `{DEFAULT_OUTPUT_DIR}/research/sessions.json`에 저장하되 TSU 콘텐츠는
  복제하지 않고 `tsu_id`/`document_id`/`citation_id` 참조만 append-only로
  기록(`extraction_failures.json`과 동일한 atomic write 패턴). Research UI
  (`ui/pages/research.py`)에 "세션에 저장" 버튼과 저장된 세션 목록/불러오기
  패널을 추가 — `QueryProcessor.process()` 기존 인터페이스만 호출하고,
  세션 불러오기는 재검색을 자동 실행하지 않는다(검색창만 채움).
  `core/retrieval.py`/`core/processing.py`/`core/identity_registry.py`/TSU
  schema/`documents.json` 전부 무변경 확인됨.
  CI 검증 과정에서 `response_package["results"]`(존재하지 않는 키) 참조 버그와
  `document_id`(metadata 중첩)/`citation_id`(citations 리스트 별도 매핑) 추출
  경로 버그를 발견해 수정하고 회귀 테스트를 추가했다.
- 커밋: `519d719`(feature), `86b1d22`(무관 테스트 docstring), `02afc3f`
  (LOCAL_LLM_HANDOFF.md) — `dev/dbma-engine`에 push 완료.
- 검증: pytest 320 passed(신규 8건: `test_research_workspace.py` 5건,
  `test_research_saved_sessions_ui.py` 3건), 회귀 없음.
- 다음 조치: SPRINT27-D — Research Workspace를 향후 MIE(Ministry Intelligence
  Engine) Memory Layer로 확장하는 방향에 대한 Architecture Preflight(투자
  조사만, 구현 없음).

### Execution Environment / Configuration Authority (SPRINT20-E3/F1)
- 상태: 완료
- 설명: PyYAML 누락 시 `core/config.py`가 `RuntimeError`로 즉시 실패하도록
  변경(과거에는 `config.yaml`이 조용히 무시되고 `DEFAULT_OUTPUT_DIR`이 stale
  경로로 폴백해 TSU 데이터셋 손상 직전까지 갔던 사고가 있었음). 공식 Python
  버전을 3.11.x로 확정하고 `scripts/check_environment.py`로 검증 가능하게 함.
- 다음 조치: 없음.

### Application Entry Point Authority (SPRINT20-G1/G2)
- 상태: 완료
- 설명: `docs/architecture/ADR-001-Retrieval-Engine-Authority.md`가 이미
  `dbma_ui.py`→`ui/app.py`를 공식 경로로, `dbma.py`의 인라인 RAG를 폐기
  대상으로 결정해 두었으나 README/`.github/instructions/*` 문서가 갱신되지
  않아 신규 사용자가 legacy 경로로 유입될 위험이 있었다. 문서 정렬 완료.
- 다음 조치: 없음 — `dbma.py` 자체의 archive 여부는 SPRINT20-I-D에서 결정·실행
  완료(`archive/legacy/`로 이동, commit `ce6b05a`, 2026-07-17). 아래 체크포인트
  항목 참고.

### Logging Authority (SPRINT20-G3)
- 상태: 완료
- 설명: `core/config.py`가 import 시점에 root logger를 `ERROR`로 강제 설정해
  `core/extractors.py`의 optional-dependency 경고(PyMuPDF/striprtf/
  pytesseract/pdf2image 없음)가 전역 억제되고 있었다. 특히 공식 진입점
  `ui/app.py`/`dbma_ui.py`에는 이를 되돌리는 보정 코드가 없어 영향이 컸다.
  해당 설정 제거 후 root logger가 Python 기본값(WARNING)으로 복원됨을
  확인했다.
- 다음 조치: 없음.

---

## 체크포인트

- [x] 프로젝트 구조 확인
- [x] 운영 규칙 정리
- [x] 문서화 기준 수립
- [x] Retrieval Engine 단일화 (ADR-001)
- [x] Citation Layer 구조화 및 Generation pass-through
- [x] Metadata Propagation (source_file/language/source_type)
- [x] Configuration Authority (PyYAML hard-fail)
- [x] Execution Environment Authority (Python 3.11 lock)
- [x] Dataset Provenance (TSU manifest v2)
- [x] Entry Point Documentation Alignment
- [x] Logging Authority Restoration
- [x] Index/TSU Builder Authority 확립 (SPRINT20-I, core/index_orchestrator.py + core/tsu_builder.py)
- [x] Registry Path Authority 단일화 (DEFAULT_REGISTRY_PATH)
- [x] `dbma.py` Legacy Archive 완료 (SPRINT20-I-D, archive/legacy/)
- [x] Retrieval Document Diversity (RETRIEVAL_DOCUMENT_CAP)
- [x] Legacy Vector Store 정책 확정 (ADR-003 Finalization)
- [ ] v1.3.0 Release Candidate 선언 (본 항목 진행 중)
- [x] Release validation (chapter-level benchmark 1500q — PASS, 회귀 없음)
- [x] Ollama HTTP 500 수정 (P2, char/token 4→2, commit f5f2753)
- [x] 잔여 cleanup (data/rag_index, 빈 backup 폴더, md_manager archive)
- [x] Research Workspace Layer — 첫 번째 Memory Layer (SPRINT27-B/C, ADR-004,
      `core/research_workspace.py`, commit `519d719`)
- [x] SPRINT27-D — Memory Layer 확장 Architecture Preflight (조사만, 구현 없음)
- [x] SPRINT28 — Chunk noise 분류기, front-matter/PAGE_BREAK 수정, TF-IDF fallback 지연 빌드
- [x] SPRINT29 — 청킹 파라미터 SSOT화(config.py), 경계 기반 overlap, heading 골격
- [x] SPRINT30 — 적응형 PDF 헤딩 감지기
- [x] SPRINT31 — Heading Provider Registry (ADR-006), HeadingAssembler 커서 매칭
- [x] SPRINT32 — PdfHeadingProvider production 연결(PDF), word-boundary 매칭 버그 수정
- [x] SPRINT33-A/B/C — Boundary Score 모델(ADR-007) 설계·shadow 검증·보정
- [x] SPRINT33-D — Hierarchical Chunk Builder 프로토타입 + D5 정식 평가 (프로덕션 전환은 미실행)
- [x] 근본 수정 (a) — `split_sentences_mixed()` 문장부호 기준 분할 추가
      (commit `d45caed`, 2026-07-21 — 2026-07-22에 "미착수" 오기재를
      정정, 잔여 0.2%는 별개의 Axis 3 unsplittable outlier 문제)
- [x] Hierarchical Chunk Builder Level 3(Hard Fallback) 구현 (ADR-008
      제안 2, commit `08d542a`, 2026-07-22) — 청크 길이 상한 보장을 Profile
      B 4개 문서(6176청크)에서 실측 확인, over_cap 0건(0.0%). ADR-008
      제안 2/3/4 모두 완료.
- [x] Hierarchical Chunk Builder **프로덕션 전환 보류 확정**
      (2026-07-27) — canary 실측(Profile A 2건/B 3건,
      `docs/PREFLIGHT-hierarchical-chunk-builder-canary-2026-07-27.md`)
      결과 Profile B의 Axis 2(Semantic Flush Ratio) 평균 23.9%로
      §5 롤백 트리거(<25%) 발동. `core/hierarchical_chunk_builder.py`는
      계속 dormant 유지, `core/processing.py`는 기존
      `core/chunking_optimizer.py` 그대로 사용. 재평가 트리거: Axis 2
      불안정 원인이 해소되거나 corpus 전체 재측정에서 다른 결과가
      나오면 재검토.
- [x] Logos 소스 인제스트 + PassageMatch/SourceTierBonus 스코어링 (SPRINT 외 병행, commit `08e5704`)
- [x] 한국어 출력 순도 검증 — 재시도 + sanitize 백스톱 (SPRINT 외 병행, commit `08e5704`)
- [x] 대시보드 문서 카운트 통일 + 수량사 적용 (SPRINT 외 병행, commit `8f40ea0`)
- [x] Legacy artifact 정리(output/registry, output/baseline, output_sav →
      backups/) + classify_documents_from_frontmatter.py 경로 버그 수정
      (C1-TASK-ORDER-007, commit `bccd3f4`)
- [ ] Logos manifest 템플릿 준비 완료, 실제 Logos 자료 인제스트는 사용자
      액션 대기 (C1-TASK-ORDER-007 항목6)
- [x] DocumentContext Registry Schema Parity 구현 완료 (C1-TASK-ORDER-017,
      commit `ed82921`, 2026-07-29) — `DocumentContext`에 registry 스키마
      갭 필드 6개(`doc_type`/`superseded_by`/`supersedes`/
      `last_content_hash`/`max_retries`/`source_provenance`) 추가,
      `to_metadata_dict()`에 신규 5개 + 기존 직렬화 누락 5개 키 추가,
      `source_provenance_from_registry_record()` 읽기 전용 accessor 신설.
      신규 테스트 17개, 관련 테스트 범위(document_context/processing/
      index_orchestrator) 48/48 통과, 다른 파일 무변경 확인. 스키마
      왕복(직렬화/역직렬화)만 다루며, `core/processing.py`가 실제
      `doc_type` 값을 채우는 배선은 범위 밖으로 남겨둠 — 대시보드 "?"
      doc_type 표시 문제는 별도 후속 과제. 설계 문서:
      `docs/architecture/DBMA-DocumentContext-Registry-Parity-Design-v1.md`.
- [x] doc_type을 DocumentContext에 실제 배선 완료 (C1-TASK-ORDER-018,
      commit `e1fe996`, 2026-07-29) — `core/processing.py`의 PROCESS
      경로(796행)에 `_document_context.doc_type = doc_type`(이미 계산된
      `guess_doc_type()` 결과), SKIP 경로(600행)에
      `_document_context.doc_type = existing_record.get("doc_type")`
      추가. `TestProcessOneFileDocType` 테스트 2개 신규
      (`tests/test_processing_pipeline.py`), 관련 테스트 범위
      (test_processing_pipeline.py + test_document_context.py) 29/29
      통과. **1차 제출 시 테스트 누락이 있었음** — CUE가 diff 대조로
      발견해 §3.1 테스트 스켈레톤을 Task Order 문서에 추가한 뒤 재제출
      받아 확인 완료. 앞으로 (재)처리되는 문서부터 registry에 실제
      `doc_type`이 채워짐 — 이미 등록된 기존 문서의 `doc_type=None`
      백필은 범위 밖(별도 과제로 남김).
- [x] 기존 등록 문서 doc_type 백필 완료 (C1-TASK-ORDER-019,
      commit `bd0bb34`, 2026-07-29) — 착수 전 실측 결과 프로덕션
      registry(`data/제련완성본/`)는 78건 전부 이미 `doc_type` 있어
      백필 대상 0건(적용 후 재확인도 0건, 불변) — 실제 대상은 진단용
      registry 6개(`output/beta_validation`~`v5`, `SPRINT2_MD_DEBUG`,
      총 61건 `None`)뿐이었음. `scripts/backfill_doc_type.py` 신규
      (dry-run 기본/`--apply` 게이팅/이미 값 있으면 무시/md 파일 없으면
      skip). 41/61건 적용, 20건은 md 파일 없어 skip(그대로 `None` —
      "never invent" 원칙대로 정상 동작). 신규 테스트 6개 통과, `--apply`
      전 registry `.bak` 백업 생성. **1차 보고서에 "적용 후 0건"이라는
      오기재가 있었음** — CUE가 registry 직접 재확인으로 발견(실제로는
      20건 잔존), 정정 후 재제출 받아 확인 완료. 상세:
      `docs/agents/c1/C1-TASK-ORDER-019-REPORT.md`.

---

## n8n Loop Operating Model — Activation 상태 (2026-08-19, CUE 기록)

**TASK-039**: PASS (conditional closure) — 2026-08-18 CUE 최종 판단 유지.
2026-08-19 00:10 재실측으로 재확인(§1-B): Research=0건, Chat=0건,
`output/bench/tsu_dataset.jsonl` 여전히 0바이트. §1-A는 정직하게
NOT VERIFIED로 유지(물리 브라우저 검증 미수행을 PASS로 위장하지 않음).
근거: `docs/agents/c1/C1-TASK-ORDER-039-REPORT.md`.

**n8n Loop**: ACTIVATED / READY — 역할 고정.
n8n = Execution Engine / C1 = Implementation Worker /
CUE = Architecture·Governance·Verification Authority.

**State Discovery**: COMPLETE.
- n8n: `dbma_n8n` 컨테이너 가동 중(재기동 안 함), workflow 4개
  (`dbma`, `DBMA Automation TEST (Phase B~D)`, `Phase E State Machine`,
  `Control Plane Pilot (Isolated)`) 모두 active, 최근 48h 실질 실행 없음.
- 마지막 loop 상태: HOLD (2026-08-17,
  `.automation/audit/CORPUS-FACTORY-SINGLE-TASK-PILOT-CUE-HOLD.json`) —
  신규 미등록 raw corpus 없음(`AF1815`/`PBC1742`/`TH1612` 0 files,
  나머지 10개 소스 전부 QUALITY_PASSED 등록 완료). 2026-08-19 재확인
  결과 변동 없음.
- Production mutation: NONE (HOLD 이후 `registration_state.json` 불변).

**Iteration #1**: NOT DEFINED. 사유: NO VALID NEW INPUT
(신규 raw source 없음 / 이미 QUALITY_PASSED 소스 재등록은 무의미한
iteration / production mutation 정당화할 input 없음).
No Input → No Iteration → No Execution 원칙 적용.

**현재 금지 사항** (다음 유효 input 전까지):
이미 등록된 source 재등록, 동일 source 재처리, synthetic iteration 생성,
production state mutation, n8n restart, `.automation/` audit 착수,
night-shift/control-plane script 수정, ADR-026을 Approved처럼 사용,
신규 workflow architecture 구현.

**ADR Authority**: ADR-022(N8N State Machine) Approved,
ADR-023(Full Processing/Executor) Approved,
ADR-026(Control Plane Corpus Factory Integration) **Proposed —
implementation authority 아님**. ADR-026이 필요한 architecture 변경
발견 시 HOLD → ADR Review로 처리, 우회 구현 금지.

**Re-entry 조건**: 새로운 유효 raw source가 존재하고, 해당 source가
현재 governance/ADR 범위 안에서 처리 가능한 상태일 것. 확인 전
절차: ① input provenance 확인 → ② 중복 여부 확인 → ③ production
mutation 가능성 확인 → ④ 관련 ADR 확인 → ⑤ iteration 정의 →
⑥ C1 전달 → ⑦ C1 execution → ⑧ CUE 독립 검증.

## UI Night Shift — C1 Task Order 040 (2026-08-19, CUE 기록)

**범위**: UX-007 §2(홈)/§3(내 자료) — 파이프라인 진행률 상세를
Home→Library로 이관 + Library 검색창 라벨 변경. `landing.html`/기존
Figma·Stitch 자산은 재생성·변경 없음(보존).

**1차 제출**: FAIL — `st.page_link("pages/library.py", icon="")`가
(a) 빈 문자열 icon이 유효하지 않아 `render_dashboard_page()` 호출 시
즉시 크래시, (b) 이 앱이 네이티브 멀티페이지 구조가 아니라 해당 경로
자체가 존재하지 않음. CUE가 `streamlit.testing.v1.AppTest`로 재현
확인 후 `_go_to` 콜백 재사용 + `<div>` 닫기로 교정 지시.

**재제출**: **PASS** — CUE가 실제 `AppTest`로 재검증(Home/Library
렌더 예외 0건, "자세히 보기" 클릭 시 `nav_page`→`"Library"` 정확 전환
확인), `pytest -k "dashboard or library"` 97/97 재확인. 상세:
`docs/agents/c1/C1-TASK-ORDER-040-REPORT.md`.

**다음 iteration 후보** (UX-007 §15 순서): ~~§1 Global Navigation(5메뉴
라벨)~~ — 아래 Task Order 041로 완료. §2 빠른 시작 버튼 재배치 — 아직
미정의.

## 오늘 밤 무인 작업 (2026-08-19, CUE 기록)

- 직전 세션이 `docs/agents/HANDOFF-PERPLEXITY-CLAUDE-001.md`로 UX-007 후속
  판단을 외부 Perplexity Claude로 이관했으나, 사용자 확인 후 **이 세션
  기준으로 진행하기로 확정** — Perplexity 트랙은 오늘 밤 보류. 이중 채널
  충돌(동일 Task Order를 두 곳에서 판단) 방지.
- 사용자가 자리를 비우며 "무인 시스템으로 가동"을 명시적으로 지시 —
  C1(Cline) 릴레이 대기 대신 **CUE가 build+audit 역할을 겸해 직접
  실행**하기로 판단(사용자 부재 시 진행 정지보다 낫다고 판단, 근거:
  Task Order 041이 이미 Core/retrieval 무접촉·저위험으로 스코프됨).

### C1 Task Order 041 — PASS (CUE 직접 구현 + 자체 검증)

- 대상: `ui/app.py::_render_sidebar()` 한정. emoji 전체 제거, 라벨
  3곳 정렬(내 자료/검색·연구/도움말), `Processing`을 `Monitor`와 같은
  `NAE_ADMIN_MODE` 게이트로 이동.
- **부수 발견**: 기존 `st.radio`에 `format_func`가 없어 라벨이 애초에
  화면에 렌더되지 않고 내부 키가 그대로 노출되던 상태였음 — 완료
  조건(라벨 표시 확인) 충족을 위해 `format_func` 배선 추가, `nav_page`
  반환값(내부 키)·`page_renderers` 라우팅은 무변경.
- `Processing`으로 가는 사이드바 외 진입점 확인: `ui/pages/dashboard.py`
  "문서 추가" 빠른 시작 버튼 — 이번 범위 밖이라 그대로 둠, 사실관계만
  기록.
- 검증: `AppTest` 실구동(mock 없음) 비관리자/관리자 양쪽 전 메뉴 클릭
  예외 0건, `pytest -k "sidebar or nav or app"` 122 passed, `pytest -k
  "dashboard or library or source_navigation"` 105 passed(회귀 없음).
  상세: `docs/agents/c1/C1-TASK-ORDER-041-REPORT.md`.
- 다음 후보(§2) 검토 후 **미착수로 보류**: `DBMA-UX-007-IMPLEMENTATION-
  SPEC.md` §2 실제 내용을 확인한 결과 "빠른 시작 버튼 재배치" 수준이
  아니라 Home 전체 재구성(이어서 읽기 카드, 최근 연구 2열 그리드,
  "조용한 통계" 등)이며, 명시적으로 "§13 참고"(신규 세션 상태, 아직
  미구현)에 의존한다. 041과 달리 저위험 단순 작업이 아니라 신규
  session-state 설계 판단이 필요해 무인 상태로 진행하지 않고 보류 —
  TODO.md의 "§2 빠른 시작 버튼 재배치" 표현은 스펙 규모를 과소평가한
  것이었음을 함께 정정.

### §13 Session State 설계 확정 (2026-08-19, CUE, 사용자 지시로 진행)

- 산출물: [DBMA-UX-007-SessionState-Design.md](DBMA-UX-007-SessionState-Design.md)
  — §13이 "신규 세션 상태 필요"라고만 적고 스키마를 정의하지 않았던
  부분을 구체화. 새 아키텍처 도입 없이 기존 3개 패턴(순수
  `st.session_state` / `chat.py` 식 단일파일 덮어쓰기 /
  `research_workspace.py`(ADR-004) append-only 세션 로그)에 매핑.
- **Tier A**(신규 코드 없음): Home "최근 검색" 카드 →
  `research_workspace.list_sessions()` 읽기 전용 연결.
- **Tier B**(신규 `st.session_state` 키만, Core 무변경, 저위험):
  `sermon_research_selection`(전환 버퍼) + `sermon_research_state`
  (§7 허브 상태) + §7 어댑터(텍스트 프리필만, `candidates`/`outline`
  직접 주입은 v1 범위 밖으로 명시).
- **Tier C**(신규 모듈 `core/reading_session.py`, "이어서 읽기" 영속화):
  ADR-004 범위를 넓히지 않기 위해 `research_workspace.py` 확장 대신
  `chat.py` 패턴을 복제한 별도 파일 제안 — **C1 Review 권장 후 착수**
  (강제 게이트는 아니나 신규 영속 모듈이라 단독 판단으로 바로 구현하지
  않음).
- 구현 순서 제안: Tier A → Tier B(허브 화면) → §7 어댑터 → Tier C.
  각 단계는 041처럼 개별 Task Order로 쪼갠다. **이번 문서는 설계까지만,
  구현 미착수.**
- `.automation/`(night-shift/control-plane), n8n Loop, RAW/Retrieval/
  Embedding Engine, 기존 ADR — 오늘 밤 무접촉 유지(확인함, 변경 없음).

### C1 Task Order 042 — Tier A/B 구현 PASS (2026-08-19, CUE 직접 실행)

- 사용자 지시로 무인 작업 계속 진행. Tier A: `dashboard.py`에 "최근
  검색" 카드(읽기 전용, `research_workspace.list_sessions()`). Tier B:
  `research.py` 결과 카드에 "설교 연구에 추가" 버튼 +
  `sermon_research_selection` 전환 버퍼 + 신규
  `ui/pages/sermon_research.py`(설교 연구 허브, 수동 입력까지) +
  `ui/app.py` 사이드바/라우팅에 "설교 연구" 추가.
- 검증: `AppTest` 실구동 전체 플로우 재현(검색→추가→허브 흡수→메모/
  개요 입력→제거→"이어가기"→`nav_page` 전환) 예외 0건, 신규 회귀
  테스트 `tests/test_sermon_research_hub.py` 8건 PASS, 전체 스위트
  `pytest tests/` **2474 passed**(회귀 없음). 상세:
  `docs/agents/c1/C1-TASK-ORDER-042-REPORT.md`.
- 범위 밖(미착수): §7 어댑터(자료·메모·개요 `sermon_draft_state` 자동
  전달), Tier C(`core/reading_session.py`, 이어서 읽기 영속화 — C1
  Review 권장).

### C1 Task Order 043 — §7 어댑터 PASS (2026-08-19, CUE 직접 실행)

- `sermon_research.py`에 어댑터 구현: `scripture_and_theme` 프리필
  (자료+메모+개요 합성), `style_files` 매칭(코퍼스가 이번 세션에
  이미 로드된 경우만 시도, 아니면 편의 기능 때문에 새로 로드하지
  않음), `candidates`/`outline`은 채우지 않고 정상 재검색 경로 유지.
  진행 중인 초안(`status != "input"` 또는 이미 입력된 본문)은 덮어
  쓰지 않도록 보호.
- 검증: `AppTest`로 허브→"이어가기"→설교 준비 화면까지 실제 전환해
  텍스트 영역 프리필 확인(예외 0건), 진행 중인 초안 보호 2가지 케이스
  확인, `style_files` 매칭(fake processor, 실제 코퍼스 로드 트리거
  없음) 확인. 신규 회귀 테스트 4건 추가(총 12건), 전체 스위트
  `pytest tests/` 재확인. 상세: `docs/agents/c1/C1-TASK-ORDER-043-REPORT.md`.
### C1 Task Order 044 — Tier C PASS (2026-08-19, CUE 직접 실행, C1 Review 생략)

- 사용자가 "C1 Review 없이 계속 진행"을 명시적으로 지시. 신규
  `core/reading_session.py`(chat.py 단일파일 원자적 덮어쓰기 패턴
  복제, ADR-004 스키마 확장 안 함) + `research.py`/`chat.py`의 기존
  상세 패널 렌더 성공 시 저장 한 줄 추가 + Home "이어서 읽기" 카드
  (기존 `research_detail_selection` 패턴으로 재진입, 새 내비게이션
  없음).
- §5 읽기(3영역 워크스페이스) 전체는 여전히 미착수 — 이미 존재하는
  detail_panel("문서 상세 패널을 봤다" = "읽었다")로 범위를 좁혀
  결합했을 뿐, 새 화면을 만들지 않았음을 명시.
- 검증: 신규 회귀 테스트 4건 PASS, `pytest -k "source_navigation or
  dashboard or sermon_research or reading_session or research or
  chat"` 150 passed, 전체 스위트 재확인. 상세:
  `docs/agents/c1/C1-TASK-ORDER-044-REPORT.md`.
- UX-007 §13 설계 문서의 Tier A/B/C + §7 어댑터 **전부 완료**.

### P0 TSU dataset 복원 (2026-08-19, 사용자 승인 후 CUE 실행)

- §5 읽기 전체 구현은 사용자가 보류 지시. 대신 "다음 우선순위"를 다시
  확인한 결과 `output/bench/tsu_dataset.jsonl`이 0바이트라 Chat/
  Research 검색이 전부 0건인 P0가 UI 작업보다 훨씬 심각하다고 판단 —
  CLAUDE.md가 "TSU Pipeline"을 절대 변경 금지 영역으로 명시해 무인
  자동 진행하지 않고 `AskUserQuestion`으로 복원 방법을 확인, 사용자가
  "백업 파일 복원(즉시)"을 선택.
- 실행: `output/bench/backup/tsu_dataset_pre_fixA_20260727T014820.jsonl`
  (2026-07-24 스냅샷, 53,231 TSU / 78개 문서)을 `output/bench/
  tsu_dataset.jsonl`로 복사 + `core/tsu_builder.py::write_manifest()`
  (기존 함수 그대로 호출, pipeline 코드 무변경)로 매니페스트를 현재
  registry(82개 문서)/git commit/config 기준으로 재생성.
- 검증: `QueryProcessor().process("로마서 8장")` 실측 3건 응답(복원
  전 0건), `pytest -k "retrieval or tsu or manifest"` 408 passed, 전체
  스위트 재확인.
- **잔여 갭(의도적으로 남김)**: 복원본은 78개 문서 스냅샷이라 현재
  registry의 82개 중 최근 처리된 4개 문서는 검색에 아직 안 잡힘 —
  완전한 커버리지는 `scripts/build_tsu_dataset.py` 재빌드가 필요(더
  오래 걸림), 이번엔 "즉시 복원"만 사용자가 선택했으므로 재빌드는
  별도 판단으로 남김.
- 두 파일 모두 `.gitignore` 대상(`output/`) — 코드 변경 없음, git
  commit 없음.

### C1 Task Order 045 발급 — §11 용어집 전역 적용, C1에게 이관 (2026-08-19)

- 사용자 지시: "다음 작업은 c1에게 이관해라" — 여기서부터 CUE가 직접
  구현하지 않고 C1(Cline)에게 넘긴다. UX-007 §15가 스스로 "위험도
  낮은 것부터 — §11 용어집 전역 적용(단순 치환, C1 가능)"이라 명시한
  항목을 다음 순서로 선택.
- CUE가 grep으로 위반 사례 4곳을 미리 찾아 문서에 남겼다(직접 고치지
  않음): `research.py:525`(TSU ID 노출), `source_link.py:131`
  (document_id 원문 노출), `tables.py:131`(RRF 원시 점수 노출),
  `library.py`/`dashboard.py`의 "RAW 폴더" 라벨(관리자 게이트 여부
  확인 필요). `ui/tabs.py`는 비활성 경로로 확인, 대상에서 제외.
- Task Order: `docs/agents/c1/C1-TASK-ORDER-045.md`. 릴레이 문구:
  `.automation/requests/C1-RELAY-SNIPPET.md` 릴레이 27.
- C1 제출 시 CUE가 diff 대조 + grep 재현 + `AppTest` 재확인으로 독립
  검증(기존 040/041과 동일 절차).

### C1 Task Order 045 — 1차 제출 FAIL(조건부), Correction Order 발행 (2026-08-19)

- C1이 14곳 수정 + grep/AppTest/43 passed 근거로 PASS 보고. CUE가 diff
  전체 재검토·grep 재현·AppTest 재실행으로 독립 검증한 결과 12곳은
  정확했으나 **2곳이 진짜 버그**로 확인됨:
  1. `source_link.py:131` — "출처 ID: N/A"를 실제 값 유무와 무관하게
     항상 고정 출력(하드코딩), 122행 `document_id` 변수가 죽은 코드로
     남음.
  2. `library.py:461` — 문서 버전 이력 리스트(`for record in chain`)
     안에서 동일 문제가 더 심각하게 발생 — 이전 버전이 2개 이상이면
     전부 `N/A`로 찍혀 **서로 구분이 안 되는 실제 정보 손실**.
  둘 다 C1이 "값을 안전하게 순화"가 아니라 "그 자리를 죽은 값으로
  대체"하는 방식으로 처리한 동일 패턴의 오류 — 보고서(§2 표)에도
  "N/A"가 의도된 결과로 명시돼 있어 실수가 아니라 잘못된 설계 판단.
  나머지 12곳(§11 표 기준 grep 재현 0건, AppTest 예외 0건, `pytest -k
  "research or library or source_navigation or tables"` 43 passed
  재확인)은 정확해 그대로 인정.
- `docs/agents/c1/C1-CORRECTION-ORDER-045.md` 발행 — 위 2곳만 수정
  지시(나머지 12곳은 다시 건드리지 말라고 명시), 릴레이 28
  (`.automation/requests/C1-RELAY-SNIPPET.md`).
- **재제출 CUE 재검증 — PASS 확정** (2026-08-19): diff 대조로 두 곳
  모두 지시한 대로 정확히 삭제(임시방편 재도입 없음) 확인. `grep "N/A"`
  로 재검사 — 남은 항목은 전부 기존의 정당한 `.get(key, 'N/A')`
  fallback뿐, 지적한 두 자리는 완전히 제거됨. 직접 `_render_
  provenance_section()`을 몽키패치로 "이전 버전" 2건 chain을 만들어
  실행 — 두 줄이 서로 다르게 렌더됨을 실측 확인(status/pipeline_state/
  chunk_count로 구분됨, 더 이상 "N/A" 충돌 없음). `AppTest`로 Library
  페이지 포함 전체 재확인 예외 0건, `pytest -k "research or library or
  source_navigation or tables"` 43 passed 재확인. **Task Order 045
  최종 PASS.**

### C1 Task Order 046 발급 — §6 인용 카드 공용 컴포넌트, C1에게 이관 (2026-08-19)

- 사용자 지시로 §6를 C1에게 이관. 착수 전 확인한 결과 `ui/components/
  citation_card.py`와 `chat.py::_render_clickable_source()`가 **이미
  다른 세션에서 §6를 구현 완료**해둔 상태(커밋 이력엔 별도 Task Order로
  안 남아있었음, CUE가 grep으로 재발견) — 이번 Task Order는 새로 만드는
  게 아니라 그 패턴을 아직 안 옮겨진 `research.py`에 적용하는 마이그레이션.
- 부수 발견: `research.py:356`의 `f"근거 신뢰도(citation): {value:.4f}"`
  가 원시 소수점 노출로 §11 위반인데 Task Order 045의 grep(정확한
  키워드 "RRF"/"TSU" 등만 검색)이 놓쳤음 — 이번 마이그레이션으로
  자동 해결되도록 범위에 포함.
- 명시적 보호: "📄 {source_file}" 내비게이션 버튼, "설교 연구에 추가"
  버튼(Task Order 042/043) 무변경 지시 — `tests/test_sermon_research_hub.py`
  가 이 버튼들에 의존.
- Task Order: `docs/agents/c1/C1-TASK-ORDER-046.md`. 릴레이:
  `.automation/requests/C1-RELAY-SNIPPET.md` 릴레이 29.
- **CUE 독립 검증 — PASS 확정** (2026-08-19): diff 대조로 지시대로만
  변경됐음 확인(제목/발췌문 카드 밖 유지, `render_citation_card()`로
  메타+별점 위임, 좌측 4px 색상 바 추가). `pytest -k "research or
  sermon_research or citation or tables"` 78 passed 재확인. 실제
  결과 데이터(evidence_confidence=0.8234 포함)로 `AppTest` 직접
  실행 — 원시 소수점 미노출, 좌측 색상바 CSS 존재, 제목/발췌문 정상
  표시, "📄" 내비게이션 버튼과 "설교 연구에 추가" 버튼 둘 다 그대로
  존재함을 실측 확인. **Task Order 046 PASS.**
- (참고, 이번 정정 지시에는 포함 안 함) "RAW 폴더" 번역이 파일마다
  다름("자료실" — library.py/sermon_review.py, "보관함" —
  dashboard.py/processing.py) — 같은 내부 개념이 두 용어로 갈라짐,
  §11의 "고정 용어집" 취지에는 어긋나지만 기능 버그는 아니라 이번
  Correction Order 범위에는 넣지 않음. 다음에 §11 관련 작업할 때 한
  용어로 통일 필요.

---

**Final State 요약**:
```
TASK-039: PASS (conditional closure)
n8n Loop: ACTIVATED / READY — LOOP READY, WAITING FOR VALID INPUT
State Discovery: COMPLETE
Iteration #1: NOT DEFINED (NO VALID NEW INPUT)
Production Mutation: NONE
.automation/: DEFERRED
Night-shift / Control-plane scripts: DEFERRED
ADR-026: PROPOSED / NOT AUTHORITY
```
새 유효 input이 확인되거나 사용자가 별도 iteration을 명시적으로
지시하기 전에는 loop execution을 시작하지 않는다.

---

## 비고

이 문서는 작업 상태를 빠르게 확인하기 위한 기준 문서다.
상태가 바뀌면 즉시 갱신한다.