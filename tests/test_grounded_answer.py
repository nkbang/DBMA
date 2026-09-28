"""core/grounded_answer.py Phase 6 tests.

Grounded Synthesis Phase 6: GroundedAnswer Assembly
Tests cover:
    AC1: included_evidence_ids == [] -> status="insufficient_evidence", reason="no_evidence"
    AC2: 모든 claim이 valid=False -> status="insufficient_evidence", reason="no_valid_claim"
    AC3: valid=True claim 존재 -> status="grounded", invalid text 제외
    AC4: insufficient text가 금지 표현("일반적으로", "일반적인 신학적 관점에서") 미포함
    AC5: 자동 충돌 탐지 코드 없음 -- 호출자 명시 플래그만 사용
    AC6: core/generation.py 함수 호출 없음 (grep 확인)

ABSOLUTE RULES:
- LLM 호출 없음 (stub만 사용)
- 자동 충돌 탐지 로직 금지
"""

import subprocess
from typing import Any

import pytest

from core.grounded_claims import Claim
from core.grounded_answer import GroundedAnswer, assemble_grounded_answer
from core.grounded_synthesis_input import SynthesisInput


# ============================================================
# FIXTURES
# ============================================================

def _make_claim(
    claim_id: str = "claim_000",
    text: str = "Valid claim text.",
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


def _make_synthesis_input(included: list[str] | None = None) -> SynthesisInput:
    """SynthesisInput을 생성하는 헬퍼. [] 전달 시 빈 리스트로 유지."""
    inc = included if included is not None else ["e1", "e2"]
    return SynthesisInput(
        query_specs=[],
        included_evidence_ids=inc,
        excluded_evidence_ids=[],
        truncated=len([]) > 0,
        prompt_text="test prompt",
    )


# ============================================================
# AC1: included_evidence_ids == [] -> insufficient_evidence
# ============================================================

class TestAC1_NoEvidencePool:
    def test_ac1_empty_included(self):
        """AC1: included_evidence_ids가 비어 있으면 status='insufficient_evidence', reason='no_evidence'."""
        si = _make_synthesis_input(included=[])
        claims = [_make_claim()]

        result = assemble_grounded_answer(claims, si)

        assert result.status == "insufficient_evidence"
        assert result.insufficiency_reason == "no_evidence"
        # claims는 그대로 포함 (폐기 없음)
        assert result.claims == claims

    def test_ac1_text_no_forbidden_phrases(self):
        """AC1: insufficient text가 금지 표현을 포함하지 않음."""
        si = _make_synthesis_input(included=[])
        claims = [_make_claim()]

        result = assemble_grounded_answer(claims, si)

        assert "일반적으로" not in result.text
        assert "일반적인 신학적 관점에서" not in result.text
        assert "보통" not in result.text


# ============================================================
# AC2: 모든 claim이 valid=False -> insufficient_evidence
# ============================================================

class TestAC2_AllInvalidClaims:
    def test_ac2_all_invalid(self):
        """AC2: 모든 claim이 valid=False -> status='insufficient_evidence', reason='no_valid_claim'."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="Invalid 1.", evidence_ids=["e999"], valid=False),
            _make_claim(claim_id="c1", text="Invalid 2.", evidence_ids=["e888"], valid=False),
        ]

        result = assemble_grounded_answer(claims, si)

        assert result.status == "insufficient_evidence"
        assert result.insufficiency_reason == "no_valid_claim"
        # invalid claim들이 여전히 claims에 남아 있음 (폐기 없음)
        assert len(result.claims) == 2
        assert result.claims[0].valid is False
        assert result.claims[1].valid is False

    def test_ac2_text_no_forbidden_phrases(self):
        """AC2: insufficient text가 금지 표현을 포함하지 않음."""
        si = _make_synthesis_input(included=["e1"])
        claims = [_make_claim(valid=False, evidence_ids=["e999"])]

        result = assemble_grounded_answer(claims, si)

        assert "일반적으로" not in result.text
        assert "일반적인 신학적 관점에서" not in result.text


# ============================================================
# AC3: valid=True claim 존재 -> grounded, invalid text 제외
# ============================================================

class TestAC3_GroundedStatus:
    def test_ac3_valid_claim_grounded(self):
        """AC3: valid=True claim이 있으면 status='grounded'."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="Valid claim.", evidence_ids=["e1"], valid=True),
            _make_claim(claim_id="c1", text="Invalid claim.", evidence_ids=["e999"], valid=False),
        ]

        result = assemble_grounded_answer(claims, si)

        assert result.status == "grounded"
        # invalid claim의 text는 text에 포함되지 않음
        assert "Valid claim." in result.text
        assert "Invalid claim." not in result.text
        # 하지만 claims 리스트에는 invalid도 남아 있음
        assert len(result.claims) == 2

    def test_ac3_all_valid(self):
        """AC3: 모든 claim이 valid=True면 status='grounded'."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="First.", evidence_ids=["e1"], valid=True),
            _make_claim(claim_id="c1", text="Second.", evidence_ids=["e2"], valid=True),
        ]

        result = assemble_grounded_answer(claims, si)

        assert result.status == "grounded"
        assert "First." in result.text
        assert "Second." in result.text


# ============================================================
# AC4: insufficient text가 금지 표현 미포함 (테스트로 못박음)
# ============================================================

class TestAC4_NoForbiddenPhrases:
    FORBIDDEN_PHRASES = [
        "일반적으로",
        "일반적인 신학적 관점에서",
        "보통",
        "대부분의",
        "일부 신학자들은",
    ]

    def test_ac4_all_insufficient_texts_clean(self):
        """AC4: 모든 insufficient 상태 text가 금지 표현을 포함하지 않음."""
        si_with_evidence = _make_synthesis_input(included=["e1"])
        si_without_evidence = _make_synthesis_input(included=[])

        # no_valid_claim 경로
        claims_invalid = [_make_claim(valid=False, evidence_ids=["e999"])]
        result1 = assemble_grounded_answer(claims_invalid, si_with_evidence)

        # no_evidence 경로
        claims_any = [_make_claim()]
        result2 = assemble_grounded_answer(claims_any, si_without_evidence)

        for result in [result1, result2]:
            assert result.status == "insufficient_evidence"
            for phrase in self.FORBIDDEN_PHRASES:
                assert phrase not in result.text, (
                    f"금지 표현 '{phrase}'가 insufficient text에 발견됨: {result.text}"
                )


# ============================================================
# AC5: 자동 충돌 탐지 코드 없음 -- 호출자 명시 플래그만 사용
# ============================================================

class TestAC5_NoAutoConflictDetection:
    def test_ac5_grep_no_similarity_code(self):
        """AC5: grep으로 코드 라인에서 유사도/반대/충돌탐지 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nEi",
                r"similarity|cosine|difflib|fuzzy|ratio\(|\.similarity|conflict.*detect|antonym|반대|유사도",
                "/Users/David/DBMA/core/grounded_answer.py",
            ],
            capture_output=True,
            text=True,
        )
        # docstring의 "자동 충돌 탐지" 설명은 허용 -- 실제 코드 라인만 확인
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        code_lines = [l for l in lines if ":" in l and not any(
            l.startswith(f"{i}|") for i in range(1, 30)
        )]
        # docstring 내의 설명은 1-30 라인 범위 내에 있으므로 제외
        non_doc_lines = [l for l in lines if not any(l.startswith(f"{n}|") for n in range(1, 30))]
        assert len(non_doc_lines) == 0, (
            f"AC5 실패: 자동 충돌 탐지 코드가 발견됨:\n{result.stdout}"
        )

    def test_ac5_conflicting_requires_explicit_flag(self):
        """AC5: conflicting 상태는 호출자가 conflicting=True 플래그로만 진입."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="View A.", evidence_ids=["e1"], valid=True),
            _make_claim(claim_id="c1", text="View B.", evidence_ids=["e2"], valid=True),
        ]

        # conflicting=False (기본값) -> grounded
        result_default = assemble_grounded_answer(claims, si)
        assert result_default.status == "grounded"

        # conflicting=True -> conflicting_evidence
        result_conflict = assemble_grounded_answer(claims, si, conflicting=True)
        assert result_conflict.status == "conflicting_evidence"
        assert "서로 다른 견해" in result_conflict.text


# ============================================================
# AC6: core/generation.py 함수 호출 없음 (grep 확인)
# ============================================================

class TestAC6_NoGenerationCall:
    def test_ac6_grep_no_generation_import(self):
        """AC6: grep으로 generation.py import 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"^(import|from)\s+.*generation",
                "/Users/David/DBMA/core/grounded_answer.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"AC6 실패: generation.py import가 발견됨:\n{result.stdout}"
        )

    def test_ac6_grep_no_directive_access(self):
        """AC6: grep으로 directive 상수 접근 부재 확인."""
        result = subprocess.run(
            [
                "grep", "-nE",
                r"_GROUNDING_DIRECTIVE|_DENOMINATION_DIRECTIVE",
                "/Users/David/DBMA/core/grounded_answer.py",
            ],
            capture_output=True,
            text=True,
        )
        # docstring 내의 설명은 1-20 라인 범위 내에 있으므로 제외
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        non_doc_lines = [l for l in lines if not any(l.startswith(f"{n}|") for n in range(1, 25))]
        assert len(non_doc_lines) == 0, (
            f"AC6 실패: directive 접근이 발견됨:\n{result.stdout}"
        )


# ============================================================
# GroundedAnswer 구조 검증
# ============================================================

class TestGroundedAnswerStructure:
    def test_grounded_answer_is_frozen_dataclass(self):
        """GroundedAnswer가 frozen dataclass인지 확인."""
        from dataclasses import fields

        assert hasattr(GroundedAnswer, "__dataclass_fields__")
        ga = GroundedAnswer(
            status="grounded",
            claims=[],
            text="test",
            insufficiency_reason=None,
        )
        with pytest.raises(Exception):
            ga.status = "insufficient_evidence"

    def test_grounded_answer_all_fields_present(self):
        """GroundedAnswer가 ADR-036 B8의 모든 필드를 갖는지 확인."""
        from dataclasses import fields

        field_names = {f.name for f in fields(GroundedAnswer)}
        expected = {"status", "claims", "text", "insufficiency_reason"}
        assert field_names == expected

    def test_grounded_answer_status_literal(self):
        """GroundedAnswer.status가 3가지 상태만 허용."""
        ga = GroundedAnswer(
            status="grounded",
            claims=[],
            text="",
            insufficiency_reason=None,
        )
        assert ga.status in ("grounded", "insufficient_evidence", "conflicting_evidence")


# ============================================================
# assemble_grounded_answer 추가 검증
# ============================================================

class TestAssembleGroundedAnswerEdgeCases:
    def test_empty_claims_list(self):
        """빈 claims 리스트는 insufficient_evidence."""
        si = _make_synthesis_input(included=["e1"])
        result = assemble_grounded_answer([], si)
        assert result.status == "insufficient_evidence"
        assert result.insufficiency_reason == "no_claims"

    def test_conflicting_text_structure(self):
        """conflicting 상태 text가 evidence_id와 함께 claim을 병기."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="View A.", evidence_ids=["e1"], valid=True),
            _make_claim(claim_id="c1", text="View B.", evidence_ids=["e2"], valid=True),
        ]

        result = assemble_grounded_answer(claims, si, conflicting=True)

        assert result.status == "conflicting_evidence"
        assert "서로 다른 견해" in result.text
        assert "e1" in result.text
        assert "e2" in result.text
        assert "View A." in result.text
        assert "View B." in result.text

    def test_mixed_valid_claims_preserved(self):
        """grounded 상태에서도 invalid claim은 claims 리스트에 남아 있음."""
        si = _make_synthesis_input(included=["e1", "e2"])
        claims = [
            _make_claim(claim_id="c0", text="Valid.", evidence_ids=["e1"], valid=True),
            _make_claim(claim_id="c1", text="Invalid.", evidence_ids=["e999"], valid=False),
        ]

        result = assemble_grounded_answer(claims, si)

        assert result.status == "grounded"
        assert len(result.claims) == 2
        assert result.claims[0].valid is True
        assert result.claims[1].valid is False
