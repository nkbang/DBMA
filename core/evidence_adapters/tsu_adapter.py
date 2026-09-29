"""core/evidence_adapters/tsu_adapter.py — TSU-derived Evidence Adapter.

Phase 1: Converts existing retrieval results (RankedCandidate) into
Evidence objects without modifying any production data.

Architecture boundary:
    RankedCandidate (existing retrieval result)
              ↓
    TSUEvidenceAdapter / RankedCandidateEvidenceAdapter (this module)
              ↓
    Evidence (core.evidence_model)

ABSOLUTE RULES:
- TSU record mutation 금지
- provenance fabrication 금지
- ranking/text 변경 금지
- production corpus mutation = 0
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Optional

from core.evidence_model import (
    CORPUS_DEFAULT,
    CORPUS_PERSONAL,
    Evidence,
    EvidenceProvenance,
)
from core.config import DEFAULT_REGISTRY_PATH
from core.retrieval import RankedCandidate

logger = logging.getLogger(__name__)


class TSUEvidenceAdapter:
    """TSU retrieval result → Evidence 변환 adapter.

    corpus_type = "default"를 TSU-derived evidence에 부여한다.
    기존 metadata를 최대한 보존하고, 없는 경우 null로 유지한다.
    """

    def __init__(self, corpus_type: str = CORPUS_DEFAULT) -> None:
        self.corpus_type = corpus_type

    def adapt(self, tsu_record: dict[str, Any], query: Optional[str] = None) -> Evidence:
        """단일 TSU record를 Evidence로 변환.

        Parameters
        ----------
        tsu_record : dict
            TSU dataset의 단일 record (json.loads 한 줄).
            core/retrieval.py::RankedCandidate.metadata 에 해당하는 필드도 포함 가능.
        query : str or None
            이 evidence가 retrieval된 query (optional, preservation용).

        Returns
        -------
        Evidence
            corpus_type=self.corpus_type 인 Evidence 객체.
            provenance는 실제 값만 보존 — fake 생성 없음.
        """
        # --- Identity ---
        tsu_id = tsu_record.get("tsu_id") or ""
        evidence_id = self._resolve_evidence_id(tsu_id, tsu_record)

        # --- Source identity (from TSU record) ---
        source_file = tsu_record.get("source_file")
        document_id = tsu_record.get("document_id")
        chunk_id = tsu_record.get("chunk_id")
        source_type = tsu_record.get("source_type")
        document_title = tsu_record.get("title")

        # --- Content ---
        text = tsu_record.get("content", "")

        # --- Provenance (real values only) ---
        provenance = EvidenceProvenance(
            source_file=source_file,
            document_id=document_id,
            chunk_id=chunk_id,
            source_type=source_type,
            metadata_source=tsu_record.get("metadata_source"),
            nae_metadata=tsu_record.get("nae_metadata"),
            source_provenance=tsu_record.get("source_provenance"),
            content_quality=tsu_record.get("content_quality"),
            structure=tsu_record.get("structure"),
        )

        # --- Raw metadata preservation (full TSU record) ---
        raw_metadata = dict(tsu_record)

        return Evidence(
            evidence_id=evidence_id,
            corpus_type=self.corpus_type,
            source_type=source_type,
            source_file=source_file,
            document_id=document_id,
            document_title=document_title,
            chunk_id=chunk_id,
            text=text,
            retrieval_query=query,
            retrieval_method="tsu",
            # Scores are preserved from RankedCandidate when available.
            # For raw TSU records (no retrieval scores), defaults remain 0.0/None.
            retrieval_score=0.0,
            theological_score=None,
            passage_score=None,
            final_score=0.0,
            provenance=provenance,
            raw_metadata=raw_metadata,
        )

    @staticmethod
    def _resolve_evidence_id(tsu_id: str, tsu_record: dict[str, Any]) -> str:
        """Resolve a stable, non-empty evidence_id from TSU record.

        Priority:
            1. tsu_id (if non-empty)
            2. source_file + document_id + chunk_id hash (immutable combination)
            3. document_id alone (if available)
            4. chunk_id alone (last resort)

        Never returns empty string.
        """
        if tsu_id:
            return tsu_id

        # Fallback: use immutable source identity fields
        source_file = tsu_record.get("source_file") or ""
        document_id = tsu_record.get("document_id") or ""
        chunk_id = tsu_record.get("chunk_id") or ""

        if source_file and document_id and chunk_id:
            # Hash the combination for stable, non-empty identity
            raw = f"{source_file}|{document_id}|{chunk_id}"
            return f"evid:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

        if document_id:
            return document_id

        if chunk_id:
            return chunk_id

        # Last resort: hash empty fields (never returns empty)
        raw = f"|{document_id}|{chunk_id}"
        return f"evid:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def adapt_batch(
        self,
        tsu_records: list[dict[str, Any]],
        query: Optional[str] = None,
    ) -> list[Evidence]:
        """여러 TSU record를 Evidence 리스트로 변환.

        Parameters
        ----------
        tsu_records : list[dict]
            TSU dataset의 record 리스트.
        query : str or None
            이 batch가 retrieval된 query.

        Returns
        -------
        list[Evidence]
            각 record에 대한 Evidence 객체 리스트.
            순서는 원본과 동일하게 유지된다 (ranking 변경 금지).
        """
        return [self.adapt(record, query) for record in tsu_records]


class TSUEvidenceFactory:
    """Evidence 생성을 위한 factory 인터페이스.

    corpus_type을 결정하는 resolver 역할을 한다.
    registry(documents.json)의 corpus_membership 필드를 조회하여
    personal/default를 구분한다.
    """

    def __init__(self, document_id: Optional[str] = None) -> None:
        self._corpus_type = TSUEvidenceFactory.resolve_corpus_type(
            source_file=None, document_id=document_id
        )
        self._default_adapter = TSUEvidenceAdapter(corpus_type=self._corpus_type)

    def create_from_tsu(
        self,
        tsu_record: dict[str, Any],
        query: Optional[str] = None,
    ) -> Evidence:
        """TSU record에서 Evidence 생성 (registry corpus_membership 기준)."""
        return self._default_adapter.adapt(tsu_record, query)

    def create_from_tsu_batch(
        self,
        tsu_records: list[dict[str, Any]],
        query: Optional[str] = None,
    ) -> list[Evidence]:
        """TSU record batch에서 Evidence 리스트 생성."""
        return self._default_adapter.adapt_batch(tsu_records, query)

    @staticmethod
    def resolve_corpus_type(
        source_file: Optional[str] = None, document_id: Optional[str] = None
    ) -> str:
        """registry 기반 corpus_type 결정.

        document_id를 documents.json registry에서 조회하여
        corpus_membership 필드의 값을 반환한다.
        registry가 없거나 필드가 없는 경우 fail-safe로 CORPUS_DEFAULT를 반환.

        Parameters
        ----------
        source_file : str or None
            원본 파일 경로 (하위 호환성 위해 유지).
        document_id : str or None
            registry 조회용 document_id.

        Returns
        -------
        str
            "personal" | "default"
        """
        if not document_id:
            return CORPUS_DEFAULT

        # Use authoritative DEFAULT_REGISTRY_PATH from core.config
        abs_path = os.path.abspath(DEFAULT_REGISTRY_PATH)
        if not os.path.isfile(abs_path):
            return CORPUS_DEFAULT

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
            doc_record = registry.get("documents", {}).get(document_id)
            if doc_record is None:
                return CORPUS_DEFAULT
            membership = doc_record.get("corpus_membership")
            if membership in (CORPUS_PERSONAL, CORPUS_DEFAULT):
                return membership
        except (json.JSONDecodeError, OSError):
            pass

        # fail-safe: registry가 없거나 필드가 없으면 기존 동작 유지
        return CORPUS_DEFAULT


class RankedCandidateEvidenceAdapter:
    """RankedCandidate → Evidence 변환 adapter.

    retrieval pipeline에서 생성된 RankedCandidate의 score와 metadata를
    Evidence에 보존한다. ranking order는 변경하지 않는다.

    Architecture:
        RankedCandidate (core.retrieval)
                  ↓
        RankedCandidateEvidenceAdapter (this class)
                  ↓
        Evidence (core.evidence_model)
    """

    def __init__(
        self,
        corpus_type: str = CORPUS_DEFAULT,
        document_id: Optional[str] = None,
    ) -> None:
        # explicit corpus_type이 있으면 그대로 사용 (하위 호환)
        # 없으면 registry에서 document_id로 조회
        if corpus_type != CORPUS_DEFAULT or document_id is None:
            self.corpus_type = corpus_type
        else:
            self.corpus_type = TSUEvidenceFactory.resolve_corpus_type(
                source_file=None, document_id=document_id
            )

    def adapt(self, candidate: RankedCandidate) -> Evidence:
        """단일 RankedCandidate를 Evidence로 변환.

        Parameters
        ----------
        candidate : RankedCandidate
            retrieval pipeline에서 생성된 RankedCandidate 객체.
            score는 이미 계산되어 있어야 한다.

        Returns
        -------
        Evidence
            corpus_type=self.corpus_type 인 Evidence 객체.
            모든 score가 원본 RankedCandidate에서 보존된다.
        """
        # --- Identity ---
        tsu_id = candidate.tsu_id or ""
        evidence_id = self._resolve_evidence_id(tsu_id, candidate)

        # --- Source identity (from RankedCandidate.metadata) ---
        metadata = candidate.metadata
        source_file = metadata.get("source_file")
        document_id = metadata.get("document_id")
        chunk_id = metadata.get("chunk_id")
        source_type = metadata.get("source_type")
        document_title = metadata.get("title")

        # --- corpus_type: per-candidate registry lookup (AD-01/AD-02) ---
        corpus_type = TSUEvidenceFactory.resolve_corpus_type(
            source_file=source_file, document_id=document_id
        )

        # --- Content ---
        text = candidate.content or ""

        # --- Provenance (real values only) ---
        provenance = EvidenceProvenance(
            source_file=source_file,
            document_id=document_id,
            chunk_id=chunk_id,
            source_type=source_type,
            metadata_source=metadata.get("metadata_source"),
            nae_metadata=metadata.get("nae_metadata"),
            source_provenance=metadata.get("source_provenance"),
            content_quality=metadata.get("content_quality"),
            structure=metadata.get("structure"),
        )

        # --- Raw metadata preservation (full TSU record from metadata) ---
        raw_metadata = dict(metadata)

        return Evidence(
            evidence_id=evidence_id,
            corpus_type=corpus_type,
            source_type=source_type,
            source_file=source_file,
            document_id=document_id,
            document_title=document_title,
            chunk_id=chunk_id,
            text=text,
            retrieval_query=None,  # will be set by caller if needed
            retrieval_method="hybrid",
            # Score preservation — all RankedCandidate scores are preserved
            retrieval_score=candidate.vector_score,
            bm25_score=candidate.bm25_score,
            theological_score=candidate.theological_score if candidate.theological_score != 0.0 else None,
            passage_score=candidate.passage_score if candidate.passage_score != 0.0 else None,
            final_score=candidate.final_score,
            provenance=provenance,
            raw_metadata=raw_metadata,
        )

    def adapt_batch(self, candidates: list[RankedCandidate]) -> list[Evidence]:
        """여러 RankedCandidate를 Evidence 리스트로 변환.

        Parameters
        ----------
        candidates : list[RankedCandidate]
            retrieval pipeline에서 생성된 RankedCandidate 리스트.
            순서가 ranking order이다.

        Returns
        -------
        list[Evidence]
            각 candidate에 대한 Evidence 객체 리스트.
            순서는 원본과 동일하게 유지된다 (ranking 변경 금지).
        """
        return [self.adapt(candidate) for candidate in candidates]

    @staticmethod
    def _resolve_evidence_id(tsu_id: str, candidate: RankedCandidate) -> str:
        """Resolve a stable, non-empty evidence_id from RankedCandidate.

        Priority:
            1. tsu_id (if non-empty)
            2. source_file + document_id + chunk_id hash (immutable combination)
            3. document_id alone (if available)
            4. chunk_id alone (last resort)

        Never returns empty string.
        """
        if tsu_id:
            return tsu_id

        metadata = candidate.metadata
        source_file = metadata.get("source_file") or ""
        document_id = metadata.get("document_id") or ""
        chunk_id = metadata.get("chunk_id") or ""

        if source_file and document_id and chunk_id:
            raw = f"{source_file}|{document_id}|{chunk_id}"
            return f"evid:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

        if document_id:
            return document_id

        if chunk_id:
            return chunk_id

        raw = f"|{document_id}|{chunk_id}"
        return f"evid:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
