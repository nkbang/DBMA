"""FixtureAdapter — test/demo adapter that reads JSON fixture files into standard row dicts.

Expected JSON format:
    [
        {"ref": "Gen.24.12", "tag": "prayer", "scope": "verse"},
        ...
    ]

Output row format:
    [
        {"canonical_reference": "Gen.24.12", "tag_namespace": "prayer", "tag_name": "prayer", "scope": "verse"},
        ...
    ]
"""

import json
from pathlib import Path

from core.dataset_adapters.base import DatasetAdapter


class FixtureAdapter(DatasetAdapter):
    """Test adapter that reads JSON fixture files."""

    # Field name mappings from fixture format to standard row format
    _MAPPINGS = {
        "ref": "canonical_reference",
        "ref_key": "canonical_reference",
        "reference": "canonical_reference",
        "tag": "tag_name",
        "tag_namespace": "tag_namespace",
        "namespace": "tag_namespace",
        "scope": "scope",
        "tag_name": "tag_name",
    }

    def load_rows(self, source_path: str) -> list[dict]:
        """Read a JSON fixture file and return standard row dicts.

        Args:
            source_path: Path to a JSON file with fixture data

        Returns:
            List of dicts with keys: canonical_reference, tag_namespace, tag_name, scope
        """
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Fixture file not found: {source_path}")

        text = path.read_text(encoding="utf-8")
        raw_rows = json.loads(text)

        rows: list[dict] = []
        for raw in raw_rows:
            row: dict = {}
            for key, value in raw.items():
                standard_key = self._MAPPINGS.get(key)
                if standard_key and value is not None:
                    row[standard_key] = str(value)
            # Ensure required keys
            if "canonical_reference" in row and "tag_name" in row and "scope" in row:
                if "tag_namespace" not in row:
                    row["tag_namespace"] = row["tag_name"]
                rows.append(row)
            elif "canonical_reference" in row and "tag_namespace" in row and "tag_name" in row and "scope" in row:
                rows.append(row)

        return rows