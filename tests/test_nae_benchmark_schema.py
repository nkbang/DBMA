"""NAE Benchmark Schema Tests — C1-TASK-ORDER-037 확장 스키마 검증."""

import json
import pytest
from NAE.benchmark.schema import (
    BenchmarkItem,
    BenchmarkQuestion,
    BenchmarkExpected,
    BenchmarkRetrieval,
    BenchmarkEvaluation,
    BenchmarkMetadata,
    QUESTION_TYPES,
    DIFFICULTY_LEVELS,
    REVIEW_STATUSES,
)


# ------------------------------------------------------------------
# Schema Constants
# ------------------------------------------------------------------

class TestSchemaConstants:
    def test_question_types_not_empty(self):
        assert len(QUESTION_TYPES) > 0

    def test_difficulty_levels_not_empty(self):
        assert len(DIFFICULTY_LEVELS) > 0

    def test_review_statuses_not_empty(self):
        assert len(REVIEW_STATUSES) > 0


# ------------------------------------------------------------------
# BenchmarkItem — Creation
# ------------------------------------------------------------------

class TestBenchmarkItemCreation:
    def test_default_creation(self):
        item = BenchmarkItem()
        assert item.benchmark_id == ""
        assert isinstance(item.question, BenchmarkQuestion)
        assert isinstance(item.expected, BenchmarkExpected)
        assert isinstance(item.retrieval, BenchmarkRetrieval)
        assert isinstance(item.evaluation, BenchmarkEvaluation)
        assert isinstance(item.metadata, BenchmarkMetadata)

    def test_full_creation(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트 질문", language="ko", question_type="concept"),
            expected=BenchmarkExpected(
                gold_tsu_ids=["TSU-001", "TSU-002"],
                required_concepts=["개념1"],
                expected_scriptures=["시편 23:1"],
                expected_doctrine="교리1",
            ),
            retrieval=BenchmarkRetrieval(top_k=5),
            difficulty="intermediate",
            review_status="draft",
        )
        assert item.benchmark_id == "B001"
        assert item.question.text == "테스트 질문"
        assert item.question.language == "ko"
        assert item.question.question_type == "concept"
        assert item.expected.gold_tsu_ids == ["TSU-001", "TSU-002"]
        assert item.difficulty == "intermediate"
        assert item.review_status == "draft"


# ------------------------------------------------------------------
# BenchmarkItem — Serialization
# ------------------------------------------------------------------

class TestBenchmarkItemSerialization:
    def test_to_dict(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            difficulty="beginner",
            review_status="approved",
        )
        d = item.to_dict()
        assert d["benchmark_id"] == "B001"
        assert d["question"]["text"] == "테스트"
        assert d["expected"]["gold_tsu_ids"] == ["TSU-001"]
        assert d["difficulty"] == "beginner"
        assert d["review_status"] == "approved"

    def test_to_json(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
        )
        j = item.to_json()
        assert isinstance(j, str)
        d = json.loads(j)
        assert d["benchmark_id"] == "B001"

    def test_from_dict(self):
        data = {
            "benchmark_id": "B001",
            "question": {"text": "테스트", "language": "ko", "question_type": "concept"},
            "expected": {"gold_tsu_ids": ["TSU-001"]},
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
            "difficulty": "intermediate",
            "review_status": "draft",
        }
        item = BenchmarkItem.from_dict(data)
        assert item.benchmark_id == "B001"
        assert item.question.text == "테스트"
        assert item.expected.gold_tsu_ids == ["TSU-001"]
        assert item.difficulty == "intermediate"
        assert item.review_status == "draft"

    def test_from_json(self):
        j = json.dumps({
            "benchmark_id": "B001",
            "question": {"text": "테스트", "language": "ko"},
            "expected": {"gold_tsu_ids": ["TSU-001"]},
            "retrieval": {"top_k": 5},
            "evaluation": {"status": "pending"},
            "metadata": {"created_version": "1.0", "source": "test"},
        })
        item = BenchmarkItem.from_json(j)
        assert item.benchmark_id == "B001"


# ------------------------------------------------------------------
# BenchmarkItem — Validation
# ------------------------------------------------------------------

class TestBenchmarkItemValidation:
    def test_valid_item(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트 질문", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            gold_tsu_ids=["TSU-001"],
        )
        assert item.validate() == []

    def test_missing_benchmark_id(self):
        item = BenchmarkItem(
            benchmark_id="",
            question=BenchmarkQuestion(text="테스트 질문", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        errors = item.validate()
        assert any("benchmark_id" in e for e in errors)

    def test_missing_question_text(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        errors = item.validate()
        assert any("question.text" in e for e in errors)

    def test_invalid_language(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ja"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        errors = item.validate()
        assert any("language" in e for e in errors)

    def test_invalid_question_type(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko", question_type="invalid_type"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        errors = item.validate()
        assert any("question_type" in e for e in errors)

    def test_invalid_top_k(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=0),
        )
        errors = item.validate()
        assert any("top_k" in e for e in errors)

    def test_invalid_difficulty(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            difficulty="invalid_level",
        )
        errors = item.validate()
        assert any("difficulty" in e for e in errors)

    def test_invalid_review_status(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            review_status="invalid_status",
        )
        errors = item.validate()
        assert any("review_status" in e for e in errors)

    def test_duplicate_gold_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001", "TSU-001"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            gold_tsu_ids=["TSU-001", "TSU-001"],
        )
        errors = item.validate()
        assert any("duplicates" in e for e in errors)

    def test_valid_question_type_values(self):
        for qt in QUESTION_TYPES:
            item = BenchmarkItem(
                benchmark_id="B001",
                question=BenchmarkQuestion(text="테스트", language="ko", question_type=qt),
                expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
                retrieval=BenchmarkRetrieval(top_k=5),
                gold_tsu_ids=["TSU-001"],
            )
            assert item.validate() == []

    def test_valid_difficulty_values(self):
        for dl in DIFFICULTY_LEVELS:
            item = BenchmarkItem(
                benchmark_id="B001",
                question=BenchmarkQuestion(text="테스트", language="ko"),
                expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
                retrieval=BenchmarkRetrieval(top_k=5),
                difficulty=dl,
            )
            assert item.validate() == []

    def test_valid_review_status_values(self):
        for rs in REVIEW_STATUSES:
            item = BenchmarkItem(
                benchmark_id="B001",
                question=BenchmarkQuestion(text="테스트", language="ko"),
                expected=BenchmarkExpected(gold_tsu_ids=["TSU-001"]),
                retrieval=BenchmarkRetrieval(top_k=5),
                gold_tsu_ids=["TSU-001"],
                review_status=rs,
            )
            assert item.validate() == []


# ------------------------------------------------------------------
# BenchmarkItem — Referential Integrity
# ------------------------------------------------------------------

class TestBenchmarkItemReferentialIntegrity:
    def test_valid_gold_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-001", "TSU-002"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        known = {"TSU-001", "TSU-002", "TSU-003"}
        assert item.validate_referential_integrity(known) == []

    def test_invalid_gold_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-999"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            gold_tsu_ids=["TSU-999"],
        )
        known = {"TSU-001", "TSU-002"}
        errors = item.validate_referential_integrity(known)
        assert len(errors) == 1
        assert "TSU-999" in errors[0]

    def test_multiple_invalid_gold_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-999", "TSU-888"]),
            retrieval=BenchmarkRetrieval(top_k=5),
            gold_tsu_ids=["TSU-999", "TSU-888"],
        )
        known = {"TSU-001", "TSU-002"}
        errors = item.validate_referential_integrity(known)
        assert len(errors) == 2

    def test_none_known_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=["TSU-999"]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        # known_tsu_ids=None 이면 검증 건너뛰기
        assert item.validate_referential_integrity(None) == []

    def test_empty_gold_tsu_ids(self):
        item = BenchmarkItem(
            benchmark_id="B001",
            question=BenchmarkQuestion(text="테스트", language="ko"),
            expected=BenchmarkExpected(gold_tsu_ids=[]),
            retrieval=BenchmarkRetrieval(top_k=5),
        )
        known = {"TSU-001"}
        # gold_tsu_ids 가 비어있으면 오류 없음
        assert item.validate_referential_integrity(known) == []


# ------------------------------------------------------------------
# BenchmarkExpected — gold_tsu_ids 중심
# ------------------------------------------------------------------

class TestBenchmarkExpected:
    def test_gold_tsu_ids_primary(self):
        expected = BenchmarkExpected(gold_tsu_ids=["TSU-001", "TSU-002"])
        assert expected.gold_tsu_ids == ["TSU-001", "TSU-002"]

    def test_gold_tsu_ids_empty_default(self):
        expected = BenchmarkExpected()
        assert expected.gold_tsu_ids == []

    def test_backward_compatible_scriptures(self):
        """expected_scriptures 는 하위 호환성으로 유지."""
        expected = BenchmarkExpected(
            gold_tsu_ids=["TSU-001"],
            expected_scriptures=["시편 23:1", "요한복음 3:16"],
        )
        assert expected.gold_tsu_ids == ["TSU-001"]
        assert expected.expected_scriptures == ["시편 23:1", "요한복음 3:16"]

    def test_backward_compatible_doctrine(self):
        """expected_doctrine 는 하위 호환성으로 유지."""
        expected = BenchmarkExpected(
            gold_tsu_ids=["TSU-001"],
            expected_doctrine="대리 속죄설",
        )
        assert expected.expected_doctrine == "대리 속죄설"