from NAE.pipeline.canonical import annotate
from NAE.pipeline.canonical.reflow import Paragraph


def test_split_sentences_basic():
    text = "Faith is the substance. Hope endures forever. Love never fails."
    sentences = annotate.split_sentences(text)
    assert sentences == [
        "Faith is the substance.",
        "Hope endures forever.",
        "Love never fails.",
    ]


def test_split_sentences_does_not_break_on_abbreviation():
    text = "This was taught by Rev. John Gill in his sermons. He was a careful exegete."
    sentences = annotate.split_sentences(text)
    assert len(sentences) == 2
    assert "Rev. John Gill" in sentences[0]


def test_classify_paragraph_detects_chapter_heading():
    p = Paragraph(index=0, type="prose", text="CHAPTER IV", page_start=10, page_end=10)
    ptype, level = annotate.classify_paragraph(p)
    assert ptype == "heading"
    assert level == 1


def test_classify_paragraph_detects_all_caps_subheading():
    p = Paragraph(index=0, type="prose", text="OF BAPTISM", page_start=10, page_end=10)
    ptype, level = annotate.classify_paragraph(p)
    assert ptype == "heading"
    assert level == 2


def test_classify_paragraph_detects_quote_block():
    p = Paragraph(index=0, type="prose",
                  text='"Faith without works is dead, as the Scripture teaches us plainly."',
                  page_start=1, page_end=1)
    ptype, level = annotate.classify_paragraph(p)
    assert ptype == "quote"
    assert level is None


def test_classify_paragraph_ordinary_prose_unclassified():
    p = Paragraph(index=0, type="prose",
                  text="This is an ordinary paragraph of theological prose about grace.",
                  page_start=1, page_end=1)
    ptype, level = annotate.classify_paragraph(p)
    assert ptype == "prose"


def test_classify_paragraph_preserves_existing_verse_type():
    p = Paragraph(index=0, type="verse", text="Amazing grace\nhow sweet the sound", page_start=1, page_end=1)
    ptype, level = annotate.classify_paragraph(p)
    assert ptype == "verse"


def test_canonicalize_scripture_ref_from_roman_numeral_form():
    assert annotate.canonicalize_scripture_ref("John iii.16") == "John 3:16"
    assert annotate.canonicalize_scripture_ref("Matt. xxviii.19") == "Matt 28:19"


def test_canonicalize_scripture_ref_from_arabic_form():
    assert annotate.canonicalize_scripture_ref("Romans 6:4") == "Romans 6:4"


def test_find_scripture_references_extended_preserves_original_and_canonical():
    text = "As it is written in John iii.16 and also Rom. 3:24."
    refs = annotate.find_scripture_references_extended(text)
    canon = {r["canonical"] for r in refs}
    original = {r["original"] for r in refs}
    assert "John 3:16" in canon
    assert "John iii.16" in original
    assert "Rom 3:24" in canon


def test_detect_script_language_greek():
    text = "λόγος καὶ θεός ἐστιν ἀγάπη"
    assert annotate.detect_script_language(text) == "greek"


def test_detect_script_language_hebrew():
    text = "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם"
    assert annotate.detect_script_language(text) == "hebrew"


def test_detect_script_language_english_returns_none():
    text = "This is ordinary English theological prose about the doctrine of grace."
    assert annotate.detect_script_language(text) is None


def test_annotate_paragraph_includes_sentences_and_scripture():
    p = Paragraph(index=0, type="prose",
                  text="Faith is central. As it is written in John 3:16, God so loved the world.",
                  page_start=5, page_end=5)
    entry = annotate.annotate_paragraph(p, 0)
    assert entry["type"] == "prose"
    assert len(entry["sentences"]) == 2
    assert any(ref["canonical"] == "John 3:16" for ref in entry["scripture_references"])
    assert entry["page_start"] == 5
    assert "heading_level" not in entry
