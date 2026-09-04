"""EvidenceUnit — 성경 절/PDF 문단/Obsidian block/Logos 위치를 공통으로 표현하는 모델.

이 모듈은 v3 계획서(NAE-Unified-Research-Search-Plan-v3.md) §3의 YAML 스키마를
Pydantic으로 구현한 것이다. core.dataset_adapters.EvidenceCandidate(성경 전용 T1/T2 축)와
혼동하지 말 것 — 두 모델은 현재 공존한다.
"""

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
    NOTION = "notion"


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
    chunk_hash: str | None = None


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
    """출처 신뢰도 계층.

    source_tier/annotation_tier는 문자열로 두되, core.dataset_registry.TrustTier의 값과
    항상 일치하게 쓴다는 것을 명시. Enum 자체를 import해서 재사용하는 것이更安全.
    """

    source_tier: str  # "T1"|"T2"|"T3"|"T4" — core.dataset_registry.TrustTier 재사용
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