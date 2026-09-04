from unittest.mock import patch

from NAE.pipeline.verify import score


def test_parser_score_rewards_length_and_terminal_punctuation():
    short = score.parser_score({"source_text": "Short."})
    long_complete = score.parser_score({
        "source_text": "This is a much longer, well-formed sentence that ends properly."
    })
    assert long_complete > short


def test_parser_score_empty_text_is_zero():
    assert score.parser_score({"source_text": ""}) == 0.0


@patch("NAE.pipeline.verify.score.evidence.check_record_evidence")
def test_evidence_score_computes_fraction_valid(mock_evidence):
    mock_evidence.return_value = [
        {"reference": "John 3:16", "format_valid": True},
        {"reference": "garbage", "format_valid": False},
    ]
    assert score.evidence_score({"scriptures": ["John 3:16", "garbage"]}) == 0.5


@patch("NAE.pipeline.verify.score.evidence.check_record_evidence")
def test_evidence_score_none_when_no_scriptures(mock_evidence):
    mock_evidence.return_value = []
    assert score.evidence_score({"scriptures": []}) is None


@patch("NAE.pipeline.verify.score.consistency.verify_citations")
def test_citation_score_computes_fraction_verified(mock_consistency):
    mock_consistency.return_value = {"a": True, "b": False}
    assert score.citation_score({"citations": ["a", "b"]}) == 0.5


@patch("NAE.pipeline.verify.score.consistency.verify_citations")
def test_citation_score_none_when_no_citations(mock_consistency):
    mock_consistency.return_value = {}
    assert score.citation_score({"citations": []}) is None


@patch("NAE.pipeline.verify.score.consistency.verify_citations")
@patch("NAE.pipeline.verify.score.evidence.check_record_evidence")
def test_compute_scores_renormalizes_when_components_missing(mock_evidence, mock_consistency):
    mock_evidence.return_value = []
    mock_consistency.return_value = {}
    record = {"confidence": 0.8, "source_text": "A reasonably long and complete sentence here."}
    result = score.compute_scores(record)
    assert result["llm_score"] == 0.8
    assert result["evidence_score"] is None
    assert result["citation_score"] is None
    # overall_score should be a weighted average of only llm_score + parser_score
    assert result["overall_score"] is not None


@patch("NAE.pipeline.verify.score.consistency.verify_citations")
@patch("NAE.pipeline.verify.score.evidence.check_record_evidence")
def test_compute_scores_all_components_present(mock_evidence, mock_consistency):
    mock_evidence.return_value = [{"reference": "John 3:16", "format_valid": True}]
    mock_consistency.return_value = {"John Gill": True}
    record = {
        "confidence": 0.9,
        "source_text": "A reasonably long and complete theological sentence here.",
        "scriptures": ["John 3:16"],
        "citations": ["John Gill"],
    }
    result = score.compute_scores(record)
    assert all(result[k] is not None for k in
               ["llm_score", "parser_score", "evidence_score", "citation_score", "overall_score"])
