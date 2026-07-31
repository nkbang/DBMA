import json
from unittest.mock import patch

from NAE.pipeline.verify import contradiction


def _mock_response(payload: dict) -> dict:
    return {"response": json.dumps(payload, ensure_ascii=False)}


@patch("NAE.pipeline.verify.contradiction.ollama.generate")
def test_check_pair_detects_contradiction(mock_generate):
    mock_generate.return_value = _mock_response({"contradicts": True, "rationale": "Direct conflict."})
    a = {"id": "TSU-0000001", "claim": "Baptism must precede communion."}
    b = {"id": "TSU-0000002", "claim": "Communion may precede baptism."}
    result = contradiction.check_pair(a, b)
    assert result.contradicts is True
    assert result.error is None


@patch("NAE.pipeline.verify.contradiction.ollama.generate")
def test_check_pair_handles_llm_failure(mock_generate):
    mock_generate.side_effect = RuntimeError("boom")
    a = {"id": "TSU-0000001", "claim": "X"}
    b = {"id": "TSU-0000002", "claim": "Y"}
    result = contradiction.check_pair(a, b)
    assert result.error is not None
    assert result.contradicts is False


@patch("NAE.pipeline.verify.contradiction.check_pair")
def test_find_contradictions_only_compares_same_doctrine(mock_check_pair):
    mock_check_pair.return_value = contradiction.ContradictionResult(id_a="a", id_b="b", contradicts=False)
    records = [
        {"id": "1", "claim": "A", "doctrine": "Baptism"},
        {"id": "2", "claim": "B", "doctrine": "Baptism"},
        {"id": "3", "claim": "C", "doctrine": "Trinity"},
    ]
    contradiction.find_contradictions(records)
    assert mock_check_pair.call_count == 1  # only the two Baptism records are paired


@patch("NAE.pipeline.verify.contradiction.check_pair")
def test_find_contradictions_respects_max_pairs_cap(mock_check_pair):
    mock_check_pair.return_value = contradiction.ContradictionResult(id_a="a", id_b="b", contradicts=False)
    records = [{"id": str(i), "claim": f"claim {i}", "doctrine": "Baptism"} for i in range(10)]
    contradiction.find_contradictions(records, max_pairs=3)
    assert mock_check_pair.call_count == 3
