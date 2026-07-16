---
title: DBMA SPRINT17 Implementation Plan v1
category: architecture
sprint: SPRINT17-0
based_on:
  - docs/architecture/DBMA-DocumentContext-Design-v1.md (SPRINT16-C-1)
  - docs/architecture/ADR-002-Document-Identity-and-Retrieval-Unit.md (SPRINT16-C-2)
  - docs/architecture/ADR-001-Retrieval-Engine-Authority.md (SPRINT16-B-3)
  - docs/architecture/DBMA-Retrieval-Migration-Matrix-v1.md (SPRINT16-B-4)
  - docs/architecture/DBMA-Legacy-EntryPoint-Analysis.md (SPRINT16-B-2)
  - docs/architecture/DBMA-Module-Responsibility-v2.md (SPRINT16-B-1)
status: draft (planning only — 구현 없음)
created: 2026-07-16
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA SPRINT17 Implementation Plan v1

목적: SPRINT16(A/B/C)에서 확정한 Architecture 결정을 코드로 옮기기 전,
실행 가능한 로드맵으로 고정한다. 이 문서는 계획이며 SPRINT17-0에서
어떤 코드도 변경하지 않는다.

---

## 1. DocumentContext Implementation Plan

### 1-1. 위치(Location)

```text
core/document_context.py   ← 신규 파일
```

**근거**: `core/document_identity.py`(ID 발급 함수)와 `core/identity_registry.py`
(영속화)는 이미 존재하는 하위 계층이다. DocumentContext는 이 둘의 산출물을
하나의 상태 객체로 조립하는 **상위 계층**이므로 별도 파일로 분리한다.
기존 두 파일을 직접 수정하지 않고 그 위에 얹는 방식 — SPRINT16-C-1 §2("Does Not
Own")가 명시한 대로 판정 로직/영속화 메커니즘의 소유권은 이동하지 않는다.

### 1-2. dataclass / interface 초안

SPRINT16-C-1 §1(owns)과 ADR-002 §7이 확정한 필드를 그대로 반영한다
(코드 초안은 설계 참고용이며 SPRINT17 본 구현 시 조정 가능):

```python
# core/document_context.py (설계 스케치 — 구현 아님)

@dataclass
class DocumentContext:
    # Identity
    document_id: str
    file_hash: str

    # Source
    source_file: str
    source_type: str
    is_ocr: bool = False

    # Structural metadata (unknown = None 원칙 유지)
    title: Optional[str] = None
    author: Optional[str] = None
    book: Optional[str] = None
    chapter: Optional[int] = None
    page: Optional[int] = None
    batch_id: Optional[str] = None

    # Processing metadata
    language: str = "en"
    noise_score: float = 0.0
    noise_mode: str = "-"
    processing_version: str = PROCESSING_VERSION

    # Chunk references
    chunk_ids: list[str] = field(default_factory=list)
    chunk_count: int = 0

    # TSU references (ADR-002 매핑 테이블 방식)
    tsu_refs: list[str] = field(default_factory=list)

    # Lifecycle
    lifecycle_state: str = "CREATED"   # SPRINT16-C-1 §3 상태 머신 값
    ingest_status: str = "PROCESSED"   # identity_registry.py 값 재사용
    retry_count: int = 0
    last_failure_reason: Optional[str] = None

    # Pipeline completion flags (registry.py와 동일 스키마)
    pipeline_flags: dict = field(default_factory=lambda: {
        "ingested": False, "copied": False, "extracted": False,
        "cleaned": False, "chunked": False, "output_generated": False,
        "verified": False,
    })

    # Timestamps
    created_at: str = ""
    last_processed_at: str = ""

    # Artifact paths
    md_path: Optional[str] = None
    copied_source_path: Optional[str] = None
```

**변환 어댑터 요구사항**: `DocumentContext.from_metadata_dict(meta: dict)`와
`DocumentContext.to_metadata_dict()`를 함께 정의해, 기존
`build_document_metadata()`의 dict 반환값과 상호 변환 가능해야 한다
(SPRINT16-C-1 §6-1 요구사항 그대로).

### 1-3. Lifecycle Integration Point

SPRINT16-C-1 §3에서 정의한 상태 머신을 `process_one_file()`의 다음 지점에
연결한다 (지점 이름은 기존 코드 주석 `[PT-PROCESSING-008]` 등을 그대로 참조):

| 상태 | 연결 지점(현재 코드 라인) | DocumentContext 동작 |
|---|---|---|
| CREATED | 파일 선택 시점 | 인스턴스 생성 (source_file만 채움) |
| IDENTIFIED | `processing.py:517` (Point A) | `document_id`, `file_hash` 설정 |
| (분기) SKIPPED | `processing.py:529` | 조기 반환, registry 기존 레코드로 컨텍스트 채움 |
| METADATA_DRAFTED | `processing.py:596` | 1차 메타데이터 반영 (chunk_count=0) |
| CHUNKED | `processing.py:663` (Point B) | `chunk_ids` 설정 |
| SOURCE_ARCHIVED | `processing.py:686` | `copied_source_path` 설정 |
| METADATA_FINALIZED | `processing.py:691` (Point C) | 2차 메타데이터로 **갱신**(재생성 아님) — SPRINT16-C-1 §0 관찰 1의 "이중 호출" 문제를 여기서 해소 |
| REGISTERED / COMPLETE | `processing.py:699-716` | `pipeline_flags` 전체 True, registry 저장 |
| FAILED | 예외 처리 블록 | `ingest_status="FAILED"`, `last_failure_reason` 설정 |

**핵심 원칙**: `process_one_file()`의 실행 순서 자체는 바꾸지 않는다.
기존 두 번의 `build_document_metadata()` 호출을
`context.update_processing_metadata(chunk_count=...)` 같은 단일 메서드
호출로 대체하는 것이 유일한 로직 변경이다.

### 1-4. Metadata Migration Strategy

기존 `identity_registry.py`의 `documents.json`(schema_version 2.0)과의
호환을 위해 **점진적 마이그레이션**을 채택한다(빅뱅 전환 금지):

1. **Phase 1 산출물**: DocumentContext는 기존 dict 스키마를 그대로 감싸는
   래퍼로 시작한다 — registry 파일 포맷은 변경하지 않는다.
2. **schema_version 3.0**은 `tsu_refs` 필드가 실제로 채워지기 시작하는
   시점(ADR-002 §6의 "매핑을 채우는 프로세스" 구현 이후)에만 도입한다.
   SPRINT17에서는 3.0 마이그레이션을 시도하지 않는다 — `migrate_registry_schema()`
   패턴(append-only, idempotent)을 그대로 재사용할 준비만 해둔다.
3. 기존 `documents.json`에 이미 저장된 레코드는 `DocumentContext.from_metadata_dict()`로
   로드 가능해야 하며, 필드 부재 시 기존 `migrate_registry_schema()`와 동일하게
   "append-only, 기본값 채움" 원칙을 따른다.

---

## 2. ExecutionContext Design Boundary

### 2-1. 통합 대상

SPRINT16-B/C 시리즈가 반복 확인한 3개 분산 상태 원천을 통합한다:

```text
core/feature_flags.py   (정적, SPRINT2_FEATURES 전역 플래그)
core/runtime_state.py   (동적, 로그/파일 기반 파이프라인 상태)
dbma.py 인라인 체크       (레거시, _qdrant_available() 등 — ADR-001에 의해 흡수/폐기 대상)
        ↓
core/execution_context.py   (신규, 통합 조회 인터페이스)
```

### 2-2. 인터페이스 초안

```python
# core/execution_context.py (설계 스케치 — 구현 아님)

@dataclass
class ExecutionContext:
    execution_mode: str          # feature_flags.SPRINT2_FEATURES 기반 ("sprint1" | "sprint2+")
    runtime_state: dict          # runtime_state.get_pipeline_status_dict() 결과
    validation_status: dict      # scripts/validate_pipeline.py 최근 실행 결과 (있으면)

    def is_feature_enabled(self, name: str) -> bool: ...
    def get_pipeline_stage_status(self, stage: str) -> str: ...
    def is_qdrant_available(self) -> bool: ...   # dbma.py::_qdrant_available() 흡수
    def get_document_state(self, document_id: str) -> Optional[DocumentContext]: ...
```

**경계 원칙(SPRINT16-C-1 §4 재확인)**: ExecutionContext는 다수의
DocumentContext를 **조회(query)**하는 상위 계층이며, 그 역방향 의존은
만들지 않는다. `get_document_state()`가 유일하게 DocumentContext를
참조하는 지점이고, DocumentContext 쪽에서 ExecutionContext를 import하지 않는다.

### 2-3. 이번 스프린트에서 다루지 않는 것

- `dbma.py` 자체의 리팩터링(ADR-001/Migration Matrix가 이미 별도 트랙으로 분리함)
- Ollama 모델 목록 조회(`list_ollama_models()` 등) — Generation 계층 설계 대상,
  ExecutionContext 범위 밖으로 명시적으로 제외(ADR-001 원칙 재적용)

---

## 3. Migration Sequence

```text
Phase 1 — DocumentContext dataclass
  산출물: core/document_context.py (신규), 단위 테스트(생성/변환만, 파이프라인 미연결)
  코드 영향 범위: 신규 파일 1개, 기존 코드 무변경
  롤백: 파일 삭제만으로 완전 롤백 가능 (아무것도 참조하지 않음)

        ↓

Phase 2 — process_one_file() integration
  산출물: processing.py의 두 번의 build_document_metadata() 호출을
          DocumentContext 갱신으로 대체
  코드 영향 범위: core/processing.py 1개 파일, 로직 순서 불변
  롤백: feature flag로 신/구 경로 분기 (§5 참조)

        ↓

Phase 3 — metadata flow migration
  산출물: identity_registry.py 저장 시 DocumentContext.to_metadata_dict() 경유
  코드 영향 범위: core/processing.py, core/identity_registry.py 연동부
  롤백: to_metadata_dict() 출력이 기존 dict와 바이트 동일함을 회귀 테스트로
       보장한 뒤 전환 — 실패 시 어댑터만 되돌리면 됨

        ↓

Phase 4 — Retrieval integration
  산출물: ADR-002의 tsu_refs 매핑을 채우는 프로세스 설계·구현
          (매핑을 "누가/언제 채우는가"는 이 Phase에서 확정)
  코드 영향 범위: core/retrieval.py는 읽기 전용 유지(ADR-002 §6 "RankedCandidate 변경 없음"
       원칙 재확인), 매핑은 DocumentContext/registry 쪽에만 추가
  롤백: tsu_refs가 비어있어도 기존 검색 동작에 영향 없음 (선택적 필드)

        ↓

Phase 5 — dbma.py isolation
  산출물: Migration Matrix(SPRINT16-B-4)의 Highest/High 우선순위 항목
          (query_qdrant → RetrievalEngine, upsert_to_qdrant → core/ingest.insert 등) 실행
  코드 영향 범위: dbma.py — 단, Legacy Entry Point Analysis(SPRINT16-B-2)의
       "사람 확인 필요" 항목(활성 사용자 존재 여부)이 해소된 이후에만 착수
  롤백: dbma.py는 Phase 5 착수 전까지 완전히 손대지 않으므로, Phase 1-4가
       실패해도 dbma.py 경로는 항상 동작 상태로 남아 자연스러운 폴백이 된다
```

**Phase 순서의 근거**: Phase 1→3은 DocumentContext/registry 내부 리팩터링으로
사용자에게 보이지 않는 변경이다. Phase 4는 ADR-002의 핵심 미해결 항목을
실행에 옮긴다. Phase 5(가장 리스크 높음, `dbma.py` 운영 지위 불확실성 포함)를
의도적으로 맨 마지막에 배치해, 앞 단계의 안정성이 검증된 뒤에만 레거시
격리에 착수하도록 한다.

---

## 4. Test Strategy

| 계층 | 테스트 | 근거 |
|---|---|---|
| 기존 유지 | `tests/test_processing_pipeline.py` 등 SPRINT15 메타데이터 검증 스위트 전체 통과 유지 | 회귀 방지 최소 기준선 |
| Document identity regression | 동일 입력 파일 세트에 대해 Phase 2/3 전후 `document_id`/`chunk_id`/`file_hash`가 **완전히 동일**한지 스냅샷 비교 | DocumentContext 도입이 식별자 발급 방식을 바꾸지 않아야 함(§1-1 근거) |
| Registry 출력 동등성 | `documents.json` 산출물이 Phase 3 전후 필드 단위로 diff 없음(신규 필드 제외) | SPRINT16-C-1 §6-7 요구사항 그대로 |
| Retrieval regression | `tests/test_book_alias_resolution.py`, `tests/test_query_enhancements_full_regression.py`,
  `tests/gold_queries.json` 기반 회귀가 Phase 4 전후 동일 결과 유지 | ADR-001/ADR-002가 `RetrievalEngine`/`RankedCandidate`를 불변으로 유지하기로 결정했으므로 이 스위트는 무변화가 기대치 |
| Pipeline lifecycle test | §1-3의 상태 전이표(CREATED→...→COMPLETE/FAILED/SKIPPED)를 모의 입력으로 전부 커버하는 신규 테스트 | 기존에 이 상태 전이를 직접 검증하는 테스트가 없었음(SPRINT16-C-1에서 확인된 공백) |
| ExecutionContext 단위 테스트 | `is_feature_enabled`, `get_pipeline_stage_status`가 기존 `feature_flags.py`/`runtime_state.py` 직접 호출과 동일한 값을 반환하는지 | 통합 계층이 기존 로직을 왜곡하지 않음을 보장 |

**커버리지 기준선**: SPRINT16-B-4가 지적한 대로 `dbma.py`의 RAG 함수 22개는
현재 테스트 커버리지 0%다. Phase 5 착수 전 최소 skeleton 테스트를 마련하는
것을 Phase 5의 Definition of Ready로 명시한다(Phase 4까지는 필수 아님).

---

## 5. Rollback Strategy

### 5-1. Feature Flag

```text
core/feature_flags.py에 신규 플래그 추가 (설계만, 구현은 Phase 1에서):

DOCUMENT_CONTEXT_ENABLED = False   # 기본값 False — 명시적 옵트인

feature_enabled("document_context") 로 조회
```

`process_one_file()`은 이 플래그가 False인 동안 기존 이중
`build_document_metadata()` 호출 경로를 그대로 유지한다. Phase 2 코드는
플래그 True일 때만 DocumentContext 경로를 탄다 — 즉 **신/구 경로가 한 코드베이스
안에 공존**하는 기간을 의도적으로 둔다.

### 5-2. Migration Branch

각 Phase는 `dev/dbma-engine`에서 분기한 별도 브랜치
(`feat/document-context-phase-N`)에서 작업하고, Phase별 독립 PR로 병합한다.
Phase N이 문제를 일으키면 해당 PR만 revert — 이전 Phase까지의 산출물은
영향받지 않는다(Phase 1-4가 서로 순차 의존이지만 각각 완결된 단위로 커밋되므로).

### 5-3. Old Metadata Compatibility

`DocumentContext.from_metadata_dict()`/`to_metadata_dict()` 어댑터(§1-2)가
**영구적으로 유지**되어야 한다 — 한시적 마이그레이션 도구가 아니라
DocumentContext의 정식 인터페이스 일부로 취급한다. 이는 기존
`documents.json`(schema 2.0)이 미래에도 계속 읽힐 수 있음을 보장하는
유일한 안전망이다.

**되돌릴 수 없는 지점 없음**: 이 계획의 Phase 1-4는 모두 additive(기존 필드/파일을
삭제하지 않음)이므로 언제든 flag를 되돌려 이전 동작으로 복귀 가능하다.
유일하게 신중해야 할 지점은 Phase 5(`dbma.py` 코드 변경)이며, 그 이유로
Phase 5는 다른 Phase와 달리 "사람 확인 완료"를 착수 조건으로 명시했다(§3).

---

## 6. Risk Assessment

| 리스크 | 등급 | 완화 방안 |
|---|---|---|
| `process_one_file()`의 이중 호출 제거 시 부작용 미발견 | 중간 | Phase 2를 feature flag 뒤에 두고, 신/구 경로 동시 실행 후 출력 비교(dual-run 검증)를 Phase 2 완료 조건에 포함 |
| `documents.json` 스키마 드리프트 | 중간 | §1-4 점진적 마이그레이션 원칙 준수, schema_version 3.0은 이번 스프린트에서 시도하지 않음 |
| TSU 생성 파이프라인 위치 미확인 상태로 Phase 4 착수 | 높음 | ADR-002 §6이 이미 "선행 조사 필요"로 명시 — Phase 4 착수 전 별도 짧은 조사 스프린트(코드 미변경) 삽입을 권고 |
| `dbma.py` 운영 지위 미확인 상태로 Phase 5 착수 | 높음 | §3에서 이미 Phase 5를 "사람 확인 완료 후 착수"로 게이팅함 — 이 게이트를 우회하지 않는다 |
| ExecutionContext가 기존 `runtime_state.py` 판정과 미묘하게 다른 값을 반환 | 중간 | §4의 ExecutionContext 단위 테스트로 기존 직접 호출과의 동치성 검증 |
| Retrieval 회귀 테스트가 실제로는 얕아서(gold_queries 수 적음) Phase 4 부작용을 못 잡음 | 낮음~중간 | 이번 계획 범위 밖이나, `tests/gold_queries.json` 규모 확인을 Phase 4 Definition of Ready에 추가 권고 |
| 여러 Phase에 걸친 일정 지연으로 SPRINT16 architecture 문서와 실제 구현 간 지식 격차 재발생 | 중간 | PM이 이미 지적한 리스크(세션 서두) — 각 Phase 완료 시 `docs/architecture/` 업데이트를 Phase Definition of Done에 포함 |

---

## 7. First Implementation Task Definition

**SPRINT17 착수 시 가장 먼저 수행할 단일 작업**:

```text
Task: core/document_context.py 신규 파일 생성 (Phase 1)

범위:
  - DocumentContext dataclass 정의 (§1-2 초안 기준)
  - from_metadata_dict() / to_metadata_dict() 어댑터 구현
  - 신규 단위 테스트: tests/test_document_context.py
      · 기존 build_document_metadata() 출력 dict → DocumentContext → dict
        왕복 변환이 원본과 동일한지 검증
      · CREATED 상태에서 REGISTERED까지 필드별 채움 순서가
        §1-3 표와 일치하는지 상태 전이 단위 테스트

제외(이번 Task에서 하지 않음):
  - process_one_file() 수정 (Phase 2)
  - feature_flags.py 신규 플래그 추가 (Phase 2 착수 시점에 함께)
  - identity_registry.py 수정 (Phase 3)

완료 기준(Definition of Done):
  - 신규 파일이 core/의 다른 어떤 모듈에서도 import되지 않은 상태로 병합 가능
    (즉 기존 파이프라인에 영향 0 — Phase 1 자체가 "완전히 격리된 추가")
  - tests/test_document_context.py 전체 통과
  - 기존 tests/ 스위트 전체가 무변화로 통과 (회귀 없음 확인)
```

이 Task는 SPRINT16-C-1 §6-1("DocumentContext 데이터 클래스 정의")과
정확히 일치하며, Migration Sequence(§3)의 Phase 1과 동일하다.

---

*본 문서는 SPRINT17-0 범위(`docs/architecture/`)에서 계획 수립만 수행했으며,
`core/`, `ui/`, `scripts/`, `tests/`, `config.yaml`, `dbma.py`는 수정하지 않았다.
문서 내 코드 스케치는 설계 참고용이며 실제 구현이 아니다.*
