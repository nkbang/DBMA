from NAE.pipeline.canonical import normalize


def test_dehyphenate_merges_lowercase_line_wrap():
    text = "The righ-\nteousness of God is reveal-\ned in the gospel."
    result = normalize.dehyphenate(text)
    assert "righteousness" in result
    assert "revealed" in result
    assert "-\n" not in result


def test_dehyphenate_preserves_proper_noun_break():
    text = "See the work of John-\nSmith on this matter."
    result = normalize.dehyphenate(text)
    assert "John-\nSmith" in result


def test_unicode_normalize_nfc_composes_diacritics():
    decomposed = "église"  # e + combining acute accent
    result = normalize.unicode_normalize(decomposed)
    assert result == "église"


def test_normalize_whitespace_collapses_blank_lines_and_spaces():
    text = "line one\n\n\n\nline   two   with   spaces  \n"
    result = normalize.normalize_whitespace(text)
    assert "\n\n\n" not in result
    assert "line two with spaces" in result


def test_normalize_page_full_pipeline():
    text = "The doc-\ntrine of grace   is  central.\n\n\n\nSecond paragraph."
    result = normalize.normalize_page(text)
    assert "doctrine" in result
    assert "\n\n\n" not in result
