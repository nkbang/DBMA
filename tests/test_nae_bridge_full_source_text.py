"""bridge_query()가 LLM에 넘기는 근거 본문이 잘리지 않는지 검증.

[2026-09-10] 회귀 방지 대상: `NAE/retrieval_adapter.py::bridge_query()`가
`RankedCandidate.content`에 `content_excerpt`(=`source_text[:200]`)를 넣고
있었다. 그 값은 `core/retrieval.py::ContextAssembler.assemble()`을 지나
그대로 `llm_context_block`이 되므로, 모델은 문장 중간에서 잘린 조각을
근거로 받아 답을 쓰고 있었다 — 실측(Fuller Vol01 3,643건)에서 TSU
`source_text` 평균 길이가 204자라 200자 상한이 실제로 물리는 레코드가
상당수였다.

`content_excerpt` 200자는 ADR-024 §C 표가 정한 계약(인용 카드 발췌)이므로
그대로 두고, LLM 문맥용 전문만 별도 필드로 분리한 것이 수정 내용이다.
따라서 이 테스트는 "둘이 각자 제 역할을 한다"를 함께 검증한다.

Qdrant/Ollama 없이 도는 순수 단위 테스트다 — 검증 대상이 payload→후보
매핑이라는 순수 변환이라서, 살아있는 인덱스가 필요 없다.
"""
import pytest


LONG_TEXT = (
    "Though the Gospel, strictly speaking, is not a Law, but a Message of "
    "pure Grace; yet it virtually requires Obedience, and such an Obedience "
    "as includes saving Faith, which is the root of all acceptable service, "
    "and without which no man shall see the Lord, as the Apostle plainly "
    "testifies in his Epistle to the Hebrews."
)


def _hit(source_text: str) -> dict:
    return {
        "tsu_id": "TSU-0004128",
        "score": 0.8123,
        "payload": {
            "tsu_id": "TSU-0004128",
            "source_text": source_text,
            "author": "Andrew Fuller",
            "book": "The Works of the Rev. Andrew Fuller — Vol. 1",
            "paragraph": 34,
            "sentence": 2,
            "source_id": "Fuller_Complete_Works_Vol01",
            "work_id": "WORK-FULLER-01",
            "edition_id": "ED-FULLER-01",
            "source_type": "soteriology",
        },
    }


class TestMappingKeepsBothFields:
    def test_excerpt_still_capped_at_200_adr024_contract(self):
        from NAE.retrieval_adapter import _map_nae_to_citation_metadata
        assert len(LONG_TEXT) > 200, "픽스처가 200자를 넘겨야 이 테스트가 의미를 갖는다"
        meta = _map_nae_to_citation_metadata(_hit(LONG_TEXT))
        assert meta["content_excerpt"] == LONG_TEXT[:200]

    def test_full_source_text_is_carried_untruncated(self):
        from NAE.retrieval_adapter import _map_nae_to_citation_metadata
        meta = _map_nae_to_citation_metadata(_hit(LONG_TEXT))
        assert meta["source_text"] == LONG_TEXT

    def test_missing_source_text_yields_empty_not_none(self):
        """payload에 source_text가 없어도 후속 문자열 연산이 깨지지 않아야 한다."""
        from NAE.retrieval_adapter import _map_nae_to_citation_metadata
        hit = _hit("")
        del hit["payload"]["source_text"]
        meta = _map_nae_to_citation_metadata(hit)
        assert meta["source_text"] == ""
        assert meta["content_excerpt"] == ""


class TestBridgeQueryCandidateContent:
    """bridge_query() 내부에서 RankedCandidate.content가 전문으로 채워지는지.

    bridge_query()는 Citation 리스트를 반환하므로 RankedCandidate를 직접
    볼 수 없다 — CitationBuilder를 가로채 후보를 붙잡는다.
    """

    def test_candidate_content_is_full_text_not_excerpt(self, monkeypatch):
        import NAE.retrieval_adapter as adapter
        import core.retrieval as core_retrieval

        monkeypatch.setattr(adapter, "_is_nae_pd_enabled", lambda: True, raising=False)
        monkeypatch.setattr(adapter, "search", lambda *a, **k: [_hit(LONG_TEXT)])

        fake_ollama = type("O", (), {})()
        fake_ollama.embeddings = lambda **kw: {"embedding": [0.0] * 1024}
        monkeypatch.setattr(adapter, "ollama_client", fake_ollama, raising=False)

        captured = {}
        original_build = core_retrieval.CitationBuilder.build_citations

        def spy(self, candidates, *a, **k):
            captured["candidates"] = candidates
            return original_build(self, candidates, *a, **k)

        monkeypatch.setattr(core_retrieval.CitationBuilder, "build_citations", spy)

        adapter.bridge_query("복음과 순종의 관계", top_k=1, limit_check=False)

        assert captured.get("candidates"), "CitationBuilder가 호출되지 않았다"
        content = captured["candidates"][0].content
        assert content == LONG_TEXT
        assert len(content) > 200
        assert content.endswith("Hebrews."), "문장 끝이 잘리지 않아야 한다"
