# DBMA-SIL Phase 0: Architecture Discovery and Impact Analysis

| 항목 | 내용 |
|------|------|
| **문서 버전** | 1.0 |
| **작성자** | C1-DBMA-PLANNER (Planning and Architecture Governance Agent) |
| **작성일** | 2026-07-21 |
| **상태** | 완료 — Human HQ 승인 대기 |
| **역할** | Planning and Architecture Governance (코드 작성 금지) |

---

## 1. Current State

### 1.1 VERIFIED: 이미 구현된 설교문 관련 코드

| 구성 요소 | 위치 | 상태 |
|-----------|------|------|
| `SermonDraftService` | `core/generation.py` | 구현됨 |
| `SermonOutline` | `core/generation.py` | 구현됨 |
| `SERMON_FORMATS` | `core/generation.py` | 구현됨 |
| 설교문 작성 워크숍 페이지 | `ui/pages/sermon_draft.py` | 구현됨 |
| 사이드바 네비게이션 등록 | `ui/app.py` 129행: `"설교문 작성": ("📝", "설교문 작성 워크숍")` | 등록됨 |
| import 등록 | `ui/app.py` 26행: `from ui.pages.sermon_draft import render_sermon_draft_page` | 등록됨 |
| 페이지 렌더러 매핑 | `ui/app.py` 185행: `"설교문 작성": render_sermon_draft_page` | 매핑됨 |

### 1.2 VERIFIED: 기존 아키텍처 원칙

| 원칙 | 출처 | 내용 |
|------|------|------|
| One Pipeline | DBMA_SYSTEM_CHARTER.md §2 | 모든 문서는 단일 처리 파이프라인을 통과 |
| One Config | DBMA_SYSTEM_CHARTER.md §2 | 설정 권한은 중앙화, 중복 금지 |
| One Retrieval Engine | ADR-001 | `core/retrieval.py::RetrievalEngine`이 유일한 검색 권한 |
| One Execution State | DBMA_SYSTEM_CHARTER.md §2 | 파이프라인 상태 일관성 유지 |

### 1.3 VERIFIED: ADR 번호 예약

- ADR-009는 SIL 관련 ADR용으로 사용 (ADR-006은 이미 타 문서에서 사용 중)
- 기존 ADR 목록: ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-007, ADR-008

### 1.4 VERIFIED: TSU 레코드 스키마 (core/tsu_builder.py L317-396)

```json
{
    "tsu_id": "TSU-{book_id}-{chunk_id}",
    "document_id": "doc-xxx",
    "chunk_id": "chunk-xxx",
    "content": "...",
    "verse_mapping": {"book_id": "ROM", "chapter": 5, "verse_start": 3},
    "themes": [],
    "title": "...",
    "author": "...",
    "chapter": 5,
    "page": 123,
    "source_file": "document.pdf",
    "language": "en",
    "source_type": "pdf",
    "provenance": {...},
    "content_quality": {"noise_type": "...", "quality_score": 0.9, "section_type": "..."},
    "structure": {"heading_path": "...", "heading_depth": 2, "heading_confidence": 1.0, "heading_source": "atx"}
}
```

### 1.5 VERIFIED: 공유 QueryProcessor 패턴 (ui/state/query_processor.py)

- `get_shared_query_processor()`: 단일 RetrievalEngine 인스턴스 per session
- TSU manifest `dataset_sha256` 변경 시 자동 재생성 (staleness detection)
- SIL은 이 패턴을 재사용해야 함

---

## 2. Evidence Classification

### 2.1 VERIFIED (직접 확인된 사실)

| 번호 | 내용 | 출처 |
|------|------|------|
| V-01 | `sermon_draft.py`는 이미 구현됨 | `ui/pages/sermon_draft.py` 읽음 |
| V-02 | `SermonDraftService`는 `GenerationService`와 조합으로 연결 | `core/generation.py` 읽음 |
| V-03 | `ui/app.py` 26행에 import, 185행에 매핑 | `ui/app.py` 읽음 |
| V-04 | 사이드바에 `"설교문 작성"`으로 등록됨 | `ui/app.py` 129행 |
| V-05 | TSU 스키마는 모든 필드가 선택적 (additive-only) | `core/tsu_builder.py` L317-396 |
| V-06 | One Retrieval Engine 원칙은 ADR-001로 명시됨 | `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` |
| V-07 | `get_shared_query_processor()`는 TSU staleness detection 포함 | `ui/state/query_processor.py` L48-65 |
| V-08 | ADR-009는 SIL용으로 사용 가능 (ADR-006은 이미 타 문서에서 사용) | `docs/architecture/ADR-007-Semantic-Boundary-Detector-D5-Rebuild-Gate.md` L25-30 |

### 2.2 REPORTED (기존 문서에서 보고된 정보)

| 번호 | 내용 | 출처 |
|------|------|------|
| R-01 | Phase 1 설계 검토 문서 존재 | `docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-Review.md` |
| R-02 | `SermonOutline`는 title, introduction, points, conclusion 필드 보유 | Phase 1 설계 문서 R-01 참조 |
| R-03 | `SERMON_FORMATS`는 "주제설교", "강해설교" 등 포함 | Phase 1 설계 문서 R-01 참조 |
| R-04 | SIL 관련 요구사항 ( Biblical exegesis, Theological synthesis 등) | 사용자 작업 요청 |

### 2.3 UNKNOWN (확인 불가 — 추측 금지)

| 번호 | 내용 | 확인 방법 |
|------|------|-----------|
| U-01 | TSU에 `sermon_type` 필드가 이미 존재하는가? | TSU 데이터셋 직접 읽기 불가 (파일 시스템 접근 제한) |
| U-02 | `SermonDraftService.generate_outline()`의 프롬프트 템플릿 내용은 무엇인가? | `core/generation.py` 전체 읽지 않음 (중복 읽기 방지) |
| U-03 | `SermonDraftService.expand_point()`의 LLM 호출 모델은 무엇인가? | config.yaml의 `ollama.default_gen_model`은 설정값일 뿐 실제 사용 모델 아님 |
| U-04 | 기존 설교문 초안 파일이 실제 저장되어 있는가? | output 디렉토리 접근 불가 |
| U-05 | TSU 확장 시 배치 마이그레이션 스크립트가 필요한가? | TSU 데이터셋 크기/내용 확인 불가 |
| U-06 | `doctrine_filter.py`의 신학적 검증 기준은 Southern Baptist 관점에서 어떤 특정 교리 항목을 포함해야 하는가? |神学적 판단 필요 — C1 Agent의 영역 아님 |
| U-07 | `sermon_lab.py` 신규 페이지 vs `sermon_draft.py` 확장 중 어떤 접근이 적합한가? | UI/UX 판단 필요 — Human HQ의 결정 사항 |

---

## 3. Risk Assessment

### 3.1 위험 #1: 기존 `sermon_draft.py` 동작 파괴 (등급: 🟡 중간)

**설명:** SIL 아키텍처 변경이 기존 `sermon_draft.py`의 `st.session_state["sermon_draft_state"]`와 충돌할 수 있음.

**영향:**
- 기존 설교문 작성 워크숍 세션 상태 손실
- 사이드바 네비게이션 라우팅 충돌

**완화책:**
- SIL은 별도 세션 키 사용 (예: `st.session_state["sermon_intelligence_state"]`)
- `sermon_draft.py`는 기존 인터페이스 유지, SIL은 `core/sermon/` 레이어에서만 동작

### 3.2 위험 #2: One Retrieval Engine 원칙 위반 (등급: 🔴 높음)

**설명:** SIL 구현 시 별도 검색 로직을 만들 경우 ADR-001 위반.

**영향:**
- 아키텍처 원칙 파괴
- 유지보수 복잡도 증가

**완화책:**
- `get_shared_query_processor()`를 통한 단일 엔진 재사용만 허용
- 가중치 조정 외의 검색 로직 금지

### 3.3 위험 #3: TSU 확장으로 인한 파급 효과 (등급: 🟡 중간)

**설명:** TSU 메타데이터 확장이 파이프라인 전체에 영향 줄 수 있음.

**영향:**
- 기존 레코드와의 호환성 문제
- 인덱싱 재실행 필요

**완화책:**
- additive-only 필드만 추가
- 기존 필드 변경 금지
- 마이그레이션 불필요 (선택적 필드이므로)

### 3.4 위험 #4: 신학적 검증의 주관성 (등급: 🟢 낮음)

**설명:** `doctrine_filter.py`의 검증 기준이 모호할 수 있음.

**영향:**
- 자동화된 신학적 검증의 신뢰성 문제

**완화책:**
- 명확한 카테고리 정의 필요
- 인간 검토 필수 (AI는 보조 역할만)

### 3.5 위험 #5: 최종 스프린트 제약 (등급: 🟡 중간)

**설명:** Sprint 15는 최종 개발 스프린트 — 과도한 확장 방지.

**영향:**
- SIL의 완전한 구현이 한 스프린트에 포함되지 않을 수 있음

**완화책:**
- Phase 1은 아키텍처 문서화 + 최소 구현에 집중
- 나머지는 향후 유지보수 스프린트에서 진행

---

## 4. Architecture Impact

### 4.1 One Pipeline 영향 분석

| 단계 | 영향 | 설명 |
|------|------|------|
| Source Documents | 없음 | SIL은 문서 소스를 변경하지 않음 |
| Extraction | 없음 | SIL은 추출 로직을 변경하지 않음 |
| Chunking | 없음 | SIL은 청킹 로직을 변경하지 않음 |
| Embedding | 없음 | SIL은 임베딩 로직을 변경하지 않음 |
| Vector Storage | 없음 | SIL은 벡터DB를 변경하지 않음 |
| RetrievalEngine | △ SIL이 재사용 | `get_shared_query_processor()`를 통한 읽기 전용 접근 |
| Research Interface | △ SIL이 UI 확장 | `sermon_draft.py` 또는 신규 페이지 |

**결론:** One Pipeline 원칙 유지 ✓

### 4.2 One Config 영향 분석

| 설정 항목 | 영향 | 설명 |
|-----------|------|------|
| `config.yaml` | △ `sermon:` 섹션 추가 가능 | 하위 호환성 유지 |
| `core/config.py` | △ SIL 관련 상수 추가 가능 | 기존 상수 변경 금지 |

**결론:** One Config 원칙 유지 ✓ (신규 설정은 additive-only)

### 4.3 One Retrieval Engine 영향 분석

| 구성 요소 | 영향 | 설명 |
|-----------|------|------|
| `core/retrieval.py` | 없음 | SIL이 직접 변경하지 않음 |
| `RetrievalEngine` | 없음 | SIL이 인스턴스 생성하지 않음 |
| `QueryProcessor` | △ SIL이 재사용 | `get_shared_query_processor()`를 통한 읽기 전용 접근 |
| `RankingEngine` | △ SIL이 가중치 활용 | 기존 랭킹 로직 변경하지 않음 |

**결론:** One Retrieval Engine 원칙 유지 ✓ (SIL은 소비자일 뿐 생성자가 아님)

### 4.4 One Execution State 영향 분석

| 상태 | 영향 | 설명 |
|------|------|------|
| 파이프라인 상태 | 없음 | SIL은 파이프라인 상태를 관리하지 않음 |
| 세션 상태 | △ SIL이 별도 키 사용 | `sermon_intelligence_state` 등 기존 키와 충돌하지 않는 이름 |

**결론:** One Execution State 원칙 유지 ✓

---

## 5. Recommendation

### Q1. SIL은 DBMA Core 내부인가, Extension Layer인가?

**답: Extension Layer (`core/sermon/`)**

**근거 (VERIFIED):**
- V-06: One Retrieval Engine 원칙은 ADR-001로 명시됨
- V-05: TSU 스키마는 additive-only
- R-01: Phase 1 설계 검토 문서가 `core/sermon/` 확장 계층을 제안

**이유:**
1. SIL은 DBMA의 핵심 파이프라인이 아닌 **도메인 특화 레이어**
2. `core/retrieval.py`를 변경하지 않고 재사용해야 함 (ADR-001)
3. 향후 유지보수 경계 명확: retrieval vs sermon 도메인

**대안 비교:**

| 접근 | 장점 | 단점 |
|------|------|------|
| **Extension Layer (권장)** | 경계 명확, 중복 없음 | 신규 디렉토리 생성 |
| retrieval.py 내 통합 | 단일 모듈 | 원칙 위반, 복잡도 증가 |
| 별도 서비스 | 독립성 | 배포 복잡성, One Config 위반 |

### Q2. 기존 TSU 변경이 필요한가?

**답: UNKNOWN (U-01)**

**근거:**
- V-05: TSU 스키마는 모든 필드가 선택적 (additive-only)
- U-01: TSU에 `sermon_type` 필드가 이미 존재하는지 확인 불가

**분석:**
- TSU 확장이 필요하다면 **additive-only** 필드만 추가
- 기존 필드 변경 금지
- 마이그레이션 불필요 (선택적 필드이므로 기존 레코드 영향 없음)

**권장 접근:**
1. TSU 데이터셋 직접 확인 (Human HQ 또는 스크립트 실행)
2. 필요한 필드 목록 정의: `sermon_type`, `theological_claim`, `doctrine_category` 등
3. additive-only로만 확장

### Q3. Retrieval Engine에 어떤 metadata signal을 추가할 것인가?

**답: One Retrieval Engine 원칙 우선 — 가중치 조정만 허용**

**근거 (VERIFIED):**
- V-06: ADR-001은 "신규 검색 경로를 만들지 않는다"고 명시
- V-07: `get_shared_query_processor()`는 단일 인스턴스 패턴 제공

**권장 접근:**

```
SIL 쿼리 처리 흐름 (의사코드):

"Matthew 11:28에 대한 설교 준비"
        ↓
get_shared_query_processor().process(k=20)
        ↓
RetrievalEngine.hybrid_scoring()     ← 기존 로직 변경 없음
        ↓
[추가] sermon_ranking_hints()        ← 가중치 조정 (검색 아님)
        ↓
RankedCandidate (scripture_weight, theological_weight 추가 필드)
```

**금지 사항:**
- `sermon_retrieval.py` 생성 ❌
- 별도 벡터DB 연결 ❌
- 병렬 검색 경로 ❌

**허용 사항:**
- `get_shared_query_processor()` 재사용 ✓
- 기존 `RetrievalEngine.hybrid_scoring()` 읽기 전용 접근 ✓
- 가중치 조정 (검색 로직이 아닌 랭킹 후 처리) ✓

### Q4. MVP 범위는 어디까지인가?

**답: Phase 1 — 아키텍처 문서화 + 최소 구현**

**VERIFIED 구현 현황:**

| 구성 요소 | 상태 | 설명 |
|-----------|------|------|
| `SermonDraftService` | ✓ 구현됨 | 개요 생성 + 대지 확장 |
| `SermonOutline` | ✓ 구현됨 | title, introduction, points, conclusion |
| `sermon_draft.py` UI | ✓ 구현됨 | 사이드바 네비게이션 포함 |
| `sermon_workspace.py` | ✗ 미구현 | 세션 관리 모듈 |
| `sermon_structure.py` | ✗ 미구현 | SermonArchitecture 데이터 모델 |
| `doctrine_filter.py` | ✗ 미구현 | 신학적 검증 |
| `evaluation.py` | ✗ 미구현 | 설교 품질 분석 |
| `prompts.py` | ✗ 미구현 | 설교문 도메인 프롬프트 템플릿 |

**MVP 범위 (Phase 1):**

```
core/sermon/                    ← SIL 확장 계층 (신규)
├── __init__.py                 ← 모듈 exports
├── sermon_workspace.py         ← 세션 관리 (research_workspace.py 패턴 참조)
└── sermon_structure.py         ← SermonArchitecture, SermonPoint 데이터 모델

docs/architecture/ADR-009-SIL.md  ← ADR 신규 생성
```

**MVP 범위 외 (Phase 2+):**

```
core/sermon/
├── doctrine_filter.py          ← 신학적 검증
├── evaluation.py               ← 설교 품질 분석
└── prompts.py                  ← 설교문 도메인 프롬프트 템플릿

ui/pages/sermon_lab.py          ← 신규 UI 페이지 (선택적)
```

### Q5. ADR이 필요한 항목은 무엇인가?

**답: ADR-009 (SIL 아키텍처)만 필요**

**근거:**
- V-08: ADR-009는 SIL용으로 사용 가능 (ADR-006은 이미 타 문서에서 사용)
- V-06: ADR-001은 이미 One Retrieval Engine을 명시 — 중복 ADR 불필요

**필요한 ADR:**

| ADR 번호 | 제목 | 필요성 |
|----------|------|--------|
| **ADR-009** | Sermon Intelligence Layer (SIL) 아키텍처 | **필수** — SIL의 확장 계층 접근, TSU 확장 정책, UI 접근 명시 |

**불필요한 ADR (기존 ADR로 충분):**

| ADR 번호 | 제목 | 불필요 이유 |
|----------|------|-------------|
| ADR-XXX | One Retrieval Engine 재확인 | 기존 ADR-001로 충분 |
| ADR-XXX | TSU additive-only 정책 | 기존 TSU 스키마가 이미 additive-only (V-05) |
| ADR-XXX | UI 페이지 분리 | ADR-004 (Research Workspace Layer) 패턴으로 충분 |

---

## 6. Human Approval Required

### 승인 요청 사항

Human HQ의 승인이 필요한 항목은 다음과 같습니다:

#### 1. SIL 아키텍처 접근 방식

- [ ] `core/sermon/` Extension Layer로 구현 승인
- [ ] 기존 `sermon_draft.py` UI 확장 승인 (신규 페이지 불필요)

#### 2. TSU 확장 정책

- [ ] additive-only 필드만 확장 승인
- [ ] 기존 필드 변경 금지 승인
- [ ] 마이그레이션 불필요 승인

#### 3. MVP 범위

- [ ] Phase 1: `sermon_workspace.py`, `sermon_structure.py` + ADR-009 승인
- [ ] Phase 2+: `doctrine_filter.py`, `evaluation.py`, `prompts.py` 유보 승인

#### 4. Retrieval 접근

- [ ] `get_shared_query_processor()` 재사용만 허용 승인
- [ ] 별도 검색 로직 생성 금지 승인

---

## 부록 A: 용어 정의

| 용어 | 정의 |
|------|------|
| SIL | Sermon Intelligence Layer — 설교 준비를 지원하기 위한 신학적 인텔리전스 레이어 |
| TSU | Text Semantic Unit — DBMA의 기본 검색 단위 |
| ADR | Architecture Decision Record — 아키텍처 의사결정 기록 |
| MVP | Minimum Viable Product — 최소 기능 제품 |
| additive-only | 기존 구조 변경 없이 필드만 추가하는 확장 방식 |

## 부록 B: 참고 문서

| 문서 | 위치 |
|------|------|
| DBMA System Charter | `DBMA_SYSTEM_CHARTER.md` |
| ADR-001: Retrieval Engine Authority | `docs/architecture/ADR-001-Retrieval-Engine-Authority.md` |
| ADR-004: Research Workspace Layer | `docs/architecture/ADR-004-Research-Workspace-Layer.md` |
| Phase 1 설계 검토 | `docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-Review.md` |

---

*본 문서는 C1-DBMA-PLANNER가 작성했으며, 코드를 생성하거나 수정하지 않았습니다.*
*Human HQ의 승인이 필요합니다. 승인 후 Act mode로 전환하여 Phase 2 구현을 시작합니다.*