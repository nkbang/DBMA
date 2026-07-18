"""Regression test — ui/pages/processing.py::_render_recent_failures()
(SPRINT23). Verifies it reads core/extraction_failures.py's log correctly
(empty state, sort order, stage label mapping) without a live Streamlit
runtime — st.* calls are monkeypatched to no-ops that record arguments.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extraction_failures import record_extraction_failure


class _Recorder:
    def __init__(self):
        self.info_calls = []
        self.caption_calls = []
        self.markdown_calls = []

    def info(self, msg): self.info_calls.append(msg)
    def caption(self, msg): self.caption_calls.append(msg)
    def markdown(self, html, **kw): self.markdown_calls.append(html)


def test_empty_state_shows_info(tmp_path, monkeypatch):
    import ui.pages.processing as mod
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_DIR", str(tmp_path))

    mod._render_recent_failures()

    assert rec.info_calls == ["실패 기록이 없습니다."]
    assert rec.markdown_calls == []


def test_shows_most_recent_first_capped_at_ten(tmp_path, monkeypatch):
    import ui.pages.processing as mod
    for i in range(12):
        record_extraction_failure(str(tmp_path), f"doc{i}.pdf", stage="extract", reason=f"reason{i}")

    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_DIR", str(tmp_path))

    mod._render_recent_failures()

    assert rec.caption_calls[0] == "전체 12건 중 최근 10건"
    assert len(rec.markdown_calls) == 10
    # most recently recorded (doc11) should appear first
    assert "doc11.pdf" in rec.markdown_calls[0]


def test_stage_label_and_reason_shown(tmp_path, monkeypatch):
    import ui.pages.processing as mod
    record_extraction_failure(str(tmp_path), "broken.pdf", stage="exception", reason="PDF corrupt", retry_count=3)

    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_DIR", str(tmp_path))

    mod._render_recent_failures()

    assert "예외 발생" in rec.markdown_calls[0]
    assert "재시도 3회" in rec.markdown_calls[0]
    assert any("PDF corrupt" in c for c in rec.caption_calls)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
