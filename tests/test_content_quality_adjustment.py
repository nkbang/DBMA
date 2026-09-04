"""Regression test — core.retrieval.compute_content_quality_factor()
(2026-07-23). Verifies the narrow (0.7~1.0) multiplicative ranking
correction that surfaces core.noise_classifier's already-computed
content_quality.quality_score (previously stored on every TSU record by
core/tsu_builder.py but never consumed by retrieval — a dead signal).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.retrieval import compute_content_quality_factor


def _tsu(quality_score=None):
    if quality_score is None:
        return {}
    return {"content_quality": {"quality_score": quality_score}}


def test_missing_field_is_neutral():
    assert compute_content_quality_factor(_tsu()) == 1.0


def test_remove_policy_gets_max_penalty():
    assert compute_content_quality_factor(_tsu(0.0)) == 0.7


def test_downweight_policy_gets_partial_penalty():
    assert round(compute_content_quality_factor(_tsu(0.3)), 4) == 0.79


def test_normal_content_gets_no_penalty():
    assert compute_content_quality_factor(_tsu(1.0)) == 1.0


def test_factor_is_monotone_in_quality_score():
    low = compute_content_quality_factor(_tsu(0.2))
    high = compute_content_quality_factor(_tsu(0.8))
    assert low < high


def test_factor_never_dominates_relevance_gap():
    # Narrow-band guarantee: the widest possible penalty (0.7) must not
    # flip the ranking of two candidates whose base relevance differs by
    # more than 30% — mirrors the design intent of Evidence Reliability
    # Adjustment (SPRINT19-C), applied here to content quality.
    worst_quality_but_relevant = 0.5 * compute_content_quality_factor(_tsu(0.0))
    best_quality_but_irrelevant = 0.3 * compute_content_quality_factor(_tsu(1.0))
    assert worst_quality_but_relevant > best_quality_but_irrelevant
