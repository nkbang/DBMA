# DBMA TODO

## 현재 목표
v1.3.0 Release 이후 SPRINT27(Research Workspace) → SPRINT31~32(Heading
Assembler/PdfHeadingProvider 안정화) → SPRINT33-A~D(Dormant Semantic
Boundary Detector → Hierarchical Chunk Builder → D-5 Metrics 공식 평가)로
이어진 라인이 D-5 metric 공식 산출(Beta corpus 12건)까지 완료됐고, 그
과정에서 `split_sentences_mixed()`의 개행 의존성으로 인한 **chunk overflow
결함**(순수 단일 언어 장문단에서 chunk_size 상한 자체가 깨지는 심각한
하위결함 B 포함)을 발견해 원인 규명까지 마쳤다(코드 미수정, Preflight
문서 고정). 현재는 이 결함의 수정 여부와 ADR-008이 제안한 후속 항목
(threshold 재산정, Level 3 Hard Fallback 구현, 임베딩 기반 6번째 feature)의
착수 여부를 HQ가 결정하는 단계다.

---

## 진행 상태

### SPRINT17~20 (Retrieval/Evidence/Citation, Governance) — 완료
- [x] 프로젝트 구조 확인 / 핵심 파일 목록 정리 / CLAUDE.md 운영 규칙 정리
- [x] Retrieval Engine 단일화 (ADR-001 — `core/retrieval.py::RetrievalEngine`/`QueryProcessor`)
- [x] Citation Layer 구조화 (`Citation` dataclass, `GenerationResult` pass-through)
- [x] TSU Metadata Propagation (`source_file`/`language`/`source_type`, 100% coverage)
- [x] Configuration / Execution Environment / Logging Authority 확정
- [x] Entry Point Documentation Alignment (`README.md`, `.github/instructions/*` → `dbma_ui.py`)
- [x] `dbma.py` Legacy Archive 완료 (`archive/legacy/`, commit `ce6b05a`)
- [x] v1.3.0 Release 태그 + chapter-level benchmark PASS + beta validation

### SPRINT27 (Research Workspace Layer) — 완료
- [x] `core/research_workspace.py` — 6번째 Authority(Memory Layer) 신설 (ADR-004)
- [x] Research UI 세션 저장/불러오기, `QueryProcessor.process()` 기존 인터페이스만 사용

### SPRINT31~32 (Heading Assembler / PDF) — 완료
- [x] PdfHeadingProvider 전환 어댑터 제거 및 정식 배선
- [x] HeadingAssembler word-boundary containment matching, bounded lookahead 복구

### SPRINT33-A~D (Semantic Boundary / Hierarchical Chunk Builder) — 완료
- [x] Dormant Semantic Boundary Detector 도입 + Shadow 분석 (Phase 1~6-B)
- [x] ScriptureReferenceBoundaryFeature, SentenceBoundaryConfidenceFeature, Tiny Fragment Penalty 등 shadow scoring feature 추가
- [x] ADR-007 / Amendment A — D-5 semantic boundary rebuild gate 정의 (Axis1 recovery / Axis2 semantic flush / Axis3 unsplittable outlier)
- [x] Hierarchical Chunk Builder 프로토타입 (Phase 1)
- [x] D-5 Metrics 공식 평가 완료 (Phase 3-A, Beta corpus 12개 문서: Profile A recovery 98.5%/semantic 29.1%/outlier 0.0%, Profile B recovery 99.0%/semantic 16.4%/outlier 5.5%)
- [x] `split_sentences_mixed()` 개행 의존성 chunk overflow 원인 규명 (Preflight, 코드 미수정) — 하위결함 A(문장 경계만 손실, 경미) / 하위결함 B(chunk_size 상한 자체 붕괴, 심각) 분리 확인
- [x] ADR-008 — semantic chunking production 전환 경로 제안 (확정 아님, 제안만)

### 운영/UI 정리 — 완료
- [x] Dashboard/Monitor 탭 책임 분리 (사용자용 Dashboard ↔ 개발자용 Monitor)
- [x] Monitor 가짜 성능 지표(하드코딩 142ms/8.3/sec/0.8923/156MB) → 실측값 교체
- [x] RAG Chat 지연 수정 + file-scoped retrieval + streaming
- [x] `.gitignore` 오버매칭 버그 수정 (`backups/`, `cache/`, `docs/**/reports/` 누락 커밋 복구)
- [x] C1(Cline 창#1) 위임 거버넌스 문서 체계 도입 (`docs/agents/c1/`, `docs/agent_governance/`)

### 미결 (다음 우선순위)
- [ ] chunk overflow 하위결함 B 수정 방향 결정 (HQ 승인 대기 — 별도 ADR 필요, 후보: `split_sentences_mixed` 무개행 폴백 / `_merge_sentence_fragments` word-safe hard slice)
- [ ] Beta corpus 대상 하위결함 B 발생 빈도 실측 (미실측 상태)
- [ ] ADR-008 제안 항목 착수 여부 결정 (threshold 재산정 / Level 3 Hard Fallback 구현 / 임베딩 기반 6번째 feature)
- [ ] Legacy Artifact 정리 (`output/registry/`, `output/baseline/`, `output_sav/` 등) — 미결
- [ ] Documentation Synchronization 상시화 (TODO.md/STATE.md가 실제 커밋 이력보다 지연되는 문제 재발 방지)

진행률: SPRINT33-D Phase 3-A까지 100% 완료, 후속 결정(수정/ADR-008 착수) 대기 중

---

## 체크포인트

### 1단계: 구조 고정
- [x] 핵심 디렉터리 식별
- [x] 주요 파일 역할 정리
- [ ] 복사본/legacy 파일 정리 기준 수립 (미결, 아래 4단계 참고)

### 2단계: Retrieval / Evidence / Citation (SPRINT17~19, SPRINT20-A~C)
- [x] Retrieval Engine Authority 확정 (ADR-001)
- [x] Scripture Evidence Resolver v1 (`provenance.confidence`)
- [x] Citation 구조화 객체 도입 및 Generation pass-through
- [x] Citation Quality baseline 측정 (1,500 gold query 기준)

### 3단계: Governance / Reproducibility (SPRINT20-D~G, v1.3.0 Release)
- [x] Registry/Configuration/Execution Environment/Logging Authority 확정
- [x] Metadata Propagation (registry → TSU → Citation)
- [x] Entry Point Authority 문서 정렬
- [x] `dbma.py` + Chroma/Qdrant island + md_manager → `archive/legacy/` 이동 완료 (commit `ce6b05a`)
- [x] v1.3.0 태그 + benchmark PASS + beta validation

### 4단계: Memory Layer / Heading / Semantic Chunking (SPRINT27, SPRINT31~33)
- [x] Research Workspace Layer(6번째 Authority) 신설 (ADR-004)
- [x] PdfHeadingProvider 배선 및 HeadingAssembler 안정화
- [x] Dormant Semantic Boundary Detector + Shadow scoring feature군 추가
- [x] ADR-007/Amendment A D-5 게이트 정의 및 Hierarchical Chunk Builder 프로토타입
- [x] D-5 Metrics 공식 평가 (Beta corpus 12건, Profile A/B 분리 산출)
- [x] chunk overflow 결함(하위 A/B) 원인 규명 (Preflight, 코드 미수정)
- [ ] 하위결함 B 수정 방향 결정 및 구현 (HQ 승인 대기)
- [ ] ADR-008 후속 항목(threshold 재산정 / Level 3 구현 / 6번째 feature) 착수 여부 결정
- [ ] Legacy artifact(`output/registry/` 등) 정리 여부 결정

### 5단계: 운영 정리
- [x] Dashboard/Monitor 책임 분리 및 Monitor 실측 지표화
- [x] `.gitignore` 오버매칭 수정
- [x] C1 위임 거버넌스 체계 도입

---

## 현재 우선순위
1. chunk overflow 하위결함 B 수정 여부/방향 결정 (별도 ADR 필요)
2. Beta corpus 대상 하위결함 B 발생 빈도 실측
3. ADR-008 후속 항목 착수 여부 결정
4. Legacy artifact 정리 여부 결정
5. TODO.md/STATE.md를 커밋 이력과 상시 동기화 (본 작업으로 1회성 정정 완료, 이후 갱신 습관화)

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