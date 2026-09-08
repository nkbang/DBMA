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
    assert annotate.canonicalize_scripture_ref("Matt. xxviii.19") == "Matthew 28:19"


def test_canonicalize_scripture_ref_from_roman_book_prefix():
    """Roman numeral book prefix (I Cor, II Pet, III John) support."""
    assert annotate.canonicalize_scripture_ref("I Cor. xiii. 4") == "1 Corinthians 13:4"
    assert annotate.canonicalize_scripture_ref("II Pet. i. 4") == "2 Peter 1:4"
    assert annotate.canonicalize_scripture_ref("III John 1:5") == "3 John 1:5"
    assert annotate.canonicalize_scripture_ref("I Cor 3:16") == "1 Corinthians 3:16"


def test_canonicalize_scripture_ref_from_arabic_form():
    assert annotate.canonicalize_scripture_ref("Romans 6:4") == "Romans 6:4"


def test_find_scripture_references_extended_preserves_original_and_canonical():
    text = "As it is written in John iii.16 and also Rom. 3:24."
    refs = annotate.find_scripture_references_extended(text)
    canon = {r["canonical"] for r in refs}
    original = {r["original"] for r in refs}
    assert "John 3:16" in canon
    assert "John iii.16" in original
    assert "Romans 3:24" in canon


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


# ============================================================
# F-1: Roman numeral parser (general, >28, round-trip validation)
# ============================================================

class TestRomanNumeralParser:
    """F-1: General Roman numeral parser replacing hardcoded _ROMAN_MAP."""

    def test_roman_xl_psalms(self):
        result = annotate.canonicalize_scripture_ref("Ps. xl. 6")
        assert result == "Psalms 40:6"

    def test_roman_cxviii_psalms(self):
        result = annotate.canonicalize_scripture_ref("Ps. cxviii. 1")
        assert result == "Psalms 118:1"

    def test_roman_cxlix_psalms_max(self):
        result = annotate.canonicalize_scripture_ref("Ps. cxlix. 6")
        assert result == "Psalms 149:6"

    def test_roman_above_upper_bound_rejected(self):
        result = annotate.canonicalize_scripture_ref("Ps. cc. 1")
        assert result is None

    def test_invalid_roman_sequence_rejected(self):
        result = annotate.canonicalize_scripture_ref("Ps. iiii. 1")
        assert result is None

    def test_invalid_roman_vx_rejected(self):
        result = annotate.canonicalize_scripture_ref("Ps. vx. 1")
        assert result is None

    def test_roman_i(self):
        result = annotate.canonicalize_scripture_ref("Ps. i. 1")
        assert result == "Psalms 1:1"

    def test_roman_c(self):
        result = annotate.canonicalize_scripture_ref("Ps. c. 1")
        assert result == "Psalms 100:1"


# ============================================================
# F-2: Book name expansion (Korean, English aliases, full names)
# ============================================================

class TestBookNameExpansion:
    """F-2: Expanded book name recognition using existing BIBLE_BOOKS."""

    def test_korean_short_rom(self):
        result = annotate.canonicalize_scripture_ref("롬 8:1")
        assert result == "Romans 8:1"

    def test_korean_short_yo(self):
        result = annotate.canonicalize_scripture_ref("요 3:16")
        assert result == "John 3:16"

    def test_korean_short_gojeon(self):
        result = annotate.canonicalize_scripture_ref("고전 13:1")
        assert result == "1 Corinthians 13:1"

    def test_korean_short_gye(self):
        result = annotate.canonicalize_scripture_ref("계 1:8")
        assert result == "Revelation 1:8"

    def test_korean_full_yohangbogum(self):
        result = annotate.canonicalize_scripture_ref("요한복음 3장 16절")
        assert result == "John 3:16"

    def test_korean_full_romaseo(self):
        result = annotate.canonicalize_scripture_ref("로마서 8장 28절")
        assert result == "Romans 8:28"

    def test_korean_full_isaaya(self):
        result = annotate.canonicalize_scripture_ref("이사야 40장 3절")
        assert result == "Isaiah 40:3"

    def test_english_all_caps_ROM(self):
        result = annotate.canonicalize_scripture_ref("ROM 8:1")
        assert result == "Romans 8:1"

    def test_english_all_caps_1COR(self):
        result = annotate.canonicalize_scripture_ref("1COR 13:1")
        assert result == "1 Corinthians 13:1"

    def test_english_all_caps_REV(self):
        result = annotate.canonicalize_scripture_ref("REV 22:20")
        assert result == "Revelation 22:20"

    def test_english_short_alias_ps(self):
        result = annotate.canonicalize_scripture_ref("Ps. 23:1")
        assert result == "Psalms 23:1"

    def test_english_short_alias_matt(self):
        result = annotate.canonicalize_scripture_ref("Matt. 5:3")
        assert result == "Matthew 5:3"

    def test_english_full_name_john(self):
        result = annotate.canonicalize_scripture_ref("John 3:16")
        assert result == "John 3:16"

    def test_korean_verse_range(self):
        result = annotate.canonicalize_scripture_ref("롬 8:1-2")
        assert result == "Romans 8:1-2"

    def test_korean_no_space_colon(self):
        result = annotate.canonicalize_scripture_ref("요3:16")
        assert result == "John 3:16"


# ============================================================
# F-4: OCR noise tolerance (conservative)
# ============================================================

class TestOCRTolerance:
    """F-4: Conservative OCR noise tolerance (0–3 chars)."""

    def test_ocr_noise_one_char(self):
        result = annotate.canonicalize_scripture_ref("Rom. i. 2")
        assert result == "Romans 1:2"

    def test_ocr_noise_multiple_dots(self):
        result = annotate.canonicalize_scripture_ref("Rom.. ii. 3")
        assert result == "Romans 2:3"

    def test_ocr_noise_three_chars(self):
        result = annotate.canonicalize_scripture_ref("Rom. ... iv. 5")
        assert result == "Romans 4:5"

    def test_ocr_noise_four_chars_rejected(self):
        result = annotate.canonicalize_scripture_ref("Rom. .... iv. 5")
        assert result is None

    def test_ocr_noise_with_special_chars(self):
        result = annotate.canonicalize_scripture_ref("Rom. § ii. 2")
        assert result == "Romans 2:2"

    def test_no_false_positive_from_noise(self):
        text = "중요한 3:16 같은 사례"
        refs = annotate.find_scripture_references_extended(text)
        assert refs == []


# ============================================================
# Negative cases (should NOT match as scripture references)
# ============================================================

class TestNegativeCases:
    """Volume/page references should not be mistaken for scripture."""

    def test_volume_reference_not_matched(self):
        text = "See Vol. iii. 5 for more details."
        refs = annotate.find_scripture_references_extended(text)
        assert all("Volume" not in (r["canonical"] or "") for r in refs)

    def test_page_reference_not_matched(self):
        text = "Refer to p. 12 for the full text."
        refs = annotate.find_scripture_references_extended(text)
        assert refs == []

    def test_chapter_reference_not_matched(self):
        text = "In chapter 5, the author discusses grace."
        refs = annotate.find_scripture_references_extended(text)
        for r in refs:
            canon = r["canonical"]
            assert "chapter" not in canon.lower()

    def test_non_book_word_volume(self):
        result = annotate._resolve_book_name("volume")
        assert result is None

    def test_non_book_word_vol(self):
        result = annotate._resolve_book_name("vol")
        assert result is None

    def test_non_book_word_page(self):
        result = annotate._resolve_book_name("page")
        assert result is None


# ============================================================
# Integration: find_scripture_references_extended with mixed content
# ============================================================

class TestFindScriptureReferencesExtended:
    """Integration tests for mixed scripture reference formats."""

    def test_mixed_english_and_korean(self):
        text = "As it says in John 3:16 and also 요 3:16."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "John 3:16" in canon

    def test_mixed_legacy_and_arabic(self):
        text = "Compare John iii.16 with Rom. 8:28."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "John 3:16" in canon
        assert "Romans 8:28" in canon

    def test_korean_full_name_with_chapter_verse(self):
        text = "요한복음 3장 16절을 믿으라."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "John 3:16" in canon

    def test_no_duplicate_across_patterns(self):
        text = "John 3:16 John 3:16"
        refs = annotate.find_scripture_references_extended(text)
        canon = [r["canonical"] for r in refs]
        assert canon.count("John 3:16") == 1

    def test_psalms_large_roman_chapter(self):
        text = "Sing Ps. cxviii. 24 with joy."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "Psalms 118:24" in canon

    def test_verse_range_arabic(self):
        text = "Read Rom. 8:1-39 carefully."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "Romans 8:1-39" in canon

    def test_verse_range_korean(self):
        text = "롬 8:1-2를 공부하라."
        refs = annotate.find_scripture_references_extended(text)
        canon = {r["canonical"] for r in refs}
        assert "Romans 8:1-2" in canon
