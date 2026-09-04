from unittest.mock import patch

from NAE.pipeline.verify import duplicate


def _fake_embed(vectors_by_claim):
    def _embed(text, *, content_hash, **kwargs):
        return vectors_by_claim.get(text)
    return _embed


@patch("NAE.pipeline.verify.duplicate.embed_client.embed_text")
def test_find_duplicates_flags_similar_same_doctrine_claims(mock_embed):
    records = [
        {"id": "TSU-0000001", "claim": "Faith alone justifies.", "doctrine": "Justification",
         "book": "A", "page": 1, "scriptures": []},
        {"id": "TSU-0000002", "claim": "We are justified by faith alone.", "doctrine": "Justification",
         "book": "B", "page": 2, "scriptures": []},
    ]
    mock_embed.side_effect = _fake_embed({
        "Faith alone justifies.": [1.0, 0.0],
        "We are justified by faith alone.": [0.99, 0.01],
    })
    duplicates = duplicate.find_duplicates(records, threshold=0.9)
    assert duplicates == {"TSU-0000002": "TSU-0000001"}


@patch("NAE.pipeline.verify.duplicate.embed_client.embed_text")
def test_find_duplicates_ignores_different_doctrine(mock_embed):
    records = [
        {"id": "TSU-0000001", "claim": "Claim X.", "doctrine": "Justification",
         "book": "A", "page": 1, "scriptures": []},
        {"id": "TSU-0000002", "claim": "Claim X restated.", "doctrine": "Baptism",
         "book": "A", "page": 1, "scriptures": []},
    ]
    mock_embed.side_effect = _fake_embed({
        "Claim X.": [1.0, 0.0],
        "Claim X restated.": [1.0, 0.0],
    })
    duplicates = duplicate.find_duplicates(records, threshold=0.9)
    assert duplicates == {}


@patch("NAE.pipeline.verify.duplicate.embed_client.embed_text")
def test_find_duplicates_skips_records_without_claim(mock_embed):
    records = [{"id": "TSU-0000001", "claim": None, "doctrine": "Baptism", "book": "A", "page": 1}]
    duplicates = duplicate.find_duplicates(records)
    assert duplicates == {}
    mock_embed.assert_not_called()


@patch("NAE.pipeline.verify.duplicate.embed_client.embed_text")
def test_find_duplicates_handles_embedding_failure_gracefully(mock_embed):
    records = [
        {"id": "TSU-0000001", "claim": "Claim.", "doctrine": "Baptism", "book": "A", "page": 1, "scriptures": []},
    ]
    mock_embed.return_value = None
    duplicates = duplicate.find_duplicates(records)
    assert duplicates == {}
