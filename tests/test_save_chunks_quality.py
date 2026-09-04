"""Regression test — core/processing.py::save_chunks() persists ChunkQuality
(2026-07-21).

Background: force_rechunk (tests/test_force_rechunk.py) lets a document be
re-chunked with a new algorithm, but save_chunks() blindly overwrote
_chunks_meta.json with no quality data — there was nothing on disk to
compare an old vs. new re-chunk against, so a regression from a chunking
change could silently replace a better version with a worse one. This is
step 1 (minimal) of that fix: persist the already-computed ChunkQuality
(avg_noise/max_noise/avg_dup/short_ratio/passed) as an additive "quality"
field. Comparison/warning logic is a follow-up, not part of this change.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.processing import save_chunks
from core.chunking_optimizer import ChunkQuality


def test_quality_persisted_when_provided(tmp_path):
    quality = ChunkQuality(noise_scores=[5.0, 10.0], dup_ratios=[0.0, 0.1], short_ratio=0.0)

    txt_path, meta_path = save_chunks(
        str(tmp_path), "doc_pdf", "doc.pdf", ["chunk one", "chunk two"], 1200, 200,
        quality=quality,
    )

    meta = json.loads(open(meta_path, encoding="utf-8").read())
    assert meta["quality"]["avg_noise"] == quality.avg_noise
    assert meta["quality"]["max_noise"] == quality.max_noise
    assert meta["quality"]["avg_dup"] == quality.avg_dup
    assert meta["quality"]["short_ratio"] == quality.short_ratio
    assert meta["quality"]["passed"] == quality.passed


def test_quality_absent_when_not_provided_no_crash(tmp_path):
    """Backward compatible: existing callers that don't pass quality (or the
    optimizer fell back to the plain splitter, chunk_result=None) must keep
    working exactly as before — no "quality" key, no error."""
    txt_path, meta_path = save_chunks(
        str(tmp_path), "doc_pdf", "doc.pdf", ["chunk one"], 1200, 200,
    )

    meta = json.loads(open(meta_path, encoding="utf-8").read())
    assert "quality" not in meta
    assert meta["chunks"] == 1


def test_existing_meta_fields_unchanged(tmp_path):
    """Additive-only: source/chunks/chunk_size/chunk_overlap must stay
    exactly as before regardless of whether quality is passed."""
    quality = ChunkQuality(noise_scores=[3.0], dup_ratios=[0.0], short_ratio=0.0)
    _, meta_path = save_chunks(
        str(tmp_path), "doc_pdf", "doc.pdf", ["a", "b", "c"], 900, 150,
        quality=quality,
    )
    meta = json.loads(open(meta_path, encoding="utf-8").read())
    assert meta["source"] == "doc.pdf"
    assert meta["chunks"] == 3
    assert meta["chunk_size"] == 900
    assert meta["chunk_overlap"] == 150


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
