"""Dataset adapters package — converts external dataset formats to standard row dicts."""

from core.dataset_adapters.base import DatasetAdapter
from core.dataset_adapters.fixture_adapter import FixtureAdapter

__all__ = ["DatasetAdapter", "FixtureAdapter"]