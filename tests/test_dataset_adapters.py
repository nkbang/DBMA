"""Tests for dataset_adapters package — Sprint B (Task Order 021)."""

import json
import tempfile
from pathlib import Path

import pytest

from core.dataset_adapters.fixture_adapter import FixtureAdapter


# ---------------------------------------------------------------------------
# Test: FixtureAdapter.load_rows()
# ---------------------------------------------------------------------------

class TestFixtureAdapter:
    def test_loads_standard_fixture(self, tmp_path: Path):
        """Fixture with 'ref'/'tag'/'scope' fields."""
        data = [
            {"ref": "Gen.24.12", "tag": "prayer", "scope": "verse"},
            {"ref": "Gen.24.13", "tag": "blessing", "scope": "clause"},
        ]
        p = tmp_path / "fixture.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        adapter = FixtureAdapter()
        rows = adapter.load_rows(str(p))

        assert len(rows) == 2
        assert rows[0]["canonical_reference"] == "Gen.24.12"
        assert rows[0]["tag_name"] == "prayer"
        assert rows[0]["scope"] == "verse"
        assert rows[0]["tag_namespace"] == "prayer"  # defaults to tag_name

        assert rows[1]["canonical_reference"] == "Gen.24.13"
        assert rows[1]["tag_name"] == "blessing"
        assert rows[1]["scope"] == "clause"

    def test_loads_explicit_namespace_fixture(self, tmp_path: Path):
        """Fixture with explicit 'tag_namespace' field."""
        data = [
            {"ref": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ]
        p = tmp_path / "fixture_ns.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        adapter = FixtureAdapter()
        rows = adapter.load_rows(str(p))

        assert len(rows) == 1
        assert rows[0]["tag_namespace"] == "prayer"
        assert rows[0]["tag_name"] == "prayer"

    def test_raises_on_missing_file(self):
        """FixtureAdapter raises FileNotFoundError for missing file."""
        adapter = FixtureAdapter()
        with pytest.raises(FileNotFoundError):
            adapter.load_rows("/nonexistent/path/fixture.json")

    def test_loads_mixed_field_names(self, tmp_path: Path):
        """Fixture with 'reference'/'namespace' aliases."""
        data = [
            {"reference": "Gen.24.14", "namespace": "wisdom", "tag_name": "wisdom_saying", "scope": "discourse_unit"},
        ]
        p = tmp_path / "fixture_mixed.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        adapter = FixtureAdapter()
        rows = adapter.load_rows(str(p))

        assert len(rows) == 1
        assert rows[0]["canonical_reference"] == "Gen.24.14"
        assert rows[0]["tag_namespace"] == "wisdom"
        assert rows[0]["tag_name"] == "wisdom_saying"