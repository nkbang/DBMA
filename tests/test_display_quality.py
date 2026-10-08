"""tests/test_display_quality.py — EUAT-001 Issue 6 회귀 테스트.

출처 표시 품질 보조 함수(ui/components/display_quality.py)를 검증한다:
- RRF 척도 점수에서 별점을 숨기는지(항상 ☆☆☆☆☆ 표시 방지)
- 깨진 청크/문장 조각이 헤딩 라벨로 쓰이지 않는지
- 표시할 내용 없는 "주장 검증:" 빈 라벨이 나오지 않는지
"""
from __future__ import annotations

from types import SimpleNamespace

from ui.components.display_quality import (
    RRF_SCORE_CEILING,
    claim_guard_message,
    is_comparable_relevance,
    usable_heading_label,
)


class TestComparableRelevance:
    def test_rrf_scale_scores_are_not_comparable(self):
        # k=60, 랭킹 3개의 이론상 최대 ≈ 3/61 — 항상 임계값 이하
        assert not is_comparable_relevance(3 / 61)
        assert not is_comparable_relevance(0.016)
        assert not is_comparable_relevance(0.0)

    def test_ceiling_covers_rrf_max(self):
        assert 3 / 61 < RRF_SCORE_CEILING

    def test_vector_similarity_scores_are_comparable(self):
        # 무관 질의 ≈ 0.37~0.41, 관련 질의 ≈ 0.46~0.5 (chat.py 소표본 보정 주석)
        assert is_comparable_relevance(0.37)
        assert is_comparable_relevance(0.55)

    def test_none_and_garbage_are_not_comparable(self):
        assert not is_comparable_relevance(None)
        assert not is_comparable_relevance("abc")  # type: ignore[arg-type]


class TestUsableHeadingLabel:
    def test_normal_headings_kept(self):
        assert usable_heading_label("Chapter 3 > The Church") == "Chapter 3 > The Church"
        assert usable_heading_label("제3장 교회의 질서") == "제3장 교회의 질서"

    def test_garbled_chunks_rejected(self):
        assert usable_heading_label("• • ••» • • • • • • • ••• •••") is None
        assert usable_heading_label("• f t I «") is None

    def test_empty_short_and_none_rejected(self):
        assert usable_heading_label(None) is None
        assert usable_heading_label("   ") is None
        assert usable_heading_label("ab") is None

    def test_too_long_rejected(self):
        assert usable_heading_label("A " * 60) is None

    def test_sentence_fragments_rejected(self):
        # 실제 EUAT 출처: 본문 문장 조각이 제목으로 표시됨
        assert usable_heading_label("compared to it.") is None
        assert (
            usable_heading_label(
                "‘These things have I spoken unto you, that My joy may be in you."
            )
            is None
        )

    def test_short_heading_with_period_kept(self):
        # 2단어 이하는 문장 조각으로 보지 않는다 ("Preface." 등)
        assert usable_heading_label("Preface.") == "Preface."


class TestClaimGuardMessage:
    def _r(self, **kw):
        base = dict(suggested_wording=None, reason="", matched_terms=[])
        base.update(kw)
        return SimpleNamespace(**base)

    def test_prefers_suggested_wording(self):
        assert claim_guard_message(self._r(suggested_wording="범위를 한정하세요", reason="r")) == "범위를 한정하세요"

    def test_falls_back_to_reason(self):
        assert claim_guard_message(self._r(reason="절대 표현")) == "절대 표현"

    def test_falls_back_to_matched_terms(self):
        msg = claim_guard_message(self._r(matched_terms=["반드시", "항상"]))
        assert msg is not None and "반드시" in msg and "항상" in msg

    def test_nothing_to_show_returns_none(self):
        assert claim_guard_message(self._r()) is None
        assert claim_guard_message(self._r(reason="   ")) is None
        assert claim_guard_message(None) is None
