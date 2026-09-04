"""DevonthinkFixtureAdapter — 테스트/데모용 JSON 픽스처를 EvidenceUnit 으로 변환.

**실제 DEVONthink 접근 없음.** 테스트 픽스처(JSON)로만 검증된다.
클래스/파일명에 `fixture` 가 명시되어 실제 연동 코드로 오인되지 않는다.
"""

import json
from pathlib import Path
from datetime import datetime

from core.evidence_adapters.base import EvidenceSourceAdapter
from core.evidence_unit import (
    EvidenceUnit,
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
)


class DevonthinkFixtureAdapter(EvidenceSourceAdapter):
    """DEVONthink JSON 픽스처를 EvidenceUnit(corpus_type=PERSONAL_LIBRARY) 으로 변환한다.

    실제 DEVONthink 애플리케이션이나 데이터베이스에 접근하지 않는다.
    """

    def load_evidence(self, source_path: str) -> list[EvidenceUnit]:
        """JSON 픽스처 파일을 읽어 EvidenceUnit 리스트로 변환한다.

        Parameters
        ----------
        source_path : str
            JSON 픽스처 파일 경로.

        Returns
        -------
        list[EvidenceUnit]
            corpus_type=PERSONAL_LIBRARY 인 EvidenceUnit 인스턴스 리스트.
        """
        path = Path(source_path)
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        units = []
        for item in items:
            unit = self._item_to_evidence_unit(item)
            units.append(unit)
        return units

    def _item_to_evidence_unit(self, item: dict) -> EvidenceUnit:
        """단일 픽스처 항목을 EvidenceUnit 으로 변환한다."""
        # OCR quality 기반 extraction_status 매핑
        ocr_score = item.get("ocr_quality_score")
        if ocr_score is not None and ocr_score < 0.7:
            extraction_status = ExtractionStatus.REVIEW
        else:
            extraction_status = ExtractionStatus.PASS

        # page -> page_start/page_end 매핑
        page = item.get("page")
        page_start = page if page is not None else None
        page_end = page if page is not None else None

        # tags 에서 doc_type 분리 (doc_type 은 title 에 저장)
        tags = item.get("tags", [])
        doc_type = item.get("doc_type")
        if doc_type and doc_type not in tags:
            tags = list(tags) + [doc_type]

        return EvidenceUnit(
            evidence_id=item.get("item_uuid", "unknown"),
            corpus_type=CorpusType.PERSONAL_LIBRARY,
            source_id=item.get("item_uuid", "unknown"),
            source_version="1.0",
            title=item.get("title"),
            author=item.get("author"),
            publication_date=None,
            location=EvidenceLocation(
                page_start=page_start,
                page_end=page_end,
            ),
            content=EvidenceContent(
                text=item.get("text", ""),
                language="ko",
                chunk_hash=item.get("file_hash", ""),
            ),
            provenance=EvidenceProvenance(
                original_uri=item.get("path", ""),
                original_file_hash=item.get("file_hash"),
                imported_at=datetime.now(),
                extractor_name="devonthink_fixture",
                extractor_version="0.1.0",
                ocr_applied=item.get("ocr_applied", False),
                ocr_quality_score=item.get("ocr_quality_score"),
            ),
            rights=EvidenceRights(
                license_status=LicenseStatus.UNKNOWN,
                retrieval_allowed=True,
                display_policy=DisplayPolicy.LOCAL_FULLTEXT,
                export_policy=ExportPolicy.CITATION_ONLY,
            ),
            quality=EvidenceQuality(
                extraction_status=extraction_status,
                text_quality_score=item.get("ocr_quality_score"),
                citation_readiness=CitationReadiness.HIGH,
                duplicate_group_id=None,
            ),
            annotations=EvidenceAnnotations(
                tags=tags,
                bible_refs=[],
                entities=[],
                claims=[],
            ),
            trust=EvidenceTrust(
                source_tier="T3",
                annotation_tier="A1",
            ),
        )