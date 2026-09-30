"""tests/test_citation_verifier.py — EUAT-001 Issue 4 회귀 테스트.

EUAT-05에서 모델은 "1689 런던신앙고백서는 … (출처: The Metropolitan Tabernacle
Pulpit — C.H.Spurgeon)"이라고 썼지만, 인용된 Spurgeon 권들에는 "1689"가 없었다
(Vol41의 "Confession of Faith"는 회심자의 개인 신앙고백 설교). 이 테스트는 그
사례를 그대로 재현하고, 정상 인용이 오탐되지 않는지 함께 검증한다.
"""
from __future__ import annotations

from types import SimpleNamespace

from core.citation_verifier import (
    KIND_SOURCE_NOT_RETRIEVED,
    KIND_TOKEN_OTHER_SOURCE,
    KIND_TOKEN_UNSUPPORTED,
    issue_messages,
    verify_citations,
)


def _cand(title, author, content, source_file="x.txt"):
    return SimpleNamespace(
        metadata={"title": title, "author": author, "source_file": source_file},
        content=content,
    )


SPURGEON = _cand(
    "The Metropolitan Tabernacle Pulpit",
    "C.H. Spurgeon",
    "Converts and their confession of faith. This confession of faith is personal.",
    "Spurgeon_MTP_Vol41.txt",
)
BROADUS = _cand(
    "A treatise on the preparation and delivery of sermons",
    "Broadus, John Albert",
    "The Scriptures themselves are an authority indeed. All that they testify to be fact "
    "is thereby fully proven.",
    "Broadus_Preparation_and_Delivery_of_Sermons.txt",
)


class TestEuat05Reproduction:
    def test_1689_claim_cited_to_spurgeon_is_flagged(self):
        answer = (
            "다만, 1689 런던신앙고백서는 성경이 하나님의 말씀으로 완전하고 오류가 없으며"
            "(출처: The Metropolitan Tabernacle Pulpit — C.H.Spurgeon), 교회의 질서의 기준임을 강조합니다."
        )
        r = verify_citations(answer, [SPURGEON, BROADUS])
        assert r.citations_found == 1
        assert len(r.issues) == 1
        issue = r.issues[0]
        assert issue.kind == KIND_TOKEN_UNSUPPORTED
        assert "1689" in issue.tokens
        msgs = issue_messages(r)
        assert "1689" in msgs[0] and "확인하지 못했습니다" in msgs[0]

    def test_same_claim_passes_when_evidence_contains_1689(self):
        ev = _cand(
            "The Metropolitan Tabernacle Pulpit",
            "C.H. Spurgeon",
            "The Confession put forth in 1689 by the London ministers.",
        )
        answer = "1689 신앙고백서가 언급됩니다(출처: The Metropolitan Tabernacle Pulpit — C.H.Spurgeon)."
        assert not verify_citations(answer, [ev]).has_issues


class TestNormalCitationsNotFlagged:
    def test_korean_only_claim_has_nothing_to_verify(self):
        answer = "성경은 그 자체로 권위가 있습니다(출처: A treatise on the preparation and delivery of sermons — Broadus, John Albert)."
        r = verify_citations(answer, [BROADUS])
        assert r.citations_found == 1 and not r.has_issues

    def test_faithful_english_quote_passes(self):
        answer = (
            '"The Scriptures themselves are an authority indeed."라고 말합니다'
            "(출처: A treatise on the preparation and delivery of sermons — Broadus, John Albert)."
        )
        assert not verify_citations(answer, [BROADUS]).has_issues

    def test_misquote_is_flagged(self):
        answer = (
            '"Scriptures always contain infallible doctrinal confessions."라고 말합니다'
            "(출처: A treatise on the preparation and delivery of sermons — Broadus, John Albert)."
        )
        r = verify_citations(answer, [BROADUS])
        assert r.has_issues and r.issues[0].kind == KIND_TOKEN_UNSUPPORTED

    def test_single_unmatched_common_word_is_not_enough(self):
        # MIN_MISSING_LATIN_TOKENS=2 — 영단어 한 개 어긋남은 잡음으로 본다
        answer = "이 설교는 Preaching에 관한 것입니다(출처: A treatise on the preparation and delivery of sermons — Broadus, John Albert)."
        assert not verify_citations(answer, [BROADUS]).has_issues

    def test_hyphenated_token_is_matched_by_parts(self):
        ev = _cand("Church Order", "John L. Dagg", "The self-denial required of members is great.")
        answer = "self-denial 요구는 큽니다(출처: Church Order — John L. Dagg)."
        assert not verify_citations(answer, [ev]).has_issues

    def test_number_in_label_is_not_treated_as_claim(self):
        ev = _cand("The Metropolitan Tabernacle Pulpit 1884: Vol 30", "C. H. Spurgeon", "text")
        answer = "이 설교는 그 해에 전해졌습니다(출처: The Metropolitan Tabernacle Pulpit 1884 — C. H. Spurgeon)."
        assert not verify_citations(answer, [ev]).has_issues


class TestSourceNotRetrieved:
    def test_unknown_source_label_is_flagged(self):
        answer = "그렇게 가르칩니다(출처: Systematic Theology Handbook — Charles Hodge)."
        r = verify_citations(answer, [SPURGEON, BROADUS])
        assert [i.kind for i in r.issues] == [KIND_SOURCE_NOT_RETRIEVED]
        assert "찾지 못했습니다" in issue_messages(r)[0]

    def test_korean_translated_label_is_skipped_not_flagged(self):
        # 라틴 토큰이 2개 미만이면 서지 대조가 불가능하므로 이슈로 세지 않는다
        answer = "그렇게 말합니다(출처: 메트로폴리탄 태버내클 강단)."
        assert not verify_citations(answer, [SPURGEON]).has_issues


class TestOtherSource:
    def test_token_found_only_in_another_retrieved_source(self):
        other = _cand("Church Order", "John L. Dagg", "The confession of 1689 was adopted.")
        answer = "1689 고백서가 채택되었습니다(출처: The Metropolitan Tabernacle Pulpit — C.H.Spurgeon)."
        r = verify_citations(answer, [SPURGEON, other])
        assert r.issues and r.issues[0].kind == KIND_TOKEN_OTHER_SOURCE
        assert "다른 검색 결과" in issue_messages(r)[0]


class TestEdgeCases:
    def test_no_citations_no_issues(self):
        r = verify_citations("자료에 근거가 없습니다.", [SPURGEON])
        assert r.citations_found == 0 and not r.has_issues

    def test_empty_inputs(self):
        assert not verify_citations("", [SPURGEON]).has_issues
        assert not verify_citations("(출처: A B C)", []).has_issues
        assert issue_messages(None) == []

    def test_multiple_citations_checked_independently(self):
        answer = (
            "성경은 권위가 있습니다(출처: A treatise on the preparation and delivery of sermons — Broadus, John Albert). "
            "1689 고백서도 그렇습니다(출처: The Metropolitan Tabernacle Pulpit — C.H.Spurgeon)."
        )
        r = verify_citations(answer, [SPURGEON, BROADUS])
        assert r.citations_found == 2
        assert len(r.issues) == 1 and "1689" in r.issues[0].tokens

    def test_supports_dict_candidates_and_citation_objects(self):
        cand = {"metadata": {"title": "Church Order", "author": "John L. Dagg"}, "content": "one two"}
        cit = SimpleNamespace(source_title="Church Order", source_author="John L. Dagg", source_file="d.txt")
        answer = "1871 판입니다(출처: Church Order — John L. Dagg)."
        r = verify_citations(answer, [cand], [cit])
        assert r.issues and "1871" in r.issues[0].tokens


class TestBibliographicCitationForm:
    """모델이 "출처:" 없이 쓴 서지 형식 인용 — 2026-09-29 실제 생성(EUAT-01 공개 자료 답변)에서 관측.

    이 형식이 인식되지 않으면 검증기가 "인용 0건 → 이슈 없음"으로 통과해 버린다.
    """

    DAGG = _cand(
        "Church Order",
        "John L. Dagg",
        "The general agreement of Baptist churches, in doctrine as well as church order.",
    )

    def test_real_generated_answer_forms_are_recognized(self):
        answer = (
            "Dagg는 침례교회의 일반적인 합의를 강조합니다"
            "(Church Order — John L. Dagg, p.296, 문단 1520). "
            "또한 그는 질문을 던집니다"
            '("그러나 교회의 질서가 바뀐 것은 무엇이었는가?" — Church Order — John L. Dagg, p.99, 문단 541).'
        )
        r = verify_citations(answer, [self.DAGG])
        assert r.citations_found == 2
        assert not r.has_issues

    def test_fabricated_number_in_bibliographic_form_is_flagged(self):
        answer = "1689 고백서가 그렇게 가르칩니다(Church Order — John L. Dagg, p.296, 문단 1520)."
        r = verify_citations(answer, [self.DAGG])
        assert r.citations_found == 1
        assert r.issues and "1689" in r.issues[0].tokens

    def test_unknown_source_in_bibliographic_form_is_flagged(self):
        answer = "그렇게 가르칩니다(Systematic Theology Handbook — Charles Hodge, p.12)."
        r = verify_citations(answer, [self.DAGG])
        assert [i.kind for i in r.issues] == [KIND_SOURCE_NOT_RETRIEVED]

    def test_ordinary_parenthetical_is_not_a_citation(self):
        # 줄표가 있어도 쪽/문단 표지가 없으면 인용으로 보지 않는다
        answer = "교회(회중 — 신자의 모임)는 성경에 근거합니다. 자세한 것은 (참고) 항목을 보십시오."
        assert verify_citations(answer, [self.DAGG]).citations_found == 0


class TestSourceNamesInSentenceAreSupported:
    """실제 생성(EUAT-04 공개 자료 답변)에서 나온 오탐 회귀: 문장에 책 제목·저자 이름이
    나오고 인용 라벨은 "p.167, 문단 790"뿐인 경우. 제목·저자는 본문이 아니라 서지 정보에
    있으므로 근거 본문에만 대조하면 오탐된다."""

    HISCOX = _cand(
        "The Standard Manual for Baptist Churches",
        "Edward T. Hiscox",
        "They held the Bible to be the only rule and authority in concerns of religious faith and practice.",
        "Hiscox_Standard_Manual",
    )

    def test_real_generated_sentence_with_page_only_label_is_not_flagged(self):
        answer = (
            'The Standard Manual for Baptist Churches — Edward T. Hiscox는 "They held the Bible to be '
            'the only rule and authority in concerns of religious faith and practice"라고 합니다'
            "(출처: p.167, 문단 790)."
        )
        r = verify_citations(answer, [self.HISCOX])
        assert r.citations_found == 1
        assert not r.has_issues

    def test_misquote_with_source_names_is_still_flagged(self):
        answer = (
            'The Standard Manual for Baptist Churches — Edward T. Hiscox는 "They rejected every '
            'creed whatsoever and confession"라고 합니다(출처: p.167, 문단 790).'
        )
        r = verify_citations(answer, [self.HISCOX])
        assert r.has_issues and r.issues[0].kind == KIND_TOKEN_UNSUPPORTED
