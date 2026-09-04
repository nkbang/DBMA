from NAE.pipeline.canonical import structure


def test_detect_repeated_lines_finds_running_header():
    pages = [
        ["THE BAPTIST QUARTERLY", "Some content on page one.", "12"],
        ["THE BAPTIST QUARTERLY", "Some content on page two.", "13"],
        ["THE BAPTIST QUARTERLY", "Some content on page three.", "14"],
    ]
    repeated = structure.detect_repeated_lines(pages)
    assert "the baptist quarterly" in repeated


def test_remove_headers_footers_strips_repeated_lines():
    pages = [
        ["RUNNING HEAD", "Body text A."],
        ["RUNNING HEAD", "Body text B."],
        ["RUNNING HEAD", "Body text C."],
    ]
    repeated = structure.detect_repeated_lines(pages)
    cleaned, removed = structure.remove_headers_footers(pages, repeated)
    assert removed == 3
    assert all("RUNNING HEAD" not in " ".join(p) for p in cleaned)


def test_remove_page_numbers_strips_arabic_and_roman():
    pages = [["Body text.", "42"], ["More text.", "xliii"]]
    cleaned, removed = structure.remove_page_numbers(pages)
    assert removed == 2
    assert cleaned == [["Body text."], ["More text."]]


def test_remove_toc_and_index_drops_toc_page():
    pages = [
        ["CONTENTS", "Chapter One .......... 1", "Chapter Two .......... 15"],
        ["This is the actual body text of chapter one."],
    ]
    cleaned, removed = structure.remove_toc_and_index(pages)
    assert removed == 1
    assert len(cleaned) == 1
    assert "chapter one" in cleaned[0][0].lower()


def test_remove_toc_and_index_does_not_delete_whole_book_when_unpaginated():
    """Regression: OCR without form-feed page breaks becomes one giant 'page'.

    A single incidental 'CONTENTS' line anywhere in that page must not delete
    the entire book - this previously happened for real archive.org items
    whose djvu.txt lacks \\x0c page markers (found via live TSU smoke testing).
    """
    body_lines = [f"This is real body text on line {i} of the book." for i in range(300)]
    pages = [["CONTENTS", *body_lines]]
    cleaned, removed = structure.remove_toc_and_index(pages)
    assert removed == 0
    assert len(cleaned[0]) == len(pages[0])


def test_remove_toc_and_index_still_drops_short_real_toc_page():
    pages = [
        ["CONTENTS", "Chapter One .......... 1", "Chapter Two .......... 15"],
        ["This is the actual body text of chapter one." for _ in range(1)],
    ]
    cleaned, removed = structure.remove_toc_and_index(pages)
    assert removed == 1


def test_extract_footnotes_pulls_numbered_marker_near_bottom():
    pages = [[
        "Main body paragraph text continues here.",
        "More body text follows on this line.",
        "1. See Calvin, Institutes, Book III.",
    ]]
    cleaned, footnotes = structure.extract_footnotes(pages)
    assert len(footnotes) == 1
    assert footnotes[0]["page"] == 1
    assert "Calvin" in footnotes[0]["text"]
    assert not any("Calvin" in line for line in cleaned[0])


def test_remove_scan_noise_strips_symbol_only_lines():
    pages = [["Real content line.", "~~~~~~~~", "|||===|||", "Another real line."]]
    cleaned, removed = structure.remove_scan_noise(pages)
    assert removed == 2
    assert cleaned == [["Real content line.", "Another real line."]]


def test_apply_structure_cleanup_end_to_end():
    pages = [
        ["JOHN GILL", "Body text about theology begins here.", "1"],
        ["JOHN GILL", "Body text continues on the second page.", "2. A footnote reference.", "2"],
        ["JOHN GILL", "Body text concludes on the third page.", "3"],
    ]
    cleaned, report = structure.apply_structure_cleanup(pages)
    assert report.headers_footers_removed >= 3
    assert report.page_numbers_removed == 3
    assert len(report.footnotes_extracted) == 1
