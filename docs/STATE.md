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
- `docs/architecture/ADR-009-SIL-Theology-Engine.md` (부분 확정 —
  구조만, 신학 어휘/임계값은 별도 승인 대기): TSU에 교리 필터 확장
  필드 골격만 추가, 태깅 로직은 미구현.
- `docs/architecture/ADR-010-DBMA-REQ-RAG-Evaluation-Quality.md`
  (구조 확정, Phase 1 착수 전 미확정 항목 2건 별도 결정 필요):
  LLM-as-judge pointwise 평가 인프라(`core/evaluation/`).
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
HEAD:      932aa93 (origin/dev/dbma-engine 동기화, 2026-07-22)
Tests:     599개 수집 확인(tests/ 스코프, 2026-07-22) — 전체 통과 여부는
           SPRINT33-D 완료 시점 기록(539 passed)이 마지막 공식 확인, 이후
           변경분(SPRINT 외 병행 작업 포함) 재실행 권장
Runtime:   APP_VERSION 1.3.0 / embed bge-m3:latest / gen my-theology-bot:latest
           (llama3.3:70b Q4_K_M) / cap 2
Status:    STABLE — GA 검토 단계 (변동 없음)
```

완료된 post-release 안정화:
- UI 수정: st.rerun 콜백, 임베딩 % 표시, 마지막 처리, 버전/임베딩 라벨 authority화
- Ollama HTTP 500: char/token 4→2 (다국어 oversized 차단)
- Orphan cleanup: data/rag_index, 빈 backup 폴더, md_manager archive
- Benchmark evidence: output/bench/chapter_level_result_v1.3.0_cap2.json

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
- **[2026-07-27 결정]** 골든셋 라벨링 담당/일정 확정 — 담당: David
  본인 직접 채점. 일정: 2026-08-02(이번 주)까지 ADR-010(RAG)과
  ADR-012(설교, DBMA-SEQ) 골든셋을 3건→5~10건으로 **동시 확장**.
  (ADR-010 §1, ADR-012 Next Steps §2 관련)

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

---

## 비고

이 문서는 작업 상태를 빠르게 확인하기 위한 기준 문서다.
상태가 바뀌면 즉시 갱신한다.