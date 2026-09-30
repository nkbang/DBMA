#!/usr/bin/env python
"""tests/test_parse_llm_claims.py -- CW-01/CW-02 검증: parse_llm_claims 단위 테스트.

CW-01: LLM이 프롬프트 지시문을 claim text로 반복하는 경우 감지·스킵
CW-02: claim text 내 [evidence_id: ...] 마커 제거 + 주변 공백/구두점 정리

실제 Ollama 출력 형태를 시뮬레이션한 입력으로 검증.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.grounded_synthesis_integration_demo import (
    _is_prompt_echo,
    _clean_evidence_markers,
    parse_llm_claims,
)


# ============================================================
# CW-01: _is_prompt_echo 검증
# ============================================================

class TestIsPromptEcho:
    def test_normal_claim_not_echo(self):
        """일반 claim text는 echo 아님."""
        assert _is_prompt_echo("개혁주의 관점에서 예정론과 인간의 자유의지는 양립할 수 있습니다.") is False

    def test_output_format_instruction_is_echo(self):
        """'출력 형식:' 지시문은 echo."""
        assert _is_prompt_echo("출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.") is True

    def test_evidence_ids_instruction_is_echo(self):
        """'evidence_ids는 위에서 본' 지시문은 echo."""
        assert _is_prompt_echo("evidence_ids는 위에서 본 [evidence_id: ...] 값을 그대로 써야 합니다.") is True

    def test_placeholder_evidence_id_is_echo(self):
        """'[evidence_id: ...]' placeholder는 echo."""
        assert _is_prompt_echo("[evidence_id: ...]") is True
        assert _is_prompt_echo("[evidence_id: ...] 값을 그대로 써야 합니다.") is True

    def test_each_line_pattern_is_echo(self):
        """'각 줄을 (' 패턴은 echo."""
        assert _is_prompt_echo("각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.") is True

    def test_claim_text_evidence_ids_pattern_is_echo(self):
        """'claim_text, [evidence_ids]' 패턴은 echo."""
        assert _is_prompt_echo("claim_text, [evidence_ids]") is True

    def test_evidence_id_bracket_pattern_is_echo(self):
        """'evidence_id를 대괄호' 패턴은 echo."""
        assert _is_prompt_echo("evidence_id를 대괄호 안의 값 그대로(수정하지 말고) 인용하세요.") is True

    def test_empty_line_not_echo(self):
        """빈 줄은 echo 아님."""
        assert _is_prompt_echo("") is False
        assert _is_prompt_echo("   ") is False

    def test_normal_text_with_evidence_id_is_not_echo(self):
        """실제 evidence_id를 포함한 claim text는 echo 아님."""
        assert _is_prompt_echo("예정론은 하나님의 주권을 강조한다 [evidence_id: NAE-TSU-0019937]") is False


# ============================================================
# CW-02: _clean_evidence_markers 검증
# ============================================================

class TestCleanEvidenceMarkers:
    def test_single_marker_removed(self):
        """단일 마커 제거 후 정리."""
        text = "claim text [evidence_id: NAE-TSU-0019937] end"
        result = _clean_evidence_markers(text)
        assert "[evidence_id:" not in result
        assert "NAE-TSU-0019937" not in result
        assert result == "claim text end"

    def test_multiple_markers_removed(self):
        """여러 마커 제거 후 정리."""
        text = "claim [evidence_id: E1] middle [evidence_id: E2] end"
        result = _clean_evidence_markers(text)
        assert "[evidence_id:" not in result
        assert result == "claim middle end"

    def test_trailing_comma_parenthesis_cleaned(self):
        """마커 제거 후 남은 ', )' 정리."""
        text = "claim [evidence_id: E1], )"
        result = _clean_evidence_markers(text)
        assert ", )" not in result
        assert result == "claim)"

    def test_multiple_trailing_punctuation_cleaned(self):
        """여러 구두점 정리."""
        text = "claim [evidence_id: E1], [evidence_id: E2], )"
        result = _clean_evidence_markers(text)
        assert "[evidence_id:" not in result
        assert ", )" not in result

    def test_no_marker_unchanged(self):
        """마커가 없으면 변경 없음."""
        text = "claim text without markers"
        result = _clean_evidence_markers(text)
        assert result == text

    def test_whitespace_normalized(self):
        """중복 공백 정리."""
        text = "claim   [evidence_id: E1]    middle"
        result = _clean_evidence_markers(text)
        assert "  " not in result
        assert result == "claim middle"


# ============================================================
# parse_llm_claims: 실제 LLM 출력 형태 시뮬레이션
# ============================================================

class TestParseLlmClaimsRealOutput:
    """실제 Ollama 출력을 시뮬레이션한 테스트."""

    def test_claim_with_inline_evidence_ids(self):
        """RPV-03a 스타일: claim text 안에 [evidence_id: X] 마커 포함."""
        llm_output = (
            "개혁주의 관점에서 예정론과 인간의 자유의지는 양립할 수 있습니다. "
            "[evidence_id: TSU-UNK-977f018156348df6732d679ff2fa0eff_chunk_01408], "
            "[evidence_id: TSU-UNK-977f018156348df6732d679ff2fa0eff_chunk_01857]"
        )
        claims = parse_llm_claims(llm_output, None)
        assert len(claims) == 1
        claim_text, evidence_ids = claims[0]
        # CW-02: 마커가 claim text에서 제거됨
        assert "[evidence_id:" not in claim_text
        # CW-01: 첫 줄이 실제 claim이므로 스킵 안 됨
        assert "출력 형식" not in claim_text
        assert "evidence_ids는 위에서 본" not in claim_text
        # evidence_ids는 추출됨
        assert len(evidence_ids) == 2

    def test_claim_with_prompt_echo_first_line(self):
        """LLM이 프롬프트 지시문을 첫 줄에 반복하는 경우."""
        llm_output = (
            "출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.\n"
            "개혁주의 관점에서 예정론과 인간의 자유의지는 양립할 수 있습니다. "
            "[evidence_id: NAE-TSU-0019937]"
        )
        claims = parse_llm_claims(llm_output, None)
        assert len(claims) == 1
        claim_text, evidence_ids = claims[0]
        # CW-01: 첫 줄(프롬프트 반복)이 스킵됨
        assert "출력 형식" not in claim_text
        assert "각 줄을 (" not in claim_text
        # 실제 claim text가 사용됨
        assert "양립할 수 있습니다" in claim_text

    def test_all_lines_are_prompt_echo(self):
        """모든 줄이 프롬프트 반복인 경우."""
        llm_output = (
            "출력 형식: 각 줄을 (claim_text, [evidence_ids]) 형태로 출력하세요.\n"
            "evidence_ids는 위에서 본 [evidence_id: ...] 값을 그대로 써야 합니다."
        )
        claims = parse_llm_claims(llm_output, None)
        assert claims == []

    def test_no_evidence_response(self):
        """근거 자료 없음 응답."""
        llm_output = "근거 자료가 없습니다."
        claims = parse_llm_claims(llm_output, None)
        assert len(claims) == 1
        assert claims[0] == ("근거 자료가 없습니다.", [])

    def test_no_evidence_english_response(self):
        """영어 근거 자료 없음 응답."""
        llm_output = "No evidence found."
        claims = parse_llm_claims(llm_output, None)
        assert len(claims) == 1
        assert claims[0] == ("근거 자료가 없습니다.", [])

    def test_claim_text_cleaned_of_punctuation(self):
        """마커 제거 후 남은 구두점 정리."""
        llm_output = (
            "claim text [evidence_id: E1], [evidence_id: E2], )\n"
            "extra line"
        )
        claims = parse_llm_claims(llm_output, None)
        assert len(claims) == 1
        claim_text, evidence_ids = claims[0]
        # CW-02: ", )" 같은 빈 구두점 정리
        assert ", )" not in claim_text
        assert "  " not in claim_text  # 중복 공백 없음


# ============================================================
# edge cases
# ============================================================

class TestParseLlmClaimsEdgeCases:
    def test_short_claim_ignored(self):
        """5자 미만 claim text는 무시."""
        llm_output = "짧은"
        claims = parse_llm_claims(llm_output, None)
        assert claims == []

    def test_empty_output(self):
        """빈 출력."""
        llm_output = ""
        claims = parse_llm_claims(llm_output, None)
        assert claims == []

    def test_only_whitespace(self):
        """공백만 있는 출력."""
        llm_output = "   \n  \n   "
        claims = parse_llm_claims(llm_output, None)
        assert claims == []

    def test_trailing_commas_cleaned(self):
        """연속 쉼표 제거 (RPV-03a 실제 출력 형태)."""
        text = "claim [evidence_id: E1], [evidence_id: E2], [evidence_id: E3], [evidence_id: E4],"
        result = _clean_evidence_markers(text)
        assert "[evidence_id:" not in result
        assert ", ," not in result
        assert result == "claim"
