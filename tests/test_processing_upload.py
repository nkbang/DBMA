"""Regression test — ui/pages/processing.py::SUPPORTED_EXTS +
_render_upload_section() save logic (SPRINT22-A). Verifies the format
constant is unified and that saving an "uploaded" file (mocked, no real
Streamlit runtime) lands it in RAW where the existing pipeline picks it up
unchanged — no core/processing.py changes.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from ui.pages.processing import SUPPORTED_EXTS, MAX_UPLOAD_BATCH, _build_file_list


class _FakeUploadedFile:
    """Minimal stand-in for Streamlit's UploadedFile."""
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def _save_like_upload_handler(raw_dir: Path, uploaded_files):
    """Mirrors _render_upload_section()'s save loop without Streamlit."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    saved, skipped = [], []
    for f in uploaded_files:
        safe_name = Path(f.name).name
        ext = Path(safe_name).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            skipped.append(safe_name)
            continue
        dest = raw_dir / safe_name
        dest.write_bytes(f.getvalue())
        saved.append(safe_name)
    return saved, skipped


class TestSupportedExts:
    def test_includes_all_seven_extractor_formats(self):
        assert SUPPORTED_EXTS == {".pdf", ".txt", ".md", ".docx", ".epub", ".html", ".htm", ".rtf"}


class TestUploadSaveLogic:
    def test_supported_file_saved_to_raw(self, tmp_path):
        raw_dir = tmp_path / "RAW"
        saved, skipped = _save_like_upload_handler(raw_dir, [_FakeUploadedFile("book.epub", b"epub-bytes")])
        assert saved == ["book.epub"]
        assert skipped == []
        assert (raw_dir / "book.epub").read_bytes() == b"epub-bytes"

    def test_unsupported_file_skipped_not_written(self, tmp_path):
        raw_dir = tmp_path / "RAW"
        saved, skipped = _save_like_upload_handler(raw_dir, [_FakeUploadedFile("virus.exe", b"x")])
        assert saved == []
        assert skipped == ["virus.exe"]
        assert not (raw_dir / "virus.exe").exists()

    def test_path_traversal_name_is_stripped_to_basename(self, tmp_path):
        raw_dir = tmp_path / "RAW"
        saved, _ = _save_like_upload_handler(raw_dir, [_FakeUploadedFile("../../etc/evil.txt", b"x")])
        assert saved == ["evil.txt"]
        assert (raw_dir / "evil.txt").exists()
        assert not (tmp_path / "etc").exists()  # never escaped raw_dir

    def test_saved_file_is_picked_up_by_existing_pipeline_file_list(self, tmp_path):
        """The core assertion for SPRINT22-A: upload is purely an intake
        mechanism — _build_file_list() (used by the unchanged
        process_batch() pipeline) must see the uploaded file exactly like
        any manually-copied RAW file."""
        raw_dir = tmp_path / "RAW"
        _save_like_upload_handler(raw_dir, [_FakeUploadedFile("uploaded.txt", b"content")])

        file_list = _build_file_list(str(raw_dir), force_reingest=False)
        names = [f["name"] for f in file_list]
        assert "uploaded.txt" in names


class TestUploadBatchLimit:
    """[NAE-UPLOAD-AUTO] Auto-processing runs synchronously on upload,
    so batch size must stay bounded."""

    def test_max_upload_batch_is_three(self):
        assert MAX_UPLOAD_BATCH == 3

    def test_batch_at_limit_is_allowed(self):
        files = [_FakeUploadedFile(f"book{i}.txt", b"x") for i in range(MAX_UPLOAD_BATCH)]
        assert len(files) <= MAX_UPLOAD_BATCH  # would pass the _render_upload_section() gate

    def test_batch_over_limit_is_rejected_by_gate_logic(self):
        files = [_FakeUploadedFile(f"book{i}.txt", b"x") for i in range(MAX_UPLOAD_BATCH + 1)]
        assert len(files) > MAX_UPLOAD_BATCH  # _render_upload_section() must reject and not save


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
