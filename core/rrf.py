"""core/rrf.py — Reciprocal Rank Fusion (DBMA-SEARCH-INFRA-001 HQ 제안 ⑦).

RRF(d) = sum, over each input ranking r that contains d, of 1/(k + rank_r(d))
— rank_r(d) is d's 1-indexed position in that ranking (rank 1 = best). k=60
is the standard RRF constant (Cormack, Clarke & Buettcher 2009), which damps
how much any single list's #1 pick can dominate the fused score.

HQ 제안 ⑦: "Weighted Score보다 Reciprocal Rank Fusion이 BM25 * Vector 혼합에서
훨씬 안정적이다." Replaces the fixed-weight sum (0.4*bm25 + 0.4*theological +
0.2*passage) `core/hybrid_candidate_pipeline.py::HybridRetriever` used
before — that formula assumed each signal's raw score scale was comparable
and that the weights were the right split, neither of which RRF requires:
it only needs each signal's relative ORDER.
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    ranked_id_lists: list[list[str]],
    k: int = 60,
) -> dict[str, float]:
    """Fuse multiple rankings of the same id space into one RRF score per id.

    Each element of `ranked_id_lists` is an ordered list of ids (best first)
    from one ranking signal (e.g. by bm25_score, by theological_score, by
    passage_score) over the SAME candidate set — an id absent from a given
    list simply contributes 0 from that list, not a penalty.

    Returns {id: rrf_score}, unsorted — the caller sorts.
    """
    scores: dict[str, float] = {}
    for ranked_ids in ranked_id_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores
