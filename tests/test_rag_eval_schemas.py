"""Regression test — core/evaluation/schemas.py::RagEvalScore (ADR-010
DBMA-REQ Phase 1).

RagEvalScore is a pure data container — no I/O, no judge-model calls.
Only structural/serialization behavior is tested here.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evaluation.schemas import RagEvalScore


def _minimal_score(**overrides) -> RagEvalScore:
    base = dict(
        run_id="run-001",
        query_id="q-001",
        question="요한복음 15장의 핵심 주제는?",
        retrieved_chunk_ids=["tsu-1", "tsu-2"],
        generated_answer="포도나무 비유를 통해 그리스도 안에 거함을 강조한다.",
    )
    base.update(overrides)
    return RagEvalScore(**base)


def test_defaults_are_reference_free():
    score = _minimal_score()
    assert score.reference_answer is None
    assert score.groundedness == 0.0
    assert score.groundedness_rationale == ""
    assert score.judge_prompt_version == ""


def test_score_fields_are_settable():
    score = _minimal_score(
        groundedness=4.5,
        groundedness_rationale="답변이 검색된 두 청크의 핵심 내용을 반영함",
        judge_model="dbma-planner-r1-q6:70b",
        judge_prompt_version="v1",
    )
    assert score.groundedness == 4.5
    assert score.judge_prompt_version == "v1"


def test_to_dict_round_trips_all_fields():
    score = _minimal_score(groundedness=3.0, groundedness_rationale="부분 근거")
    d = score.to_dict()

    assert d["run_id"] == "run-001"
    assert d["retrieved_chunk_ids"] == ["tsu-1", "tsu-2"]
    assert d["groundedness"] == 3.0
    assert d["groundedness_rationale"] == "부분 근거"


def test_retrieved_chunk_ids_defaults_to_empty_list_not_shared():
    a = _minimal_score(retrieved_chunk_ids=[])
    b = _minimal_score(retrieved_chunk_ids=[])
    a.retrieved_chunk_ids.append("tsu-x")
    assert b.retrieved_chunk_ids == []


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
