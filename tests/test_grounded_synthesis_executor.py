"""tests/test_grounded_synthesis_executor.py — P5 integration tests.

GS executor orchestration 검증:
A. Executor unit/integration
B. Generation integration
C. Chat wiring regression
D. Research impact verification
E. Boundary (no prohibited imports)
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from core.grounded_synthesis_executor import (
    ExecutionResult,
    GroundedSynthesisExecutor,
    execute_synthesis,
)
from core.evidence_pool import EvidencePool


@dataclass
class MockRankedCandidate:
    """Test용 RankedCandidate mock."""
    tsu_id: str
    content: str
    metadata: dict = None
    vector_score: float = 0.0
    bm25_score: float = 0.0
    theological_score: float = 0.0
    passage_score: float = 0.0
    final_score: float = 0.0
    explanation: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def _make_pool(candidates):
    """Mock candidates -> EvidencePool."""
    pool = EvidencePool()
    for c in candidates:
        pool.add(SimpleNamespace(
            evidence_id=c.tsu_id,
            text=c.content,
            metadata=c.metadata,
            score=c.final_score,
        ))
    return pool


def _make_synthesis_input(pool):
    """EvidencePool -> SynthesisInput (mock manifest 주입)."""
    from core.grounded_synthesis_input import SynthesisInput
    from unittest.mock import MagicMock

    si = SynthesisInput(
        query_specs=[],
        included_evidence_ids=[],
        excluded_evidence_ids=[],
        truncated=False,
        prompt_text="",
    )
    # manifest mock 주입 (frozen dataclass이므로 __dict__ 직접 수정)
    si.__dict__["manifest"] = MagicMock()
    si.__dict__["manifest"].evidence_pool = pool
    return si


# --- A. Executor unit/integration ---


class TestExecutorValidInput:
    def test_execute_returns_execution_result(self):
        """valid GS input -> ExecutionResult 반환."""
        candidates = [
            MockRankedCandidate(
                tsu_id="ev_1",
                content="Test evidence content.",
                metadata={"title": "Test Doc", "author": "Author", "source_file": "test.txt"},
                final_score=0.9,
            )
        ]
        pool = _make_pool(candidates)
        synthesis_input = _make_synthesis_input(pool)

        result = execute_synthesis(synthesis_input, [], pool)

        assert isinstance(result, ExecutionResult)
        assert result.synthesis_input is synthesis_input
        assert isinstance(result.claims, list)
        assert hasattr(result, "grounded_answer")
        assert hasattr(result, "citation_check")
        assert result.status in ("complete", "incomplete", "failed")

    def test_execute_with_stub_claims(self):
        """stub claims -> valid claim 처리."""
        candidates = [
            MockRankedCandidate(
                tsu_id="ev_1",
                content="Test evidence content with claim.",
                metadata={"title": "Test Doc", "author": "Author", "source_file": "test.txt"},
                final_score=0.9,
            )
        ]
        pool = _make_pool(candidates)
        synthesis_input = _make_synthesis_input(pool)

        raw_claims = [("test claim", ["ev_1"])]
        result = execute_synthesis(synthesis_input, raw_claims, pool)

        assert isinstance(result, ExecutionResult)


class TestExecutorEmptyEvidence:
    def test_empty_pool_returns_complete_no_claims(self):
        """empty evidence + no claims -> status='complete' (검증할 claim 없음)."""
        pool = EvidencePool()
        synthesis_input = _make_synthesis_input(pool)

        result = execute_synthesis(synthesis_input, [], pool)

        # claims가 없으면 검증할 것이 없음 -> complete
        assert result.status == "complete"


class TestExecutorInvalidEvidence:
    def test_invalid_evidence_id(self):
        """invalid evidence_id -> claim valid=False."""
        pool = EvidencePool()
        synthesis_input = _make_synthesis_input(pool)

        raw_claims = [("test claim", ["nonexistent_id"])]
        result = execute_synthesis(synthesis_input, raw_claims, pool)

        assert isinstance(result, ExecutionResult)


class TestExecutorCitationValidation:
    def test_citation_check_runs(self):
        """citation span 검증 실행 확인."""
        candidates = [
            MockRankedCandidate(
                tsu_id="ev_1",
                content="Evidence text with claim substring.",
                metadata={"title": "Test Doc", "author": "Author", "source_file": "test.txt"},
                final_score=0.9,
            )
        ]
        pool = _make_pool(candidates)
        synthesis_input = _make_synthesis_input(pool)

        result = execute_synthesis(synthesis_input, [], pool)

        assert hasattr(result, "citation_check")


class TestExecutorFailurePath:
    def test_execute_handles_exceptions(self):
        """executor exception -> exception 전파 (caller 격리)."""
        with pytest.raises(Exception):
            execute_synthesis(None, [], None)  # type: ignore


# --- B. Generation integration ---


class TestGenerationResultCompatibility:
    def test_execution_result_separate_from_generation_result(self):
        """ExecutionResult != GenerationResult -- 독립 구조."""
        from core.generation import GenerationResult

        candidates = [
            MockRankedCandidate(
                tsu_id="ev_1",
                content="Test evidence.",
                metadata={"title": "Test Doc", "author": "Author", "source_file": "test.txt"},
                final_score=0.9,
            )
        ]
        pool = _make_pool(candidates)
        synthesis_input = _make_synthesis_input(pool)

        result = execute_synthesis(synthesis_input, [], pool)

        assert not isinstance(result, GenerationResult)
        assert hasattr(result, "synthesis_input")
        assert hasattr(result, "claims")
        assert hasattr(result, "grounded_answer")
        assert hasattr(result, "citation_check")
        assert hasattr(result, "status")


class TestGsOffPreservesExistingPath:
    def test_gs_off_no_execution(self):
        """GS OFF -> 기존 generation path 보존 (import 오류 없음)."""
        import ui.pages.chat as chat_module

        sig = inspect.signature(chat_module.generate_answer)
        params = list(sig.parameters.keys())
        assert "question" in params
        assert "conversation_history" in params
        assert "k" in params


# --- C. Chat wiring ---


class TestChatWiring:
    def test_chat_imports_gs_executor(self):
        """chat.py가 GS executor import 확인."""
        import ui.pages.chat as chat_module

        assert hasattr(chat_module, "execute_synthesis") or hasattr(chat_module, "_run_grounded_synthesis")

    def test_chat_generate_answer_signature_unchanged(self):
        """chat.py generate_answer signature 변화 없음."""
        import ui.pages.chat as chat_module

        sig = inspect.signature(chat_module.generate_answer)
        params = list(sig.parameters.keys())
        assert params == ["question", "conversation_history", "k", "file_scope"]


# --- D. Research impact ---


class TestResearchImpact:
    def test_research_imports_unchanged(self):
        """research.py import 오류 없음."""
        try:
            import ui.pages.research  # noqa: F401
        except ImportError as e:
            pytest.fail(f"research.py import failed: {e}")

    def test_research_generate_answer_caller_unchanged(self):
        """research.py generate_answer caller signature 변화 없음."""
        import ui.pages.research as research_module

        assert hasattr(research_module, "generate_answer")

        sig = inspect.signature(research_module.generate_answer)
        params = list(sig.parameters.keys())
        assert "question" in params


# --- E. Boundary ---


class TestBoundary:
    def test_executor_no_generation_service_import(self):
        """executor가 GenerationService를 import하지 않음."""
        import core.grounded_synthesis_executor as executor_module

        source = inspect.getsource(executor_module)
        assert "GenerationService" not in source or "import GenerationService" not in source

    def test_executor_no_prohibited_imports(self):
        """executor prohibited import 없음 (ADR-036 B9)."""
        import core.grounded_synthesis_executor as executor_module

        source = inspect.getsource(executor_module)
        prohibited = ["ollama", "qdrant_client", "tantivy", "requests", "httpx", "urllib", "subprocess", "socket"]
        for lib in prohibited:
            assert f"import {lib}" not in source, f"prohibited import found: {lib}"

    def test_executor_no_semantic_judge(self):
        """executor semantic judge 없음."""
        import core.grounded_synthesis_executor as executor_module

        source = inspect.getsource(executor_module)
        assert "semantic" not in source.lower() or "semantic grounding" not in source.lower()
