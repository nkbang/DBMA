"""Regression test — core/retrieval.py::compute_source_tier_bonus()
(PM 정렬 감사 선결 #5).

종전 구현은 이름과 달리 source_tier를 전혀 보지 않고 review_status만
봤다 — provenance 없는 기존 코퍼스에서 항상 0.0(no-op). 이제 source_tier
등급을 반영하되, 기존 코퍼스 동작(0.0)은 그대로 둔다.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import compute_source_tier_bonus


def test_no_provenance_returns_zero():
    # 기존 코퍼스 — source_provenance 필드 자체가 없음. 동작 불변.
    assert compute_source_tier_bonus({}) == 0.0
    assert compute_source_tier_bonus({"content": "x", "source_provenance": None}) == 0.0


def test_primary_tier_reviewed_full_value():
    tsu = {"source_provenance": {"source_tier": "logos_primary", "review_status": "reviewed"}}
    assert compute_source_tier_bonus(tsu) == 1.0


def test_scholarly_tier_graded_below_primary():
    reviewed = {"source_provenance": {"source_tier": "scholarly_commentary", "review_status": "reviewed"}}
    assert compute_source_tier_bonus(reviewed) == 0.7


def test_personal_research_tier_low():
    tsu = {"source_provenance": {"source_tier": "personal_research", "review_status": "reviewed"}}
    assert compute_source_tier_bonus(tsu) == 0.3


def test_unreviewed_tiered_source_gets_partial_not_full():
    reviewed = {"source_provenance": {"source_tier": "scholarly_commentary", "review_status": "reviewed"}}
    unreviewed = {"source_provenance": {"source_tier": "scholarly_commentary", "review_status": "unreviewed"}}
    assert compute_source_tier_bonus(unreviewed) < compute_source_tier_bonus(reviewed)
    assert compute_source_tier_bonus(unreviewed) > 0.0  # provenance 없는 자료보단 높음


def test_unknown_tier_string_gets_midpoint():
    tsu = {"source_provenance": {"source_tier": "some_new_tier", "review_status": "reviewed"}}
    assert compute_source_tier_bonus(tsu) == 0.5


def test_no_tier_falls_back_to_review_flag():
    # source_tier가 비어 있으면 종전 동작(reviewed면 1.0, 아니면 0.0)
    reviewed = {"source_provenance": {"review_status": "approved"}}
    unreviewed = {"source_provenance": {"review_status": "unreviewed"}}
    assert compute_source_tier_bonus(reviewed) == 1.0
    assert compute_source_tier_bonus(unreviewed) == 0.0


def test_result_clamped_to_unit_interval():
    for tier in ("logos_primary", "scholarly_commentary", "personal_research", "weird", ""):
        for status in ("reviewed", "unreviewed", None):
            v = compute_source_tier_bonus(
                {"source_provenance": {"source_tier": tier, "review_status": status}}
            )
            assert 0.0 <= v <= 1.0
