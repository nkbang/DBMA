"""NAE Benchmark Review CLI Tests — promote 재검증 로직 포함."""

import json
import tempfile
from pathlib import Path

import pytest

from NAE.benchmark.review import (
    load_jsonl,
    save_jsonl,
    cmd_promote,
    cmd_approve,
    _find_record_index,
)


def _make_draft_record(bid: str, text: str = "", gold_ids: list | None = None, approved: bool = True) -> dict:
    """draft 레코드 생성."""
    if gold_ids is None:
        gold_ids = []
    return {
        "benchmark_id": bid,
        "question": {"text": text, "language": "ko", "question_type": "other", "theology_area": ""},
        "expected": {"gold_tsu_ids": [], "required_concepts": [], "expected_scriptures": [], "expected_doctrine": ""},
        "retrieval": {"top_k": 5},
        "evaluation": {"status": "pending", "scores": {}, "notes": ""},
        "metadata": {"created_version": "v1", "source": "template", "created_at": "2024-01-01T00:00:00+00:00", "tsu_schema_version": "", "collector_version": "", "canonical_version": ""},
        "gold_tsu_ids": gold_ids,
        "difficulty": "beginner",
        "review_status": "approved" if approved else "draft",
        "review": {"status": "approved", "reviewer": "test", "reviewed_at": "2024-01-01T00:00:00+00:00"} if approved else {},
    }


def _write_draft(records: list, path: str) -> None:
    """draft JSONL 파일 작성."""
    save_jsonl(records, path)


class TestFindRecordIndex:
    def test_found(self):
        records = [{"benchmark_id": "B001"}, {"benchmark_id": "B002"}]
        assert _find_record_index(records, "B002") == 1

    def test_not_found(self):
        records = [{"benchmark_id": "B001"}]
        assert _find_record_index(records, "B999") == -1


class TestPromote:
    def test_promote_all_valid(self, tmp_path: Path) -> None:
        """모든 레코드가 유효하면 모두 promote되어야 함."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [_make_draft_record("B001", "질문", ["TSU-001"])]
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 0
        assert output.exists()
        loaded = load_jsonl(str(output))
        assert len(loaded) == 1
        assert manifest.exists()
        with open(manifest) as f:
            m = json.load(f)
        assert m["question_count"] == 1

    def test_promote_rejects_empty_question_text(self, tmp_path: Path) -> None:
        """approved인데 question.text가 비어있으면 promote 실패."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [_make_draft_record("B001", text="", gold_ids=["TSU-001"])]
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 1  # 실패

    def test_promote_rejects_empty_gold_tsu_ids(self, tmp_path: Path) -> None:
        """approved인데 gold_tsu_ids가 비어있으면 promote 실패."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [_make_draft_record("B001", text="질문", gold_ids=[])]
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 1  # 실패

    def test_promote_partial_valid(self, tmp_path: Path) -> None:
        """일부만 유효하면 promote 실패, output 파일도 생성되지 않음."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [
            _make_draft_record("B001", text="질문1", gold_ids=["TSU-001"]),  # 유효
            _make_draft_record("B002", text="", gold_ids=["TSU-002"]),  # question.text 비어있음
        ]
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 1  # 일부 실패로 전체 promote 중단
        # promote 실패 시 output 파일이 생성되지 않음
        assert not output.exists()

    def test_promote_no_approved_records(self, tmp_path: Path) -> None:
        """approved 레코드가 없으면 0개 promote하고 성공."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [_make_draft_record("B001", text="질문", gold_ids=["TSU-001"], approved=False)]
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 0
        loaded = load_jsonl(str(output))
        assert len(loaded) == 0

    def test_promote_doctrine_coverage(self, tmp_path: Path) -> None:
        """doctrine_coverage가 manifest에 집계되어야 함."""
        draft = tmp_path / "draft.jsonl"
        output = tmp_path / "gold.jsonl"
        manifest = tmp_path / "manifest.json"
        records = [
            _make_draft_record("B001", text="질문1", gold_ids=["TSU-001"]),
            _make_draft_record("B002", text="질문2", gold_ids=["TSU-002"]),
        ]
        # theology_area 설정
        records[0]["question"]["theology_area"] = "Baptism"
        records[1]["question"]["theology_area"] = "Soteriology"
        _write_draft(records, str(draft))

        result = cmd_promote(str(draft), str(output), str(manifest))
        assert result == 0
        with open(manifest) as f:
            m = json.load(f)
        assert m["doctrine_coverage"]["Baptism"] == 1
        assert m["doctrine_coverage"]["Soteriology"] == 1


class TestApprove:
    def test_approve_changes_status(self, tmp_path: Path) -> None:
        """approve 후 review_status가 approved로 변경되어야 함."""
        dataset = tmp_path / "draft.jsonl"
        records = [_make_draft_record("B001", text="질문", gold_ids=["TSU-001"], approved=False)]
        save_jsonl(records, str(dataset))

        result = cmd_approve(str(dataset), "B001", "tester")
        assert result == 0
        loaded = load_jsonl(str(dataset))
        assert loaded[0]["review_status"] == "approved"
        assert loaded[0]["review"]["status"] == "approved"
        assert loaded[0]["review"]["reviewer"] == "tester"

    def test_approve_nonexistent(self, tmp_path: Path) -> None:
        """존재하지 않는 benchmark_id는 에러."""
        dataset = tmp_path / "draft.jsonl"
        records = [_make_draft_record("B001")]
        save_jsonl(records, str(dataset))

        result = cmd_approve(str(dataset), "B999", "tester")
        assert result == 1
