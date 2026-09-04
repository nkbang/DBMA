from NAE.pipeline.tsu import citation, scripture


def test_extract_author_mentions_finds_known_author():
    text = "As John Gill argues in his Body of Divinity, this doctrine is essential."
    assert citation.extract_author_mentions(text) == ["John Gill"]


def test_extract_author_mentions_no_match():
    text = "This paragraph mentions no known theologians by name."
    assert citation.extract_author_mentions(text) == []


def test_nearby_footnotes_matches_within_window():
    footnotes = [{"page": 5, "text": "See Calvin."}, {"page": 20, "text": "Unrelated."}]
    result = citation.nearby_footnotes(page=5, footnotes=footnotes, window=1)
    assert result == ["See Calvin."]


def test_nearby_footnotes_respects_window():
    footnotes = [{"page": 10, "text": "Far footnote."}]
    result = citation.nearby_footnotes(page=5, footnotes=footnotes, window=1)
    assert result == []


def test_scripture_extract_for_sentence_returns_canonical_forms():
    text = "As it is written in John iii.16, God so loved the world."
    assert scripture.extract_for_sentence(text) == ["John 3:16"]


def test_scripture_extract_for_sentence_no_refs():
    text = "This sentence contains no scripture reference at all."
    assert scripture.extract_for_sentence(text) == []
