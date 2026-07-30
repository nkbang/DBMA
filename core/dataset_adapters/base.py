"""DatasetAdapter ABC — interface for converting external dataset formats to standard row dicts."""

from abc import ABC, abstractmethod


class DatasetAdapter(ABC):
    """External dataset adapter interface.

    Converts raw external data sources into standard row dicts that
    TagIngestValidator accepts:
        [{"canonical_reference": "Gen.24.12", "tag_namespace": "...",
          "tag_name": "...", "scope": "verse"}, ...]
    """

    @abstractmethod
    def load_rows(self, source_path: str) -> list[dict]:
        """Read source_path and return list of standard row dicts.

        Args:
            source_path: Path to the external data source (JSON file, API endpoint, etc.)

        Returns:
            List of dicts with keys: canonical_reference, tag_namespace, tag_name, scope
        """
        ...