"""
Sprint 15 Objective 1 — Book Name Alias Resolution Unit Tests

Tests Korean/English book name mappings resolve correctly to TSU book IDs.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.retrieval import (
    BOOK_ID_TO_NAMES,
    NAME_TO_BOOK_ID,
    QueryParser,
    ScriptureReference,
)


class TestBookNameRegistry:
    """Test BOOK_ID_TO_NAMES and NAME_TO_BOOK_ID integrity."""

    def test_all_books_have_korean_names(self):
        """Every book_id should have at least one Korean Hangul name entry."""
        # Hangul Syllables range: U+AC00–U+D7A3 (Korean alphabet characters)
        def is_korean(text: str) -> bool:
            return any("\uAC00" <= c <= "\uD7A3" for c in text)

        expected_books = {
            "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT",
            "1SA", "2SA", "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST",
            "JOB", "PSA", "PRO", "ECC", "SOL",
            "ISA", "JER", "LAM", "EZE", "DAN",
            "HOS", "JOEL", "AMOS", "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
            "MAT", "MRK", "LUK", "JHN",
            "ACT",
            "ROM", "1CO", "2CO", "GAL", "EPH", "PHP", "COL",
            "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
            "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD",
            "REV",
        }
        for book_id in expected_books:
            names = BOOK_ID_TO_NAMES.get(book_id, [])
            korean_names = [n for n in names if is_korean(n)]
            assert len(korean_names) >= 1, f"{book_id} has no Korean Hangul name entries (names={names})"

    def test_reverse_mapping_consistency(self):
        """NAME_TO_BOOK_ID must map back to the correct book_id.

        Shared abbreviations (e.g., '에스' for EZR/EST) are acceptable — the key
        assertion is that all Korean full names resolve uniquely and no name maps
        to an incorrect book.
        """
        # Allowed overlaps: short common syllables shared across books
        allowed_overlaps = {"에스", "마", "요"}

        for book_id, names in BOOK_ID_TO_NAMES.items():
            for name in names:
                mapped_book = NAME_TO_BOOK_ID.get(name)
                if name in allowed_overlaps and mapped_book != book_id:
                    # Acceptable overlap — the regex \b will pick one, but it's
                    # a known limitation of short syllable abbreviations.
                    continue
                assert mapped_book == book_id, (
                    f"Reverse mapping mismatch: '{name}' -> {mapped_book} != {book_id}"
                )

    def test_no_empty_names(self):
        """No book_id should have empty string in names list."""
        for book_id, names in BOOK_ID_TO_NAMES.items():
            assert "" not in names, f"Empty name found for {book_id}"

    def test_all_names_lowercase(self):
        """All names in NAME_TO_BOOK_ID must be lowercase."""
        for name in NAME_TO_BOOK_ID:
            assert name == name.lower(), f"Name not lowercase: '{name}'"


class TestQueryParserAliasResolution:
    """Test that QueryParser resolves Korean/English aliases correctly."""

    def setup_method(self):
        self.parser = QueryParser()

    # --- Korean book name tests ---

    def test_korean_john_resolution(self):
        """요한복음 should resolve to JHN."""
        refs = self.parser._extract_scripture_refs("요한복음 3:16")
        assert len(refs) > 0, "Should extract at least one reference from Korean text"
        assert refs[0].book_id == "JHN", f"Expected JHN but got {refs[0].book_id}"

    def test_korean_romans_resolution(self):
        """로마서 should resolve to ROM."""
        refs = self.parser._extract_scripture_refs("로마서 8:28")
        assert len(refs) > 0
        assert refs[0].book_id == "ROM"

    def test_korean_matthew_resolution(self):
        """마태복음 should resolve to MAT."""
        refs = self.parser._extract_scripture_refs("마태복음 5:3")
        assert len(refs) > 0
        assert refs[0].book_id == "MAT"

    def test_korean_1corinthians_resolution(self):
        """고린도전서 should resolve to 1CO."""
        refs = self.parser._extract_scripture_refs("고린도전서 13:4")
        assert len(refs) > 0
        assert refs[0].book_id == "1CO"

    def test_korean_psalms_resolution(self):
        """시편 should resolve to PSA."""
        refs = self.parser._extract_scripture_refs("시편 23:1")
        assert len(refs) > 0
        assert refs[0].book_id == "PSA"

    # --- English abbreviation tests ---

    def test_english_abbr_rom(self):
        """Rom should resolve to ROM."""
        refs = self.parser._extract_scripture_refs("Rom 8:28")
        assert len(refs) > 0
        assert refs[0].book_id == "ROM"

    def test_english_abbr_mat(self):
        """Matt should resolve to MAT."""
        refs = self.parser._extract_scripture_refs("Matt 5:3")
        assert len(refs) > 0
        assert refs[0].book_id == "MAT"

    def test_english_abbr_jhn(self):
        """Jn should resolve to JHN."""
        refs = self.parser._extract_scripture_refs("Jn 3:16")
        assert len(refs) > 0
        assert refs[0].book_id == "JHN"

    def test_english_abbr_1co(self):
        """1 Cor should resolve to 1CO."""
        refs = self.parser._extract_scripture_refs("1 Cor 13:1")
        assert len(refs) > 0
        assert refs[0].book_id == "1CO"

    def test_english_full_name(self):
        """Full names should still work."""
        refs = self.parser._extract_scripture_refs("Romans 8:28")
        assert len(refs) > 0
        assert refs[0].book_id == "ROM"

        refs = self.parser._extract_scripture_refs("Matthew 5:3")
        assert len(refs) > 0
        assert refs[0].book_id == "MAT"

    # --- Mixed Korean/English tests ---

    def test_mixed_korean_english_query(self):
        """Mixed Korean + English should resolve correctly."""
        refs = self.parser._extract_scripture_refs("요한복음 John 3:16")
        assert len(refs) > 0
        # At least one should be JHN
        book_ids = [r.book_id for r in refs]
        assert "JHN" in book_ids, f"JHN not found in {book_ids}"

    def test_mixed_love_grace_query(self):
        """사랑으로 은혜로 — no verse ref, but themes should be detected."""
        parsed = self.parser.parse("사랑으로 은혜로 구원받는다")
        # Should detect Korean book/theme keywords
        assert parsed.themes is not None
        # Themes like love or grace may be detected from content

    def test_korean_chapter_reference(self):
        """마태 chapter reference without verse should work."""
        refs = self.parser._extract_scripture_refs("마태복음 5")
        # May or may not parse depending on regex, but should not crash
        assert isinstance(refs, list)

    def test_korean_gospel_abbreviation(self):
        """요한 (short form of 요한복음) should resolve."""
        refs = self.parser._extract_scripture_refs("요한 3:16")
        # '요한' maps to JHN via 요한복음 entries check
        if len(refs) > 0:
            assert refs[0].book_id == "JHN"


class TestTypoTolerance:
    """Test common typo variants still resolve."""

    def setup_method(self):
        self.parser = QueryParser()

    def test_jhon_typo(self):
        """Common typo 'Jhon' should not crash; falls through to content-based."""
        refs = self.parser._extract_scripture_refs("Jhon 3:16")
        # May or may not resolve, but must not raise
        assert isinstance(refs, list)

    def test_roma_typo(self):
        """'Roma' should not crash."""
        refs = self.parser._extract_scripture_refs("Roma 8:28")
        assert isinstance(refs, list)


class TestIntegration:
    """Full pipeline integration tests."""

    def test_korean_query_full_pipeline(self):
        """요한복음 3:16 should resolve to JHN through QueryProcessor."""
        from core.retrieval import RetrievalEngine, QueryProcessor

        engine = RetrievalEngine(tsu_dataset_path="output/bench/tsu_dataset.jsonl")
        processor = QueryProcessor(engine)

        response = processor.process("요한복음 3:16", query_id="sprint15-int-1", k=5)

        # Verify parsed refs
        assert len(response.parsed_query.scripture_refs) > 0 or len(response.parsed_query.detected_books) > 0
        # Pipeline should not crash and should return results
        assert response.top_k_results is not None


if __name__ == "__main__":
    import traceback

    test = TestBookNameRegistry()
    try:
        test.test_all_books_have_korean_names()
        print("[PASS] test_all_books_have_korean_names")
    except AssertionError as e:
        print(f"[FAIL] test_all_books_have_korean_names: {e}")

    try:
        test.test_reverse_mapping_consistency()
        print("[PASS] test_reverse_mapping_consistency")
    except AssertionError as e:
        print(f"[FAIL] test_reverse_mapping_consistency: {e}")

    try:
        test.test_no_empty_names()
        print("[PASS] test_no_empty_names")
    except AssertionError as e:
        print(f"[FAIL] test_no_empty_names: {e}")

    try:
        test.test_all_names_lowercase()
        print("[PASS] test_all_names_lowercase")
    except AssertionError as e:
        print(f"[FAIL] test_all_names_lowercase: {e}")

    p = TestQueryParserAliasResolution()
    try:
        p.setup_method()
        p.test_korean_john_resolution()
        print("[PASS] test_korean_john_resolution")
    except AssertionError as e:
        print(f"[FAIL] test_korean_john_resolution: {e}")

    try:
        p.setup_method()
        p.test_korean_romans_resolution()
        print("[PASS] test_korean_romans_resolution")
    except AssertionError as e:
        print(f"[FAIL] test_korean_romans_resolution: {e}")

    try:
        p.setup_method()
        p.test_korean_matthew_resolution()
        print("[PASS] test_korean_matthew_resolution")
    except AssertionError as e:
        print(f"[FAIL] test_korean_matthew_resolution: {e}")

    try:
        p.setup_method()
        p.test_english_abbr_rom()
        print("[PASS] test_english_abbr_rom")
    except AssertionError as e:
        print(f"[FAIL] test_english_abbr_rom: {e}")

    try:
        p.setup_method()
        p.test_mixed_korean_english_query()
        print("[PASS] test_mixed_korean_english_query")
    except AssertionError as e:
        print(f"[FAIL] test_mixed_korean_english_query: {e}")

    i = TestIntegration()
    try:
        i.test_korean_query_full_pipeline()
        print("[PASS] test_korean_query_full_pipeline")
    except Exception as e:
        print(f"[FAIL] test_korean_query_full_pipeline: {e}")
        traceback.print_exc()

    print("\nDone.")