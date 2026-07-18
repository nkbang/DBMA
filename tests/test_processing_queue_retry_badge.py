"""Regression test — ui/pages/processing.py::_render_processing_queue()
retry-candidate cross-reference (SPRINT24-1). Verifies a queued file whose
name matches a recorded extraction failure is flagged distinctly from a
brand-new file, using only the most recent failure per filename.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extraction_failures import record_extraction_failure


class _Recorder:
    def __init__(self):
        self.caption_calls = []
        self.markdown_calls = []
        self.info_calls = []

    def caption(self, msg): self.caption_calls.append(msg)
    def markdown(self, html, **kw): self.markdown_calls.append(html)
    def info(self, msg): self.info_calls.append(msg)


def _setup(tmp_path, monkeypatch, raw_files, batch_state_processed=None):
    import ui.pages.processing as mod
    raw_dir = tmp_path / "RAW"
    raw_dir.mkdir()
    for name in raw_files:
        (raw_dir / name).write_text("x", encoding="utf-8")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    if batch_state_processed:
        import json
        (out_dir / ".batch_state.json").write_text(
            json.dumps({"processed": batch_state_processed}), encoding="utf-8")

    monkeypatch.setattr(mod, "DEFAULT_RAW_DIR", str(raw_dir))
    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_DIR", str(out_dir))
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    return mod, rec, str(out_dir)


def test_file_with_prior_failure_shows_retry_badge(tmp_path, monkeypatch):
    mod, rec, out_dir = _setup(tmp_path, monkeypatch, ["broken.pdf"])
    record_extraction_failure(out_dir, "broken.pdf", stage="extract", reason="추출 텍스트 없음")

    mod._render_processing_queue()

    assert len(rec.markdown_calls) == 1
    assert "재시도 예정" in rec.markdown_calls[0]
    assert "이전 실패: 추출 텍스트 없음" in rec.markdown_calls[0]


def test_new_file_without_failure_shows_default_badge(tmp_path, monkeypatch):
    mod, rec, out_dir = _setup(tmp_path, monkeypatch, ["fresh.txt"])

    mod._render_processing_queue()

    assert len(rec.markdown_calls) == 1
    assert "대기 중" in rec.markdown_calls[0]
    assert "재시도 예정" not in rec.markdown_calls[0]


def test_only_most_recent_failure_reason_shown(tmp_path, monkeypatch):
    mod, rec, out_dir = _setup(tmp_path, monkeypatch, ["a.txt"])
    record_extraction_failure(out_dir, "a.txt", stage="extract", reason="first reason")
    record_extraction_failure(out_dir, "a.txt", stage="exception", reason="second reason")

    mod._render_processing_queue()

    assert "second reason" in rec.markdown_calls[0]
    assert "first reason" not in rec.markdown_calls[0]


def test_unrelated_failure_does_not_flag_other_files(tmp_path, monkeypatch):
    mod, rec, out_dir = _setup(tmp_path, monkeypatch, ["clean.txt"])
    record_extraction_failure(out_dir, "other_file.pdf", stage="extract", reason="unrelated")

    mod._render_processing_queue()

    assert "대기 중" in rec.markdown_calls[0]
    assert "재시도 예정" not in rec.markdown_calls[0]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
