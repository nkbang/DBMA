"""Unit tests — rebuild_embedding_cache.py maintenance script (embedding
cache lifecycle audit follow-up). Uses a temp cache dir and a temp TSU
JSONL -- never touches the real cache/embeddings or output/bench/
tsu_dataset.jsonl.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from core.retrieval import EmbeddingCache
from rebuild_embedding_cache import _iter_tsu_contents, compute_coverage


def _write_tsu_dataset(path: Path, contents: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for i, content in enumerate(contents):
            f.write(json.dumps({"tsu_id": f"TSU-{i:04d}", "content": content}) + "\n")


class TestIterTsuContents:
    def test_yields_content_field_for_each_record(self, tmp_path):
        path = tmp_path / "tsu.jsonl"
        _write_tsu_dataset(path, ["첫 문서 내용", "둘째 문서 내용"])
        assert list(_iter_tsu_contents(path)) == ["첫 문서 내용", "둘째 문서 내용"]

    def test_skips_blank_lines_and_dollar_prefixed_lines(self, tmp_path):
        path = tmp_path / "tsu.jsonl"
        path.write_text(
            '\n$comment\n{"content": "본문"}\n\n', encoding="utf-8"
        )
        assert list(_iter_tsu_contents(path)) == ["본문"]

    def test_skips_records_with_empty_content(self, tmp_path):
        path = tmp_path / "tsu.jsonl"
        path.write_text(
            '{"content": ""}\n{"content": "본문 있음"}\n', encoding="utf-8"
        )
        assert list(_iter_tsu_contents(path)) == ["본문 있음"]

    def test_skips_malformed_json_lines(self, tmp_path):
        path = tmp_path / "tsu.jsonl"
        path.write_text('not json\n{"content": "정상"}\n', encoding="utf-8")
        assert list(_iter_tsu_contents(path)) == ["정상"]


class TestComputeCoverage:
    def test_reports_zero_missing_when_fully_cached(self, tmp_path):
        cache = EmbeddingCache(cache_dir=str(tmp_path / "cache"))
        tsu_path = tmp_path / "tsu.jsonl"
        contents = ["문서 A", "문서 B", "문서 C"]
        _write_tsu_dataset(tsu_path, contents)
        for c in contents:
            cache.insert(cache._hash_text(c), c, [0.1, 0.2])

        stats = compute_coverage(cache, tsu_path)
        assert stats["total_tsu"] == 3
        assert stats["distinct_hashes"] == 3
        assert stats["matched"] == 3
        assert stats["missing"] == 0
        assert stats["orphaned"] == 0
        assert stats["coverage_pct"] == 100.0

    def test_reports_missing_for_uncached_tsus(self, tmp_path):
        cache = EmbeddingCache(cache_dir=str(tmp_path / "cache"))
        tsu_path = tmp_path / "tsu.jsonl"
        _write_tsu_dataset(tsu_path, ["문서 A", "문서 B"])
        cache.insert(cache._hash_text("문서 A"), "문서 A", [0.1])

        stats = compute_coverage(cache, tsu_path)
        assert stats["matched"] == 1
        assert stats["missing"] == 1
        assert stats["coverage_pct"] == 50.0

    def test_deduplicates_content_shared_across_tsu_records(self, tmp_path):
        # [rebuild_embedding_cache.py finding] the cache is content-
        # addressed, so two TSU records with identical content only need
        # one cache entry between them -- distinct_hashes must be less
        # than total_tsu here, and coverage must be computed against it.
        cache = EmbeddingCache(cache_dir=str(tmp_path / "cache"))
        tsu_path = tmp_path / "tsu.jsonl"
        _write_tsu_dataset(tsu_path, ["중복 문단", "중복 문단", "고유 문단"])
        cache.insert(cache._hash_text("중복 문단"), "중복 문단", [0.1])

        stats = compute_coverage(cache, tsu_path)
        assert stats["total_tsu"] == 3
        assert stats["distinct_hashes"] == 2
        assert stats["matched"] == 1
        assert stats["missing"] == 1
        assert stats["coverage_pct"] == 50.0  # 1/2, not 1/3

    def test_reports_orphaned_cache_entries_without_deleting(self, tmp_path):
        cache = EmbeddingCache(cache_dir=str(tmp_path / "cache"))
        tsu_path = tmp_path / "tsu.jsonl"
        _write_tsu_dataset(tsu_path, ["현재 문서"])
        cache.insert(cache._hash_text("현재 문서"), "현재 문서", [0.1])
        cache.insert(cache._hash_text("옛날에 삭제된 문서"), "옛날에 삭제된 문서", [0.2])

        stats = compute_coverage(cache, tsu_path)
        assert stats["orphaned"] == 1
        assert stats["matched"] == 1
        # orphan file must still be on disk -- report-only policy
        assert len(list(cache.cache_dir.glob("*.json"))) == 2
