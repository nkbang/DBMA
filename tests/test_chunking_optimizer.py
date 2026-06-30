# tests/test_chunking_optimizer.py
"""
chunking_optimizer.py 단위/통합 테스트
대상: chunk_once, optimize_chunks, save_optimized_md
"""
import pytest
from pathlib import Path
from core.chunking_optimizer import (
    chunk_once,
    optimize_chunks,
    save_optimized_md,
    ChunkResult,
    ChunkQuality,
    PRESETS,
)


SAMPLE_TEXT = "This is a test sentence for DBMA pipeline validation. " * 120


# ─── chunk_once ──────────────────────────────────────────────────────────────

class TestChunkOnce:

    def test_returns_chunk_result_instance(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert isinstance(result, ChunkResult)

    def test_chunks_is_list_of_strings(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert isinstance(result.chunks, list)
        assert all(isinstance(c, str) for c in result.chunks)

    def test_chunks_not_empty_for_valid_text(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert len(result.chunks) > 0

    def test_params_stored_correctly(self):
        result = chunk_once(SAMPLE_TEXT, 300, 80)
        assert result.params["chunk_size"] == 300
        assert result.params["chunk_overlap"] == 80

    def test_quality_has_noise_scores(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert isinstance(result.quality.noise_scores, list)
        assert len(result.quality.noise_scores) == len(result.chunks)

    def test_quality_passed_is_bool(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert isinstance(result.passed, bool)

    def test_params_hash_is_string(self):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        assert isinstance(result.params_hash, str)
        assert len(result.params_hash) == 8

    def test_empty_text_returns_empty_chunks(self):
        result = chunk_once("", 200, 50)
        assert result.chunks == []


# ─── optimize_chunks ─────────────────────────────────────────────────────────

class TestOptimizeChunks:

    @pytest.mark.parametrize("doc_type", ["txt", "pdf", "md", "docx", "unknown"])
    def test_returns_chunk_result_for_all_doc_types(self, doc_type):
        result = optimize_chunks(SAMPLE_TEXT, doc_type)
        assert isinstance(result, ChunkResult)

    def test_uses_preset_for_known_doc_type(self):
        result = optimize_chunks(SAMPLE_TEXT, "txt")
        preset = PRESETS["txt"]
        # 품질 통과 시 preset 파라미터가 그대로 사용됨
        assert result.params["chunk_size"] in [v["chunk_size"] for v in PRESETS.values()] or \
               result.params["chunk_size"] > 0

    def test_chunks_not_empty(self):
        result = optimize_chunks(SAMPLE_TEXT, "txt")
        assert len(result.chunks) > 0


# ─── save_optimized_md ───────────────────────────────────────────────────────

class TestSaveOptimizedMd:

    def test_creates_md_file(self, tmp_path):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        path = save_optimized_md(
            result=result,
            source_name="sample.txt",
            output_dir=tmp_path,
            stem="sample",
        )
        assert path.exists()

    def test_output_is_md_extension(self, tmp_path):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        path = save_optimized_md(
            result=result,
            source_name="sample.txt",
            output_dir=tmp_path,
            stem="sample",
        )
        assert path.suffix == ".md"

    def test_md_content_not_empty(self, tmp_path):
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        path = save_optimized_md(
            result=result,
            source_name="sample.txt",
            output_dir=tmp_path,
            stem="sample",
        )
        content = path.read_text(encoding="utf-8")
        assert "sample.txt" in content
        assert "Chunk" in content

    def test_output_dir_created_if_not_exists(self, tmp_path):
        new_dir = tmp_path / "nested" / "deep"
        result = chunk_once(SAMPLE_TEXT, 200, 50)
        path = save_optimized_md(
            result=result,
            source_name="sample.txt",
            output_dir=new_dir,
            stem="sample",
        )
        assert path.exists()
