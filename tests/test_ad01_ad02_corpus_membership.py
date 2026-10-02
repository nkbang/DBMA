"""tests/test_ad01_ad02_corpus_membership.py - AD-01/AD-02 단위 검증.

AD-01: registry corpus_membership -> Evidence.corpus_type 전달
AD-02: retrieval relevance + corpus role preservation (ranking 무변경)

격리 환경(worktree isolated fixture)에서만 실행 - production data 사용 금지.
"""

import json
from unittest import mock

import pytest

from core.evidence_adapters.tsu_adapter import (
    RankedCandidateEvidenceAdapter,
    TSUEvidenceFactory,
)
from core.evidence_model import CORPUS_DEFAULT, CORPUS_PERSONAL
from core.retrieval import RankedCandidate


class TestAD01ResolveCorpusType:
    """TSUEvidenceFactory.resolve_corpus_type() - registry 기반 결정."""

    def test_no_document_id_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type()
        assert result == CORPUS_DEFAULT

    def test_empty_document_id_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="")
        assert result == CORPUS_DEFAULT

    def test_nonexistent_document_returns_default(self):
        result = TSUEvidenceFactory.resolve_corpus_type(
            document_id="nonexistent_doc_id_00000"
        )
        assert result == CORPUS_DEFAULT

    def test_missing_corpus_membership_field_returns_default(self, tmp_path):
        reg = {"documents": {"some_doc_id": {"source_file": "test.txt"}}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_invalid_corpus_membership_returns_default(self, tmp_path):
        reg = {"documents": {"some_doc_id": {"corpus_membership": "invalid_value"}}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_registry_file_not_found_returns_default(self):
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", "/nonexistent/path.json"):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT

    def test_corrupted_registry_returns_default(self, tmp_path):
        reg_file = tmp_path / "documents.json"
        reg_file.write_text("{invalid json", encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            result = TSUEvidenceFactory.resolve_corpus_type(source_file=None, document_id="some_doc_id")
        assert result == CORPUS_DEFAULT


class TestAD01TSUEvidenceFactory:
    """TSUEvidenceFactory - document_id 기반 corpus_type."""

    def test_init_with_personal_document(self, tmp_path):
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"}
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            factory = TSUEvidenceFactory(document_id="6f323b08ce388551d2fa772c756a828e")
            assert factory._corpus_type == CORPUS_PERSONAL

    def test_init_with_default_document(self, tmp_path):
        reg = {"documents": {}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            factory = TSUEvidenceFactory(document_id="nonexistent_doc_id_00000")
            assert factory._corpus_type == CORPUS_DEFAULT

    def test_create_from_tsu_preserves_corpus_type(self, tmp_path):
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"}
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            factory = TSUEvidenceFactory(document_id="6f323b08ce388551d2fa772c756a828e")
            tsu_record = {
                "tsu_id": "TSU-TEST-001",
                "source_file": "test.txt",
                "document_id": "6f323b08ce388551d2fa772c756a828e",
                "content": "test content",
            }
            evidence = factory.create_from_tsu(tsu_record)
            assert evidence.corpus_type == CORPUS_PERSONAL


class TestAD02RankedCandidateEvidenceAdapter:
    """RankedCandidateEvidenceAdapter - per-candidate corpus_type."""

    def _make_candidate(self, final_score: float, document_id: str) -> RankedCandidate:
        return RankedCandidate(
            tsu_id=f"TSU-AD02-{document_id[:8]}",
            content="test evidence text",
            vector_score=0.85,
            bm25_score=0.72,
            final_score=final_score,
            metadata={
                "source_file": f"fixture_{document_id}.txt",
                "document_id": document_id,
                "chunk_id": "chunk-1",
                "source_type": "txt",
                "title": "Test Document",
            },
        )

    def test_adapt_personal_fixture_a(self, tmp_path):
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"}
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
            candidate = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
            evidence = adapter.adapt(candidate)
            assert evidence.corpus_type == CORPUS_PERSONAL
            assert evidence.retrieval_score == 0.85
            assert evidence.bm25_score == 0.72
            assert evidence.final_score == 0.78
            assert evidence.provenance.source_file == "fixture_6f323b08ce388551d2fa772c756a828e.txt"
            assert evidence.provenance.document_id == "6f323b08ce388551d2fa772c756a828e"

    def test_adapt_nonexistent_document_default(self, tmp_path):
        reg = {"documents": {}}
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            adapter = RankedCandidateEvidenceAdapter(document_id="nonexistent_doc_id_00000")
            candidate = self._make_candidate(0.78, "nonexistent_doc_id_00000")
            evidence = adapter.adapt(candidate)
            assert evidence.corpus_type == CORPUS_DEFAULT

    def test_adapt_batch_preserves_order(self, tmp_path):
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"}
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
            c1 = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
            c2 = self._make_candidate(0.82, "nonexistent_doc_id_00000")
            evidences = adapter.adapt_batch([c1, c2])
            assert len(evidences) == 2
            assert evidences[0].corpus_type == CORPUS_PERSONAL
            assert evidences[1].corpus_type == CORPUS_DEFAULT
            assert evidences[0].final_score == c1.final_score
            assert evidences[1].final_score == c2.final_score

    def test_adapt_always_uses_per_candidate_lookup(self, tmp_path):
        """adapt()는 항상 per-candidate registry lookup을 사용함 (AD-02 설계)."""
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"}
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            adapter = RankedCandidateEvidenceAdapter(
                corpus_type=CORPUS_DEFAULT,
                document_id="6f323b08ce388551d2fa772c756a828e",
            )
            candidate = self._make_candidate(0.78, "6f323b08ce388551d2fa772c756a828e")
            evidence = adapter.adapt(candidate)
            assert evidence.corpus_type == CORPUS_PERSONAL


class TestAD02RankingUnchanged:
    """AD-02: corpus_type 태깅이 ranking/scoring에 영향을 주지 않음."""

    def _make_candidate(self, final_score: float, document_id: str) -> RankedCandidate:
        return RankedCandidate(
            tsu_id=f"TSU-RANK-{document_id[:8]}",
            content="test",
            vector_score=0.5,
            bm25_score=0.6,
            final_score=final_score,
            metadata={
                "source_file": f"doc_{document_id}.txt",
                "document_id": document_id,
                "chunk_id": "chunk-1",
                "source_type": "txt",
            },
        )

    def test_personal_candidate_does_not_boost_score(self):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        original_score = 0.78
        candidate = self._make_candidate(original_score, "6f323b08ce388551d2fa772c756a828e")
        evidence = adapter.adapt(candidate)
        assert evidence.final_score == original_score
        assert evidence.retrieval_score == candidate.vector_score
        assert evidence.bm25_score == candidate.bm25_score

    def test_mixed_corpus_candidates_preserve_original_order(self):
        personal_candidate = self._make_candidate(0.85, "6f323b08ce388551d2fa772c756a828e")
        default_candidate = self._make_candidate(0.92, "nonexistent_doc_id_00000")
        personal_adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        default_adapter = RankedCandidateEvidenceAdapter(document_id="nonexistent_doc_id_00000")
        personal_evidence = personal_adapter.adapt(personal_candidate)
        default_evidence = default_adapter.adapt(default_candidate)
        assert personal_evidence.final_score == 0.85
        assert default_evidence.final_score == 0.92
        assert default_evidence.final_score > personal_evidence.final_score


class TestIsolatedFixtureVerification:
    """tmp_path + mock.patch 기반 자기완결적 fixture A/B 검증.

    원래 목적: worktree isolated registry의 fixture A/B가 실제로 personal로
    인식되는지 확인. CI 환경에서는 로컬 registry 파일이 없으므로, tmp_path에
    fixture A/B가 corpus_membership="personal"로 등록된 registry를 직접 만들고
    mock.patch로 주입해 동일한 검증을 수행한다.
    """

    @pytest.fixture(autouse=True)
    def _isolated_fixture_registry(self, tmp_path):
        """Fixture A/B가 personal로 등록된 registry를 tmp_path에 생성."""
        reg = {
            "documents": {
                "6f323b08ce388551d2fa772c756a828e": {"corpus_membership": "personal"},
                "5ce2824e947da15da8893fbb45c07239": {"corpus_membership": "personal"},
            }
        }
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps(reg), encoding="utf-8")
        with mock.patch("core.evidence_adapters.tsu_adapter.DEFAULT_REGISTRY_PATH", str(reg_file)):
            yield reg_file

    def test_fixture_a_resolve_personal(self, _isolated_fixture_registry):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="6f323b08ce388551d2fa772c756a828e")
        assert result == CORPUS_PERSONAL

    def test_fixture_b_resolve_personal(self, _isolated_fixture_registry):
        result = TSUEvidenceFactory.resolve_corpus_type(document_id="5ce2824e947da15da8893fbb45c07239")
        assert result == CORPUS_PERSONAL

    def test_fixture_a_evidence_personal(self, _isolated_fixture_registry):
        adapter = RankedCandidateEvidenceAdapter(document_id="6f323b08ce388551d2fa772c756a828e")
        candidate = RankedCandidate(
            tsu_id="TSU-JHN-6f323b08",
            content="test vine text",
            vector_score=0.65, bm25_score=0.70, final_score=0.67,
            metadata={
                "source_file": "rpv_fixture_A_john15_sermon_notes.txt",
                "document_id": "6f323b08ce388551d2fa772c756a828e",
                "chunk_id": "chunk-1", "source_type": "txt",
            },
        )
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL

    def test_fixture_b_evidence_personal(self, _isolated_fixture_registry):
        adapter = RankedCandidateEvidenceAdapter(document_id="5ce2824e947da15da8893fbb45c07239")
        candidate = RankedCandidate(
            tsu_id="TSU-UNK-5ce2824e",
            content="test gifts text",
            vector_score=0.55, bm25_score=0.60, final_score=0.57,
            metadata={
                "source_file": "rpv_fixture_B_spirit_gifts_notes.txt",
                "document_id": "5ce2824e947da15da8893fbb45c07239",
                "chunk_id": "chunk-1", "source_type": "txt",
            },
        )
        evidence = adapter.adapt(candidate)
        assert evidence.corpus_type == CORPUS_PERSONAL


class TestAD01RegisterDocumentDirectCall:
    """register_document() 직접 호출 — PR-A #110의 3줄 변경 검증.

    이 테스트들은 register_document()를 실제 호출하여
    corpus_membership="default" 기본값이 실제로 기록되는지 검증한다.
    기존 테스트는 tsu_adapter.mock 기반이므로 register_document()를
    직접 호출하지 않았다.

    절대 수정 금지: production code (identity_registry.py) 는 그대로 유지.
    이 테스트들은 PR-A의 3줄을 제거하면 반드시 실패해야 한다.
    """

    @pytest.fixture
    def _empty_reg(self, tmp_path):
        """빈 registry를 tmp_path에 생성하고 path를 반환."""
        reg_file = tmp_path / "documents.json"
        reg_file.write_text(json.dumps({
            "schema_version": "2.0",
            "documents": {},
            "_meta": {"total_documents": 0},
        }, ensure_ascii=False), encoding="utf-8")
        return reg_file

    def _load_reg(self, reg_file):
        from core.identity_registry import load_identity_registry
        return load_identity_registry(str(reg_file))

    # ------------------------------------------------------------------ Test A
    def test_a_missing_membership_becomes_default(self, _empty_reg):
        """Test A — default registration.

        register_document()를 실제 호출한다. 입력 metadata에
        corpus_membership이 없는 경우 record["corpus_membership"] == "default"
        를 반드시 검증한다.
        """
        from core.identity_registry import register_document

        registry = self._load_reg(_empty_reg)
        doc_id = "test_a_doc_00001"
        metadata = {
            "document_id": doc_id,
            "source_file": "test_a_source.txt",
            "file_hash": "abc123def456",
        }
        record, is_new = register_document(registry, metadata)

        assert is_new is True, "신규 문서여야 함"
        assert record["document_id"] == doc_id
        assert record["corpus_membership"] == "default", (
            f"corpus_membership이 없으면 'default'여야 함 — 실제: {record['corpus_membership']!r}"
        )

    # ------------------------------------------------------------------ Test B
    def test_b_explicit_personal_preserved(self, _empty_reg):
        """Test B — personal registration.

        입력 metadata에 corpus_membership="personal"을 전달하면
        record["corpus_membership"] == "personal"이어야 한다.
        """
        from core.identity_registry import register_document

        registry = self._load_reg(_empty_reg)
        doc_id = "test_b_doc_00002"
        metadata = {
            "document_id": doc_id,
            "source_file": "test_b_source.txt",
            "file_hash": "xyz789ghi012",
            "corpus_membership": "personal",
        }
        record, is_new = register_document(registry, metadata)

        assert is_new is True
        assert record["corpus_membership"] == "personal", (
            f"explicit personal이어야 함 — 실제: {record['corpus_membership']!r}"
        )

    # ------------------------------------------------------------------ Test C
    def test_c_exact_match_reegistration_preserves_personal(self, _empty_reg):
        """Test C — exact-match 재등록 보존.

        corpus_membership="personal"으로 등록한 동일 문서를 다시 등록한다.
        두 번째 호출에서 기존 record의 corpus_membership이 "personal"로
        유지되는지 검증한다. is_new=False도 확인한다.
        """
        from core.identity_registry import register_document

        registry = self._load_reg(_empty_reg)
        doc_id = "test_c_doc_00003"
        first_metadata = {
            "document_id": doc_id,
            "source_file": "test_c_source_v1.txt",
            "file_hash": "hash_c_first",
            "corpus_membership": "personal",
        }
        record1, is_new1 = register_document(registry, first_metadata)

        assert is_new1 is True
        assert record1["document_id"] == doc_id
        assert record1["corpus_membership"] == "personal"

        # 두 번째 호출 — 동일한 doc_id로 재등록
        second_metadata = {
            "document_id": doc_id,
            "source_file": "test_c_source_v2.txt",  # 다른 source_file
            "file_hash": "hash_c_different",         # 다른 hash
            "corpus_membership": "default",           # 다른 membership 시도
        }
        record2, is_new2 = register_document(registry, second_metadata)

        assert is_new2 is False, (
            "동일 doc_id이므로 is_new=False여야 함"
        )
        assert record2["corpus_membership"] == "personal", (
            f"exact-match 재등록 시 기존 personal이 유지되어야 함 — 실제: {record2['corpus_membership']!r}"
        )

    # ------------------------------------------------------------------ Test D
    def test_d_hash_match_reegistration_preserves_personal(self, _empty_reg):
        """Test D — hash-match 재등록 보존.

        동일한 file_hash로 다른 doc_id를 사용해 재등록하면
        기존 corpus_membership이 덮어써지지 않아야 한다.
        exact-match와 hash-match가 다른 코드 경로임을 독립적으로 검증한다.
        """
        from core.identity_registry import register_document

        registry = self._load_reg(_empty_reg)
        doc_id_d1 = "test_d_doc_00004a"
        first_metadata = {
            "document_id": doc_id_d1,
            "source_file": "test_d_source_v1.txt",
            "file_hash": "hash_d_shared",
            "corpus_membership": "personal",
        }
        record1, is_new1 = register_document(registry, first_metadata)

        assert is_new1 is True
        assert record1["document_id"] == doc_id_d1
        assert record1["corpus_membership"] == "personal"

        # 두 번째 호출 — 다른 doc_id지만 동일한 file_hash
        doc_id_d2 = "test_d_doc_00004b"
        second_metadata = {
            "document_id": doc_id_d2,
            "source_file": "test_d_source_v2.txt",
            "file_hash": "hash_d_shared",  # 동일한 hash
            "corpus_membership": "default",  # 다른 membership 시도
        }
        record2, is_new2 = register_document(registry, second_metadata)

        assert is_new2 is False, (
            "동일 file_hash이므로 is_new=False여야 함"
        )
        assert record2["corpus_membership"] == "personal", (
            f"hash-match 재등록 시 기존 personal이 유지되어야 함 — 실제: {record2['corpus_membership']!r}"
        )
        # record2는 첫 번째 record를 반환해야 함 (same object)
        assert record2["document_id"] == doc_id_d1, (
            "hash-match는 기존 record를 반환해야 함"
        )
