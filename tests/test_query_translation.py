"""Korean → English query translation (core/query_translation.py) and its
wiring into QueryParser / CandidateGenerator / search cache key."""

from core.query_translation import (
    KO_EN_THEOLOGY_TERMS,
    QUERY_TRANSLATION_VERSION,
    translate_query_terms,
)
from core.retrieval import QueryParser
from core.search_cache import make_cache_key


def test_english_query_unchanged():
    assert translate_query_terms("justification and sanctification") == []
    parsed = QueryParser().parse("justification and sanctification")
    assert parsed.translated_terms == []
    assert parsed.keywords == ["justification", "sanctification"]


def test_korean_doctrine_terms_translated_in_query_order():
    terms = translate_query_terms("칭의와 성화의 관계")
    assert terms == ["justification", "justified", "sanctification", "sanctified"]


def test_longest_match_suppresses_contained_shorter_term():
    # "제사장" claims the span, so "제사"(sacrifice) must not fire inside it.
    assert translate_query_terms("제사장의 직분") == ["priest"]
    # "이신칭의" wins over the "칭의" it contains — no duplicate/extra terms.
    assert translate_query_terms("이신칭의") == ["justification", "faith"]


def test_genitive_particle_not_translated():
    # 조사 "의" must never map to anything (no single-syllable "의" entry).
    assert "의" not in KO_EN_THEOLOGY_TERMS
    assert translate_query_terms("하나님의 사랑") == ["god", "love"]


def test_book_names_prepended_alpha_only():
    assert translate_query_terms("사무엘상 해설", ["1 samuel"]) == ["samuel"]


def test_parser_appends_translations_to_keywords():
    parsed = QueryParser().parse("로마서 8장 28절 해설")
    assert parsed.detected_books == ["ROM"]
    assert parsed.translated_terms[0] == "romans"
    # Korean keywords kept, English appended after them.
    assert parsed.keywords[: len(parsed.keywords) - len(parsed.translated_terms)] == ["로마서", "해설"]
    assert "romans" in parsed.keywords
    assert parsed.to_dict()["translated_terms"] == parsed.translated_terms


def test_parser_korean_doctrine_query_gets_english_keywords():
    parsed = QueryParser().parse("칭의와 성화의 관계")
    assert {"justification", "sanctification"} <= set(parsed.keywords)
    assert {"칭의", "성화"} <= set(parsed.keywords)


def test_cache_key_depends_on_translation_version(monkeypatch):
    import core.search_cache as sc

    k1 = make_cache_key("칭의", 10, None, "fp")
    monkeypatch.setattr(sc, "QUERY_TRANSLATION_VERSION", QUERY_TRANSLATION_VERSION + "x")
    k2 = make_cache_key("칭의", 10, None, "fp")
    assert k1 != k2


# --- v2: chapter/verse terms and verse phrases (2026-09-26) ---------------

from core.query_translation import scripture_ref_phrases, scripture_ref_terms, to_roman
from core.retrieval import BOOK_ID_TO_NAMES, ScriptureReference


def test_to_roman():
    assert [to_roman(n) for n in (1, 4, 8, 9, 23, 40, 119, 150)] == [
        "i", "iv", "viii", "ix", "xxiii", "xl", "cxix", "cl"
    ]


def test_scripture_ref_terms_verse_and_chapter_only():
    assert scripture_ref_terms([ScriptureReference("ROM", 8, 28)]) == ["viii", "8", "28"]
    # verse_start == 0 is the parser's "chapter only" sentinel — no verse term.
    assert scripture_ref_terms([ScriptureReference("PSA", 23, 0)]) == ["xxiii", "23"]


def test_production_parser_translates_korean_chapter_verse():
    # "8장 28절" is only parsed by EnhancedQueryParser (the production
    # QueryParser alias), after the base parse — translation must re-run.
    parsed = QueryParser().parse("로마서 8장 28절")
    assert parsed.translated_terms == ["romans", "viii", "8", "28"]
    assert ["romans", "viii", "28"] in parsed.translated_phrases
    assert ["rom", "viii", "28"] in parsed.translated_phrases


def test_verse_phrases_skip_short_and_non_ascii_aliases():
    phrases = scripture_ref_phrases([ScriptureReference("JHN", 3, 16)], BOOK_ID_TO_NAMES)
    assert ["john", "iii", "16"] in phrases
    assert all(p[0] not in {"jn", "요한복음", "요"} for p in phrases)


def test_english_query_gets_no_phrases():
    assert QueryParser().parse("Romans 8:28").translated_phrases == []


# --- v3: numbered-book (ordinal prefix) verse matches -----------------------

import pytest

from core.query_translation import verse_phrase_match_kind

_JOHN_3_16 = [["john", "iii", "16"], ["john", "3", "16"]]


@pytest.mark.parametrize("text,kind", [
    ("For God so loved the world, John iii. 16.", "exact"),
    ("see John 3:16 again", "exact"),
    ("He laid down his life for us, 1 John iii. 16.", "ordinal_only"),
    ("First John iii. 16", "ordinal_only"),
    ("I. John iii. 16 and also John 3:16", "exact"),  # one unprefixed hit suffices
    ("Levi John iii. 16", "exact"),  # a word ending in "i" is not an ordinal
    ("no reference here", None),
])
def test_verse_phrase_match_kind(text, kind):
    assert verse_phrase_match_kind(text, _JOHN_3_16) == kind
