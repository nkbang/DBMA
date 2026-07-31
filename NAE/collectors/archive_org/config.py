"""Configuration for the Internet Archive Baptist collector.

Settings live in config.yaml (shared shape for future collectors: gutenberg,
hathitrust, google, loc, ...) and keywords.yaml (editable keyword lists).
Both are loaded at import time; missing/invalid YAML falls back to the
defaults below so the collector still runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE_DIR = Path(__file__).resolve().parent

CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"
DOWNLOAD_ROOT = CORPUS_ROOT / "raw" / "archive_org"
METADATA_ROOT = CORPUS_ROOT / "metadata"
MANIFESTS_ROOT = CORPUS_ROOT / "manifests"
REPORTS_ROOT = CORPUS_ROOT / "reports"
LOGS_ROOT = CORPUS_ROOT / "logs"
CACHE_ROOT = CORPUS_ROOT / "cache"
CATALOG_PATH = METADATA_ROOT / "archive_org_catalog.json"

CONFIG_YAML_PATH = MODULE_DIR / "config.yaml"
KEYWORDS_YAML_PATH = MODULE_DIR / "keywords.yaml"

_DEFAULTS: dict[str, Any] = {
    "collector_version": "1.1.0",
    "search_api_url": "https://archive.org/advancedsearch.php",
    "metadata_api_url": "https://archive.org/metadata/{identifier}",
    "download_url_template": "https://archive.org/download/{identifier}/{filename}",
    "max_results": 200,
    "max_download": 100,
    "threads": 4,
    "retry": 3,
    "timeout": 30,
    "backoff_base": 2.0,
    "allowed_languages": ["english", "eng", "en", "latin", "lat", "german", "ger", "deu",
                           "dutch", "dut", "nld", "french", "fre", "fra"],
    "excluded_mediatypes": ["movies", "audio", "software", "collection", "web"],
    "excluded_title_keywords": ["newspaper", "microfilm", "magazine scan only"],
    "allowed_license_keywords": ["publicdomain", "public domain", "cc0",
                                  "creativecommons.org/publicdomain", "cc-by",
                                  "creativecommons.org/licenses/by/"],
    "disallowed_license_keywords": ["in-copyright", "in copyright", "borrow", "restricted"],
    "public_domain_rights_keywords": ["public domain", "no known copyright", "not in copyright"],
    "public_domain_year_cutoff": 1929,
    "download_format_priority": ["pdf", "epub", "djvu", "txt"],
    "category_keywords": {
        "tracts": ["tract"],
        "journals": ["journal", "quarterly", "review", "magazine", "record"],
        "pamphlets": ["pamphlet"],
    },
    "default_category": "books",
}

_DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "priority_a": ["Baptist", "Primitive Baptist", "Particular Baptist", "General Baptist",
                   "Reformed Baptist", "Southern Baptist", "Missionary Baptist",
                   "Free Will Baptist", "Baptist Union", "Baptist Magazine",
                   "Baptist Quarterly", "Baptist Review", "Baptist Record"],
    "priority_b": ["John Smyth", "Thomas Helwys", "Benjamin Keach", "John Gill",
                   "Andrew Fuller", "William Carey", "Charles Spurgeon", "B. H. Carroll",
                   "J. M. Pendleton", "John Broadus", "A. H. Strong", "E. Y. Mullins"],
    "priority_c": ["Baptism", "Believer's Baptism", "Church Covenant", "Church Discipline",
                   "Lord's Supper", "Confession", "1689 Confession", "Philadelphia Confession",
                   "New Hampshire Confession", "Baptist Catechism"],
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except (yaml.YAMLError, OSError):
        return {}


_settings = {**_DEFAULTS, **_load_yaml(CONFIG_YAML_PATH)}
_keywords = {**_DEFAULT_KEYWORDS, **_load_yaml(KEYWORDS_YAML_PATH)}

COLLECTOR_VERSION: str = _settings["collector_version"]

SEARCH_API_URL: str = _settings["search_api_url"]
METADATA_API_URL: str = _settings["metadata_api_url"]
DOWNLOAD_URL_TEMPLATE: str = _settings["download_url_template"]

MAX_RESULTS: int = _settings["max_results"]
MAX_DOWNLOAD: int = _settings["max_download"]
THREADS: int = _settings["threads"]
RETRY: int = _settings["retry"]
TIMEOUT: int = _settings["timeout"]
BACKOFF_BASE: float = _settings["backoff_base"]

ALLOWED_LANGUAGES: set[str] = {s.lower() for s in _settings["allowed_languages"]}
EXCLUDED_MEDIATYPES: set[str] = {s.lower() for s in _settings["excluded_mediatypes"]}
EXCLUDED_TITLE_KEYWORDS: set[str] = {s.lower() for s in _settings["excluded_title_keywords"]}

ALLOWED_LICENSE_KEYWORDS: tuple[str, ...] = tuple(_settings["allowed_license_keywords"])
DISALLOWED_LICENSE_KEYWORDS: tuple[str, ...] = tuple(_settings["disallowed_license_keywords"])
PUBLIC_DOMAIN_RIGHTS_KEYWORDS: tuple[str, ...] = tuple(_settings["public_domain_rights_keywords"])
PUBLIC_DOMAIN_YEAR_CUTOFF: int = _settings["public_domain_year_cutoff"]

DOWNLOAD_FORMAT_PRIORITY: list[str] = list(_settings["download_format_priority"])

CATEGORY_KEYWORDS: dict[str, list[str]] = _settings["category_keywords"]
DEFAULT_CATEGORY: str = _settings["default_category"]

PRIORITY_A: list[str] = list(_keywords["priority_a"])
PRIORITY_B: list[str] = list(_keywords["priority_b"])
PRIORITY_C: list[str] = list(_keywords["priority_c"])


@dataclass
class CollectorConfig:
    download_root: Path = field(default_factory=lambda: DOWNLOAD_ROOT)
    max_results: int = MAX_RESULTS
    max_download: int = MAX_DOWNLOAD
    threads: int = THREADS
    retry: int = RETRY
    timeout: int = TIMEOUT
