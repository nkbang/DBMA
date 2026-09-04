# C1 Task Order 025 — v3 Phase 2 착수 준비: EvidenceUnit 모델 + DEVONthinkAdapter 인터페이스 (픽스처만)

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P1
**선행 작업**: Task Order 020~024(v2 Sprint A~D + 응답생성 연동) 완료·검증됨(137/137 통과).
**근거 문서**: [docs/architecture/NAE-Unified-Research-Search-Plan-v3.md](../../architecture/NAE-Unified-Research-Search-Plan-v3.md)
§3(Phase 1/2), §7(착수 계획)
**작성일**: 2026-07-29
**⚠️ 범위 제약 (반드시 지킬 것)**: **DEVONthink 실제 연동 방식(AppleScript/수동 export/기타)은 사용자가
아직 결정하지 않았다 (2026-07-29, "일단 보류").** 이번 Task Order는 실제 DEVONthink 애플리케이션이나
데이터베이스에 접근하는 코드를 **작성하지 않는다** — `osascript`/AppleScript 호출, DEVONthink SQLite
파일 직접 읽기, `x-devonthink-item://` 실제 open 처리 등은 전부 금지. 순수 데이터 모델과, 테스트
픽스처(JSON)로만 검증되는 어댑터 인터페이스만 구현한다. 실제 연동은 사용자가 접근 방식을 정한 뒤 별도
Task Order로 진행한다.

---

## 1. 배경

v3 계획서(§7)는 "v2 완결 후 v3 Phase 2 착수, 단 EvidenceUnit 일반화는 Phase 2 착수 직전에 확인"이라고
명시했다. 지금이 그 시점이다. `EvidenceUnit`은 성경 절/PDF 문단/Obsidian block/Logos 위치를 공통으로
표현하는 모델인데, 아직 코드에 없다 (Sprint A~D의 `EvidenceCandidate`는 성경 전용 T1/T2 축만 감싼
좁은 모델 — 혼동하지 말 것).

---

## 2. 구현 범위

### 2.1 신규 모듈 — `core/evidence_unit.py`

원본 PM 지시서(NAE 통합 검색 작업명령서)의 YAML 스키마를 Pydantic으로 그대로 구현한다.

```python
from enum import Enum
from pydantic import BaseModel
from datetime import date, datetime

class CorpusType(str, Enum):
    SCRIPTURE = "scripture"
    LOGOS = "logos"
    PERSONAL_LIBRARY = "personal_library"
    OBSIDIAN = "obsidian"
    SERMON = "sermon"
    RESEARCH = "research"

class LicenseStatus(str, Enum):
    OWNED = "owned"
    LICENSED = "licensed"
    PUBLIC_DOMAIN = "public_domain"
    PERMISSION_GRANTED = "permission_granted"
    UNKNOWN = "unknown"
    RESTRICTED = "restricted"

class DisplayPolicy(str, Enum):
    SNIPPET_ONLY = "snippet_only"
    LOCAL_FULLTEXT = "local_fulltext"
    METADATA_ONLY = "metadata_only"

class ExportPolicy(str, Enum):
    CITATION_ONLY = "citation_only"
    EXCERPT_LIMITED = "excerpt_limited"
    PROHIBITED = "prohibited"

class ExtractionStatus(str, Enum):
    PASS = "pass"
    RECHUNK = "rechunk"
    REVIEW = "review"
    QUARANTINE = "quarantine"

class CitationReadiness(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class EvidenceLocation(BaseModel):
    canonical_bible_ref: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section_path: str | None = None
    paragraph_index: int | None = None
    note_heading: str | None = None
    char_start: int | None = None
    char_end: int | None = None

class EvidenceContent(BaseModel):
    text: str
    language: str
    chunk_hash: str

class EvidenceProvenance(BaseModel):
    original_uri: str
    original_file_hash: str | None = None
    imported_at: datetime
    extractor_name: str
    extractor_version: str
    ocr_applied: bool = False
    ocr_quality_score: float | None = None

class EvidenceRights(BaseModel):
    license_status: LicenseStatus
    retrieval_allowed: bool
    display_policy: DisplayPolicy
    export_policy: ExportPolicy

class EvidenceQuality(BaseModel):
    extraction_status: ExtractionStatus
    text_quality_score: float | None = None
    citation_readiness: CitationReadiness
    duplicate_group_id: str | None = None

class EvidenceAnnotations(BaseModel):
    tags: list[str] = []
    bible_refs: list[str] = []
    entities: list[str] = []
    claims: list[str] = []

class EvidenceTrust(BaseModel):
    source_tier: str    # "T1"|"T2"|"T3"|"T4" — core.dataset_registry.TrustTier 재사용
    annotation_tier: str

class EvidenceUnit(BaseModel):
    evidence_id: str
    corpus_type: CorpusType
    source_id: str
    source_version: str
    title: str | None = None
    author: str | None = None
    publication_date: date | None = None
    location: EvidenceLocation
    content: EvidenceContent
    provenance: EvidenceProvenance
    rights: EvidenceRights
    quality: EvidenceQuality
    annotations: EvidenceAnnotations
    trust: EvidenceTrust
```

`source_tier`/`annotation_tier`는 문자열로 두되, `core.dataset_registry.TrustTier`의 값과 항상 일치하게
쓴다는 걸 docstring에 명시 (Enum 자체를 import해서 재사용해도 됨 — 그게 더 안전하면 그렇게 할 것,
C1 판단에 맡김).

### 2.2 신규 모듈 — `core/evidence_adapters/base.py`

```python
from abc import ABC, abstractmethod
from core.evidence_unit import EvidenceUnit

class EvidenceSourceAdapter(ABC):
    """외부 자료(Logos/DEVONthink/Obsidian 등)를 EvidenceUnit 리스트로 변환하는 인터페이스.
    core.dataset_adapters.DatasetAdapter(Sprint B, 성경 태그 전용)와는 별개 —
    이쪽은 코퍼스 범용."""

    @abstractmethod
    def load_evidence(self, source_path: str) -> list[EvidenceUnit]:
        ...
```

### 2.3 신규 모듈 — `core/evidence_adapters/devonthink_fixture_adapter.py`

**실제 DEVONthink 접근 없음.** 테스트/데모용 JSON 픽스처(예:
`{"item_uuid": "...", "title": "...", "author": "...", "path": "x-devonthink-item://...",
"file_hash": "sha256...", "ocr_applied": true, "ocr_quality_score": 0.9, "page": 101, "text": "...",
"tags": [...], "doc_type": "commentary"}` 형태)를 읽어 `EvidenceUnit`(corpus_type=PERSONAL_LIBRARY)으로
변환하는 `DevonthinkFixtureAdapter(EvidenceSourceAdapter)`를 구현한다. 클래스/파일명에 `fixture`를 명시해
실제 연동 코드로 오인되지 않게 한다.

- `original_uri`는 픽스처의 `path`(예: `x-devonthink-item://UUID`) 값을 **문자열로 저장만** 한다 —
  실제로 그 링크를 열거나 검증하는 로직은 만들지 않는다.
- `quality.extraction_status`는 `ocr_quality_score < 0.7`이면 `"review"`, 아니면 `"pass"`로 간단히 매핑
  (정교한 규칙은 나중에).

### 2.4 이번 범위에서 제외

- 실제 DEVONthink AppleScript/SQLite/API 연동 — 사용자 결정 대기.
- Obsidian/Logos/PDF 실제 추출기 — 후속 Task Order.
- `ParallelRetriever`/검색 파이프라인에 `EvidenceUnit` 연결 — v3 Phase 4 이후.
- v2의 `EvidenceCandidate`(성경 전용)를 `EvidenceUnit`으로 통합/치환 — 지금은 두 모델이 공존한다.
  통합 시점은 v3 Phase 4에서 CUE가 결정.

---

## 3. 검증 계획

1. **단위 테스트** (`tests/test_evidence_unit.py` 신규):
   - `EvidenceUnit` 필수 필드만으로 정상 생성되는지, 선택 필드 기본값 확인
   - 각 하위 모델(`EvidenceLocation`/`EvidenceRights`/`EvidenceQuality` 등)이 독립적으로도 유효 검증되는지
2. **단위 테스트** (`tests/test_devonthink_fixture_adapter.py` 신규):
   - 픽스처 JSON → `EvidenceUnit(corpus_type=PERSONAL_LIBRARY)` 정확 변환
   - `ocr_quality_score` 낮은 경우 `extraction_status="review"`로 매핑되는지
   - `original_uri`에 픽스처의 `path` 값이 그대로 저장되는지 (열기 시도 없음)
3. Sprint A~D + 응답생성 연동 회귀 없음 확인 (137/137 유지).

---

## 4. 보고 형식

1. `core/evidence_unit.py`, `core/evidence_adapters/base.py`,
   `core/evidence_adapters/devonthink_fixture_adapter.py`, 테스트 파일 diff
2. 테스트 실행 결과 (pytest 출력 그대로 복사)
3. `core/retrieval.py`/`core/parallel_retriever.py`/`core/generation.py`/`ui/pages/chat.py` — 이번엔
   전부 미접촉이어야 함 (`git diff` 빈 diff 확인)
4. 실제 DEVONthink 연동을 시작하기 전에 사용자가 결정해야 할 사항(접근 방식 3가지 옵션) 다시 정리해
   보고서에 남길 것 — 다음 세션에서 바로 물어볼 수 있게

---

## 5. 다음 조치

사용자가 DEVONthink 접근 방식(AppleScript 브리지 / 수동 export / 기타)을 결정하면, CUE가 그에 맞는
실제 연동 Task Order를 발급한다. 그 전까지 v3 Phase 2는 이 픽스처 기반 인프라 상태로 대기.
