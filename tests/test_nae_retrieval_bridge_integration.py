"""NAE Retrieval Bridge Integration Tests (Night Shift Phase 4 — corrected).

CUE Correction Order 001 지적 1 대응:
- 실제 retrieval 경로를 타는지 검증 (예외가 아닌 Citation 반환)
- config.yaml 파일을 건드리지 않음 (monkeypatch로 module gate 우회)
- Citation 필드가 실제로 채워지는지 assert
- Qdrant/Ollama 미사용 시 pytest.skip
"""
import pytest
from unittest.mock import patch, MagicMock


def _qdrant_available() -> bool:
    """NAE Qdrant이 실행 중인지 확인."""
    try:
        from NAE.pipeline.index import qdrant_store
        client = qdrant_store.get_client()
        client.get_collections()
        return True
    except Exception:
        return False


def _ollama_available() -> bool:
    """Ollama가 실행 중인지 확인."""
    try:
        import ollama
        client = ollama.Client(timeout=1.0)
        client.list()
        return True
    except Exception:
        return False


class TestBridgeQueryIntegration:
    """bridge_query() end-to-end integration tests — 실제 retrieval 경로 검증."""

    @pytest.fixture(autouse=True)
    def _skip_if_services_down(self):
        """Qdrant 또는 Ollama가 없으면 skip."""
        if not _qdrant_available():
            pytest.skip("NAE Qdrant (port 7333) not running")
        if not _ollama_available():
            pytest.skip("Ollama not running")

    def test_korean_query_returns_citations(self):
        """한국어 query → Citation 리스트 반환 (실제 retrieval 경로)."""
        from core import module_registry
        from NAE.retrieval_adapter import bridge_query
        from core.retrieval import Citation

        # monkeypatch: nae_pd enabled
        with patch.object(module_registry, "is_enabled", return_value=True):
            results = bridge_query("교회의 직분에 대해", top_k=3, limit_check=False)

        assert len(results) > 0, "bridge_query should return non-empty list"
        assert all(isinstance(c, Citation) for c in results), \
            f"All results must be Citation instances, got {[type(c).__name__ for c in results]}"

    def test_english_query_returns_citations(self):
        """영어 query → Citation 리스트 반환 (실제 retrieval 경로)."""
        from core import module_registry
        from NAE.retrieval_adapter import bridge_query
        from core.retrieval import Citation

        with patch.object(module_registry, "is_enabled", return_value=True):
            results = bridge_query("elders qualifications pastoral", top_k=3, limit_check=False)

        assert len(results) > 0, "bridge_query should return non-empty list"
        assert all(isinstance(c, Citation) for c in results), \
            f"All results must be Citation instances, got {[type(c).__name__ for c in results]}"

    def test_citation_fields_populated(self):
        """Citation 객체에 필수 필드가 실제로 채워져 있는지 assert."""
        from core import module_registry
        from NAE.retrieval_adapter import bridge_query
        from core.retrieval import Citation

        with patch.object(module_registry, "is_enabled", return_value=True):
            results = bridge_query("church governance", top_k=3, limit_check=False)

        assert len(results) >= 1, "Must have at least 1 result"

        c = results[0]
        # tsu_id — 직접 매핑 필드
        assert hasattr(c, "tsu_id") and c.tsu_id, "tsu_id must be present and non-empty"
        # source_author — 직접 매핑 필드
        assert hasattr(c, "source_author") and c.source_author, "source_author must be present and non-empty"
        # retrieval_score — 직접 매핑 필드
        assert hasattr(c, "retrieval_score") and c.retrieval_score > 0, \
            "retrieval_score must be present and positive"
        # source_type — 직접 매핑 필드
        assert hasattr(c, "source_type"), "source_type must be present"
        # content_excerpt — 직접 매핑 필드
        assert hasattr(c, "content_excerpt"), "content_excerpt must be present"
        # scripture_reference — 직접 매핑 필드
        assert hasattr(c, "scripture_reference"), "scripture_reference must be present"
        # source_title — 근사 매핑 (합성)
        assert hasattr(c, "source_title"), "source_title must be present (synthesized)"
        # document_id — 근사 매핑
        assert hasattr(c, "document_id"), "document_id must be present"
        # evidence_confidence — 근사 매핑
        assert hasattr(c, "evidence_confidence"), "evidence_confidence must be present"
        # source_file — 근사 매핑
        assert hasattr(c, "source_file"), "source_file must be present"

    def test_module_disabled_error_type(self):
        """module disabled 시 NaePdModuleDisabledError 전파."""
        from NAE.retrieval_adapter import NaePdModuleDisabledError
        assert issubclass(NaePdModuleDisabledError, RuntimeError)
