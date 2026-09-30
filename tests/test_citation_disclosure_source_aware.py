"""tests/test_citation_disclosure_source_aware.py — EUAT-001 Issue 5 회귀 테스트.

`get_disclosure()`는 `historical_witness` 등급이면 무조건 Andrew Fuller 고정
고지문을 반환했다. Dagg/Hiscox 같은 다른 `historical_witness` 소스 카드에도
"Andrew Fuller ... 에서 자동 추출" 고지가 붙어 잘못된 저자가 표시됐다. 이 테스트는
소스 정보가 주어지면 Fuller에게만 Fuller 고정 고지문이 붙는지, 하위 호환이
유지되는지 검증한다.
"""
from __future__ import annotations

from NAE.citation_disclosure import (
    HISTORICAL_WITNESS_DISCLOSURE,
    get_disclosure,
)


class TestBackwardCompatible:
    def test_no_source_info_returns_fixed_fuller_text(self):
        assert get_disclosure("historical_witness") == HISTORICAL_WITNESS_DISCLOSURE

    def test_non_historical_witness_returns_none_even_with_source(self):
        assert get_disclosure("verified", author="John L. Dagg") is None
        assert get_disclosure(None, author="John L. Dagg") is None


class TestFullerKeepsFixedNotice:
    def test_fuller_by_source_id(self):
        assert (
            get_disclosure("historical_witness", source_id="BAP-MISS-FULLER-VOL03")
            == HISTORICAL_WITNESS_DISCLOSURE
        )

    def test_fuller_by_identifier(self):
        assert (
            get_disclosure("historical_witness", identifier="Fuller_Complete_Works_Vol01")
            == HISTORICAL_WITNESS_DISCLOSURE
        )

    def test_fuller_by_author_full_name(self):
        assert (
            get_disclosure("historical_witness", author="Andrew Fuller")
            == HISTORICAL_WITNESS_DISCLOSURE
        )


class TestOtherSourcesDoNotGetFullerNotice:
    def test_dagg_names_dagg_not_fuller(self):
        text = get_disclosure(
            "historical_witness",
            identifier="Dagg_Church_Order",
            author="John L. Dagg",
            work="Church Order",
        )
        assert text is not None
        assert "John L. Dagg" in text and "Church Order" in text
        assert "Fuller" not in text
        assert "historical_witness" in text

    def test_hiscox_names_hiscox_not_fuller(self):
        text = get_disclosure(
            "historical_witness",
            identifier="Hiscox_Standard_Manual",
            author="Edward T. Hiscox",
            work="The Standard Manual for Baptist Churches",
        )
        assert "Edward T. Hiscox" in text
        assert "Fuller" not in text

    def test_generic_text_makes_no_fuller_specific_claims(self):
        # 페이지 번호 없음/신뢰도 미교정/성구 추출 누락은 Fuller OCR에 대한 서술이다.
        text = get_disclosure("historical_witness", author="John L. Dagg", work="Church Order")
        assert "페이지" not in text
        assert "No page numbers" not in text
        assert "uncalibrated" not in text

    def test_same_surname_different_person_is_not_fuller(self):
        text = get_disclosure(
            "historical_witness", author="Thomas Fuller", work="The Holy State"
        )
        assert "Thomas Fuller" in text
        assert "Andrew Fuller" not in text

    def test_missing_names_falls_back_without_fuller(self):
        # 소스 정보 필드를 하나라도 넘겼지만 이름이 없는 경우(예: identifier만)
        text = get_disclosure("historical_witness", identifier="Dagg_Church_Order")
        assert text is not None
        assert "Fuller" not in text
        assert "이 자료" in text
