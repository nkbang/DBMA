"""NAE Benchmark Schema 테스트.

확인:
    - valid JSONL 구조
    - required fields 존재
    - 직렬화/역직렬화
    - validation 로직
"""

import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from NAE.benchmark.schema import (
    BenchmarkItem,
    BenchmarkQuestion,
    BenchmarkExpected,
    BenchmarkRetrieval,
    BenchmarkEvaluation,
    BenchmarkMetadata,
    SCHEMA_EXAMPLE,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def valid_item() -> BenchmarkItem:
    return BenchmarkItem(
        benchmark_id="B001",
        question=BenchmarkQuestion(text="테스트 질문", language="ko"),
        expected=BenchmarkExpected(
            required_concepts=["속죄"],
            expected_scriptures=["로마서 3:25"],
            expected_doctrine="대리 속죄설",
        ),
        retrieval=BenchmarkRetrieval(top_k=5),
    )


@pytest.fixture
def valid_dict() -> dict:
    return {
        "benchmark_id": "B001",
        "question": {"text": "테스트 질문", "language": "ko"},
        "expected": {
            "required_concepts": ["속죄"],
            "expected_scriptures": ["로마서 3:25"],
            "expected_doctrine": "대리 속죄설",
        },
        "retrieval": {"top_k": 5},
        "evaluation": {"status": "pending"},
        "metadata": {"created_version": "1.0", "source": "test"},
    }


# ------------------------------------------------------------------
# Schema Structure Tests
# ------------------------------------------------------------------

class TestSchemaStructure:
    """스키마 구조 테스트."""

    def test_schema_example_has_required_keys(self):
        """SCHEMA_EXAMPLE에 필수 키가 모두 있어야 함."""
        for key in ["benchmark_id", "question", "expected", "retrieval", "evaluation", "metadata"]:
            assert key in SCHEMA_EXAMPLE, f"SCHEMA_EXAMPLE에 '{key}' 키가 없음"

    def test_question_required_fields(self):
        """question에 text, language가 있어야 함."""
        for key in ["text", "language"]:
            assert key in SCHEMA_EXAMPLE["question"], f"question에 '{key}'가 없음"

    def test_expected_required_fields(self):
        """expected에 required_concepts, expected_scriptures, expected_doctrine가 있어야 함."""
        for key in ["required_concepts", "expected_scriptures", "expected_doctrine"]:
            assert key in SCHEMA_EXAMPLE["expected"], f"expected에 '{key}'가 없음"

    def test_retrieval_required_fields(self):
        """retrieval에 top_k가 있어야 함."""
        assert "top_k" in SCHEMA_EXAMPLE["retrieval"]

    def test_evaluation_required_fields(self):
        """evaluation에 status가 있어야 함."""
        assert "status" in SCHEMA_EXAMPLE["evaluation"]


# ------------------------------------------------------------------
# Data Class Tests
# ------------------------------------------------------------------

class TestDataClass:
    """BenchmarkItem 데이터 클래스 테스트."""

    def test_default_values(self):
        """기본값이 올바르게 설정되어야 함."""
        item = BenchmarkItem()
        assert item.question.language == "ko"
        assert item.retrieval.top_k == 5
        assert item.evaluation.status == "pending"
        assert item.retrieved_tsu_ids == []
        assert item.relevant_tsu_ids == []

    def test_from_dict(self, valid_dict):
        """딕셔너리에서 역직렬화되어야 함."""
        item = BenchmarkItem.from_dict(valid_dict)
        assert item.benchmark_id == "B001"
        assert item.question.text == "테스트 질문"
        assert item.question.language == "ko"
        assert item.expected.required_concepts == ["속죄"]
        assert item.retrieval.top_k == 5

    def test_to_dict(self, valid_item):
        """딕셔너리로 직렬화되어야 함."""
        d = valid_item.to_dict()
        assert d["benchmark_id"] == "B001"
        assert d["question"]["text"] == "테스트 질문"
        assert isinstance(d, dict)

    def test_roundtrip(self, valid_dict):
        """직렬화 → 역직렬화가 원본과 동일해야 함."""
        item = BenchmarkItem.from_dict(valid_dict)
        d2 = item.to_dict()
        assert d2["benchmark_id"] == valid_dict["benchmark_id"]
        assert d2["question"]["text"] == valid_dict["question"]["text"]

    def test_to_json(self, valid_item):
        """JSON 문자열로 직렬화되어야 함."""
        json_str = valid_item.to_json()
        parsed = json.loads(json_str)
        assert parsed["benchmark_id"] == "B001"

    def test_from_json(self, valid_item):
        """JSON 문자열에서 역직렬화되어야 함."""
        json_str = valid_item.to_json()
        item2 = BenchmarkItem.from_json(json_str)
        assert item2.benchmark_id == valid_item.benchmark_id
        assert item2.question.text == valid_item.question.text


# ------------------------------------------------------------------
# Validation Tests
# ------------------------------------------------------------------

class TestValidation:
    """스키마 검증 테스트."""

    def test_valid_item_no_errors(self, valid_item):
        """유효한 항목은 에러가 없어야 함."""
        errors = valid_item.validate()
        assert errors == []

    def test_missing_benchmark_id(self):
        """benchmark_id가 비어있으면 에러."""
        item = BenchmarkItem(benchmark_id="", question=BenchmarkQuestion(text="질문"))
        errors = item.validate()
        assert any("benchmark_id" in e for e in errors)

    def test_missing_question_text(self):
        """question.text가 비어있으면 에러."""
        item = BenchmarkItem(benchmark_id="B001", question=BenchmarkQuestion(text=""))
        errors = item.validate()
        assert any("question.text" in e for e in errors)

    def test_invalid_language(self):
        """language가 ko/en이 아니면 에러."""
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="질문", language="jp"),
        )
        errors = item.validate()
        assert any("language" in e for e in errors)

    def test_invalid_top_k(self):
        """top_k가 1보다 작으면 에러."""
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="질문"),
            retrieval=BenchmarkRetrieval(top_k=0),
        )
        errors = item.validate()
        assert any("top_k" in e for e in errors)

    def test_whitespace_question_text(self):
        """question.text가 공백만 있으면 에러."""
        item = BenchmarkItem(benchmark_id="B001", question=BenchmarkQuestion(text="   "))
        errors = item.validate()
        assert any("question.text" in e for e in errors)


# ------------------------------------------------------------------
# JSONL File Tests
# ------------------------------------------------------------------

class TestJSONLFile:
    """benchmark_v1.jsonl 파일 테스트."""

    @pytest.fixture
    def jsonl_path(self) -> Path:
        return Path(__file__).resolve().parent.parent / "NAE" / "benchmark" / "datasets" / "benchmark_v1.jsonl"

    def test_file_exists(self, jsonl_path):
        """benchmark_v1.jsonl 파일이 존재해야 함."""
        assert jsonl_path.exists(), f"benchmark_v1.jsonl이 없음: {jsonl_path}"

    def test_all_lines_are_valid_json(self, jsonl_path):
        """모든 줄이 유효한 JSON이어야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as exc:
                    pytest.fail(f"line {lineno}이(가) 유효하지 않은 JSON: {exc}")

    def test_all_records_have_required_fields(self, jsonl_path):
        """모든 레코드가 필수 필드를 가져야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                for key in ["benchmark_id", "question", "expected", "retrieval", "evaluation", "metadata"]:
                    assert key in data, f"line {lineno}에 '{key}' 키가 없음"

    def test_all_records_pass_validation(self, jsonl_path):
        """모든 레코드가 검증을 통과해야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                item = BenchmarkItem.from_dict(data)
                errors = item.validate()
                assert errors == [], f"line {lineno} 검증 실패: {errors}"

    def test_has_benchmark_id(self, jsonl_path):
        """모든 레코드가 benchmark_id를 가져야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                assert data.get("benchmark_id"), f"line {lineno}에 benchmark_id가 없음"

    def test_has_question_text(self, jsonl_path):
        """모든 레코드가 question.text를 가져야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                assert data.get("question", {}).get("text"), f"line {lineno}에 question.text가 없음"

    def test_has_top_k(self, jsonl_path):
        """모든 레코드가 retrieval.top_k를 가져야 함."""
        with open(jsonl_path, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                assert data.get("retrieval", {}).get("top_k"), f"line {lineno}에 top_k가 없음"