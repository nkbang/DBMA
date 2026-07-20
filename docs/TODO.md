# DBMA TODO

## 현재 목표
SPRINT17~19에서 완성한 Retrieval/Evidence/Citation Layer 위에서, SPRINT20이
드러낸 governance 결함(Configuration/Environment/Entry Point/Logging
Authority)을 마무리하고 Research Grade Release Candidate 선언 여부를
결정한다.

---

## 진행 상태

- [x] 프로젝트 구조 확인
- [x] 핵심 파일 목록 정리
- [x] CLAUDE.md 운영 규칙 정리
- [x] Retrieval Engine 단일화 (ADR-001 — `core/retrieval.py::RetrievalEngine`/`QueryProcessor`)
- [x] Citation Layer 구조화 (`Citation` dataclass, `GenerationResult` pass-through)
- [x] TSU Metadata Propagation (`source_file`/`language`/`source_type`, 100% coverage)
- [x] Configuration Authority (PyYAML 누락 시 hard-fail, `requirements.txt`/`environment.yml` 정합)
- [x] Execution Environment Authority (Python 3.11.x 공식 확정, `scripts/check_environment.py`)
- [x] TSU Snapshot Provenance (`build_commit`/`registry_sha256`/`dataset_sha256`/`config_sha256`)
- [x] Entry Point Documentation Alignment (`README.md`, `.github/instructions/*` → `dbma_ui.py`)
- [x] Logging Authority Restoration (`core/config.py`의 root logger 강제 설정 제거)
- [ ] Documentation Synchronization 완료 (본 문서/STATE.md/CHANGELOG.md 갱신 — 진행 중)
- [x] `dbma.py` Legacy Migration 결정 (CUE-20H)
- [ ] Legacy Artifact 정리 (`output/registry/`, `output/baseline/`, `output_sav/` 등)
- [ ] SPRINT20-RC Final Audit / RC 선언

진행률: 85%

---

## 체크포인트

### 1단계: 구조 고정
- [x] 핵심 디렉터리 식별
- [x] 주요 파일 역할 정리
- [ ] 복사본/legacy 파일 정리 기준 수립 (CUE-20H 대상)

### 2단계: Retrieval / Evidence / Citation (SPRINT17~19, SPRINT20-A~C)
- [x] Retrieval Engine Authority 확정 (ADR-001)
- [x] Scripture Evidence Resolver v1 (`provenance.confidence`)
- [x] Citation 구조화 객체 도입 및 Generation pass-through
- [x] Citation Quality baseline 측정 (1,500 gold query 기준)

### 3단계: Governance / Reproducibility (SPRINT20-D~G)
- [x] Registry Authority 정리 (`core/identity_registry.py` docstring)
- [x] Metadata Propagation (registry → TSU → Citation)
- [x] Configuration Hardening (PyYAML hard-fail)
- [x] Execution Environment Lock (Python 3.11)
- [x] Dataset Provenance Manifest v2
- [x] Entry Point Authority 문서 정렬
- [x] Logging Authority 복원
- [ ] Documentation Synchronization 마무리

### 4단계: Legacy 정리 (CUE-20H, 별도 승인 필요)
- [x] `dbma.py` 함수군(`query_rag`, `build_rag_store`, `embed_text_ollama`,
      `query_qdrant`, `upsert_to_qdrant`) archive 완료
- [ ] 2026-07-15 커밋(Chroma metadata schema)의 활성 여부 사람 확인
- [ ] Legacy artifact(`output/registry/` 등) 정리 여부 결정

### 5단계: RC 선언
- [ ] SPRINT20-RC Final Audit
- [ ] Green/Yellow/Red 재평가 후 RC 선언 여부 결정

---

## 현재 우선순위
1. 문서 동기화 마무리 (본 작업)
2. `dbma.py` Legacy Migration 결정 (CUE-20H Preflight) (완료됨)
3. Legacy artifact 정리 여부 결정
4. SPRINT20-RC Final Audit 진행

---

## 작업 기록 형식

### 작업 제목
- 날짜:
- 대상 파일:
- 대상 함수:
- 변경 내용:
- 검증 결과:
- 다음 조치:

---

## 메모
- 큰 수정은 한 번에 하지 않는다.
- 모든 변경은 검증 후 기록한다.
- 진행률은 수시로 업데이트한다.