"""Regression test — RetrievalEngine._apply_document_diversity()
(SPRINT20-I-E-3). Verifies per-document cap, k guarantee, cap=0 rollback,
single-document corpus, and document_id fallback.

This test suite validates the document diversity mechanism in the retrieval engine,
ensuring that documents from the same source are properly capped to avoid
over-representation in search results.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import RetrievalEngine, RankedCandidate


def _c(doc_id, score, tsu_id, source_file=None):
    """Helper function to create RankedCandidate objects for testing.
    
    Parameters
    ----------
    doc_id : str or None
        Document identifier for diversity control
    score : float
        Final score for ranking
    tsu_id : str
        TSU identifier
    source_file : str or None, optional
        Source file name for fallback document identification
    
    Returns
    -------
    RankedCandidate
        Test candidate with specified parameters
    """
    meta = {"tsu_id": tsu_id}
    if doc_id is not None:
        meta["document_id"] = doc_id
    if source_file is not None:
        meta["source_file"] = source_file
    return RankedCandidate(
        tsu_id=tsu_id, content=f"c-{tsu_id}", metadata=meta,
        vector_score=0.0, bm25_score=0.0, theological_score=0.0,
        final_score=score, explanation="",
    )


# _apply_document_diversity is a pure method — call on an unconstructed instance.
_apply = RetrievalEngine._apply_document_diversity


def test_cap_enforced_and_backfill_from_other_docs():
    """Test that document cap is enforced and backfill occurs from other documents.
    
    This test verifies that when a document cap is set (cap=2), the function will
    limit the number of candidates from the same document to that cap, but will 
    still return k results by backfilling from other documents.
    
    Test case: doc A dominates with 5 candidates, doc B has 2 candidates. 
    With cap=2 and k=4, we should get exactly 2 from A and 2 from B.
    """
    # doc A dominates (5), doc B has 2. cap=2, k=4.
    cands = [_c("A", 0.9 - i * 0.01, f"A{i}") for i in range(5)] + \
            [_c("B", 0.5, "B0"), _c("B", 0.49, "B1")]
    out = _apply(None, cands, k=4, cap=2)
    keys = [x.metadata["document_id"] for x in out]
    assert len(out) == 4
    assert keys.count("A") == 2 and keys.count("B") == 2


def test_k_guaranteed_via_overflow_single_document():
    """Test that k results are guaranteed even when documents are capped.
    
    When a single document has many candidates, the function should still return
    at least k results by overflowing from other documents when needed.
    """
    cands = [_c("A", 0.9 - i * 0.01, f"A{i}") for i in range(5)]
    out = _apply(None, cands, k=3, cap=2)
    assert len(out) == 3  # cap=2면 2개뿐이지만 overflow로 3개 보충


def test_cap_zero_is_legacy_behavior():
    """Test that cap=0 behaves as legacy fallback (no diversity).
    
    When cap=0 is set, the function should fall back to the legacy behavior
    of selecting candidates without applying document diversity.
    """
    cands = [_c("A", 0.9 - i * 0.01, f"A{i}") for i in range(5)]
    out = _apply(None, cands, k=3, cap=0)
    assert [x.tsu_id for x in out] == ["A0", "A1", "A2"]


def test_score_order_preserved_within_selection():
    """Test that score ordering is preserved within document selection.
    
    Within each document, candidates should be selected in descending score order,
    and when backfilling occurs, the original ordering should be maintained.
    """
    cands = [_c("A", 0.9, "A0"), _c("B", 0.8, "B0"), _c("A", 0.7, "A1"), _c("C", 0.6, "C0")]
    out = _apply(None, cands, k=4, cap=1)
    assert [x.tsu_id for x in out] == ["A0", "B0", "C0", "A1"]  # A1 backfilled last


def test_missing_document_id_falls_back_to_source_file_then_tsu_id():
    """Test fallback behavior when document_id is missing.
    
    When document_id is not available, the function should fall back to source_file
    for document identification, and finally to tsu_id if neither is available.
    """
    cands = [
        _c(None, 0.9, "T0", source_file="f.pdf"),
        _c(None, 0.8, "T1", source_file="f.pdf"),
        _c(None, 0.7, "T2"),  # no doc_id, no source_file → tsu_id key
    ]
    out = _apply(None, cands, k=3, cap=1)
    # f.pdf capped at 1; T2 distinct → selected=[T0,T2], overflow=[T1]
    assert [x.tsu_id for x in out] == ["T0", "T2", "T1"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
