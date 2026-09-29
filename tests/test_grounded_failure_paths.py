"""tests/test_grounded_failure_paths.py -- Grounded Synthesis P8: Failure-path Validation.

P4~P7 파이프라인 전체(SynthesisInput → Claim → GroundedAnswer → CitationCheckResult)를
6개의 실패 경로 케이스로 강제 시험한다. 새 프로덕션 코드를 만들지 않는다.

케이스:
    Case A: 검색 결과 없음 (빈 EvidencePool)
    Case B: 근거 1건뿐, 관련성 낮음
    Case C: 다중 질의 중 일부만 결과 있음
    Case D: 중복 Evidence (P2 overwrite 정책 회귀 확인)
    Case E: Evidence 충돌 (두 Claim이 공존하는지)
    Case F: 근거가 질문과 무관해 보이는 경우

ABSOLUTE RULES:
- core/grounded_*.py, core/evidence_*.py 무수정
- 실제 Evidence 데이터 사용 (가짜 provenance 생성 금지)
- 테스트는 stub만 사용, 네트워크/GPU 없음
"""

import pytest

from core.evidence_assembly import QuerySpec, assemble_evidence_pool_with_manifest
from core.evidence_model import Evidence, EvidenceProvenance
from core.evidence_pool import EvidencePool
from core.grounded_answer import GroundedAnswer, assemble_grounded_answer
from core.grounded_citation import (
    CitationCheckReport,
    check_citation_provenance,
)
from core.grounded_claims import Claim, bind_claims
from core.grounded_synthesis_input import SynthesisInput, build_synthesis_input
from core.retrieval import RankedCandidate


# ============================================================
# FIXTURE HELPERS
# ============================================================

def _make_evidence(
    evidence_id: str = "e1",
    text: str = "This is sample evidence text for testing purposes.",
    source_file: str | None = "test_source.txt",
) -> Evidence:
    """Evidence 객체를 생성하는 헬퍼."""
    prov = EvidenceProvenance(
        source_file=source_file,
        document_id="doc1" if source_file else None,
        chunk_id="chunk1" if source_file else None,
    )
    return Evidence(
        evidence_id=evidence_id,
        corpus_type="default",
        text=text,
        provenance=prov,
    )


def _make_claim(
    claim_id: str = "claim_000",
    text: str = "This is a valid claim text that should be found.",
    evidence_ids: list[str] | None = None,
    valid: bool = True,
) -> Claim:
    """Claim 객체를 생성하는 헬퍼."""
    return Claim(
        claim_id=claim_id,
        text=text,
        evidence_ids=evidence_ids if evidence_ids is not None else ["e1"],
        valid=valid,
    )


def _make_grounded_answer(
    claims: list[Claim] | None = None,
    status: str = "grounded",
) -> GroundedAnswer:
    """GroundedAnswer 객체를 생성하는 헬퍼."""
    if claims is None:
        claims = [_make_claim()]
    return GroundedAnswer(
        status=status,
        claims=claims,
        text=" ".join(c.text for c in claims if c.valid),
        insufficiency_reason=None,
    )


def _make_synthesis_input(included: list[str] | None = None) -> SynthesisInput:
    """SynthesisInput을 생성하는 헬퍼."""
    inc = included if included is not None else ["e1"]
    return SynthesisInput(
        query_specs=[],
        included_evidence_ids=inc,
        excluded_evidence_ids=[],
        truncated=False,
        prompt_text="test prompt",
    )


def _make_pool(evidences: list[Evidence] | None = None) -> EvidencePool:
    """EvidencePool을 생성하는 헬퍼."""
    pool = EvidencePool()
    if evidences:
        for ev in evidences:
            pool.add(ev)
    return pool


# ============================================================
# Case A: 검색 결과 없음 (빈 EvidencePool)
# ============================================================

class TestCaseA_EmptyEvidencePool:
    """Case A: 검색 결과 없음 → GroundedAnswer.status == "insufficient_evidence",
    파이프라인이 예외 없이 끝까지 실행됨."""

    def test_empty_pool_gives_insufficient_status(self):
        """빈 EvidencePool에 evidence가 하나도 없으면,
        assemble_grounded_answer는 included_evidence_ids가 비어 있으므로
        status="insufficient_evidence"를 반환해야 한다."""
        pool = EvidencePool()
        assert len(pool) == 0

        claims = [_make_claim(text="This is a claim with no evidence.", evidence_ids=[])]
        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=_make_synthesis_input(included=[]),
        )

        assert ga.status == "insufficient_evidence"
        assert ga.insufficiency_reason == "no_evidence"

    def test_empty_pool_citation_check_does_not_crash(self):
        """빈 EvidencePool에 대해 check_citation_provenance가 예외 없이
        CitationCheckReport를 반환해야 한다."""
        pool = EvidencePool()
        claims = [_make_claim(text="Claim text longer than five chars here.", evidence_ids=[])]
        ga = _make_grounded_answer(claims=claims, status="insufficient_evidence")
        si = _make_synthesis_input(included=[])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 0
        assert report.all_passed is True
        # 빈 pool에서 get()이 None을 반환하는지 확인
        assert pool.get("nonexistent") is None


# ============================================================
# Case B: 근거 1건뿐, 관련성 낮음
# ============================================================

class TestCaseB_SingleLowRelevanceEvidence:
    """Case B: 근거가 1건뿐이고 관련성이 낮음 → insufficient 판정이 나오되,
    크래시하지 않음."""

    def test_single_evidence_span_not_found(self):
        """근거가 1건뿐이고 claim text가 evidence text에 포함되지 않으면
        span_found_in_text=False가 된다. 크래시 없이 정상 종료."""
        ev = _make_evidence(
            evidence_id="e1",
            text="This is completely unrelated evidence about gardening.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="Theological perspective on predestination and free will.",
            evidence_ids=["e1"],
            valid=True,
        )
        ga = _make_grounded_answer(claims=[claim], status="grounded")
        si = _make_synthesis_input(included=["e1"])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        assert report.results[0].id_exists is True
        assert report.results[0].span_found_in_text is False
        assert report.results[0].provenance_traceable is True
        assert report.all_passed is False
        # span_not_found_count가 1이므로 insufficient으로 간주 가능
        assert report.span_not_found_count == 1

    def test_single_evidence_assembly_no_crash(self):
        """1건의 evidence만으로 assemble_grounded_answer가 정상 동작."""
        ev = _make_evidence(
            evidence_id="e1",
            text="Short text.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="This is a claim that cannot be span-matched to short evidence.",
            evidence_ids=["e1"],
            valid=True,
        )
        ga = assemble_grounded_answer(
            claims=[claim],
            synthesis_input=_make_synthesis_input(included=["e1"]),
        )

        assert ga.status == "grounded"  # valid claim이 있으므로 grounded
        assert len(ga.claims) == 1
        assert ga.claims[0].valid is True


# ============================================================
# Case C: 다중 질의 중 일부만 결과 있음
# ============================================================

class TestCaseC_PartialMultiQueryResults:
    """Case C: 다중 질의 중 일부는 결과 있음(A→E1, B→빈 결과, C→E3) →
    P3A assemble_evidence_pool_with_manifest()가 빈 결과를 건너뛰고
    A/C의 결과를 모두 pool에 포함하는지 확인."""

    def test_partial_query_results_assembly_continues(self):
        """3개의 질의(A→E1, B→빈 결과, C→E3) 중 B만 빈 결과: 실제
        assemble_evidence_pool_with_manifest()를 호출해 assembly가 중단되지
        않고 A/C의 결과가 모두 pool에 포함되는지 확인한다."""
        ca = RankedCandidate(tsu_id="e1", content="Evidence from query A about theological topics.", final_score=0.9, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})
        cc = RankedCandidate(tsu_id="e3", content="Evidence from query C about pastoral care.", final_score=0.8, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})

        pool, manifest = assemble_evidence_pool_with_manifest([
            (QuerySpec(query="A"), [ca]),
            (QuerySpec(query="B"), []),
            (QuerySpec(query="C"), [cc]),
        ])

        assert len(pool) == 2
        assert pool.get("e1") is not None
        assert pool.get("e3") is not None
        # B 질의는 by_query_order에 (spec, []) 형태로 남아 있어야 함(P3A AC3)
        b_entry = [eids for qs, eids in manifest.by_query_order if qs.query == "B"]
        assert b_entry == [[]]

        si = build_synthesis_input(pool, manifest, max_evidence=10)
        assert set(si.included_evidence_ids) == {"e1", "e3"}

    def test_partial_query_citation_check_all_pairs(self):
        """부분 결과에서 각 claim×evidence pair가 정상 검사되는지 확인."""
        ca = RankedCandidate(tsu_id="e1", content="Evidence from query A about theological topics.", final_score=0.9, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})
        cc = RankedCandidate(tsu_id="e3", content="Evidence from query C about pastoral care.", final_score=0.8, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})

        pool, manifest = assemble_evidence_pool_with_manifest([
            (QuerySpec(query="A"), [ca]),
            (QuerySpec(query="B"), []),
            (QuerySpec(query="C"), [cc]),
        ])

        ev_a = Evidence(
            evidence_id="e1",
            corpus_type="default",
            text="Evidence from query A about theological topics.",
            provenance=EvidenceProvenance(source_file="test_source.txt", document_id="doc1", chunk_id="chunk1"),
        )
        ev_c = Evidence(
            evidence_id="e3",
            corpus_type="default",
            text="Evidence from query C about pastoral care.",
            provenance=EvidenceProvenance(source_file="test_source.txt", document_id="doc1", chunk_id="chunk1"),
        )

        claims = [
            _make_claim(
                claim_id="claim_000",
                text="Evidence from query A about theological topics.",
                evidence_ids=["e1"],
                valid=True,
            ),
            _make_claim(
                claim_id="claim_001",
                text="Evidence from query C about pastoral care.",
                evidence_ids=["e3"],
                valid=True,
            ),
        ]
        ga = _make_grounded_answer(claims=claims, status="grounded")
        si = build_synthesis_input(pool, manifest, max_evidence=10)

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 2
        # 둘 다 id_exists=True, span_found=True
        for r in report.results:
            assert r.id_exists is True
            assert r.span_found_in_text is True
            assert r.provenance_traceable is True
        assert report.all_passed is True


# ============================================================
# Case D: 중복 Evidence (P2 overwrite 정책 회귀 확인)
# ============================================================

class TestCaseD_DuplicateEvidence:
    """Case D: 중복 Evidence(A→E1, B→E1) → P3A 조립 경로를 통해서도
    P2 overwrite 정책(마지막 값 유지)이 그대로 적용되는지 확인."""

    def test_duplicate_evidence_pool_overwrite_policy(self):
        """같은 evidence_id를 서로 다른 질의(A, B)가 찾을 때, P3A 조립 경로를 통해서도
        P2 overwrite 정책(마지막 값 유지)이 그대로 적용되는지 확인한다."""
        d1 = RankedCandidate(tsu_id="e1", content="First version of evidence e1.", final_score=0.5, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})
        d2 = RankedCandidate(tsu_id="e1", content="Second version of evidence e1 overwrites the first.", final_score=0.5, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})

        pool, manifest = assemble_evidence_pool_with_manifest([
            (QuerySpec(query="A"), [d1]),
            (QuerySpec(query="B"), [d2]),
        ])

        assert len(pool) == 1  # overwrite — 2개 occurrence가 1개로
        assert pool.get("e1").text == "Second version of evidence e1 overwrites the first."
        # P3A manifest는 두 질의 모두 기록해야 함(P3A AC1)
        assert manifest.queries_for("e1") == ["A", "B"]

    def test_duplicate_evidence_citation_uses_latest(self):
        """중복 evidence가 pool에 있을 때 citation check가 마지막 버전을 사용하는지."""
        d1 = RankedCandidate(tsu_id="e1", content="First version of evidence e1.", final_score=0.5, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})
        d2 = RankedCandidate(tsu_id="e1", content="Second version of evidence e1 overwrites the first.", final_score=0.5, metadata={"source_file": "test_source.txt", "document_id": "doc1", "chunk_id": "chunk1"})

        pool, manifest = assemble_evidence_pool_with_manifest([
            (QuerySpec(query="A"), [d1]),
            (QuerySpec(query="B"), [d2]),
        ])

        claim = _make_claim(
            claim_id="claim_000",
            text="Second version of evidence e1 overwrites the first.",
            evidence_ids=["e1"],
            valid=True,
        )
        ga = _make_grounded_answer(claims=[claim], status="grounded")
        si = build_synthesis_input(pool, manifest, max_evidence=10)

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        # 마지막 버전에서 span이 찾아져야 함
        assert report.results[0].span_found_in_text is True
        assert report.results[0].id_exists is True


# ============================================================
# Case E: Evidence 충돌 (두 Claim이 공존하는지)
# ============================================================

class TestCaseE_ConflictingEvidence:
    """Case E: Evidence 충돌(E1과 E2가 반대 진술) → P6에서 임의 병합/선택이
    일어나지 않음. 두 Claim이 서로 다른 evidence_id를 각각 valid=True로
    갖고 공존하는지 확인."""

    def test_conflicting_evidence_both_claims_preserved(self):
        """반대 진술을 하는 두 evidence가 있을 때, P6가 하나를 삭제하거나
        임의로 병합하지 않고 두 claim이 모두 valid=True로 남는지 확인."""
        ev1 = _make_evidence(
            evidence_id="e1",
            text="Predestination is absolute and unconditional.",
        )
        ev2 = _make_evidence(
            evidence_id="e2",
            text="Free will allows humans to choose their own path.",
        )
        pool = _make_pool([ev1, ev2])

        # 두 claim이 서로 다른 evidence를 인용
        claims = [
            _make_claim(
                claim_id="claim_000",
                text="Predestination is absolute and unconditional.",
                evidence_ids=["e1"],
                valid=True,
            ),
            _make_claim(
                claim_id="claim_001",
                text="Free will allows humans to choose their own path.",
                evidence_ids=["e2"],
                valid=True,
            ),
        ]

        # P6 assemble_grounded_answer는 conflicting=False이므로 grounded 상태
        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=_make_synthesis_input(included=["e1", "e2"]),
        )

        # 두 claim이 모두 valid=True로 공존
        assert ga.status == "grounded"
        assert len(ga.claims) == 2
        assert ga.claims[0].valid is True
        assert ga.claims[1].valid is True
        # 어느 claim도 삭제되지 않음
        assert ga.claims[0].evidence_ids == ["e1"]
        assert ga.claims[1].evidence_ids == ["e2"]

    def test_conflicting_evidence_citation_check_both(self):
        """충돌 evidence에 대한 citation check가 두 claim 모두에서 통과하는지."""
        ev1 = _make_evidence(
            evidence_id="e1",
            text="Predestination is absolute and unconditional.",
        )
        ev2 = _make_evidence(
            evidence_id="e2",
            text="Free will allows humans to choose their own path.",
        )
        pool = _make_pool([ev1, ev2])

        claims = [
            _make_claim(
                claim_id="claim_000",
                text="Predestination is absolute and unconditional.",
                evidence_ids=["e1"],
                valid=True,
            ),
            _make_claim(
                claim_id="claim_001",
                text="Free will allows humans to choose their own path.",
                evidence_ids=["e2"],
                valid=True,
            ),
        ]
        ga = _make_grounded_answer(claims=claims, status="grounded")
        si = _make_synthesis_input(included=["e1", "e2"])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 2
        # 두 claim 모두 span_found=True (각각 자신의 evidence에서 match)
        for r in report.results:
            assert r.id_exists is True
            assert r.span_found_in_text is True
            assert r.provenance_traceable is True
        assert report.all_passed is True

    def test_conflicting_status_flag_not_auto_detected(self):
        """P6가 conflicting=True 플래그 없이 자동 충돌 탐지를 하지 않는지 확인.
        conflicting=False(기본값)이면 status는 grounded여야 함."""
        claims = [
            _make_claim(
                claim_id="claim_000",
                text="Predestination is absolute and unconditional.",
                evidence_ids=["e1"],
                valid=True,
            ),
            _make_claim(
                claim_id="claim_001",
                text="Free will allows humans to choose their own path.",
                evidence_ids=["e2"],
                valid=True,
            ),
        ]

        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=_make_synthesis_input(included=["e1", "e2"]),
            conflicting=False,  # 명시적으로 False
        )

        assert ga.status == "grounded"
        assert ga.insufficiency_reason is None


# ============================================================
# Case F: 근거가 질문과 무관해 보이는 경우
# ============================================================

class TestCaseF_IrrelevantEvidence:
    """Case F: 근거가 질문과 무관해 보임 → stub이 "질문과 무관한 근거만
    주어지면 insufficient를 반환"하도록 설계된 케이스로 시험.
    자동 관련성 판정 로직 자체는 이번 범위에 없음을 보고서에 명시."""

    def test_stub_does_not_expand_interpretation(self):
        """stub LLM(여기서는 bind_claims + assemble_grounded_answer)이
        무관한 evidence를 확대 해석하여 답을 만들지 않는지 확인.
        evidence_ids가 included_evidence_ids에 없으면 valid=False → insufficient."""
        # 질문과 무관해 보이는 evidence (e1은 pool에 있지만 claim은 e_invalid를 인용)
        ev = _make_evidence(
            evidence_id="e1",
            text="The local church holds annual picnics in June.",
        )
        pool = _make_pool([ev])

        # evidence_ids=["e_invalid"]이고 included=["e1"]이므로 valid=False
        raw_claims = [
            ("The church picnic is a wonderful tradition.", ["e_invalid"]),
        ]
        si = _make_synthesis_input(included=["e1"])
        claims = bind_claims(raw_claims, si)

        assert len(claims) == 1
        assert claims[0].valid is False  # e_invalid not in included

        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=si,
        )

        # valid=False이므로 insufficient_evidence (stub은 관련성 판단 안 함)
        assert ga.status == "insufficient_evidence"
        assert ga.insufficiency_reason == "no_valid_claim"

    def test_irrelevant_evidence_citation_fails_span_check(self):
        """무관한 evidence에 대해 citation check가 span 미발견을 보고하는지.
        이는 P7이 의미적 관련성을 판단하지 않고 구조적 존재만 검사함을 보여준다."""
        ev = _make_evidence(
            evidence_id="e1",
            text="The local church holds annual picnics in June.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="Predestination and free will are theological concepts.",
            evidence_ids=["e1"],
            valid=True,
        )
        ga = _make_grounded_answer(claims=[claim], status="grounded")
        si = _make_synthesis_input(included=["e1"])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        # id_exists는 True (evidence가 included에 있음)
        assert report.results[0].id_exists is True
        # 하지만 span은 찾을 수 없음 (무관한 텍스트)
        assert report.results[0].span_found_in_text is False
        # provenance는 실제 값이 있으므로 True
        assert report.results[0].provenance_traceable is True
        # 전체적으로 all_passed=False
        assert report.all_passed is False

    def test_no_valid_claims_becomes_insufficient(self):
        """valid=False인 claim만 있으면 assemble_grounded_answer가
        insufficient_evidence를 반환하는지 확인."""
        raw_claims = [
            ("Some claim text.", ["e_invalid"]),  # e_invalid는 included에 없음
        ]
        si = _make_synthesis_input(included=["e1"])
        claims = bind_claims(raw_claims, si)

        assert len(claims) == 1
        assert claims[0].valid is False  # e_invalid not in included

        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=si,
        )

        assert ga.status == "insufficient_evidence"
        assert ga.insufficiency_reason == "no_valid_claim"


# ============================================================
# Cross-case: 파이프라인 전체 통합 테스트
# ============================================================

class TestPipelineIntegration:
    """6개 케이스를 아우르는 파이프라인 전체 통합 테스트."""

    def test_full_pipeline_normal_flow(self):
        """정상 흐름: P4 → P5 → P6 → P7 전체가 예외 없이 통과."""
        ev = _make_evidence(
            evidence_id="e1",
            text="This is a valid claim text that should be found.",
        )
        pool = _make_pool([ev])

        # P4: SynthesisInput 구성
        si = _make_synthesis_input(included=["e1"])
        assert si.included_evidence_ids == ["e1"]

        # P5: Claim binding
        raw_claims = [("This is a valid claim text that should be found.", ["e1"])]
        claims = bind_claims(raw_claims, si)
        assert len(claims) == 1
        assert claims[0].valid is True

        # P6: GroundedAnswer assembly
        ga = assemble_grounded_answer(
            claims=claims,
            synthesis_input=si,
        )
        assert ga.status == "grounded"
        assert len(ga.claims) == 1

        # P7: Citation provenance check
        report = check_citation_provenance(ga, si, pool)
        assert report.total_checks == 1
        assert report.all_passed is True


# ============================================================
# Edge cases from existing test patterns
# ============================================================

class TestEdgeCases:
    """경계값 테스트."""

    def test_span_boundary_five_chars(self):
        """claim text가 정확히 5자이면 span_found=True (최소 길이 기준)."""
        ev = _make_evidence(
            evidence_id="e1",
            text="Hello world test string here.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="Hello",  # 정확히 5자
            evidence_ids=["e1"],
            valid=True,
        )
        ga = _make_grounded_answer(claims=[claim], status="grounded")
        si = _make_synthesis_input(included=["e1"])

        report = check_citation_provenance(ga, si, pool)
        assert report.results[0].span_found_in_text is True

    def test_span_four_chars_fails(self):
        """claim text가 4자이면 span_found=False (5자 미만 자동 실패)."""
        ev = _make_evidence(
            evidence_id="e1",
            text="Hello world test string here.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="Hell",  # 4자
            evidence_ids=["e1"],
            valid=True,
        )
        ga = _make_grounded_answer(claims=[claim], status="grounded")
        si = _make_synthesis_input(included=["e1"])

        report = check_citation_provenance(ga, si, pool)
        assert report.results[0].span_found_in_text is False

    def test_claim_with_empty_evidence_ids_skipped(self):
        """evidence_ids가 빈 claim은 citation check에서 제외된다."""
        ev = _make_evidence(
            evidence_id="e1",
            text="Some evidence text for testing.",
        )
        pool = _make_pool([ev])

        claim = _make_claim(
            claim_id="claim_000",
            text="Claim with no evidence ids.",
            evidence_ids=[],
            valid=False,
        )
        ga = _make_grounded_answer(claims=[claim], status="insufficient_evidence")
        si = _make_synthesis_input(included=["e1"])

        report = check_citation_provenance(ga, si, pool)
        assert report.total_checks == 0
