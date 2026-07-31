import json
from unittest.mock import patch

from NAE.pipeline.tsu import claim


def _mock_response(payload: dict) -> dict:
    return {"response": json.dumps(payload, ensure_ascii=False)}


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_parses_positive_claim(mock_generate):
    mock_generate.return_value = _mock_response({
        "is_claim": True,
        "claim": "Believer's baptism follows a profession of faith.",
        "doctrine": "Baptism",
        "scriptures": ["Acts 2:41"],
        "citations": ["John Gill"],
        "confidence": 0.9,
    })
    result = claim.extract_claim(
        "Baptism is administered only after a credible profession of faith.",
        candidate_scriptures=["Acts 2:41"],
        candidate_citations=["John Gill"],
    )
    assert result.is_claim is True
    assert result.doctrine == "Baptism"
    assert result.scriptures == ["Acts 2:41"]
    assert result.citations == ["John Gill"]
    assert result.confidence == 0.9
    assert result.extraction_method == "llm"
    assert result.review_status == "unverified"
    assert result.error is None


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_parses_negative_claim(mock_generate):
    mock_generate.return_value = _mock_response({"is_claim": False})
    result = claim.extract_claim("See page 12 for further discussion.")
    assert result.is_claim is False
    assert result.claim is None


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_drops_hallucinated_scripture_not_in_candidates(mock_generate):
    mock_generate.return_value = _mock_response({
        "is_claim": True,
        "claim": "Some claim.",
        "doctrine": "Baptism",
        "scriptures": ["Romans 6:4"],  # not in candidate list
        "citations": [],
        "confidence": 0.8,
    })
    result = claim.extract_claim("A sentence.", candidate_scriptures=["Acts 2:41"])
    assert result.scriptures == []


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_coerces_unknown_doctrine_to_other(mock_generate):
    mock_generate.return_value = _mock_response({
        "is_claim": True,
        "claim": "Some claim.",
        "doctrine": "Made-up Category",
        "scriptures": [],
        "citations": [],
        "confidence": 0.5,
    })
    result = claim.extract_claim("A sentence.")
    assert result.doctrine == "Other"


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_clips_out_of_range_confidence(mock_generate):
    mock_generate.return_value = _mock_response({
        "is_claim": True, "claim": "X", "doctrine": None,
        "scriptures": [], "citations": [], "confidence": 1.5,
    })
    result = claim.extract_claim("A sentence.")
    assert result.confidence == 1.0


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_handles_llm_failure_without_raising(mock_generate):
    mock_generate.side_effect = RuntimeError("connection refused")
    result = claim.extract_claim("A sentence.")
    assert result.is_claim is False
    assert result.error is not None


@patch("NAE.pipeline.tsu.claim.ollama.generate")
def test_extract_claim_handles_unparseable_response(mock_generate):
    mock_generate.return_value = {"response": "I cannot help with that."}
    result = claim.extract_claim("A sentence.")
    assert result.is_claim is False
    assert result.error is not None
