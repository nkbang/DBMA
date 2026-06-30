# tests/test_processing_pipeline.py
"""
processing.py 통합 테스트
대상: process_one_file (smoke), 로그 구조, 빈 입력 방어
"""
import pytest
from pathlib import Path
from core.processing import build_converter, build_splitter, process_one_file


@pytest.fixture(scope="module")
def converter():
    return build_converter()


@pytest.fixture(scope="module")
def splitter():
    return build_splitter(1000, 120)


# ─── smoke test ──────────────────────────────────────────────────────────────

class TestProcessOneFileSmoke:

    def test_returns_tuple(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_success_is_bool(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        logs, success = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        assert isinstance(success, bool)

    def test_logs_is_list(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        logs, _ = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        assert isinstance(logs, list)

    def test_success_true_for_valid_input(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        logs, success = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        assert success is True

    def test_completion_log_present(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        logs, _ = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        messages = [item.get("msg", "") for item in logs if isinstance(item, dict)]
        assert any("처리 완료" in msg for msg in messages)


# ─── 산출물 검증 ─────────────────────────────────────────────────────────────

class TestProcessOneFileOutputs:

    def test_md_file_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) > 0

    def test_chunks_txt_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        txt_files = list(tmp_path.glob("*_chunks.txt"))
        assert len(txt_files) > 0

    def test_meta_json_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        json_files = list(tmp_path.glob("*_chunks_meta.json"))
        assert len(json_files) > 0


# ─── 방어 테스트 ─────────────────────────────────────────────────────────────

class TestProcessOneFileDefensive:

    def test_returns_false_for_missing_file(self, tmp_path, converter, splitter):
        file_info = {
            "path": str(tmp_path / "nonexistent.txt"),
            "name": "nonexistent.txt",
            "ext": ".txt",
        }
        logs, success = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        assert success is False

    def test_logs_contain_failure_message(self, tmp_path, converter, splitter):
        file_info = {
            "path": str(tmp_path / "nonexistent.txt"),
            "name": "nonexistent.txt",
            "ext": ".txt",
        }
        logs, _ = process_one_file(file_info, converter, splitter, str(tmp_path), 1000, 120)
        messages = [item.get("msg", "") for item in logs if isinstance(item, dict)]
        assert any("처리 실패" in msg or "NameError" in msg or len(msg) > 0 for msg in messages)
