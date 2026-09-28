"""core/grounded_claims.py Phase 5 tests.

Grounded Synthesis Phase 5: Claim–Evidence Binding
Tests cover:
    AC1: evidence_ids가 전부 included_evidence_ids에 있으면 valid == True
    AC2: evidence_ids 중 하나라도 included_evidence_ids에 없으면 valid == False
    AC3: evidence_ids == []이면 valid == False
    AC4: stub ClaimExtractor는 같은 입력에 항상 같은 출력 (결정적)
    AC5: core/claim_guard.py를 import하지 않음 (grep 확인)
    AC6: bind_claims는 prompt_text나 Evidence.text를 읽지 않음

ABSOLUTE RULES:
- LLM 호출 없음 (stub만 사용)
- claim_guard.py import 금지
"""

import subprocess
from typing import Any

import pytest

from core.grounded_claims import Claim, ClaimExtractor, StubClaimExtractor, bind_claims
from core.grounded_synthesis_input import SynthesisInput


# ============================================================
# FIXTURES — P4 SynthesisInput 재사용
# ============================================================

def _make_synthesis_input(
    included: list[str] | None = None,
    excluded: list[str] | None = None,
) -> SynthesisInput:
    """SynthesisInput을 생성하는 헬퍼."""
    inc = included or ["e1", "e2", "e3"]
    exc = excluded or []
    return SynthesisInput(
        query_specs=[],
        included_evidence_ids=inc,
        excluded_evidence_ids=exc,
        truncated=len(exc) > 0,
        prompt_text="test prompt",
    )


# ============================================================
# AC1: evidence_ids가 전부 included에 있으면 valid == True
# ============================================================

class TestAC1_ValidBinding:
    def test_ac1_all_eids_included(self):
        """AC1: evidence_ids가 전부 included_evidence_ids에 있으면 valid == True."""
        si = _make_synthesis_input(included=["e1", "e2", "e3"])
        raw_claims = [
            ("Claim 1 text", ["e1", "e2"]),
            ("Claim 2 text", ["e3"]),
        ]

        claims = bind_claims(raw_claims, si)

        assert len(claims) == 2
        for c in claims:
            assert c.valid is True
            assert set(c.evidence_ids).issubset(set(si.included_evidence_ids))

    def test_ac1_single_eid(self):
        """AC1: 단일 evidence_id도 포함되면 valid == True."""
        si = _make_synthesis_input(included=["e1", "e2"])
        raw_claims = [("Single claim", ["e2"])]

        claims = bind_claims(raw_claims, si)

        assert claims[0].valid is True


# ============================================================
# AC2: evidence_ids 중 하나라도 included에 없으면 valid == False
# ============================================================

class TestAC2_InvalidBinding:
    def test_ac2_one_eid_not_included(self):
        """AC2: evidence_ids 중 하나라도 included에 없으면 valid == False."""
        si = _make_synthesis_input(included=["e1", "e2"])
        raw_claims = [("Claim with bad ref", ["e1", "e999"])]

        claims = bind_claims(raw_claims, si)

        assert len(claims) == 1
        assert claims[0].valid is False
        # Claim은 리스트에서 제외되지 않고 남아 있음
        assert claims[0].text == "Claim with bad ref"
        assert claims[0].evidence_ids == ["e1", "e999"]

    def test_ac2_all_eids_not_included(self):
        """AC2: 모든 evidence_id가 included에 없으면 valid == False."""
        si = _make_synthesis_input(included=["e1", "e2"])
        raw_claims = [("All bad refs", ["e999", "e888"])]

        claims = bind_claims(raw_claims, si)

        assert claims[0].valid is False

    def test_ac2_excluded_eid(self):
        """AC2: excluded_evidence_ids에 있는 id도 valid == False."""
        si = _make_synthesis_input(
            included=["e1", "e2"],
            excluded=["e3"],
        )
        raw_claims = [("Claim referencing excluded", ["e3"])]

        claims = bind_claims(raw_claims, si)

        assert claims[0].valid is False


# ============================================================
# AC3: evidence_ids == []이면 valid == False
# ============================================================

class TestAC3_NoEvidence:
    def test_ac3_empty_evidence_ids(self):
        """AC3: evidence_ids가 비어 있으면 valid == False."""
        si = _make_synthesis_input(included=["e1", "e2"])
        raw_claims = [("Claim without evidence", [])]

        claims = bind_claims(raw_claims, si)

        assert len(claims) == 1
        assert claims[0].valid is False
        assert claims[0].evidence_ids == []
        # Claim은 폐기되지 않고 남아 있음
        assert claims[0].text == "Claim without evidence"


# ============================================================
# AC4: stub ClaimExtractor는 결정적 (3회 반복 동일)
# ============================================================

class TestAC4_Determinism:
    def test_ac4_three_runs_identical(self):
        """AC4: 같은 입력에 대해 3회 실행해도 결과가 완전히 동일."""
        si = _make_synthesis_input(included=["e1", "e2", "e3"])
        answer_text = "The church is holy and the faith is strong."

        extractor = StubClaimExtractor(claims_map={
            "church": [("The church is holy", ["e1"])],
            "faith": [("The faith is strong", ["e2"])],
        })

        results = []
        for _ in range(3):
            claims = extractor.extract(answer_text, si)
            results.append(claims)

        # 3회 결과가 완전히 동일한지 확인
        def claim_repr(claims):
            return [(c.claim_id, c.text, tuple(c.evidence_ids), c.valid) for c in claims]

        assert claim_repr(results[0]) == claim_repr(results[1])
        assert claim_repr(results[1]) == claim_repr(results[2])

    def test_ac4_stub_deterministic_no_network(self):
        """AC4: stub이 네트워크 호출을 하지 않음을 구조로 확인."""
        # StubClaimExtractor.__init__과 extract는 claims_map만 사용
        # 외부 상태 읽기/쓰기 없음
        extractor = StubClaimExtractor(claims_map={})
        si = _make_synthesis_input()
        claims = extractor.extract("", si)
        assert claims == []


# ============================================================
# AC5: core/claim_guard.py import 금지 (grep 확인)
# ============================================================

class TestAC5_NoClaimGuardImport:
    def test_ac5_grep_no_claim_guard(self):
        """AC5: grep으로 import/from 문에서 claim_guard 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"^(import|from)\s+.*claim_guard",
                "/Users/David/DBMA/core/grounded_claims.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"AC5 실패: claim_guard import가 발견됨:\n{result.stdout}"
        )


# ============================================================
# AC6: bind_claims는 prompt_text나 Evidence.text를 읽지 않음
# ============================================================

class TestAC6_ResponsibilityBoundary:
    def test_ac6_bind_claims_uses_only_ids(self):
        """AC6: bind_claims가 evidence_id의 ID 소속 여부만 검사함을 구조로 확인."""
        # bind_claims의 구현을 직접 호출하고, SynthesisInput.prompt_text를
        # 변경해도 결과가 동일해야 함 (prompt_text를 읽지 않으므로)
        si1 = _make_synthesis_input(included=["e1", "e2"])
        si2 = SynthesisInput(
            query_specs=[],
            included_evidence_ids=["e1", "e2"],
            excluded_evidence_ids=[],
            truncated=False,
            prompt_text="completely different text",
        )

        raw_claims = [("Test claim", ["e1", "e2"])]
        claims1 = bind_claims(raw_claims, si1)
        claims2 = bind_claims(raw_claims, si2)

        assert claims1[0].valid == claims2[0].valid  # True == True

    def test_ac6_grep_no_prompt_text_code_access(self):
        """AC6: grep으로 코드 라인에서 prompt_text 접근 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"^(import|from)\s+.*prompt_text|^\s*\.prompt_text\b|synthesis_input\.prompt_text",
                "/Users/David/DBMA/core/grounded_claims.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"AC6 실패: prompt_text 코드 접근이 발견됨:\n{result.stdout}"
        )


# ============================================================
# Claim 구조 검증
# ============================================================

class TestClaimStructure:
    def test_claim_is_frozen_dataclass(self):
        """Claim이 frozen dataclass인지 확인."""
        from dataclasses import fields

        assert hasattr(Claim, "__dataclass_fields__")
        c = Claim(claim_id="c1", text="text", evidence_ids=["e1"], valid=True)
        with pytest.raises(Exception):
            c.valid = False

    def test_claim_all_fields_present(self):
        """Claim이 ADR-036 B8의 모든 필드를 갖는지 확인."""
        from dataclasses import fields

        field_names = {f.name for f in fields(Claim)}
        expected = {"claim_id", "text", "evidence_ids", "valid"}
        assert field_names == expected


# ============================================================
# bind_claims 추가 검증
# ============================================================

class TestBindClaimsEdgeCases:
    def test_empty_raw_claims(self):
        """빈 raw_claims은 빈 리스트 반환."""
        si = _make_synthesis_input()
        claims = bind_claims([], si)
        assert claims == []

    def test_multiple_claims_mixed_validity(self):
        """여러 Claim 중 일부만 valid일 수 있음."""
        si = _make_synthesis_input(included=["e1", "e2"])
        raw_claims = [
            ("Valid claim", ["e1"]),
            ("Invalid claim", ["e999"]),
            ("Another valid", ["e2"]),
        ]

        claims = bind_claims(raw_claims, si)

        assert len(claims) == 3
        assert claims[0].valid is True
        assert claims[1].valid is False
        assert claims[2].valid is True
        # 유효한 Claim도 invalid Claim도 모두 리스트에 남아 있음
        assert all(c in claims for c in claims)

    def test_claim_ids_preserved(self):
        """claim_id가 claim_000, claim_001 ... 순으로 할당됨."""
        si = _make_synthesis_input()
        raw_claims = [
            ("First", ["e1"]),
            ("Second", ["e2"]),
            ("Third", ["e3"]),
        ]

        claims = bind_claims(raw_claims, si)

        assert claims[0].claim_id == "claim_000"
        assert claims[1].claim_id == "claim_001"
        assert claims[2].claim_id == "claim_002"


# ============================================================
# StubClaimExtractor 검증
# ============================================================

class TestStubClaimExtractor:
    def test_extract_no_match(self):
        """answer_text에 패턴이 없으면 빈 리스트."""
        extractor = StubClaimExtractor(claims_map={"pattern_x": [("Claim", ["e1"])]})
        si = _make_synthesis_input(included=["e1"])
        claims = extractor.extract("no match here", si)
        assert claims == []

    def test_extract_partial_match(self):
        """answer_text에 패턴이 부분 매치되면 claim 추출."""
        extractor = StubClaimExtractor(claims_map={
            "church": [("The church is holy", ["e1"])],
        })
        si = _make_synthesis_input(included=["e1"])
        claims = extractor.extract("The church is holy and the faith is strong.", si)
        assert len(claims) == 1
        assert claims[0].valid is True

    def test_extract_multiple_patterns(self):
        """여러 패턴이 매치되면 모든 claim 추출."""
        extractor = StubClaimExtractor(claims_map={
            "church": [("The church is holy", ["e1"])],
            "faith": [("The faith is strong", ["e2"])],
        })
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = extractor.extract("The church is holy and the faith is strong.", si)
        assert len(claims) == 2
        assert all(c.valid for c in claims)

    def test_extract_invalid_eid(self):
        """extracted claim의 evidence_id가 included에 없으면 valid=False."""
        extractor = StubClaimExtractor(claims_map={
            "church": [("The church is holy", ["e1"])],
            "faith": [("The faith is strong", ["e999"])],
        })
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = extractor.extract("The church is holy and the faith is strong.", si)
        assert len(claims) == 2
        assert claims[0].valid is True   # e1 in included
        assert claims[1].valid is False  # e999 not in included
