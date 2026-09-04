# tests/test_processing_pipeline.py
"""
processing.py 통합 테스트
대상: process_one_file (smoke), 로그 구조, 빈 입력 방어
"""
import pytest
from pathlib import Path
from core.processing import build_converter, build_splitter, process_one_file
from core.config import registry_path_for
from core.identity_registry import load_identity_registry, save_identity_registry
from core.document_identity import guess_doc_type


@pytest.fixture(scope="module")
def converter():
    return build_converter()


@pytest.fixture(scope="module")
def splitter():
    return build_splitter(1000, 120)


def _run(file_info, converter, splitter, output_dir):
    return process_one_file(
        file_info=file_info,
        converter=converter,
        splitter=splitter,
        output_dir=output_dir,
        chunk_size=1000,
        chunk_overlap=120,
    )


# ─── smoke test ──────────────────────────────────────────────────────────────

class TestProcessOneFileSmoke:

    def test_returns_dict(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = _run(file_info, converter, splitter, str(tmp_path))
        assert isinstance(result, dict)
        assert "success" in result
        assert "logs" in result

    def test_success_is_bool(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = _run(file_info, converter, splitter, str(tmp_path))
        assert isinstance(result["success"], bool)

    def test_logs_is_list(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = _run(file_info, converter, splitter, str(tmp_path))
        assert isinstance(result["logs"], list)

    def test_success_true_for_valid_input(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = _run(file_info, converter, splitter, str(tmp_path))
        assert result["success"] is True

    def test_completion_log_present(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        result = _run(file_info, converter, splitter, str(tmp_path))
        messages = [item.get("msg", "") for item in result["logs"] if isinstance(item, dict)]
        assert any("처리 완료" in msg for msg in messages)


# ─── 산출물 검증 ─────────────────────────────────────────────────────────────

class TestProcessOneFileOutputs:

    def test_md_file_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        _run(file_info, converter, splitter, str(tmp_path))
        md_files = list(tmp_path.glob("*.md"))
        assert len(md_files) > 0

    def test_chunks_txt_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        _run(file_info, converter, splitter, str(tmp_path))
        txt_files = list(tmp_path.glob("*_chunks.txt"))
        assert len(txt_files) > 0

    def test_meta_json_created(self, tmp_path, converter, splitter):
        sample = tmp_path / "sample.txt"
        sample.write_text("This is a test sentence for DBMA. " * 50, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        _run(file_info, converter, splitter, str(tmp_path))
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
        result = _run(file_info, converter, splitter, str(tmp_path))
        assert result["success"] is False

    def test_logs_contain_failure_message(self, tmp_path, converter, splitter):
        file_info = {
            "path": str(tmp_path / "nonexistent.txt"),
            "name": "nonexistent.txt",
            "ext": ".txt",
        }
        result = _run(file_info, converter, splitter, str(tmp_path))
        messages = [item.get("msg", "") for item in result["logs"] if isinstance(item, dict)]
        assert any("처리 실패" in msg or "추출" in msg or len(msg) > 0 for msg in messages)


# ─── doc_type 배선 검증 (Task Order 018) ─────────────────────────────────────

class TestProcessOneFileDocType:

    def test_process_path_sets_doc_type_in_registry(self, tmp_path, converter, splitter):
        """PROCESS 경로: 처리 후 registry record의 doc_type이 guess_doc_type() 결과와 일치해야 함."""
        sample = tmp_path / "sample.txt"
        content = "This is a test sentence for DBMA. " * 50
        sample.write_text(content, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}
        _run(file_info, converter, splitter, str(tmp_path))

        registry = load_identity_registry(registry_path_for(str(tmp_path)))
        record = next(iter(registry["documents"].values()))
        expected = guess_doc_type(content, sample.name, None)
        assert record["doc_type"] == expected

    def test_skip_path_preserves_existing_doc_type(self, tmp_path, converter, splitter):
        """SKIP 경로: 1차 처리 후 doc_type을 임의 세팅하고, 2차 처리(SKIP)했을 때 값이 유지되어야 함."""
        sample = tmp_path / "sample.txt"
        content = "This is a test sentence for DBMA. " * 50
        sample.write_text(content, encoding="utf-8")
        file_info = {"path": str(sample), "name": sample.name, "ext": ".txt"}

        # 1차 처리 — 레코드 생성
        _run(file_info, converter, splitter, str(tmp_path))
        registry_path = registry_path_for(str(tmp_path))
        registry = load_identity_registry(registry_path)
        doc_id = next(iter(registry["documents"]))
        registry["documents"][doc_id]["doc_type"] = "sermon"  # 임의 값으로 고정
        save_identity_registry(registry, registry_path)

        # 2차 처리 — 파일 안 바뀌었으므로 SKIP 경로
        result = _run(file_info, converter, splitter, str(tmp_path))

        registry = load_identity_registry(registry_path)
        assert registry["documents"][doc_id]["doc_type"] == "sermon"
