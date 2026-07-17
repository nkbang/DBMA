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

---

## 아키텍처 결정 (ADR)

- `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` (accepted):
  `core/retrieval.py::RetrievalEngine`/`QueryProcessor`가 유일한 Retrieval
  Engine Authority. `dbma.py`의 인라인 RAG(`query_rag` 등)는 폐기 대상.
- 공식 실행 진입점: `dbma_ui.py` → `ui/app.py` (SPRINT20-G2에서 README/
  `.github/instructions/*` 문서 정렬 완료).

---

## 프로젝트 진행률

전체 진행률: 100% (SPRINT20-I Architecture Consolidation 완료, v1.3.0 태그·검증 완료)

### 세부 진행 (SPRINT20-I 완료)
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
Version:   v1.3.0 (tag 07ec084) + post-release stabilization
HEAD:      7a51a31 (origin/dev/dbma-engine 동기화)
Tests:     237 passed
Runtime:   APP_VERSION 1.3.0 / embed bge-m3:latest / gen my-theology-bot:latest / cap 2
Status:    STABLE — GA 검토 단계
```

완료된 post-release 안정화:
- UI 수정: st.rerun 콜백, 임베딩 % 표시, 마지막 처리, 버전/임베딩 라벨 authority화
- Ollama HTTP 500: char/token 4→2 (다국어 oversized 차단)
- Orphan cleanup: data/rag_index, 빈 backup 폴더, md_manager archive
- Benchmark evidence: output/bench/chapter_level_result_v1.3.0_cap2.json

## 잔여 (비blocker, 향후)
- monitor.py 정적 하드코딩 값(메모리 72% 등) → 실시간화 (P3)
- GA 선언 여부 판단 (안정화 기간 후)

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

### Citation Layer (SPRINT20-B/E)
- 상태: 완료
- 설명: `CitationBuilder`가 `list[str]` 대신 구조화된 `Citation` 객체를 생성하고,
  `ResponsePackage.citations` → `GenerationResult.citations`까지 손실 없이
  전달된다. `source_file`/`language`/`source_type`이 registry→TSU→Citation
  전 구간에서 100% coverage로 propagate됨을 1,500개 gold query로 확인했다.
- 다음 조치: 없음(SPRINT20-F 이후 후속 품질 개선은 별도 스프린트로 분리).

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
- 다음 조치: `dbma.py` 자체의 archive/wrapper/제거 여부 결정(CUE-20H, 사람
  확인 선행 조건 있음).

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

---

## 비고

이 문서는 작업 상태를 빠르게 확인하기 위한 기준 문서다.
상태가 바뀌면 즉시 갱신한다.