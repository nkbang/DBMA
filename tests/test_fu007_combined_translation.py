"""FU-007 결합안: LLM 번역 + 원문 구절 표기 확장 + 교단명 사전 보정."""

from unittest.mock import patch

from core.hybrid_candidate_pipeline import _carry_scripture_notation
from core.query_translation import translate_query_terms
from core.retrieval import QueryParser


def _pair(korean: str, english: str):
    parser = QueryParser()
    return parser.parse(korean), parser.parse(english)


def test_carry_adds_roman_chapter_and_phrases_from_original_refs():
    original, translated = _pair(
        "로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?",
        "What does Romans 8:1-4 say about no condemnation for Christians?",
    )
    out = _carry_scripture_notation(original, translated)
    assert "viii" in out.translated_terms
    assert ["romans", "viii", "1"] in out.translated_phrases


def test_carry_does_not_add_dictionary_theology_terms():
    original, translated = _pair(
        "로마서 8:1-4은 그리스도인의 정죄 없음에 대해 무엇을 말합니까?",
        "What does Romans 8:1-4 say about no condemnation for Christians?",
    )
    assert "christ" in original.translated_terms  # 사전 번역어는 원문 파싱에만 있다
    out = _carry_scripture_notation(original, translated)
    assert "christ" not in out.translated_terms
    assert "sin" not in out.translated_terms


def test_carry_is_noop_without_scripture_refs():
    original, translated = _pair(
        "오랜 우울증을 겪는 성도를 목회적으로 어떻게 돌봐야 합니까?",
        "How should we pastorally care for believers with long-term depression?",
    )
    out = _carry_scripture_notation(original, translated)
    assert out.translated_terms == []
    assert out.translated_phrases == []


def test_carry_uses_original_refs_when_translation_drops_reference():
    original, translated = _pair(
        "히브리서 11장으로 청년부 설교를 준비합니다",
        "Preparing a youth sermon on the chapter about faith",
    )
    out = _carry_scripture_notation(original, translated)
    assert "xi" in out.translated_terms
    assert any(p[0] == "hebrews" for p in out.translated_phrases)


def test_denomination_names_do_not_translate_as_sacrament_or_office():
    terms = translate_query_terms("개혁파 침례교 관점에서 교회의 권징")
    assert "baptist" in terms and "baptism" not in terms
    terms = translate_query_terms("장로교 입장")
    assert "presbyterian" in terms and "elder" not in terms


def test_llm_failure_falls_back_to_dictionary_terms():
    """LLM 번역이 실패하면 원문 파싱(사전 번역어 포함)이 그대로 Stage-1에 간다."""
    from core.hybrid_candidate_pipeline import HybridRetriever

    captured = {}

    class _Gen:
        def search(self, parsed_query, **kw):
            captured["pq"] = parsed_query
            return []

    retriever = HybridRetriever(_Gen(), tsu_by_id={})
    pq = QueryParser().parse("칭의와 성화는 어떻게 다릅니까?")
    with patch("core.hybrid_candidate_pipeline.translate_to_english", return_value=None):
        retriever.retrieve(pq, k_output=5)
    assert "justification" in captured["pq"].translated_terms
