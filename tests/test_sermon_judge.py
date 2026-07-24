"""tests/test_sermon_judge.py — DBMA-SEQ Phase 1: sermon_judge.py 테스트.

ollama 호출은 mock 처리.
- 정상 JSON 파싱 케이스
- JSON 파싱 실패 시 score=0.0 fallback 케이스 (rag_judge.py 기존 테스트 패턴 따름)
"""

import json
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

# RankedCandidate 피스처용 더미 클래스
class _DummyCandidate:
    def __init__(self, cid: str, title: str = "테스트 문서", author: str = "테저자"):
        self.id = cid
        self.content = f"[청크 내용 {cid}]"
        self.metadata = {"title": title, "author": author, "tsu_id": cid}


# ============================================================
# fixtures
# ============================================================

@pytest.fixture
def candidates():
    return [
        _DummyCandidate("tsu_001", "로마서 주석", "루터"),
        _DummyCandidate("tsu_002", "바울 신학입문", "본권"),
    ]


# ============================================================
# judge_sermon_groundedness — 정상 JSON 파싱
# ============================================================

def test_judge_sermon_groundedness_success():
    """ollama가 유효한 JSON을 반환하면 점수+근거가 제대로 파싱되어야 한다."""
    from core.evaluation.sermon_judge import judge_sermon_groundedness

    mock_response = '{"groundedness": 4, "groundedness_rationale": "대지의 주장을 지원하는 자료가 명확히 존재한다"}'

    with patch("core.evaluation.sermon_judge.ollama.generate") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}

        score = judge_sermon_groundedness(
            run_id="run_001",
            query_id="sermon_001",
            scripture_and_theme="로마서 8:28 — 모든 것이 합력하여 선을 이루느니라",
            retrieved_candidates=[
                _DummyCandidate("tsu_001", "로마서 주석", "루터"),
                _DummyCandidate("tsu_002", "바울 신학입문", "본권"),
            ],
            generated_text="대지1: 모든 사건에는 하나님의 주권이 작동한다 — 루터는 이를 '하나님의 인도'라고 불렀다.",
            text_type="outline",
        )

    # assertions
    assert score.groundedness == 4.0
    assert score.groundedness_rationale == "대지의 주장을 지원하는 자료가 명확히 존재한다"
    assert score.text_type == "outline"
    assert score.scripture_and_theme == "로마서 8:28 — 모든 것이 합력하여 선을 이루느니라"
    assert len(score.retrieved_candidate_ids) == 2
    assert "tsu_001" in score.retrieved_candidate_ids
    assert "tsu_002" in score.retrieved_candidate_ids
    assert score.judge_model == "dbma-planner-r1-q6:70b"
    assert score.run_id == "run_001"
    assert score.query_id == "sermon_001"


def test_judge_sermon_groundedness_expansion_type():
    """text_type='expansion'으로 호출해도 올바르게 전달되어야 한다."""
    from core.evaluation.sermon_judge import judge_sermon_groundedness

    mock_response = '{"groundedness": 5, "groundedness_rationale": "전체적으로 자료에 잘 근거함"}'

    with patch("core.evaluation.sermon_judge.ollama.generate") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}

        score = judge_sermon_groundedness(
            run_id="run_002",
            query_id="sermon_002",
            scripture_and_theme="마태복음 6:13",
            retrieved_candidates=[_DummyCandidate("tsu_010", "마태복이 주석", "저자A")],
            generated_text="문단1: 루터는 마태 6:13의 '악의'를...",
            text_type="expansion",
        )

    assert score.groundedness == 5.0
    assert score.text_type == "expansion"


# ============================================================
# judge_sermon_groundedness — JSON 파싱 실패 시 fallback
# ============================================================

def test_judge_sermon_groundedness_json_parse_failure():
    """ollama가 JSON을 못 반환하면 score=0.0 + rationale에 오류메시지."""
    from core.evaluation.sermon_judge import judge_sermon_groundedness

    # JSON이 아닌 잡담 응답
    mock_response = "음... 이건 좀 어렵군요. 일단 좋은 설교가 되길 바랍니다."

    with patch("core.evaluation.sermon_judge.ollama.generate") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}

        score = judge_sermon_groundedness(
            run_id="run_003",
            query_id="sermon_003",
            scripture_and_theme="요한복음 3:16",
            retrieved_candidates=[_DummyCandidate("tsu_020", "요한복음 연구", "저자B")],
            generated_text="하나님이 세상을 이처럼 사랑하사...",
            text_type="outline",
        )

    assert score.groundedness == 0.0
    assert "[judge 실패]" in score.groundedness_rationale
    assert "run_003" == score.run_id


def test_judge_sermon_groundedness_ollama_exception():
    """ollama 호출 자체가 예외를 던지면 score=0.0."""
    from core.evaluation.sermon_judge import judge_sermon_groundedness

    with patch("core.evaluation.sermon_judge.ollama.generate") as mock_ollama:
        mock_ollama.side_effect = ConnectionError("Ollama 서버 응답 없음")

        score = judge_sermon_groundedness(
            run_id="run_004",
            query_id="sermon_004",
            scripture_and_theme="시편 23:1",
            retrieved_candidates=[],
            generated_text="여호와께서는 나의 목자시므로...",
            text_type="outline",
        )

    assert score.groundedness == 0.0
    assert "[judge 실패]" in score.groundedness_rationale


# ============================================================
# _parse_judge_json 단위 테스트
# ============================================================

def test_parse_judge_json_clean():
    from core.evaluation.sermon_judge import _parse_judge_json

    raw = '{"groundedness": 3, "groundedness_rationale": "중간 정도 근거"}'
    score, rationale = _parse_judge_json(raw)
    assert score == 3.0
    assert rationale == "중간 정도 근거"


def test_parse_judge_json_with_jabber():
    """JSON 앞뒤에 잡담이 있어도 첫 '{'~마지막 '}'만 추출한다."""
    from core.evaluation.sermon_judge import _parse_judge_json

    raw = '음, 평가해보겠습니다.\n\n{"groundedness": 2, "groundedness_rationale": "약함"}\n끝.'
    score, rationale = _parse_judge_json(raw)
    assert score == 2.0
    assert rationale == "약함"


def test_parse_judge_json_no_braces():
    """JSON 중괄호가 없으면 ValueError를 던진다."""
    from core.evaluation.sermon_judge import _parse_judge_json

    with pytest.raises(ValueError, match="JSON을 찾지 못함"):
        _parse_judge_json("아무 텍스트도 아닌 그냥 문자열")


# ============================================================
# SermonQualityScore.to_dict()
# ============================================================

def test_sermon_quality_score_to_dict():
    from core.evaluation.schemas import SermonQualityScore

    s = SermonQualityScore(
        run_id="r1",
        query_id="q1",
        scripture_and_theme="마태 5:3",
        retrieved_candidate_ids=["tsu_x"],
        generated_text="복있는 자",
        text_type="outline",
        groundedness=4.5,
        groundedness_rationale="좋음",
        judge_model="test",
        timestamp="2026-07-24T00:00:00+00:00",
    )

    d = s.to_dict()
    assert d["run_id"] == "r1"
    assert d["groundedness"] == 4.5
    assert d["text_type"] == "outline"