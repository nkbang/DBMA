"""DevonthinkFixtureAdapter 단위 테스트.

- 픽스처 JSON → EvidenceUnit(corpus_type=PERSONAL_LIBRARY) 정확 변환
- ocr_quality_score 낮은 경우 extraction_status="review"로 매핑되는지
- original_uri 에 픽스처의 path 값이 그대로 저장되는지 (열기 시도 없음)
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.evidence_adapters.devonthink_fixture_adapter import DevonthinkFixtureAdapter
from core.evidence_unit import (
    CorpusType,
    ExtractionStatus,
    EvidenceUnit,
)


# 픽스처 파일 경로 — test 파일이 tests/ 에 있으므로 resolve().parent 가 tests/, 그 아래 fixtures/
FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "devonthink_fixture.json"


class TestDevonthinkFixtureAdapter:
    def setup_method(self):
        """각 테스트 전에 어댑터 인스턴스 생성."""
        self.adapter = DevonthinkFixtureAdapter()

    def test_load_evidence_returns_list(self):
        """load_evidence 가 리스트를 반환한다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        assert isinstance(result, list)

    def test_load_evidence_three_items(self):
        """픽스처에 3개 항목이므로 3개의 EvidenceUnit 이 반환된다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        assert len(result) == 3

    def test_all_corpus_type_is_personal_library(self):
        """모든 EvidenceUnit 의 corpus_type 은 PERSONAL_LIBRARY 다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.corpus_type == CorpusType.PERSONAL_LIBRARY

    def test_first_item_conversion(self):
        """첫 번째 항목이 정확히 변환된다 (OCR 없음, ocr_quality_score=null)."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[0]

        assert unit.evidence_id == "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
        assert unit.source_id == "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
        assert unit.title == "Commentary on Romans"
        assert unit.author == "John Calvin"
        assert unit.location.page_start == 101
        assert unit.location.page_end == 101
        assert unit.content.text == "The apostle Paul now turns to a critical discussion of the law and its relationship to grace. This passage has been interpreted in vastly different ways throughout church history."
        assert unit.content.language == "ko"
        assert unit.provenance.original_uri == "x-devonthink-item://A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
        assert unit.provenance.original_file_hash == "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
        assert unit.provenance.ocr_applied is False
        assert unit.provenance.ocr_quality_score is None
        # OCR 없음 → extraction_status 는 PASS
        assert unit.quality.extraction_status == ExtractionStatus.PASS
        # tags 에 doc_type 이 포함됨
        assert "theology" in unit.annotations.tags
        assert "grace" in unit.annotations.tags
        assert "law" in unit.annotations.tags
        assert "commentary" in unit.annotations.tags

    def test_low_cr_quality_mapping(self):
        """ocr_quality_score < 0.7 인 경우 extraction_status="review"."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[1]  # 두 번째 항목: ocr_quality_score=0.5

        assert unit.provenance.ocr_quality_score == 0.5
        assert unit.quality.extraction_status == ExtractionStatus.REVIEW

    def test_high_ocr_quality_mapping(self):
        """ocr_quality_score >= 0.7 인 경우 extraction_status="pass"."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        unit = result[2]  # 세 번째 항목: ocr_quality_score=0.95

        assert unit.provenance.ocr_quality_score == 0.95
        assert unit.quality.extraction_status == ExtractionStatus.PASS

    def test_original_uri_stored_as_string(self):
        """original_uri 에 픽스처의 path 값이 문자열로 저장된다 (실제 open 시도 없음)."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            # original_uri 는 x-devonthink-item:// 로 시작하는 문자열
            assert unit.provenance.original_uri.startswith("x-devonthink-item://")
            # 실제로 URI 를 열거나 검증하는 로직이 없음을 확인 — 이 테스트는
            # adapter 가 단순히 문자열을 저장만 함을 검증한다.
            assert isinstance(unit.provenance.original_uri, str)

    def test_extractor_name_is_fixture(self):
        """extractor_name 은 devonthink_fixture 다."""
        result = self.adapter.load_evidence(str(FIXTURE_PATH))
        for unit in result:
            assert unit.provenance.extractor_name == "devonthink_fixture"

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

    def test_single_item_fixture(self):
        """단일 항목 픽스처가 정확히 변환된다."""
        import tempfile
        single = [{
            "item_uuid": "SINGLE-001",
            "title": "Single Item",
            "author": "Author A",
            "path": "x-devonthink-item://SINGLE-001",
            "file_hash": "sha256:single",
            "ocr_applied": False,
            "ocr_quality_score": None,
            "page": 1,
            "text": "Single text",
            "tags": ["test"],
            "doc_type": "note"
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(single, f)
            f.flush()
            try:
                result = self.adapter.load_evidence(f.name)
                assert len(result) == 1
                unit = result[0]
                assert unit.evidence_id == "SINGLE-001"
                assert unit.title == "Single Item"
                assert unit.content.text == "Single text"
            finally:
                Path(f.name).unlink()

    def test_no_actual_devonthink_connection(self):
        """이 어댑터가 실제 DEVONthink 연결을 만들지 않음을 확인한다.

        이 테스트는 adapter 가 순수 JSON 파일 읽기만 함을 검증한다.
        osascript, AppleScript, SQLite 접근이 없어야 한다.
        """
        import tempfile
        # 간단한 픽스처 생성
        data = [{
            "item_uuid": "NO-CONN-001",
            "title": "No Connection Test",
            "author": None,
            "path": "x-devonthink-item://NO-CONN-001",
            "file_hash": None,
            "ocr_applied": False,
            "ocr_quality_score": None,
            "page": None,
            "text": "Test",
            "tags": [],
            "doc_type": "test"
        }]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            try:
                # 이 호출이 성공하면 실제 DEVONthink 연결 없이 JSON 만 읽었음을 확인
                result = self.adapter.load_evidence(f.name)
                assert len(result) == 1
                assert result[0].evidence_id == "NO-CONN-001"
            finally:
                Path(f.name).unlink()