"""tests/test_grounded_synthesis_integration.py -- Grounded Synthesis P9: Full Pipeline Integration Test.

P1~P8 각 Phase의 산출물을 손으로 만든 RankedCandidate 리스트로 연결해서
전체 파이프라인이 오류 없이 GroundedAnswer + CitationCheckResult까지 도달하는지
확인한다(순수 함수 합성 테스트, stub LLM).

테스트 케이스:
    Case G (grounded): 2개 evidence -> valid claim -> grounded status
    Case I (insufficient): 빈 EvidencePool -> insufficient_evidence status
    Case C (partial): 다중 질의 중 일부만 결과 있음
    Case D (duplicate): 중복 evidence overwrite 정책

ABSOLUTE RULES:
- core/grounded_*.py, core/evidence_*.py 무수정
- 실제 Evidence 데이터 사용 (가짜 provenance 생성 금지)
- stub만 사용, 네트워크/GPU 없음
- QueryProcessor/HybridQueryProcessor 인스턴스화하지 않음
"""

import pytest

from core.evidence_assembly import (
    QuerySpec,
    assemble_evidence_pool_with_manifest,
)
from core.evidence_model import Evidence, EvidenceProvenance
from core.evidence_pool import EvidencePool
from core.grounded_answer import GroundedAnswer, assemble_grounded_answer
from core.grounded_citation import check_citation_provenance
from core.grounded_claims import Claim, bind_claims
from core.grounded_synthesis_input import SynthesisInput, build_synthesis_input
from core.retrieval import RankedCandidate


# ============================================================
# FIXTURE HELPERS
# ============================================================

def _make_ranked_candidate(
    tsu_id: str = "tsu_001",
    content: str = "Sample TSU content for testing.",
    final_score: float = 0.95,
) -> RankedCandidate:
    """RankedCandidate를 생성하는 헬퍼."""
    return RankedCandidate(
        tsu_id=tsu_id,
        content=content,
        metadata={"source_file": "test_doc.txt", "document_title": "Test Document"},
        bm25_score=0.8,
        theological_score=0.9,
        passage_score=0.85,
        final_score=final_score,
    )


def _make_evidence_from_candidate(cand: RankedCandidate) -> Evidence:
    """RankedCandidate를 Evidence로 변환 (TSUEvidenceAdapter와 동일한 로직)."""
    prov = EvidenceProvenance(
        source_file=cand.metadata.get("source_file"),
        document_id=cand.metadata.get("document_id"),
    )
    return Evidence(
        evidence_id=cand.tsu_id,
        corpus_type="default",
        text=cand.content,
        provenance=prov,
        source_file=cand.metadata.get("source_file"),
        document_title=cand.metadata.get("document_title"),
        bm25_score=cand.bm25_score,
        theological_score=cand.theological_score,
        passage_score=cand.passage_score,
        final_score=cand.final_score,
    )


def _make_pool_from_candidates(
    candidates: list[RankedCandidate], query: str = "test query",
) -> EvidencePool:
    """RankedCandidate 리스트를 EvidencePool로 변환."""
    pool = EvidencePool(default_query=query)
    for cand in candidates:
        ev = _make_evidence_from_candidate(cand)
        pool.add(ev, build_query=query)
    return pool


# ============================================================
# Case G (grounded): 정상 흐름 -- 2개 evidence -> valid claim -> grounded
# ============================================================

class TestGroundedPath:
    """정상 경로: 검색 결과 있음 -> valid claim -> grounded status."""

    def test_full_pipeline_grounded(self):
        """P1~P7 전체가 예외 없이 통과하고 status='grounded' 도달."""
        c1 = _make_ranked_candidate(
            tsu_id="tsu_001",
            content="Romans 8:1-4 teaches that there is no condemnation for those who are in Christ Jesus.",
            final_score=0.95,
        )
        c2 = _make_ranked_candidate(
            tsu_id="tsu_002",
            content="The law of the Spirit of life has set you free in Christ Jesus from the law of sin and death.",
            final_score=0.88,
        )

        pool = _make_pool_from_candidates([c1, c2], query="로마서 8:1-4 정죄 없음")
        assert len(pool) == 2
        assert pool.get("tsu_001") is not None
        assert pool.get("tsu_002") is not None

        query_specs = [QuerySpec(query="로마서 8:1-4 정죄 없음", role="primary", order=0)]
        multi_input = [(query_specs[0], [c1, c2])]
        pool2, manifest = assemble_evidence_pool_with_manifest(multi_input)

        assert len(pool2) == 2
        assert len(manifest.by_query_order) == 1

        si = build_synthesis_input(pool2, manifest, max_evidence=10)
        assert len(si.included_evidence_ids) == 2
        assert "tsu_001" in si.included_evidence_ids
        assert "tsu_002" in si.included_evidence_ids

        # claim text를 evidence text의 부분문자열로 설정 (span check 통과용)
        raw_claims = [
            ("there is no condemnation for those who are in Christ Jesus", ["tsu_001"]),
            ("The law of the Spirit of life has set you free", ["tsu_002"]),
        ]
        claims = bind_claims(raw_claims, si)
        assert len(claims) == 2
        assert all(c.valid for c in claims)

        ga = assemble_grounded_answer(claims, si)
        assert ga.status == "grounded"
        assert len(ga.claims) == 2
        assert ga.insufficiency_reason is None

        report = check_citation_provenance(ga, si, pool2)
        assert report.total_checks == 2
        assert report.all_passed is True


# ============================================================
# Case I (insufficient): 빈 EvidencePool -> insufficient_evidence
# ============================================================

class TestInsufficientPath:
    """근거 부족 경로: 검색 결과 없음 -> insufficient_evidence status."""

    def test_full_pipeline_insufficient_empty_pool(self):
        """빈 pool -> included_evidence_ids=[] -> insufficient_evidence, reason='no_evidence'."""
        pool = _make_pool_from_candidates([], query="존 스미스 3세 교회론")
        assert len(pool) == 0

        query_specs = [QuerySpec(query="존 스미스 3세 교회론", role="primary", order=0)]
        multi_input = [(query_specs[0], [])]
        pool2, manifest = assemble_evidence_pool_with_manifest(multi_input)
        assert len(pool2) == 0

        si = build_synthesis_input(pool2, manifest, max_evidence=10)
        assert len(si.included_evidence_ids) == 0

        raw_claims = [("존 스미스 3세의 교회론에 대해", ["tsu_999"])]
        claims = bind_claims(raw_claims, si)
        assert len(claims) == 1
        assert claims[0].valid is False

        ga = assemble_grounded_answer(claims, si)
        assert ga.status == "insufficient_evidence"
        assert ga.insufficiency_reason == "no_evidence"
        assert ga.text == "이 질문은 현재 등록된 자료로는 답할 수 없습니다."

        report = check_citation_provenance(ga, si, pool2)
        assert report.total_checks == 1
        assert report.id_missing_count == 1


# ============================================================
# Case C (partial): 다중 질의 중 일부만 결과 있음
# ============================================================

class TestPartialPath:
    """다중 질의: 일부 질의만 결과를 반환."""

    def test_full_pipeline_partial_results(self):
        """2개 질의 중 1개만 결과 -> 일부 evidence만 included."""
        c1 = _make_ranked_candidate(
            tsu_id="tsu_010",
            content="Baptist churches historically practice believer's baptism by immersion.",
            final_score=0.90,
        )

        qs1 = QuerySpec(query="신자 침례 성경적 근거", role="primary", order=0)
        qs2 = QuerySpec(query="존 스미스 3세 세례론", role="expanded", order=1)
        multi_input = [(qs1, [c1]), (qs2, [])]
        pool, manifest = assemble_evidence_pool_with_manifest(multi_input)

        assert len(pool) == 1
        assert "tsu_010" in pool

        si = build_synthesis_input(pool, manifest, max_evidence=10)
        assert len(si.included_evidence_ids) == 1
        assert "tsu_010" in si.included_evidence_ids

        # claim text를 evidence의 부분문자열로
        raw_claims = [("practice believer's baptism by immersion", ["tsu_010"])]
        claims = bind_claims(raw_claims, si)
        assert len(claims) == 1
        assert claims[0].valid is True

        ga = assemble_grounded_answer(claims, si)
        assert ga.status == "grounded"

        report = check_citation_provenance(ga, si, pool)
        assert report.total_checks == 1
        assert report.all_passed is True


# ============================================================
# Case D (duplicate): 중복 evidence overwrite 정책
# ============================================================

class TestDuplicatePath:
    """중복 evidence: 동일 ID가 여러 질의에서 발견되면 마지막이 overwrite."""

    def test_full_pipeline_duplicate_evidence(self):
        """동일 tsu_id가 두 질의에서 등장 -> pool에 1개만, overwrite 정책 확인."""
        c1 = _make_ranked_candidate(
            tsu_id="tsu_020",
            content="Original content from first query.",
            final_score=0.85,
        )
        c2 = _make_ranked_candidate(
            tsu_id="tsu_020",
            content="Updated content from second query.",
            final_score=0.92,
        )

        qs1 = QuerySpec(query="첫 번째 질의", role="primary", order=0)
        qs2 = QuerySpec(query="두 번째 질의", role="expanded", order=1)
        multi_input = [(qs1, [c1]), (qs2, [c2])]
        pool, manifest = assemble_evidence_pool_with_manifest(multi_input)

        assert len(pool) == 1
        ev = pool.get("tsu_020")
        assert ev is not None
        assert ev.text == "Updated content from second query."

        queries_for = manifest.queries_for("tsu_020")
        assert "첫 번째 질의" in queries_for
        assert "두 번째 질의" in queries_for

        si = build_synthesis_input(pool, manifest, max_evidence=10)
        assert len(si.included_evidence_ids) == 1

        # claim text를 evidence의 부분문자열로
        raw_claims = [("Updated content from second query", ["tsu_020"])]
        claims = bind_claims(raw_claims, si)
        ga = assemble_grounded_answer(claims, si)
        assert ga.status == "grounded"

        report = check_citation_provenance(ga, si, pool)
        assert report.total_checks == 1
        assert report.all_passed is True


# ============================================================
# Edge case: 빈 claim list
# ============================================================

class TestEdgeCases:
    """경계값 테스트."""

    def test_full_pipeline_no_claims(self):
        """claim이 아예 없으면 insufficient_evidence, reason='no_claims'."""
        c1 = _make_ranked_candidate(tsu_id="tsu_030", content="Some content.", final_score=0.9)
        pool = _make_pool_from_candidates([c1], query="test")
        qs = QuerySpec(query="test", role="primary", order=0)
        _, manifest = assemble_evidence_pool_with_manifest([(qs, [c1])])
        si = build_synthesis_input(pool, manifest, max_evidence=10)

        claims = bind_claims([], si)
        assert len(claims) == 0

        ga = assemble_grounded_answer(claims, si)
        assert ga.status == "insufficient_evidence"
        assert ga.insufficiency_reason == "no_claims"

        report = check_citation_provenance(ga, si, pool)
        assert report.total_checks == 0


# ============================================================
# Pipeline integration: 모든 케이스를 아우르는 통합 테스트
# ============================================================

class TestPipelineIntegration:
    """P1~P8 전체 파이프라인 통합 테스트."""

    def test_grounded_path_no_exceptions(self):
        """정상 흐름: P1->P2->P3->P4->P5->P6->P7 전체가 예외 없이 통과."""
        c1 = _make_ranked_candidate(
            tsu_id="tsu_100",
            content="The justification by faith is a central doctrine of the Reformation.",
            final_score=0.95,
        )
        pool = _make_pool_from_candidates([c1], query="칭의 교리")
        qs = QuerySpec(query="칭의 교리", role="primary", order=0)
        _, manifest = assemble_evidence_pool_with_manifest([(qs, [c1])])
        si = build_synthesis_input(pool, manifest, max_evidence=10)

        # claim text를 evidence의 부분문자열로
        raw_claims = [("justification by faith is a central doctrine", ["tsu_100"])]
        claims = bind_claims(raw_claims, si)
        ga = assemble_grounded_answer(claims, si)
        report = check_citation_provenance(ga, si, pool)

        assert ga.status == "grounded"
        assert report.all_passed is True
        assert len(ga.claims) == 1

    def test_insufficient_path_no_exceptions(self):
        """근거 부족 흐름: P1->P2->P3->P4->P5->P6->P7 전체가 예외 없이 통과."""
        pool = _make_pool_from_candidates([], query="가상의 인물")
        qs = QuerySpec(query="가상의 인물", role="primary", order=0)
        _, manifest = assemble_evidence_pool_with_manifest([(qs, [])])
        si = build_synthesis_input(pool, manifest, max_evidence=10)

        raw_claims = [("가상의 인물의 주장", ["tsu_999"])]
        claims = bind_claims(raw_claims, si)
        ga = assemble_grounded_answer(claims, si)
        report = check_citation_provenance(ga, si, pool)

        assert ga.status == "insufficient_evidence"
        assert report.id_missing_count == 1
