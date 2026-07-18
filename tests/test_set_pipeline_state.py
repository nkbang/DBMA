"""Regression test — core/document_context.py::set_pipeline_state()
(SPRINT21-F-2). Verifies typo/invalid-value rejection and that it works
uniformly on both DocumentContext instances and registry record dicts.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.document_context import DocumentContext, PIPELINE_STATES, set_pipeline_state


class TestSetPipelineState:
    def test_valid_state_on_document_context(self):
        ctx = DocumentContext(document_id="d1", file_hash="h1", source_file="a.pdf", source_type="pdf")
        set_pipeline_state(ctx, "INDEXED")
        assert ctx.pipeline_state == "INDEXED"

    def test_valid_state_on_dict(self):
        record = {"pipeline_state": "NEW"}
        set_pipeline_state(record, "PROCESSED")
        assert record["pipeline_state"] == "PROCESSED"

    def test_invalid_state_raises_on_context(self):
        ctx = DocumentContext(document_id="d1", file_hash="h1", source_file="a.pdf", source_type="pdf")
        with pytest.raises(ValueError):
            set_pipeline_state(ctx, "INDEXEDD")  # typo
        assert ctx.pipeline_state == "NEW"  # untouched on rejection

    def test_invalid_state_raises_on_dict(self):
        record = {"pipeline_state": "PROCESSED"}
        with pytest.raises(ValueError):
            set_pipeline_state(record, "PROCESED")  # typo
        assert record["pipeline_state"] == "PROCESSED"  # untouched

    def test_all_documented_states_are_valid(self):
        record = {}
        for state in PIPELINE_STATES:
            set_pipeline_state(record, state)  # must not raise
            assert record["pipeline_state"] == state


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v"])
