"""tests/test_citation_disclosure_tier.py — NAE.citation_disclosure의
authority_tier(T1-T4) 라벨 축 회귀 테스트.

DBMA/NAE 개인 RAG 제안서 §11/§13에서 설계한 신학적 권위 등급(T1~T4) 라벨을
`NAE/citation_disclosure.py::get_tier_disclosure()`로 구현한 부분만 검증한다.
기존 `authority_class`(ADR-030 §7.3) 축과는 완전히 독립된 축이므로, 기존
`get_disclosure()` 동작(tests/test_nae_f6_chat_wiring.py::TestDisclosure)에는
영향이 없어야 한다 — 이 파일은 그 기존 테스트를 중복하지 않는다.

실제 문서에 authority_tier를 부여하는 큐레이션 파이프라인은 아직 없다
(제안서 §14.5) — 이 테스트는 라벨 조회 함수 자체의 결정론적 동작만 검증한다.
"""
from __future__ import annotations

import pytest

from NAE.citation_disclosure import get_tier_disclosure


class TestT1T2NoDisclosure:
    def test_t1_returns_none(self):
        assert get_tier_disclosure("T1") is None

    def test_t2_returns_none(self):
        assert get_tier_disclosure("T2") is None

    def test_missing_tier_returns_none(self):
        assert get_tier_disclosure(None) is None
        assert get_tier_disclosure("") is None


class TestT3RequiresCounterRef:
    def test_t3_without_counter_refs_raises(self):
        with pytest.raises(ValueError, match="counter_refs"):
            get_tier_disclosure("T3")

    def test_t3_with_empty_counter_refs_raises(self):
        with pytest.raises(ValueError, match="counter_refs"):
            get_tier_disclosure("T3", counter_refs=[])

    def test_t3_with_counter_ref_returns_warning(self):
        text = get_tier_disclosure(
            "T3", counter_refs=["t2-hoekema-mormonism-critique"]
        )
        assert text is not None
        assert "T3" in text
        assert "정통 교리로 제시된 것이 아니라" in text
        assert "t2-hoekema-mormonism-critique" in text

    def test_t3_includes_tradition_when_given(self):
        text = get_tier_disclosure(
            "T3", tradition="lds", counter_refs=["t2-westminster-ch1"]
        )
        assert "lds" in text

    def test_t3_multiple_counter_refs_all_listed(self):
        text = get_tier_disclosure(
            "T3",
            counter_refs=["t2-hoekema-mormonism-critique", "t1-westminster-ch2"],
        )
        assert "t2-hoekema-mormonism-critique" in text
        assert "t1-westminster-ch2" in text


class TestT4Blocked:
    def test_t4_returns_review_message(self):
        text = get_tier_disclosure("T4")
        assert text is not None
        assert "T4" in text
        assert "검토" in text


class TestUnknownTier:
    def test_unknown_tier_raises(self):
        with pytest.raises(ValueError, match="Unknown authority_tier"):
            get_tier_disclosure("T5")

    def test_unknown_tier_does_not_silently_pass(self):
        with pytest.raises(ValueError):
            get_tier_disclosure("primary_doctrinal")  # authority_class 값 오용 방지


class TestAxisIndependence:
    def test_existing_authority_class_api_unaffected(self):
        from NAE.citation_disclosure import get_disclosure

        assert get_disclosure("historical_witness") is not None
        assert get_disclosure("verified") is None
        assert get_disclosure(None) is None
