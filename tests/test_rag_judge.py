"""Regression test — core/evaluation/rag_judge.py::judge_groundedness()
(ADR-010 DBMA-REQ Phase 1).

All cases mock ollama.generate — no real model call. Validating the
*actual* judge model's scoring quality against a human-labeled golden
set is a separate, user-gated step (ADR-010 Decision-미확정 §1), not
covered by this unit-level test.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evaluation.rag_judge import judge_groundedness, JUDGE_PROMPT_VERSION


def _mock_ollama_response(text: str):
    return {"response": text}


def test_high_groundedness_parsed_correctly():
    raw = '{"groundedness": 5, "groundedness_rationale": "모든 주장이 청크에서 확인됨"}'
    with patch("core.evaluation.rag_judge.ollama.generate", return_value=_mock_ollama_response(raw)):
        score = judge_groundedness(
            run_id="run-1", query_id="q-1",
            question="요한복음 15장의 핵심 주제는?",
            retrieved_chunks=["포도나무 비유는 그리스도 안에 거함을 강조한다."],
            retrieved_chunk_ids=["tsu-1"],
            answer="포도나무 비유를 통해 그리스도 안에 거함을 강조한다.",
        )
    assert score.groundedness == 5.0
    assert "확인됨" in score.groundedness_rationale
    assert score.judge_prompt_version == JUDGE_PROMPT_VERSION


def test_low_groundedness_unrelated_answer():
    raw = '{"groundedness": 0, "groundedness_rationale": "답변이 청크와 무관함"}'
    with patch("core.evaluation.rag_judge.ollama.generate", return_value=_mock_ollama_response(raw)):
        score = judge_groundedness(
            run_id="run-1", query_id="q-2",
            question="로마서 8장의 핵심 주제는?",
            retrieved_chunks=["로마서 8장은 성령 안에서의 삶을 다룬다."],
            retrieved_chunk_ids=["tsu-2"],
            answer="오늘 날씨는 맑습니다.",
        )
    assert score.groundedness == 0.0


def test_judge_response_with_extra_chatter_around_json():
    raw = '물론입니다! 평가 결과입니다:\n{"groundedness": 3, "groundedness_rationale": "부분적으로 근거함"}\n감사합니다.'
    with patch("core.evaluation.rag_judge.ollama.generate", return_value=_mock_ollama_response(raw)):
        score = judge_groundedness(
            run_id="run-1", query_id="q-3",
            question="q", retrieved_chunks=["c"], retrieved_chunk_ids=["tsu-3"],
            answer="a",
        )
    assert score.groundedness == 3.0


def test_ollama_exception_does_not_raise_and_scores_zero():
    with patch("core.evaluation.rag_judge.ollama.generate", side_effect=RuntimeError("connection refused")):
        score = judge_groundedness(
            run_id="run-1", query_id="q-4",
            question="q", retrieved_chunks=["c"], retrieved_chunk_ids=["tsu-4"],
            answer="a",
        )
    assert score.groundedness == 0.0
    assert "judge 실패" in score.groundedness_rationale


def test_malformed_json_does_not_raise_and_scores_zero():
    with patch("core.evaluation.rag_judge.ollama.generate", return_value=_mock_ollama_response("이건 JSON이 아님")):
        score = judge_groundedness(
            run_id="run-1", query_id="q-5",
            question="q", retrieved_chunks=["c"], retrieved_chunk_ids=["tsu-5"],
            answer="a",
        )
    assert score.groundedness == 0.0


def test_result_carries_run_and_query_ids_and_metadata():
    raw = '{"groundedness": 4, "groundedness_rationale": "대체로 근거함"}'
    with patch("core.evaluation.rag_judge.ollama.generate", return_value=_mock_ollama_response(raw)):
        score = judge_groundedness(
            run_id="run-42", query_id="q-99",
            question="q", retrieved_chunks=["c1", "c2"], retrieved_chunk_ids=["tsu-1", "tsu-2"],
            answer="a", judge_model="custom-model",
        )
    assert score.run_id == "run-42"
    assert score.query_id == "q-99"
    assert score.retrieved_chunk_ids == ["tsu-1", "tsu-2"]
    assert score.judge_model == "custom-model"
    assert score.timestamp != ""


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
