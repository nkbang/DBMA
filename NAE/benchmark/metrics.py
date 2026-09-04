"""NAE Benchmark Metrics — Retrieval 지표 계산.

평가 대상: answer quality 아님.
검색 품질만 측정 (Recall@K, Precision@K, MRR).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Individual Metrics
# ------------------------------------------------------------------

def recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 안에 관련 결과가 몇 개 있는지 비율.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요 아님).
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0 사이의 Recall 값.
    """
    if not relevant_ids:
        # 관련 결과가 없으면 Recall은 0.0 (분모 0 — zero-gold 정책)
        return 0.0

    if k is not None:
        retrieved_subset = retrieved_ids[:k]
    else:
        retrieved_subset = retrieved_ids

    relevant_set: Set[str] = set(relevant_ids)
    # 교집합 크기로 계산 — retrieved_subset에 동일 ID가 중복되어도
    # 한 번만 카운트한다 (중복 시 recall이 1.0을 초과하는 것을 방지).
    hits = len(relevant_set & set(retrieved_subset))

    return hits / len(relevant_ids)


def precision_at_k(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 중 관련 결과의 비율.

    중복 검색 결과를 처리하는 정책 (HQ-C1-DIRECTIVE-NAE-PHASE5.1-REMEDIATION-004):
    - retrieved IDs는 순서를 보존하며 중복 제거한다 (effective retrieved).
    - numerator = effective retrieved IDs 중 gold_tsu_ids에 포함된 고유 ID 수
    - denominator = effective retrieved IDs 수
    - effective retrieved IDs가 비어 있으면 precision = 0.0

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요, 중복 가능).
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 ~ 1.0 사이의 Precision 값.
    """
    if not retrieved_ids:
        return 0.0

    if k is not None:
        retrieved_subset = retrieved_ids[:k]
    else:
        retrieved_subset = retrieved_ids

    # HQ 정책: 순서를 보존하며 중복 제거 (effective retrieved)
    seen: Set[str] = set()
    effective_retrieved: List[str] = []
    for rid in retrieved_subset:
        if rid not in seen:
            seen.add(rid)
            effective_retrieved.append(rid)

    relevant_set: Set[str] = set(relevant_ids)
    # numerator = effective retrieved IDs 중 gold_tsu_ids에 포함된 고유 ID 수
    hits = len(relevant_set & set(effective_retrieved))
    # denominator = effective retrieved IDs 수
    return hits / len(effective_retrieved)


def mean_reciprocal_rank(
    retrieved_ids: List[str],
    relevant_ids: List[str],
) -> float:
    """첫 번째 관련 결과가 몇 번째인지 역수.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록 (순서 중요).
        relevant_ids: gold standard 관련 TSU ID 목록.

    Returns:
        1/rank 값. 관련 결과가 없으면 0.0.
    """
    relevant_set: Set[str] = set(relevant_ids)

    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_set:
            return 1.0 / rank

    return 0.0


# ------------------------------------------------------------------
# Aggregation Helpers
# ------------------------------------------------------------------

def hit_rate(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    k: int | None = None,
) -> float:
    """Top-K 안에 최소 하나의 관련 결과가 있는지 여부.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록.
        relevant_ids: gold standard 관련 TSU ID 목록.
        k: 사용할 K. None이면 len(retrieved_ids) 사용.

    Returns:
        0.0 또는 1.0.
    """
    recall = recall_at_k(retrieved_ids, relevant_ids, k)
    return 1.0 if recall > 0.0 else 0.0


def compute_all_metrics(
    retrieved_ids: List[str],
    relevant_ids: List[str],
    top_k: int = 5,
) -> Dict[str, float]:
    """모든 지표를 한 번에 계산.

    Args:
        retrieved_ids: 검색 결과 TSU ID 목록.
        relevant_ids: gold standard 관련 TSU ID 목록.
        top_k: 사용할 K 값.

    Returns:
        {"recall@K": ..., "precision@K": ..., "mrr": ..., "hit_rate": ...}
    """
    return {
        f"recall@{top_k}": recall_at_k(retrieved_ids, relevant_ids, top_k),
        f"precision@{top_k}": precision_at_k(retrieved_ids, relevant_ids, top_k),
        "mrr": mean_reciprocal_rank(retrieved_ids, relevant_ids),
        f"hit_rate@{top_k}": hit_rate(retrieved_ids, relevant_ids, top_k),
    }