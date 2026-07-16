"""Regression test — document metadata backfill (SPRINT17-Phase6A-4).

scripts/backfill_document_metadata.py fills registry.title/author/book
from raw source files without going through full reprocessing. This test
guards the junk-value filter that keeps known-bad extracted metadata
(scanner-tool IDs, generic placeholder authors) out of the registry —
worse to store than leaving the field honestly None.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.backfill_document_metadata import (
    _is_usable_title,
    _is_usable_author,
    backfill,
)


class TestJunkValueFilters:
    def test_scanner_id_title_rejected(self):
        assert _is_usable_title("22C-6e-20161211191417") is False

    def test_real_title_accepted(self):
        assert _is_usable_title("2 Kings, Volume 13") is True

    def test_none_title_rejected(self):
        assert _is_usable_title(None) is False

    def test_generic_placeholder_author_rejected(self):
        assert _is_usable_author("Holy Bible") is False
        assert _is_usable_author("holy bible") is False  # case-insensitive

    def test_real_author_accepted(self):
        assert _is_usable_author("Raymond B. Dillard") is True

    def test_none_author_rejected(self):
        assert _is_usable_author(None) is False


class TestBackfillSkipsFilledFields:
    def test_skips_document_with_all_fields_present(self):
        """A document that already has title/author/book must not be
        re-examined — never overwrite a value a human already set via the
        Library manual-edit form."""
        registry = {
            "documents": {
                "doc1": {
                    "source_file": "does_not_exist.pdf",
                    "title": "Existing Title",
                    "author": "Existing Author",
                    "book": "ROM",
                }
            }
        }
        changes = backfill(registry, raw_dir=__import__("pathlib").Path("/nonexistent"))
        assert changes == []

    def test_missing_raw_file_produces_no_silent_invention(self):
        """If the raw file can't be found, fields must stay unfilled —
        never invent a value."""
        registry = {
            "documents": {
                "doc1": {
                    "source_file": "does_not_exist.pdf",
                    "title": None,
                    "author": None,
                    "book": None,
                }
            }
        }
        changes = backfill(registry, raw_dir=__import__("pathlib").Path("/nonexistent"))
        assert changes == []  # found_file=False -> no fields added to change


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
