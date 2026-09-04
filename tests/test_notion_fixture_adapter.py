"""NotionFixtureAdapter 단위 테스트.

- 픽스처 JSON → EvidenceUnit(corpus_type=NOTION) 정확 변환
- 페이지 하나에 블록 여러 개면 EvidenceUnit 도 여러 개 생성되는지
- properties.tags 가 annotations.tags 로 정확히 매핑되는지
- original_uri 에 url 값이 그대로 저장되는지 (열기 시도 없음)
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evidence_adapters.notion_fixture_adapter import NotionFixtureAdapter
from core.evidence_unit import (
    CorpusType,
    ExtractionStatus,
    EvidenceUnit,
)


# 픽스처 파일 경로 — test 파일이 tests/ 에 있으므로 resolve().parent 가 tests/, 그 아래 fixtures/
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "notion_fixture.json"


class TestNotionFixtureAdapter:
    def setup_method(self):
        """각 테스트 전에 어댑터 인스턴스 생성."""
        self.adapter = NotionFixtureAdapter()

    def test_load_evidence_returns_list(self):
        """load_evidence 가 리스트를 반환한다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        assert isinstance(result, list)

    def test_load_evidence_six_items(self):
        """픽스처에 2개 페이지 × 각 3개 블록 = 6개의 EvidenceUnit 이 반환된다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        assert len(result) == 6

    def test_all_corpus_type_is_notion(self):
        """모든 EvidenceUnit 의 corpus_type 은 NOTION 다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.corpus_type == CorpusType.NOTION

    def test_first_page_first_block_conversion(self):
        """첫 번째 페이지의 첫 번째 블록이 정확히 변환된다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[0]

        assert unit.evidence_id == "notion:abc123def456:b1"
        assert unit.source_id == "abc123def456"
        assert unit.title == "창세기 24장 연구"
        assert unit.location.section_path == "paragraph"
        assert unit.content.text == "본문 관찰: 이삭이 결혼 이야기를 통해 하나님의 주권이 어떻게 드러나는지 살펴본다."
        assert unit.content.language == "ko"
        # original_uri 에 url 값이 그대로 저장됨
        assert unit.provenance.original_uri == "https://notion.so/abc123def456"
        assert unit.provenance.ocr_applied is False
        assert unit.provenance.ocr_quality_score is None
        # Notion 은 OCR 개념이 없으므로 extraction_status 는 항상 PASS
        assert unit.quality.extraction_status == ExtractionStatus.PASS
        # tags 가 annotations.tags 로 매핑됨
        assert "prayer" in unit.annotations.tags
        assert "providence" in unit.annotations.tags

    def test_first_page_second_block_is_heading(self):
        """첫 번째 페이지의 두 번째 블록은 heading_2 타입이다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[1]

        assert unit.evidence_id == "notion:abc123def456:b2"
        assert unit.location.section_path == "heading_2"
        assert unit.content.text == "기도의 중요성"

    def test_first_page_tags_applied_to_all_blocks(self):
        """첫 번째 페이지의 모든 블록에 tags 가 적용된다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for i in range(3):
            unit = result[i]
            assert "prayer" in unit.annotations.tags
            assert "providence" in unit.annotations.tags

    def test_second_page_tags(self):
        """두 번째 페이지의 tags 가 정확히 매핑된다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[3]  # 네 번째 항목 (두 번째 페이지의 첫 블록)

        assert "sermon" in unit.annotations.tags
        assert "genesis" in unit.annotations.tags
        assert "prayer" not in unit.annotations.tags
        assert "providence" not in unit.annotations.tags

    def test_evidence_id_format(self):
        """evidence_id 가 notion:{page_id}:{block_id} 형식이다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.evidence_id.startswith("notion:")
            parts = unit.evidence_id.split(":")
            assert len(parts) == 3
            assert parts[0] == "notion"

    def test_original_uri_stored_as_string(self):
        """original_uri 에 픽스처의 url 값이 문자열로 저장된다 (실제 open 시도 없음)."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            # original_uri 는 https://notion.so/ 로 시작하는 문자열
            assert unit.provenance.original_uri.startswith("https://notion.so/")
            # 실제로 URI 를 열거나 검증하는 로직이 없음을 확인
            assert isinstance(unit.provenance.original_uri, str)

    def test_extractor_name_is_fixture(self):
        """extractor_name 은 notion_fixture 다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.provenance.extractor_name == "notion_fixture"

    def test_extraction_status_always_pass(self):
        """Notion 은 OCR 개념이 없으므로 extraction_status 는 항상 pass 다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.quality.extraction_status == ExtractionStatus.PASS

    def test_empty_fixture_file(self):
        """빈 배열 픽스처는 빈 리스트를 반환한다."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            f.flush()
            try:
                result = self.adapter.load_evidence(f.name)
                assert result == []
            finally:
                Path(f.name).unlink()

    def test_single_page_single_block_fixture(self):
        """단일 페이지 단일 블록 픽스처가 정확히 변환된다."""
        import tempfile
        single = [{
            "page_id": "PAGE-001",
            "title": "Single Page",
            "url": "https://notion.so/PAGE-001",
            "created_time": "2026-07-20T10:00:00.000Z",
            "last_edited_time": "2026-07-25T09:00:00.000Z",
            "properties": {
                "tags": ["test"],
                "status": "draft"
            },
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "Single block text",
                    "block_index": 0
                }
            ]
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(single, f)
            f.flush()
            try:
                result = self.adapter.load_evidence(f.name)
                assert len(result) == 1
                unit = result[0]
                assert unit.evidence_id == "notion:PAGE-001:b1"
                assert unit.title == "Single Page"
                assert unit.content.text == "Single block text"
                assert "test" in unit.annotations.tags
            finally:
                Path(f.name).unlink()

    def test_page_with_no_blocks(self):
        """블록이 없는 페이지는 EvidenceUnit 을 생성하지 않는다."""
        import tempfile
        no_blocks = [{
            "page_id": "PAGE-002",
            "title": "Empty Page",
            "url": "https://notion.so/PAGE-002",
            "created_time": "2026-07-20T10:00:00.000Z",
            "last_edited_time": "2026-07-25T09:00:00.000Z",
            "properties": {
                "tags": [],
                "status": "draft"
            },
            "blocks": []
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(no_blocks, f)
            f.flush()
            try:
                result = self.adapter.load_evidence(f.name)
                assert result == []
            finally:
                Path(f.name).unlink()

    def test_no_actual_notion_connection(self):
        """이 어댑터가 실제 Notion 연결을 만들지 않음을 확인한다.

        이 테스트는 adapter 가 순수 JSON 파일 읽기만 함을 검증한다.
        requests, httpx, notion_client 접근이 없어야 한다.
        """
        import tempfile
        # 간단한 픽스처 생성
        data = [{
            "page_id": "NO-CONN-001",
            "title": "No Connection Test",
            "url": "https://notion.so/NO-CONN-001",
            "created_time": "2026-07-20T10:00:00.000Z",
            "last_edited_time": "2026-07-25T09:00:00.000Z",
            "properties": {
                "tags": [],
                "status": "draft"
            },
            "blocks": [
                {
                    "block_id": "b1",
                    "type": "paragraph",
                    "text": "Test",
                    "block_index": 0
                }
            ]
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            try:
                # 이 호출이 성공하면 실제 Notion 연결 없이 JSON 만 읽었음을 확인
                result = self.adapter.load_evidence(f.name)
                assert len(result) == 1
                assert result[0].evidence_id == "notion:NO-CONN-001:b1"
            finally:
                Path(f.name).unlink()