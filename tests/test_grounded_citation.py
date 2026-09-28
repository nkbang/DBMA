"""tests/test_grounded_citation.py -- Grounded Synthesis Phase 7: Citation Provenance Check.

Tests cover:
    AC1: id_exists -- evidence_id가 included_evidence_ids에 존재/부재
    AC2: span_found_in_text -- Evidence.text에 claim text가 부분일치
    AC3: provenance_traceable -- Evidence.has_provenance
    AC4: span 최소 길이 기준 (5자 미만 = 자동 실패)
    AC5: claim.evidence_ids 빈 경우 검사 제외
    AC6: evidence_pool.get(eid) == None 인 경우 처리
    AC7: CitationCheckReport.all_passed / claim_summary

판정 기준 명시 (core/grounded_citation.py::_check_span_in_text):
    - 최소 길이: 5자 이상 (공백 포함, case-sensitive 부분일치)
    - 5자 미만 claim text는 span_found_in_text = False (자동 실패)
    - exact substring match: evidence_text.find(claim_text) >= 0

ABSOLUTE RULES:
- 실제 Evidence 데이터 사용 (가짜 provenance 생성 금지)
- 의미적 분석 없음 -- 구조적 존재 여부만 검사
"""

from dataclasses import fields

import pytest

from core.evidence_model import Evidence, EvidenceProvenance
from core.evidence_pool import EvidencePool
from core.grounded_answer import GroundedAnswer
from core.grounded_citation import (
    CitationCheckReport,
    CitationCheckResult,
    check_citation_provenance,
)
from core.grounded_claims import Claim
from core.grounded_synthesis_input import SynthesisInput


# ============================================================
# FIXTURES
# ============================================================

def _make_evidence(
    evidence_id: str = "e1",
    text: str = "This is sample evidence text for testing purposes.",
    has_prov: bool = True,
) -> Evidence:
    """Evidence 객체를 생성하는 헬퍼."""
    prov = EvidenceProvenance(
        source_file="test_source.txt" if has_prov else None,
        document_id="doc1" if has_prov else None,
        chunk_id="chunk1" if has_prov else None,
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
# AC1: id_exists -- evidence_id가 included_evidence_ids에 존재/부재
# ============================================================

class TestAC1_IdExists:
    def test_ac1_id_exists_true(self):
        """AC1: evidence_id가 included_evidence_ids에 있으면 id_exists=True."""
        ga = _make_grounded_answer(
            claims=[_make_claim(evidence_ids=["e1"])]
        )
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        assert report.results[0].id_exists is True

    def test_ac1_id_exists_false(self):
        """AC1: evidence_id가 included_evidence_ids에 없으면 id_exists=False."""
        ga = _make_grounded_answer(
            claims=[_make_claim(evidence_ids=["e999"])]
        )
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        assert report.results[0].id_exists is False

    def test_ac1_multiple_eids_mixed(self):
        """AC1: 여러 evidence_id 중 일부만 존재."""
        ga = _make_grounded_answer(
            claims=[_make_claim(evidence_ids=["e1", "e2", "e999"])]
        )
        si = _make_synthesis_input(included=["e1", "e2"])
        pool = _make_pool([_make_evidence("e1"), _make_evidence("e2")])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 3
        assert report.results[0].id_exists is True   # e1
        assert report.results[1].id_exists is True   # e2
        assert report.results[2].id_exists is False  # e999
        assert report.id_missing_count == 1


# ============================================================
# AC2: span_found_in_text -- Evidence.text에 claim text가 부분일치
# ============================================================

class TestAC2_SpanFoundInText:
    def test_ac2_span_found(self):
        """AC2: claim text가 Evidence.text에 있으면 span_found_in_text=True."""
        claim = _make_claim(text="sample evidence text for testing")
        ga = _make_grounded_answer(claims=[claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "This is sample evidence text for testing purposes.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is True

    def test_ac2_span_not_found(self):
        """AC2: claim text가 Evidence.text에 없으면 span_found_in_text=False."""
        claim = _make_claim(text="completely different text here")
        ga = _make_grounded_answer(claims=[claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "This is sample evidence text for testing purposes.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is False

    def test_ac2_case_sensitive(self):
        """AC2: 대소문자 구분 -- 'Sample'과 'sample'은 다름."""
        claim = _make_claim(text="Sample evidence text")
        ga = _make_grounded_answer(claims=[claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "this is sample evidence text for testing.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is False


# ============================================================
# AC3: provenance_traceable -- Evidence.has_provenance
# ============================================================

class TestAC3_ProvenanceTraceable:
    def test_ac3_provenance_exists(self):
        """AC3: provenance가 있으면 provenance_traceable=True."""
        ga = _make_grounded_answer(claims=[_make_claim()])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", has_prov=True)])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].provenance_traceable is True

    def test_ac3_no_provenance(self):
        """AC3: provenance가 없으면 provenance_traceable=False."""
        ga = _make_grounded_answer(claims=[_make_claim()])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", has_prov=False)])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].provenance_traceable is False


# ============================================================
# AC4: span 최소 길이 기준 (5자 미만 = 자동 실패)
# ============================================================

class TestAC4_SpanMinimumLength:
    def test_ac4_span_too_short(self):
        """AC4: claim text가 5자 미만이면 span_found_in_text=False."""
        short_claim = _make_claim(text="abc")
        ga = _make_grounded_answer(claims=[short_claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "abc is in this text.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is False

    def test_ac4_span_exactly_five(self):
        """AC4: claim text가 정확히 5자이면 최소 길이 조건 통과."""
        five_char_claim = _make_claim(text="hello")
        ga = _make_grounded_answer(claims=[five_char_claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "world hello there")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is True

    def test_ac4_span_four_chars(self):
        """AC4: claim text가 4자이면 실패."""
        four_char_claim = _make_claim(text="hell")
        ga = _make_grounded_answer(claims=[four_char_claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "world hello there")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is False


# ============================================================
# AC5: claim.evidence_ids 빈 경우 검사 제외
# ============================================================

class TestAC5_EmptyEvidenceIds:
    def test_ac5_empty_evidence_ids_excluded(self):
        """AC5: evidence_ids가 빈 claim은 검사에서 제외."""
        empty_claim = _make_claim(evidence_ids=[])
        ga = _make_grounded_answer(claims=[empty_claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 0
        assert report.results == []


# ============================================================
# AC6: evidence_pool.get(eid) == None 인 경우 처리
# ============================================================

class TestAC6_MissingEvidenceInPool:
    def test_ac6_evidence_not_in_pool(self):
        """AC6: pool에 없는 evidence_id -> span_found=False, provenance_traceable=False."""
        ga = _make_grounded_answer(claims=[_make_claim(evidence_ids=["e1"])])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 1
        assert report.results[0].id_exists is True      # included에는 있음
        assert report.results[0].span_found_in_text is False
        assert report.results[0].provenance_traceable is False


# ============================================================
# AC7: CitationCheckReport.all_passed / claim_summary
# ============================================================

class TestAC7_ReportSummary:
    def test_ac7_all_passed_true(self):
        """AC7: 모든 검사가 통과하면 all_passed=True."""
        claim_text = "This is a valid claim text that should be found."
        claim = _make_claim(text=claim_text)
        ga = _make_grounded_answer(claims=[claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", f"{claim_text} more text here.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.all_passed is True

    def test_ac7_all_passed_false(self):
        """AC7: 하나라도 실패하면 all_passed=False."""
        ga = _make_grounded_answer(claims=[_make_claim(evidence_ids=["e999"])])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        assert report.all_passed is False

    def test_ac7_claim_summary_grouping(self):
        """AC7: claim_summary가 claim_id별로 그룹화."""
        claims = [
            _make_claim(claim_id="claim_000", evidence_ids=["e1"]),
            _make_claim(claim_id="claim_001", evidence_ids=["e1"]),
        ]
        ga = _make_grounded_answer(claims=claims)
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        summary = report.claim_summary
        assert "claim_000" in summary
        assert "claim_001" in summary
        assert len(summary["claim_000"]) == 1
        assert len(summary["claim_001"]) == 1

    def test_ac7_count_statistics(self):
        """AC7: id_missing_count, span_not_found_count, provenance_untraceable_count 정확."""
        pool_evidence_text = "This is sample evidence text for testing purposes."
        claims = [
            _make_claim(claim_id="c0", text="sample evidence text for testing", evidence_ids=["e1"]),  # all pass
            _make_claim(claim_id="c1", evidence_ids=["e999"]),  # id_missing + pool 없음 -> span_not_found
            _make_claim(claim_id="c2", text="short"),           # span too short
        ]
        ga = _make_grounded_answer(claims=claims)
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", pool_evidence_text)])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 3
        assert report.id_missing_count == 1    # e999
        assert report.span_not_found_count == 2  # c1 (pool 없음) + c2 (short)
        assert report.provenance_untraceable_count == 1  # c1 (pool 없음 -> provenance=False)


# ============================================================
# CitationCheckResult 구조 검증
# ============================================================

class TestCitationCheckResultStructure:
    def test_result_is_frozen_dataclass(self):
        """CitationCheckResult가 frozen dataclass."""
        r = CitationCheckResult(
            claim_id="c0",
            evidence_id="e1",
            id_exists=True,
            span_found_in_text=True,
            provenance_traceable=True,
        )
        with pytest.raises(Exception):
            r.id_exists = False

    def test_result_all_fields_present(self):
        """CitationCheckResult가 모든 필드를 갖는지 확인."""
        field_names = {f.name for f in fields(CitationCheckResult)}
        expected = {"claim_id", "evidence_id", "id_exists", "span_found_in_text", "provenance_traceable"}
        assert field_names == expected


# ============================================================
# CitationCheckReport 구조 검증
# ============================================================

class TestCitationCheckReportStructure:
    def test_report_is_frozen_dataclass(self):
        """CitationCheckReport가 frozen dataclass."""
        r = CitationCheckReport()
        with pytest.raises(Exception):
            r.total_checks = 999

    def test_report_all_fields_present(self):
        """CitationCheckReport의 dataclass 필드 확인 (computed properties 제외)."""
        field_names = {f.name for f in fields(CitationCheckReport)}
        expected = {"results"}
        assert field_names == expected

    def test_report_computed_properties_exist(self):
        """CitationCheckReport의 computed properties 확인."""
        report = CitationCheckReport()
        assert hasattr(report, "total_checks")
        assert hasattr(report, "id_missing_count")
        assert hasattr(report, "span_not_found_count")
        assert hasattr(report, "provenance_untraceable_count")
        assert hasattr(report, "all_passed")
        assert hasattr(report, "claim_summary")

    def test_report_default_values(self):
        """CitationCheckReport 기본값 확인."""
        report = CitationCheckReport()
        assert report.results == []
        assert report.total_checks == 0
        assert report.id_missing_count == 0
        assert report.span_not_found_count == 0
        assert report.provenance_untraceable_count == 0
        assert report.all_passed is True


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    def test_empty_grounded_answer(self):
        """빈 claims의 GroundedAnswer."""
        ga = _make_grounded_answer(claims=[])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1")])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 0
        assert report.all_passed is True

    def test_multiple_claims_multiple_eids(self):
        """여러 claim x 여러 evidence_id."""
        claims = [
            _make_claim(claim_id="c0", text="first claim text for verification", evidence_ids=["e1"]),
            _make_claim(claim_id="c1", text="second claim text for verification", evidence_ids=["e2"]),
        ]
        ga = _make_grounded_answer(claims=claims)
        si = _make_synthesis_input(included=["e1", "e2"])
        pool = _make_pool([
            _make_evidence("e1", "This is first claim text for verification evidence."),
            _make_evidence("e2", "This is second claim text for verification evidence."),
        ])

        report = check_citation_provenance(ga, si, pool)

        assert report.total_checks == 2
        assert report.results[0].id_exists is True
        assert report.results[0].span_found_in_text is True
        assert report.results[0].provenance_traceable is True
        assert report.results[1].id_exists is True
        assert report.results[1].span_found_in_text is True
        assert report.results[1].provenance_traceable is True
        assert report.all_passed is True

    def test_span_at_boundary(self):
        """claim text가 Evidence.text의 시작/끝에 위치."""
        claim = _make_claim(text="beginning of text")
        ga = _make_grounded_answer(claims=[claim])
        si = _make_synthesis_input(included=["e1"])
        pool = _make_pool([_make_evidence("e1", "beginning of text is here at start.")])

        report = check_citation_provenance(ga, si, pool)

        assert report.results[0].span_found_in_text is True


# ============================================================
# AC8: Short-circuit when id_exists=False (GS-P07 r2 REWORK)
# ============================================================

class TestAC8_ShortCircuit:
    def test_ac1_short_circuit_when_evidence_in_pool_but_excluded(self):
        """AC1/AC8: evidence가 Pool에는 실재하지만 included_evidence_ids에는 없으면
        (max_evidence 절단으로 excluded된 경우) id_exists=False이고
        span_found_in_text/provenance_traceable도 자동으로 False여야 한다
        (CUE V7 재현 케이스)."""
        pool = EvidencePool()
        pool.add(Evidence(
            evidence_id="e_excluded", corpus_type="default",
            text="This is a real evidence text that fully supports the claim below.",
            source_file="real_source.pdf",
            provenance=EvidenceProvenance(source_file="real_source.pdf"),
        ))
        si = SynthesisInput(
            query_specs=[], included_evidence_ids=["e1"],
            excluded_evidence_ids=["e_excluded"], truncated=True, prompt_text="...",
        )
        claim = Claim(
            claim_id="c1",
            text="This is a real evidence text that fully supports the claim below.",
            evidence_ids=["e_excluded"], valid=False,
        )
        ga = GroundedAnswer(status="insufficient_evidence", claims=[claim],
                             text="...", insufficiency_reason="no_valid_claim")

        report = check_citation_provenance(ga, si, pool)
        r = report.results[0]
        assert r.id_exists is False
        assert r.span_found_in_text is False   # 자동 False여야 함
        assert r.provenance_traceable is False  # 자동 False여야 함
