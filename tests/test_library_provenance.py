"""Regression test — ui/pages/library.py::_render_provenance_section()
(SPRINT24-2). Verifies the failure-history join (by source_file) and that
detail rendering triggers only when there's something to show — st.* is
monkeypatched to a recorder, no live Streamlit runtime needed.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.extraction_failures import record_extraction_failure
from core.identity_registry import register_document, mark_superseded, save_identity_registry, load_identity_registry


class _ExpanderCtx:
    def __enter__(self): return self
    def __exit__(self, *a): return False


class _Recorder:
    def __init__(self):
        self.caption_calls = []
        self.markdown_calls = []
        self.expander_calls = []

    def caption(self, msg): self.caption_calls.append(msg)
    def markdown(self, msg, **kw): self.markdown_calls.append(msg)
    def expander(self, label, **kw):
        self.expander_calls.append(label)
        return _ExpanderCtx()


def _setup(tmp_path, monkeypatch):
    import ui.pages.library as mod
    out_dir = tmp_path / "output"
    (out_dir / "registry").mkdir(parents=True)
    registry_path = out_dir / "registry" / "documents.json"

    monkeypatch.setattr(mod, "DEFAULT_OUTPUT_DIR", str(out_dir))
    monkeypatch.setattr(mod, "_registry_path", lambda: registry_path)
    rec = _Recorder()
    monkeypatch.setattr(mod, "st", rec)
    return mod, rec, str(out_dir), registry_path


def test_no_history_shows_nothing(tmp_path, monkeypatch):
    mod, rec, out_dir, registry_path = _setup(tmp_path, monkeypatch)
    mod._render_provenance_section("untouched.pdf")
    assert rec.expander_calls == []


def test_failure_history_shown_without_registry(tmp_path, monkeypatch):
    mod, rec, out_dir, registry_path = _setup(tmp_path, monkeypatch)
    record_extraction_failure(out_dir, "broken.pdf", stage="extract", reason="추출 텍스트 없음")

    mod._render_provenance_section("broken.pdf")

    assert rec.expander_calls == ["🕓 이력 (버전 / 실패 기록)"]
    assert any("실패 기록 1건" in c for c in rec.caption_calls)
    assert any("추출 텍스트 없음" in m for m in rec.markdown_calls)


def test_version_chain_and_failure_joined_by_filename(tmp_path, monkeypatch):
    mod, rec, out_dir, registry_path = _setup(tmp_path, monkeypatch)

    registry = {"documents": {}, "_meta": {"total_documents": 0}}
    r1, _ = register_document(registry, {"document_id": "v1", "file_hash": "h1", "source_file": "book.pdf"})
    r2, _ = register_document(registry, {"document_id": "v2", "file_hash": "h2", "source_file": "book.pdf"})
    mark_superseded(registry, "v1", "v2")
    save_identity_registry(registry, str(registry_path))

    record_extraction_failure(out_dir, "book.pdf", stage="exception", reason="이전 시도 실패")

    mod._render_provenance_section("book.pdf")

    assert any("버전 2개" in c for c in rec.caption_calls)
    assert any("실패 기록 1건" in c for c in rec.caption_calls)
    joined = "\n".join(rec.markdown_calls)
    assert "이전 버전(대체됨)" in joined
    assert "현재" in joined
    assert "이전 시도 실패" in joined


def test_unrelated_filename_not_matched(tmp_path, monkeypatch):
    mod, rec, out_dir, registry_path = _setup(tmp_path, monkeypatch)
    record_extraction_failure(out_dir, "other.pdf", stage="extract", reason="x")

    mod._render_provenance_section("mine.pdf")

    assert rec.expander_calls == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
