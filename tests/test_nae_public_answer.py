"""tests/test_nae_public_answer.py — ADR-037 방안 B(공개 자료 근거 답변) 검증.

수용 기준 대응: AC-2(검색 범위 문구), AC-3(근거 0건이면 생성 안 함), AC-4(내 서재
경로와 미병합), AC-5(소스별 고지), AC-6(저장 계층 무변경), AC-7(모듈 비활성 no-op).
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from NAE import public_answer as pa

DAGG = {
    "tsu_id": "TSU-0000689",
    "retrieval_score": 0.5974,
    "evidence_paragraph": "But what is a church, according to the teaching of the inspired word.",
    "authority_class": "historical_witness",
    "bibliography": {
        "author": "John L. Dagg",
        "work": "Church Order",
        "identifier": "Dagg_Church_Order",
        "page_start": 82,
        "page_end": 82,
        "paragraph_index": 456,
    },
}
HISCOX = {
    "tsu_id": "TSU-0003533",
    "retrieval_score": 0.617,
    "evidence_paragraph": "Offenses calling for discipline are usually considered as of two classes.",
    "authority_class": "historical_witness",
    "bibliography": {
        "author": "Edward T. Hiscox",
        "work": "The Standard Manual for Baptist Churches",
        "identifier": "Hiscox_Standard_Manual",
        "page_start": 36,
        "page_end": 36,
        "paragraph_index": 100,
    },
}


class TestSelectEvidence:
    def test_skips_empty_paragraphs_and_non_dicts(self):
        empty = {**DAGG, "evidence_paragraph": "   "}
        assert pa.select_evidence([empty, "x", None, HISCOX]) == [HISCOX]

    def test_same_paragraph_is_used_once(self):
        # 같은 (identifier, 문단 번호)가 서로 다른 TSU로 두 번 검색될 수 있다(Dagg p.296 §1520)
        dup = {**DAGG, "tsu_id": "TSU-OTHER"}
        assert pa.select_evidence([DAGG, dup, HISCOX]) == [DAGG, HISCOX]

    def test_caps_at_max_items_preserving_order(self):
        hits = []
        for i in range(10):
            h = {**DAGG, "tsu_id": f"T{i}", "bibliography": {**DAGG["bibliography"], "paragraph_index": i}}
            hits.append(h)
        chosen = pa.select_evidence(hits)
        assert [h["tsu_id"] for h in chosen] == [f"T{i}" for i in range(pa.MAX_EVIDENCE)]

    def test_empty_input(self):
        assert pa.select_evidence([]) == []
        assert pa.select_evidence(None) == []  # type: ignore[arg-type]


class TestBuildPackage:
    def test_none_when_no_usable_evidence(self):
        assert pa.build_public_evidence_package("q", []) is None
        assert pa.build_public_evidence_package("q", [{**DAGG, "evidence_paragraph": ""}]) is None

    def test_package_carries_question_evidence_and_labels(self):
        pkg = pa.build_public_evidence_package("Dagg는 무엇을 말합니까?", [DAGG, HISCOX])
        assert pkg.question == "Dagg는 무엇을 말합니까?"
        assert len(pkg.top_k_results) == 2 and len(pkg.citations) == 2
        ctx = pkg.llm_context_block
        assert 'id="TSU-0000689"' in ctx and "출처:" in ctx
        assert "John L. Dagg" in ctx and "Church Order" in ctx and "p.82" in ctx
        assert "Offenses calling for discipline" in ctx

    def test_paragraph_is_capped(self):
        long_hit = {**DAGG, "evidence_paragraph": "word " * 3000}
        pkg = pa.build_public_evidence_package("q", [long_hit])
        assert len(pkg.top_k_results[0].content) <= pa.MAX_PARAGRAPH_CHARS

    def test_citation_metadata_supports_source_matching(self):
        pkg = pa.build_public_evidence_package("q", [DAGG])
        cit = pkg.citations[0]
        assert cit.source_author == "John L. Dagg" and cit.source_title == "Church Order"


class TestDisclosures:
    def test_per_source_no_fuller_on_dagg_hiscox(self):
        texts = pa.public_disclosures([DAGG, HISCOX])
        assert len(texts) == 2
        assert all("Fuller" not in t for t in texts)
        assert any("John L. Dagg" in t for t in texts) and any("Hiscox" in t for t in texts)

    def test_same_source_disclosure_not_repeated(self):
        assert len(pa.public_disclosures([DAGG, {**DAGG, "tsu_id": "X"}])) == 1

    def test_non_historical_witness_has_none(self):
        assert pa.public_disclosures([{**DAGG, "authority_class": "verified"}]) == []


class TestScopeNote:
    def test_none_when_scope_unknown(self):
        assert pa.scope_note(None) is None
        assert pa.scope_note([]) is None

    def test_lists_actual_sources_and_states_out_of_scope_meaning(self):
        note = pa.scope_note(["John L. Dagg — Church Order", "Edward T. Hiscox — Manual"])
        assert "John L. Dagg" in note and "Edward T. Hiscox" in note
        assert "검색 범위 밖" in note

    def test_indexed_sources_reads_payload_and_caches(self):
        pa._scope_cache.update({"at": 0.0, "value": None})
        pts = [MagicMock(payload={"author": "A B", "book": "Book One"}),
               MagicMock(payload={"author": "A B", "book": "Book One"}),
               MagicMock(payload={"author": "C D", "book": ""})]
        client = MagicMock()
        client.scroll.return_value = (pts, None)
        with patch("NAE.pipeline.index.qdrant_store.get_client", return_value=client):
            first = pa.indexed_sources(now=1000.0)
            second = pa.indexed_sources(now=1100.0)  # TTL 이내 → 캐시
        assert first == ["A B — Book One", "C D"]
        assert second == first
        assert client.scroll.call_count == 1

    def test_indexed_sources_failure_returns_none_not_stale_claim(self):
        pa._scope_cache.update({"at": 0.0, "value": None})
        with patch("NAE.pipeline.index.qdrant_store.get_client", side_effect=RuntimeError("down")):
            assert pa.indexed_sources(now=5000.0) is None


class TestGenerationIntegration:
    def test_prompt_uses_grounding_directive_and_only_public_evidence(self):
        from core.generation import GenerationService

        pkg = pa.build_public_evidence_package("Dagg는 교회를 어떻게 정의합니까?", [DAGG])
        prompt, used = GenerationService._build_prompt(pkg)
        assert used is True
        assert "지시:" in prompt and "자료:" in prompt
        assert "But what is a church" in prompt
        assert "Dagg는 교회를 어떻게 정의합니까?" in prompt

    def test_unsupported_number_is_flagged_by_citation_verifier(self):
        from core.generation import GenerationService

        pkg = pa.build_public_evidence_package("q", [DAGG])
        answer = (
            "1689 고백서가 그렇게 가르칩니다"
            "(출처: Church Order — John L. Dagg)."
        )
        with patch("ollama.generate", return_value={"response": answer}):
            result = GenerationService().generate(pkg)
        assert result.citation_check is not None
        assert result.citation_check.has_issues
        assert "1689" in result.citation_check.issues[0].tokens

    def test_supported_citation_has_no_issue(self):
        from core.generation import GenerationService

        pkg = pa.build_public_evidence_package("q", [DAGG])
        answer = "교회는 성경의 가르침에 따라 정의됩니다(출처: Church Order — John L. Dagg)."
        with patch("ollama.generate", return_value={"response": answer}):
            result = GenerationService().generate(pkg)
        assert not result.citation_check.has_issues


class TestIsolationAndWiring:
    def test_module_does_not_touch_dbma_store_or_write_apis(self):
        # 독스트링·주석은 "접근하지 않는다"고 설명하며 금지어를 언급하므로 코드(ast)만 검사한다
        import ast

        tree = ast.parse(inspect.getsource(pa))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(node):
                node.body = node.body[1:] or [ast.Pass()]
        code = ast.unparse(tree)
        for forbidden in ("6333", "dbma_qdrant", ".upsert(", "upsert_points", ".delete(", "create_collection"):
            assert forbidden not in code, forbidden

    def test_chat_answer_path_still_does_not_reference_bridge_or_public_answer(self):
        import ui.pages.chat as chat

        for fn in (chat.generate_answer, chat._handle_user_message):
            src = inspect.getsource(fn)
            assert "bridge_query" not in src
            assert "public_answer" not in src
            assert "NAE.retrieval_adapter" not in src

    def test_section_is_noop_when_module_disabled(self, monkeypatch):
        import ui.components.nae_public_section as sec
        from core import module_registry

        monkeypatch.setattr(module_registry, "is_enabled", lambda *a, **k: False)
        button = MagicMock()
        monkeypatch.setattr(sec.st, "button", button)
        monkeypatch.setattr(sec.st, "markdown", MagicMock())
        sec.render_nae_public_section(key_prefix="chat")
        button.assert_not_called()

    def test_answer_section_hidden_without_paragraph_evidence(self, monkeypatch):
        import ui.components.nae_public_section as sec

        button = MagicMock(return_value=False)
        monkeypatch.setattr(sec.st, "button", button)
        monkeypatch.setattr(sec.st, "markdown", MagicMock())
        # 구형 Citation 객체(dict 아님)만 있는 결과 → 답변 기능 미제공
        sec._render_public_answer("chat", "q", [object()], "k")
        button.assert_not_called()

    def test_button_click_generates_only_from_public_evidence_and_stores_answer(self, monkeypatch):
        import ui.components.nae_public_section as sec

        state: dict = {}
        monkeypatch.setattr(sec.st, "session_state", state)
        monkeypatch.setattr(sec.st, "markdown", MagicMock())
        monkeypatch.setattr(sec.st, "caption", MagicMock())
        monkeypatch.setattr(sec.st, "warning", MagicMock())
        monkeypatch.setattr(sec.st, "button", MagicMock(return_value=True))
        monkeypatch.setattr(sec.st, "spinner", MagicMock())
        monkeypatch.setattr(sec.st, "write_stream", lambda s: "".join(list(s)))
        monkeypatch.setattr(sec, "indexed_sources", lambda: ["John L. Dagg — Church Order"])

        fake_stream = MagicMock()
        fake_stream.__iter__ = lambda self: iter(["교회는 ", "회중입니다."])
        fake_stream.to_result.return_value = MagicMock(
            answer="교회는 회중입니다.", error=None, claim_guard_result=None, citation_check=None
        )
        gen_service = MagicMock()
        gen_service.return_value.generate_stream.return_value = fake_stream
        with patch("core.generation.GenerationService", gen_service):
            sec._render_public_answer("chat", "교회란?", [DAGG], "chat_answer")

        pkg = gen_service.return_value.generate_stream.call_args.args[0]
        assert "But what is a church" in pkg.llm_context_block  # 공개 근거만
        stored = state["chat_answer"]
        assert stored["answer"] == "교회는 회중입니다."
        assert stored["scope"] and "John L. Dagg" in stored["scope"]
        assert stored["disclosures"] and "Fuller" not in stored["disclosures"][0]
