"""NAE Benchmark Loader 테스트.

확인:
    - 정상 load
    - corrupted row skip
    - validate_dataset
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from NAE.benchmark.loader import (
    load_dataset,
    validate_dataset,
    check_duplicate_benchmark_ids,
    check_empty_dataset,
)
from NAE.benchmark.schema import BenchmarkItem


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def valid_jsonl(tmp_path: Path) -> Path:
    """유효한 JSONL 파일 생성."""
    p = tmp_path / "valid.jsonl"
    records = [
        {
            "benchmark_id": "B001",
            "question": {"text": "질문 1", "language": "ko"},
            "expected": {
                "gold_tsu_ids": ["TSU-001"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-001"],
            "difficulty": "beginner",
            "review_status": "draft",
        },
        {
            "benchmark_id": "B002",
            "question": {"text": "질문 2", "language": "en"},
            "expected": {
                "gold_tsu_ids": ["TSU-002"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-002"],
            "difficulty": "beginner",
            "review_status": "draft",
        },
    ]
    with open(p, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


@pytest.fixture
def mixed_jsonl(tmp_path: Path) -> Path:
    """유효 + 불완전 record가 섞인 JSONL 파일 생성."""
    p = tmp_path / "mixed.jsonl"
    records = [
        # valid
        {
            "benchmark_id": "B001",
            "question": {"text": "질문 1", "language": "ko"},
            "expected": {
                "gold_tsu_ids": ["TSU-001"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-001"],
            "difficulty": "beginner",
            "review_status": "draft",
        },
        # invalid: missing benchmark_id
        {
            "question": {"text": "질문 2", "language": "ko"},
            "expected": {
                "gold_tsu_ids": [],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
        },
        # valid
        {
            "benchmark_id": "B003",
            "question": {"text": "질문 3", "language": "ko"},
            "expected": {
                "gold_tsu_ids": ["TSU-003"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-003"],
            "difficulty": "beginner",
            "review_status": "draft",
        },
    ]
    with open(p, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return p


@pytest.fixture
def corrupted_jsonl(tmp_path: Path) -> Path:
    """corrupted record가 섞인 JSONL 파일 생성."""
    p = tmp_path / "corrupted.jsonl"
    with open(p, "w", encoding="utf-8") as fh:
        # valid
        fh.write(json.dumps({
            "benchmark_id": "B001",
            "question": {"text": "질문 1", "language": "ko"},
            "expected": {
                "gold_tsu_ids": ["TSU-001"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-001"],
            "difficulty": "beginner",
            "review_status": "draft",
        }) + "\n")
        # corrupted: invalid JSON
        fh.write("{invalid json content\n")
        # valid
        fh.write(json.dumps({
            "benchmark_id": "B003",
            "question": {"text": "질문 3", "language": "ko"},
            "expected": {
                "gold_tsu_ids": ["TSU-003"],
                "required_concepts": [],
                "expected_scriptures": [],
                "expected_doctrine": "",
            },
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "gold_tsu_ids": ["TSU-003"],
            "difficulty": "beginner",
            "review_status": "draft",
        }) + "\n")
    return p


# ------------------------------------------------------------------
# load_dataset Tests
# ------------------------------------------------------------------

class TestLoadDataset:
    """load_dataset 함수 테스트."""

    def test_load_valid_jsonl(self, valid_jsonl):
        """유효한 JSONL 파일이 정상 로드되어야 함."""
        items = load_dataset(valid_jsonl)
        assert len(items) == 2
        assert isinstance(items[0], BenchmarkItem)
        assert items[0].benchmark_id == "B001"
        assert items[1].benchmark_id == "B002"

    def test_load_mixed_jsonl_skip_invalid(self, mixed_jsonl):
        """불완전 record는 skip되고 유효한 record만 로드되어야 함."""
        items = load_dataset(mixed_jsonl)
        assert len(items) == 2
        assert items[0].benchmark_id == "B001"
        assert items[1].benchmark_id == "B003"

    def test_load_corrupted_jsonl_skip_invalid(self, corrupted_jsonl):
        """corrupted record는 skip되고 유효한 record만 로드되어야 함."""
        items = load_dataset(corrupted_jsonl)
        assert len(items) == 2
        assert items[0].benchmark_id == "B001"
        assert items[1].benchmark_id == "B003"

    def test_load_file_not_found(self):
        """존재하지 않는 파일은 FileNotFoundError를 던져야 함."""
        with pytest.raises(FileNotFoundError):
            load_dataset("/nonexistent/path.jsonl")

    def test_load_with_skip_malformed_false(self, corrupted_jsonl):
        """skip_malformed=False이면 예외를 던져야 함."""
        with pytest.raises(ValueError):
            load_dataset(corrupted_jsonl, skip_malformed=False)

    def test_load_returns_benchmark_items(self, valid_jsonl):
        """반환된 항목은 모두 BenchmarkItem이어야 함."""
        items = load_dataset(valid_jsonl)
        for item in items:
            assert isinstance(item, BenchmarkItem)

    def test_load_preserves_all_fields(self, valid_jsonl):
        """모든 필드가 보존되어야 함."""
        items = load_dataset(valid_jsonl)
        item = items[0]
        assert item.benchmark_id == "B001"
        assert item.question.text == "질문 1"
        assert item.question.language == "ko"
        assert item.retrieval.top_k == 5
        assert item.evaluation.status == "pending"


# ------------------------------------------------------------------
# validate_dataset Tests
# ------------------------------------------------------------------

class TestValidateDataset:
    """validate_dataset 함수 테스트."""

    def test_validate_valid_jsonl(self, valid_jsonl):
        """유효한 JSONL은 모두 valid로 계산되어야 함."""
        result = validate_dataset(valid_jsonl)
        assert result["total"] == 2
        assert result["valid"] == 2
        assert result["invalid"] == 0

    def test_validate_mixed_jsonl(self, mixed_jsonl):
        """섞인 JSONL은 valid/invalid가 올바르게 계산되어야 함."""
        result = validate_dataset(mixed_jsonl)
        assert result["total"] == 3
        assert result["valid"] == 2
        assert result["invalid"] == 1

    def test_validate_returns_dict(self, valid_jsonl):
        """딕셔너리를 반환해야 함."""
        result = validate_dataset(valid_jsonl)
        assert isinstance(result, dict)
        assert "total" in result
        assert "valid" in result
        assert "invalid" in result


# ------------------------------------------------------------------
# Integration: load benchmark_v1.jsonl
# ------------------------------------------------------------------

class TestIntegration:
    """실제 benchmark_v1.jsonl 파일 통합 테스트."""

    @pytest.fixture
    def jsonl_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "NAE" / "benchmark" / "datasets" / "benchmark_v1.jsonl"

    def test_load_benchmark_v1(self, jsonl_path):
        """benchmark_v1.jsonl이 로드되어야 함."""
        assert jsonl_path.exists()
        items = load_dataset(jsonl_path)
        assert len(items) == 5
        for item in items:
            assert isinstance(item, BenchmarkItem)

    def test_benchmark_ids(self, jsonl_path):
        """모든 benchmark_id가 고유해야 함."""
        items = load_dataset(jsonl_path)
        ids = [item.benchmark_id for item in items]
        assert len(ids) == len(set(ids)), "benchmark_id가 중복됨"