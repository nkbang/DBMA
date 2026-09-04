"""NotionFixtureAdapter — 테스트/데모용 JSON 픽스처를 EvidenceUnit 으로 변환.

**실제 Notion API 접근 없음.** 테스트 픽스처(JSON)로만 검증된다.
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


class NotionFixtureAdapter(EvidenceSourceAdapter):
    """Notion JSON 픽스처를 EvidenceUnit(corpus_type=NOTION) 으로 변환한다.

    실제 Notion 애플리케이션이나 API 에 접근하지 않는다.
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
            corpus_type=NOTION 인 EvidenceUnit 인스턴스 리스트.
        """
        path = Path(source_path)
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)

        units = []
        for item in items:
            units.extend(self._page_to_evidence_units(item))
        return units

    def _page_to_evidence_units(self, page: dict) -> list[EvidenceUnit]:
        """단일 Notion 페이지 항목을 EvidenceUnit 리스트로 변환한다.

        Notion 페이지는 여러 블록을 가질 수 있으므로, 각 블록마다
        EvidenceUnit 을 생성한다.
        """
        page_id = page.get("page_id", "unknown")
        page_title = page.get("title", "")
        page_url = page.get("url", "")
        properties = page.get("properties", {})
        tags = properties.get("tags", [])

        units = []
        blocks = page.get("blocks", [])
        for block in blocks:
            block_id = block.get("block_id", f"b_{page_id}")
            evidence_id = f"notion:{page_id}:{block_id}"

            unit = EvidenceUnit(
                evidence_id=evidence_id,
                corpus_type=CorpusType.NOTION,
                source_id=page_id,
                source_version="1.0",
                title=page_title,
                author=None,
                publication_date=None,
                location=EvidenceLocation(
                    section_path=block.get("type", "unknown"),
                ),
                content=EvidenceContent(
                    text=block.get("text", ""),
                    language="ko",
                ),
                provenance=EvidenceProvenance(
                    original_uri=page_url,
                    original_file_hash=None,
                    imported_at=datetime.now(),
                    extractor_name="notion_fixture",
                    extractor_version="0.1.0",
                    ocr_applied=False,
                    ocr_quality_score=None,
                ),
                rights=EvidenceRights(
                    license_status=LicenseStatus.UNKNOWN,
                    retrieval_allowed=True,
                    display_policy=DisplayPolicy.LOCAL_FULLTEXT,
                    export_policy=ExportPolicy.CITATION_ONLY,
                ),
                quality=EvidenceQuality(
                    extraction_status=ExtractionStatus.PASS,
                    text_quality_score=None,
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
            units.append(unit)
        return units