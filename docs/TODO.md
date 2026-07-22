# DBMA TODO

## 현재 목표
[2026-07-22 갱신] 이 문서는 SPRINT20-RC 시점에서 오래 갱신이 밀려 있었다
— 아래 "진행 상태"/"체크포인트"는 SPRINT20 스코프의 **역사적 기록**으로
남기고, 실제 현재 우선순위는 하단 "SPRINT28~33-D 이후 현재 우선순위"를
따른다(`docs/STATE.md`의 "SPRINT28~33-D 진행 내역"과 함께 볼 것).

원래 목표(SPRINT17~19에서 완성한 Retrieval/Evidence/Citation Layer 위에서
SPRINT20 governance 결함을 마무리하고 RC 선언 여부 결정)는 RC 선언 자체는
보류된 채 SPRINT20-I(Architecture Consolidation)로 흡수되어 v1.3.0 태그로
마무리됐고, 이후 SPRINT28~33-D(청킹 품질 고도화)로 이어졌다.

---

## SPRINT28~33-D 이후 현재 우선순위 (2026-07-22)

1. **근본 수정 (a)** — `core/text_normalizer.py::split_sentences_mixed()`가
   입력에 `\n`이 없으면 `split_sentences()`(정규식 기반)로 위임하도록 수정.
   corpus 전체 문장분할 동작에 영향을 주므로 별도 벤치마크 검증 필요 —
   **HQ 결정 대기** (`docs/PREFLIGHT-split-sentences-mixed-chunk-overflow.md`).
2. **Hierarchical Chunk Builder 프로덕션 전환 여부** — 현재
   `core/hierarchical_chunk_builder.py`는 프로토타입 단계이고 프로덕션
   경로(`core/chunking_optimizer.py`)는 무접촉 상태. 전환 조건은
   ADR-008에 정의되어 있으나 착수 여부 미결정.
3. **ADR-009 SIL Theology Engine** — 구조(TSU 확장 필드)만 확정, 신학
   교리 어휘·임계값 확정 및 실제 태깅 로직은 미착수.
4. **ADR-010 RAG Evaluation** — Phase 1 착수 전 미확정 항목 2건 결정 필요
   (`core/evaluation/` 인프라는 존재, 정식 실행 미착수).
5. **Legacy artifact 정리** — `output/registry/`, `output/baseline/`,
   `output_sav/` 등 정리 여부 — SPRINT20 때부터 미결정 상태로 이월.
6. **Logos 소스 인제스트 실사용** — `scripts/ingest_logos_export.py`는
   구현·검증 완료. 실제 Logos Clippings/manifest 준비가 있어야 다음
   단계(로마서 시리즈 MVP) 진행 가능 — 사용자 액션 대기.

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
- [x] Documentation Synchronization 완료 (본 문서/STATE.md 갱신, 2026-07-22 —
      단 CHANGELOG.md는 별도 미확인)
- [x] `dbma.py` Legacy Migration 결정 (CUE-20H)
- [ ] Legacy Artifact 정리 (`output/registry/`, `output/baseline/`, `output_sav/` 등) — 미결정 이월
- [ ] SPRINT20-RC Final Audit / RC 선언 — SPRINT20-I로 흡수되어 v1.3.0 태그로 사실상
      해소, RC "선언" 자체는 명시적으로 이루어지지 않음(STATE.md "GA 검토 단계" 참고)

진행률(SPRINT20 스코프): 85% → 사실상 v1.3.0 태그로 종료, 이후 SPRINT28~33-D는
별도 트랙(위 "SPRINT28~33-D 이후 현재 우선순위" 참고).

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

## 현재 우선순위 (SPRINT20 스코프, 역사적 기록)
1. 문서 동기화 마무리 (완료, 2026-07-22)
2. `dbma.py` Legacy Migration 결정 (CUE-20H Preflight) (완료됨)
3. Legacy artifact 정리 여부 결정 (미결정 이월 — 위 "SPRINT28~33-D 이후 현재 우선순위" §5)
4. SPRINT20-RC Final Audit 진행 (SPRINT20-I로 흡수, v1.3.0 태그로 사실상 종료)

**실제 현재 우선순위는 상단 "SPRINT28~33-D 이후 현재 우선순위" 참고.**

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