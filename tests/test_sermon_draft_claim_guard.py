"""tests/test_sermon_draft_claim_guard.py — SermonDraftService ClaimGuard 커버리지.

배경: PM 정렬 감사 / "답변 신뢰도 검증" 개선(2026-09-17). ClaimGuard는
Chat/Research 경로(GenerationService.generate/generate_stream)에만
연결되어 있었고, 설교 개요(generate_outline)와 대지 확장(expand_point)은
위험 표현·근거 등급 판정을 전혀 받지 않았다 — 특히 expand_point()는
사람이 검토하는 단계 없이 바로 최종 초안에 조립되므로 이 공백이 더 크다.

이 테스트는 Ollama 호출을 mock으로 가로채 실제 모델을 부르지 않는다."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from core.claim_guard import ClaimGuardResult, RiskLevel
from core.generation import SermonDraftService, SermonOutline
from core.retrieval import RankedCandidate


def _candidate(metadata: dict | None = None) -> RankedCandidate:
    return RankedCandidate(
        tsu_id="test-tsu-001",
        content="칭의는 믿음으로 말미암는다.",
        final_score=0.9,
        metadata=metadata or {"source_file": "test.txt"},
    )


class TestGenerateOutlineClaimGuard(unittest.TestCase):
    """generate_outline()이 반환하는 SermonOutline에 claim_guard_result가
    붙는다."""

    @patch("core.generation.ollama.generate")
    def test_low_risk_outline(self, mock_ollama):
        mock_ollama.return_value = {
            "response": (
                "제목: 고난 중의 소망\n서론: 로마서 5장은 소망을 말한다.\n"
                "대지1: 첫째\n대지2: 둘째\n대지3: 셋째\n결론: 소망으로 마친다."
            )
        }
        outline, error = SermonDraftService().generate_outline(
            "로마서 5:1-5, 고난 중의 소망", [_candidate()]
        )

        self.assertIsNone(error)
        self.assertIsInstance(outline, SermonOutline)
        self.assertIsNotNone(outline.claim_guard_result)
        self.assertEqual(outline.claim_guard_result.risk_level, RiskLevel.NONE)

    @patch("core.generation.ollama.generate")
    def test_high_risk_outline_flagged_not_blocked(self, mock_ollama):
        """절대주장 표현이 있으면 claim_guard_result가 위험을 표시하지만,
        개요 생성 자체(error)는 막지 않는다 — 사후 탐지 배너 설계와 동일."""
        mock_ollama.return_value = {
            "response": (
                "제목: 유일한 사례\n서론: 이는 성경 전체에서 유일한 사례입니다.\n"
                "대지1: 첫째\n대지2: 둘째\n대지3: 셋째\n결론: 끝."
            )
        }
        outline, error = SermonDraftService().generate_outline(
            "로마서 5:1-5, 고난 중의 소망", [_candidate()]
        )

        self.assertIsNone(error)
        self.assertIsNotNone(outline.claim_guard_result)
        self.assertTrue(outline.claim_guard_result.absolute_claim_blocked)

    @patch("core.generation.ollama.generate")
    def test_exception_path_has_no_claim_guard_result(self, mock_ollama):
        """Ollama 호출 실패 시 claim_guard_result는 기본값 None (SermonOutline
        dataclass 기본값) — 실패 경로에서 새로 계산하지 않는다."""
        mock_ollama.side_effect = Exception("연결 실패")
        outline, error = SermonDraftService().generate_outline(
            "로마서 5:1-5, 고난 중의 소망", [_candidate()]
        )

        self.assertIsNotNone(error)
        self.assertIsNone(outline.claim_guard_result)


class TestExpandPointClaimGuard(unittest.TestCase):
    """expand_point()가 3-tuple (text, error, claim_guard_result)을
    반환한다."""

    @patch("core.generation.ollama.generate")
    def test_low_risk_expansion(self, mock_ollama):
        mock_ollama.return_value = {"response": "그리스도는 고난을 통해 성장하게 하십니다."}
        text, error, claim_guard_result = SermonDraftService().expand_point(
            "첫째 대지", "로마서 5:1-5, 소망", [_candidate()]
        )

        self.assertIsNone(error)
        self.assertTrue(text)
        self.assertIsNotNone(claim_guard_result)
        self.assertEqual(claim_guard_result.risk_level, RiskLevel.NONE)

    @patch("core.generation.ollama.generate")
    def test_high_risk_expansion_flagged(self, mock_ollama):
        mock_ollama.return_value = {"response": "이는 반드시 유일하게 옳은 해석입니다."}
        text, error, claim_guard_result = SermonDraftService().expand_point(
            "첫째 대지", "로마서 5:1-5, 소망", [_candidate()]
        )

        self.assertIsNone(error)
        self.assertIsNotNone(claim_guard_result)
        self.assertTrue(
            claim_guard_result.absolute_claim_blocked
            or claim_guard_result.scope_qualifier_required
        )

    @patch("core.generation.ollama.generate")
    def test_exception_path_returns_none_claim_guard(self, mock_ollama):
        mock_ollama.side_effect = Exception("연결 실패")
        text, error, claim_guard_result = SermonDraftService().expand_point(
            "첫째 대지", "로마서 5:1-5, 소망", [_candidate()]
        )

        self.assertIsNotNone(error)
        self.assertEqual(text, "")
        self.assertIsNone(claim_guard_result)

    @patch("core.generation.ollama.generate")
    def test_claim_guard_failure_does_not_block_answer(self, mock_ollama):
        """ClaimGuard 자체가 예외를 던져도 대지 확장 텍스트는 그대로 반환된다
        (GenerationService.generate()와 동일한 fail-open 계약)."""
        mock_ollama.return_value = {"response": "테스트 문장."}

        with patch("core.generation.ClaimGuard") as MockGuard:
            MockGuard.return_value.detect_risk.side_effect = Exception("DB 연결 실패")
            text, error, claim_guard_result = SermonDraftService().expand_point(
                "첫째 대지", "로마서 5:1-5, 소망", [_candidate()]
            )

            self.assertIsNone(error)
            self.assertEqual(text, "테스트 문장.")
            self.assertIsNotNone(claim_guard_result)
            self.assertIn("claim_guard 실패", claim_guard_result.reason)


if __name__ == "__main__":
    unittest.main()
