"""core/evidence_model.py — Grounded Synthesis Phase 1: Evidence Data Model.

Evidence는 retrieval 결과의 명시적 내부 표현이다.
retrieval 알고리즘을 개선하지 않는다 — 단지 결과를 정규화된 형태로 전달한다.

Architecture:
    Retrieval Result (RankedCandidate)
              ↓
    Evidence Adapter / Factory
              ↓
    Evidence (this module)

이 모델은 기존 TSU record를 변경하지 않는다.
corpus_type은 adapter/resolver가 결정한다.

ABSOLUTE RULES:
- fake provenance 생성 금지
- existing metadata 손실 금지
- retrieval ranking/text 변경 금지
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceProvenance:
    """Evidence의 provenance 정보.

    실제 값만 보존 — 없는 경우 null/absent.
    가짜 provenance를 생성하지 않는다.
    """

    source_file: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_type: Optional[str] = None
    metadata_source: Optional[str] = None
    # nae_metadata가 있는 경우 그 원본 dict를 보존 (None 가능)
    nae_metadata: Optional[dict[str, Any]] = None
    # source_provenance가 있는 경우 보존 (None 가능)
    source_provenance: Optional[Any] = None
    # content_quality 구조체 보존 (None 가능)
    content_quality: Optional[dict[str, Any]] = None
    # structure 구조체 보존 (None 가능)
    structure: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class Evidence:
    """Grounded Synthesis의 기본 단위.

    retrieval 결과를 정규화된 형태로 표현한다.
    corpus_type은 adapter가 결정 — TSU-derived면 "default".

    Immutable (frozen=True): 한번 생성되면 변경 불가.
    """

    # --- Identity ---
    evidence_id: str
    corpus_type: str  # "default" | "personal" | future-proof

    # --- Content (required, before optional fields) ---
    text: str

    # --- Source identity (from TSU record) ---
    source_type: Optional[str] = None
    source_file: Optional[str] = None
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    chunk_id: Optional[str] = None

    # --- Retrieval metadata ---
    retrieval_query: Optional[str] = None
    retrieval_method: Optional[str] = None  # "bm25" | "semantic" | "hybrid" | ...
    retrieval_score: float = 0.0
    bm25_score: float = 0.0  # BM25 score from RankedCandidate
    theological_score: Optional[float] = None
    passage_score: Optional[float] = None
    final_score: float = 0.0

    # --- Provenance (preserved from source, never fabricated) ---
    provenance: EvidenceProvenance = field(default_factory=EvidenceProvenance)

    # --- Original TSU metadata (full preservation) ---
    # verse_mapping, themes, doctrine_category, baptist_theme 등
    # adapter가 원본 TSU record의 모든 필드를 보존한다.
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """frozen dataclass에서 __post_init__ 호출 허용."""
        pass

    @property
    def is_default_corpus(self) -> bool:
        """corpus_type이 default인지 확인 (read-only)."""
        return self.corpus_type == "default"

    @property
    def has_provenance(self) -> bool:
        """실제 provenance 데이터가 있는지 확인 (fake 아님)."""
        p = self.provenance
        return bool(p.source_file or p.document_id or p.chunk_id)

    def to_dict(self) -> dict[str, Any]:
        """Evidence를 dict로 직렬화 (testing/debugging용)."""
        return {
            "evidence_id": self.evidence_id,
            "corpus_type": self.corpus_type,
            "source_type": self.source_type,
            "source_file": self.source_file,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "chunk_id": self.chunk_id,
            "text": self.text[:500] if len(self.text) > 500 else self.text,
            "retrieval_query": self.retrieval_query,
            "retrieval_method": self.retrieval_method,
            "retrieval_score": self.retrieval_score,
            "bm25_score": self.bm25_score,
            "theological_score": self.theological_score,
            "passage_score": self.passage_score,
            "final_score": self.final_score,
            "provenance": {
                "source_file": self.provenance.source_file,
                "document_id": self.provenance.document_id,
                "chunk_id": self.provenance.chunk_id,
                "source_type": self.provenance.source_type,
                "metadata_source": self.provenance.metadata_source,
                "nae_metadata": self.provenance.nae_metadata,
                "source_provenance": self.provenance.source_provenance,
                "content_quality": self.provenance.content_quality,
                "structure": self.provenance.structure,
            },
            "raw_metadata_keys": list(self.raw_metadata.keys()),
        }


# CorpusType 상수 — adapter가 이 값을 사용한다.
CORPUS_DEFAULT = "default"
CORPUS_PERSONAL = "personal"
