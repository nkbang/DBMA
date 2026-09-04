"""Regression test — RetrievalEngine.book_coverage() (2026-07-21, Sermon
Draft book-coverage picker).

Distinct source_file count per Bible book_id, aggregated read-only over
the already-loaded self.tsus corpus (same data RetrievalEngine.retrieve()
uses) — no new corpus-access path, matching the existing
list_source_files() pattern. Used to label the 66 book buttons with how
many source documents cover each book (e.g. "창세기 2").
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retrieval import RetrievalEngine


def _write_dataset(tmp_path, records) -> str:
    path = tmp_path / "tsu_dataset.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return str(path)


def test_counts_distinct_source_files_per_book(tmp_path):
    records = [
        {"tsu_id": "1", "content": "a", "verse_mapping": {"book_id": "GEN"}, "source_file": "commentary_a.pdf"},
        {"tsu_id": "2", "content": "b", "verse_mapping": {"book_id": "GEN"}, "source_file": "commentary_a.pdf"},  # same file, 2nd chunk
        {"tsu_id": "3", "content": "c", "verse_mapping": {"book_id": "GEN"}, "source_file": "commentary_b.pdf"},
        {"tsu_id": "4", "content": "d", "verse_mapping": {"book_id": "ROM"}, "source_file": "commentary_c.pdf"},
    ]
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path, records))
    coverage = engine.book_coverage()

    assert coverage["GEN"] == 2   # commentary_a + commentary_b, not 3 chunks
    assert coverage["ROM"] == 1


def test_book_with_no_tsu_records_absent_from_result(tmp_path):
    records = [
        {"tsu_id": "1", "content": "a", "verse_mapping": {"book_id": "GEN"}, "source_file": "x.pdf"},
    ]
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path, records))
    coverage = engine.book_coverage()

    assert "OBA" not in coverage
    assert coverage.get("OBA", 0) == 0


def test_missing_verse_mapping_or_source_file_ignored_not_crash(tmp_path):
    records = [
        {"tsu_id": "1", "content": "a", "verse_mapping": {}, "source_file": "x.pdf"},
        {"tsu_id": "2", "content": "b", "source_file": "y.pdf"},
        {"tsu_id": "3", "content": "c", "verse_mapping": {"book_id": "GEN"}},
        {"tsu_id": "4", "content": "d", "verse_mapping": {"book_id": "GEN"}, "source_file": "z.pdf"},
    ]
    engine = RetrievalEngine(tsu_dataset_path=_write_dataset(tmp_path, records))
    coverage = engine.book_coverage()

    assert coverage == {"GEN": 1}


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
