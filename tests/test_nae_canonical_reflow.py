from NAE.pipeline.canonical import reflow


def test_reconstruct_paragraphs_joins_prose_lines():
    pages = [[
        "This is the first line of a rather long theological paragraph",
        "that continues wrapping onto a second full-width line of text",
        "and it finally finishes with a proper terminal sentence here.",
        "",
        "This is a separate paragraph entirely, also written in ordinary prose.",
    ]]
    paragraphs = reflow.reconstruct_paragraphs(pages)
    assert len(paragraphs) == 2
    assert paragraphs[0].type == "prose"
    assert "continues wrapping onto a second full-width line" in paragraphs[0].text
    assert paragraphs[0].text.count("\n") == 0


def test_reconstruct_paragraphs_preserves_verse_block():
    pages = [[
        "Amazing grace, how sweet the sound",
        "That saved a wretch like me",
        "I once was lost, but now am found",
        "Was blind but now I see",
    ]]
    paragraphs = reflow.reconstruct_paragraphs(pages)
    assert len(paragraphs) == 1
    assert paragraphs[0].type == "verse"
    assert paragraphs[0].text.count("\n") == 3


def test_reconstruct_paragraphs_tracks_page_span():
    pages = [
        ["A paragraph that starts on page one"],
        ["and continues onto page two."],
    ]
    paragraphs = reflow.reconstruct_paragraphs(pages)
    assert paragraphs[0].page_start == 1
    assert paragraphs[0].page_end == 2


def test_find_scripture_references_detects_common_forms():
    text = "As it is written in John 3:16, and again in 1 Cor. 13:4-7, love is patient."
    refs = reflow.find_scripture_references(text)
    assert any("John 3:16" in r for r in refs)
    assert any("13:4" in r for r in refs)
