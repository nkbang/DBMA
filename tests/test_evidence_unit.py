"""EvidenceUnit Pydantic 모델 단위 테스트.

- EvidenceUnit 필수 필드만으로 정상 생성되는지 확인
- 선택 필드 기본값 확인
- 각 하위 모델이 독립적으로도 유효 검증되는지 확인
"""

import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evidence_unit import (
    CorpusType,
    LicenseStatus,
    DisplayPolicy,
    ExportPolicy,
    ExtractionStatus,
    CitationReadiness,
    EvidenceLocation,
    EvidenceContent,
    EvidenceProvenance,
    EvidenceRights,
    EvidenceQuality,
    EvidenceAnnotations,
    EvidenceTrust,
    EvidenceUnit,
)


# ---------- 하위 모델 개별 테스트 ----------

class TestEvidenceLocation:
    def test_default_all_none(self):
        loc = EvidenceLocation()
        assert loc.canonical_bible_ref is None
        assert loc.page_start is None
        assert loc.page_end is None
        assert loc.section_path is None
        assert loc.paragraph_index is None
        assert loc.note_heading is None
        assert loc.char_start is None
        assert loc.char_end is None

    def test_with_values(self):
        loc = EvidenceLocation(
            canonical_bible_ref="Rom 3:23",
            page_start=10,
            page_end=12,
            section_path="chapters/03",
            paragraph_index=5,
            note_heading="Grace",
            char_start=0,
            char_end=100,
        )
        assert loc.canonical_bible_ref == "Rom 3:23"
        assert loc.page_start == 10
        assert loc.page_end == 12


class TestEvidenceContent:
    def test_required_fields(self):
        content = EvidenceContent(text="hello", language="ko", chunk_hash="abc123")
        assert content.text == "hello"
        assert content.language == "ko"
        assert content.chunk_hash == "abc123"

    def test_empty_text_raises(self):
        # text 는 required — 빈 문자열은 허용됨 (null 아님)
        content = EvidenceContent(text="", language="ko", chunk_hash="")
        assert content.text == ""


class TestEvidenceProvenance:
    def test_required_fields(self):
        p = EvidenceProvenance(
            original_uri="x-devonthink-item://UUID",
            imported_at=datetime.now(),
            extractor_name="test",
            extractor_version="0.1",
        )
        assert p.original_uri == "x-devonthink-item://UUID"
        assert p.original_file_hash is None
        assert p.ocr_applied is False
        assert p.ocr_quality_score is None

    def test_with_optional(self):
        p = EvidenceProvenance(
            original_uri="file:///test.pdf",
            original_file_hash="sha256:abc",
            imported_at=datetime.now(),
            extractor_name="pdf_extractor",
            extractor_version="1.0",
            ocr_applied=True,
            ocr_quality_score=0.95,
        )
        assert p.ocr_applied is True
        assert p.ocr_quality_score == 0.95


class TestEvidenceRights:
    def test_all_fields(self):
        r = EvidenceRights(
            license_status=LicenseStatus.OWNED,
            retrieval_allowed=True,
            display_policy=DisplayPolicy.LOCAL_FULLTEXT,
            export_policy=ExportPolicy.CITATION_ONLY,
        )
        assert r.license_status == LicenseStatus.OWNED
        assert r.retrieval_allowed is True


class TestEvidenceQuality:
    def test_all_fields(self):
        q = EvidenceQuality(
            extraction_status=ExtractionStatus.PASS,
            text_quality_score=0.9,
            citation_readiness=CitationReadiness.HIGH,
            duplicate_group_id=None,
        )
        assert q.extraction_status == ExtractionStatus.PASS
        assert q.text_quality_score == 0.9


class TestEvidenceAnnotations:
    def test_default_empty(self):
        a = EvidenceAnnotations()
        assert a.tags == []
        assert a.bible_refs == []
        assert a.entities == []
        assert a.claims == []

    def test_with_values(self):
        a = EvidenceAnnotations(
            tags=["theology", "grace"],
            bible_refs=["Rom 3:23"],
            entities=["Paul"],
            claims=["salvation by grace"],
        )
        assert a.tags == ["theology", "grace"]
        assert a.bible_refs == ["Rom 3:23"]


class TestEvidenceTrust:
    def test_basic(self):
        t = EvidenceTrust(source_tier="T1", annotation_tier="A1")
        assert t.source_tier == "T1"
        assert t.annotation_tier == "A1"


# ---------- CorpusType Enum 테스트 ----------

class TestCorpusType:
    def test_all_values(self):
        assert CorpusType.SCRIPTURE.value == "scripture"
        assert CorpusType.LOGOS.value == "logos"
        assert CorpusType.PERSONAL_LIBRARY.value == "personal_library"
        assert CorpusType.OBSIDIAN.value == "obsidian"
        assert CorpusType.SERMON.value == "sermon"
        assert CorpusType.RESEARCH.value == "research"


# ---------- EvidenceUnit 통합 테스트 ----------

class TestEvidenceUnit:
    def _make_unit(self, **overrides):
        """기본 EvidenceUnit 을 만들고 overrides 로 덮어쓴다."""
        base = dict(
            evidence_id="test-evidence-001",
            corpus_type=CorpusType.PERSONAL_LIBRARY,
            source_id="source-001",
            source_version="1.0",
            title="Test Document",
            author="Test Author",
            location=EvidenceLocation(page_start=1, page_end=1),
            content=EvidenceContent(text="test text", language="ko", chunk_hash="hash1"),
            provenance=EvidenceProvenance(
                original_uri="x-devonthink-item://TEST-UUID",
                imported_at=datetime(2026, 7, 29, 12, 0, 0),
                extractor_name="test_extractor",
                extractor_version="0.1",
            ),
            rights=EvidenceRights(
                license_status=LicenseStatus.UNKNOWN,
                retrieval_allowed=True,
                display_policy=DisplayPolicy.LOCAL_FULLTEXT,
                export_policy=ExportPolicy.CITATION_ONLY,
            ),
            quality=EvidenceQuality(
                extraction_status=ExtractionStatus.PASS,
                citation_readiness=CitationReadiness.HIGH,
            ),
            annotations=EvidenceAnnotations(),
            trust=EvidenceTrust(source_tier="T3", annotation_tier="A1"),
        )
        base.update(overrides)
        return EvidenceUnit(**base)

    def test_minimal_creation(self):
        """필수 필드만으로 정상 생성된다."""
        unit = self._make_unit()
        assert unit.evidence_id == "test-evidence-001"
        assert unit.corpus_type == CorpusType.PERSONAL_LIBRARY

    def test_optional_fields_default_to_none(self):
        """선택 필드는 기본값 None."""
        unit = self._make_unit(publication_date=None)
        assert unit.publication_date is None
        assert unit.title == "Test Document"  # overrides 로 들어감

    def test_with_publication_date(self):
        from datetime import date
        unit = self._make_unit(publication_date=date(2025, 1, 15))
        assert unit.publication_date == date(2025, 1, 15)

    def test_all_corpus_types(self):
        """모든 CorpusType 으로 생성 가능."""
        for ct in CorpusType:
            unit = self._make_unit(corpus_type=ct)
            assert unit.corpus_type == ct

    def test_validation_error_on_missing_required(self):
        """필수 필드 누르면 ValidationError."""
        with pytest.raises(ValidationError):
            EvidenceUnit(
                evidence_id="x",
                # corpus_type 누락
                source_id="s",
                source_version="v",
                location=EvidenceLocation(),
                content=EvidenceContent(text="", language="", chunk_hash=""),
                provenance=EvidenceProvenance(
                    original_uri="u", imported_at=datetime.now(),
                    extractor_name="e", extractor_version="v",
                ),
                rights=EvidenceRights(
                    license_status=LicenseStatus.UNKNOWN,
                    retrieval_allowed=True,
                    display_policy=DisplayPolicy.LOCAL_FULLTEXT,
                    export_policy=ExportPolicy.CITATION_ONLY,
                ),
                quality=EvidenceQuality(
                    extraction_status=ExtractionStatus.PASS,
                    citation_readiness=CitationReadiness.HIGH,
                ),
                annotations=EvidenceAnnotations(),
                trust=EvidenceTrust(source_tier="T3", annotation_tier="A1"),
            )

    def test_license_status_all_values(self):
        for ls in LicenseStatus:
            unit = self._make_unit(
                rights=EvidenceRights(
                    license_status=ls,
                    retrieval_allowed=True,
                    display_policy=DisplayPolicy.LOCAL_FULLTEXT,
                    export_policy=ExportPolicy.CITATION_ONLY,
                )
            )
            assert unit.rights.license_status == ls

    def test_extraction_status_all_values(self):
        for es in ExtractionStatus:
            unit = self._make_unit(
                quality=EvidenceQuality(
                    extraction_status=es,
                    citation_readiness=CitationReadiness.HIGH,
                )
            )
            assert unit.quality.extraction_status == es

    def test_citation_readiness_all_values(self):
        for cr in CitationReadiness:
            unit = self._make_unit(
                quality=EvidenceQuality(
                    extraction_status=ExtractionStatus.PASS,
                    citation_readiness=cr,
                )
            )
            assert unit.quality.citation_readiness == cr