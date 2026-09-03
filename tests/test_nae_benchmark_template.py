"""NAE Benchmark Template Tests — placeholder 생성 검증."""

import json
import tempfile
from pathlib import Path

from NAE.benchmark.template import generate_placeholder_item, generate_template, write_jsonl


class TestGeneratePlaceholderItem:
    def test_returns_dict(self):
        """placeholder item은 딕셔너리여야 함."""
        item = generate_placeholder_item(1, "v1")
        assert isinstance(item, dict)

    def test_benchmark_id_format(self):
        """benchmark_id는 B{index:04d} 형식이어야 함."""
        item = generate_placeholder_item(42, "v1")
        assert item["benchmark_id"] == "B0042"

    def test_question_text_is_empty(self):
        """question.text는 빈 문자열이어야 함 (실제 내용 없음)."""
        item = generate_placeholder_item(1, "v1")
        assert item["question"]["text"] == ""

    def test_gold_tsu_ids_is_empty(self):
        """gold_tsu_ids는 빈 리스트여야 함."""
        item = generate_placeholder_item(1, "v1")
        assert item["gold_tsu_ids"] == []

    def test_expected_scriptures_is_empty(self):
        """expected_scriptures는 빈 리스트여야 함."""
        item = generate_placeholder_item(1, "v1")
        assert item["expected"]["expected_scriptures"] == []

    def test_theology_area_is_empty(self):
        """theology_area는 빈 문자열이어야 함."""
        item = generate_placeholder_item(1, "v1")
        assert item["question"]["theology_area"] == ""

    def test_review_status_is_draft(self):
        """review_status는 draft여야 함."""
        item = generate_placeholder_item(1, "v1")
        assert item["review_status"] == "draft"

    def test_dataset_version_in_metadata(self):
        """metadata.created_version에 dataset_version이 들어가야 함."""
        item = generate_placeholder_item(1, "v2_test")
        assert item["metadata"]["created_version"] == "v2_test"


class TestGenerateTemplate:
    def test_count(self):
        """요청한 개수가 생성되어야 함."""
        records = generate_template(5, "v1")
        assert len(records) == 5

    def test_all_empty(self):
        """모든 레코드가 빈 값을 가져야 함."""
        records = generate_template(3, "v1")
        for rec in records:
            assert rec["question"]["text"] == ""
            assert rec["gold_tsu_ids"] == []

    def test_unique_ids(self):
        """모든 benchmark_id가 고유해야 함."""
        records = generate_template(10, "v1")
        ids = [r["benchmark_id"] for r in records]
        assert len(ids) == len(set(ids))


class TestWriteJsonl:
    def test_writes_and_reads_back(self):
        """JSONL로 쓰고 읽었을 때 원본과 동일해야 함."""
        records = [{"a": 1}, {"b": 2}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        write_jsonl(records, path)
        loaded = []
        with open(path, "r") as f:
            for line in f:
                loaded.append(json.loads(line.strip()))
        assert loaded == records
        Path(path).unlink()
