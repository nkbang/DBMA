"""Configuration for the Internet Archive Baptist collector."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "NAE" / "corpus"

DOWNLOAD_ROOT = CORPUS_ROOT / "raw" / "archive_org"
METADATA_ROOT = CORPUS_ROOT / "metadata"
LOGS_ROOT = CORPUS_ROOT / "logs"
CATALOG_PATH = METADATA_ROOT / "archive_org_catalog.json"

SEARCH_API_URL = "https://archive.org/advancedsearch.php"
METADATA_API_URL = "https://archive.org/metadata/{identifier}"
DOWNLOAD_URL_TEMPLATE = "https://archive.org/download/{identifier}/{filename}"

MAX_RESULTS = 200
MAX_DOWNLOAD = 100
THREADS = 4
RETRY = 3
TIMEOUT = 30
BACKOFF_BASE = 2.0

ALLOWED_LANGUAGES = {"english", "eng", "en", "latin", "lat", "german", "ger", "deu",
                      "dutch", "dut", "nld", "french", "fre", "fra"}

EXCLUDED_MEDIATYPES = {"movies", "audio", "software", "collection", "web"}
EXCLUDED_TITLE_KEYWORDS = {
    "newspaper", "microfilm", "magazine scan only",
}

ALLOWED_LICENSE_KEYWORDS = (
    "publicdomain",
    "public domain",
    "cc0",
    "creativecommons.org/publicdomain",
    "cc-by",
    "creativecommons.org/licenses/by/",
)
DISALLOWED_LICENSE_KEYWORDS = (
    "in-copyright",
    "in copyright",
    "borrow",
    "restricted",
)

PRIORITY_A = [
    "Baptist", "Primitive Baptist", "Particular Baptist", "General Baptist",
    "Reformed Baptist", "Southern Baptist", "Missionary Baptist",
    "Free Will Baptist", "Baptist Union", "Baptist Magazine",
    "Baptist Quarterly", "Baptist Review", "Baptist Record",
]
PRIORITY_B = [
    "John Smyth", "Thomas Helwys", "Benjamin Keach", "John Gill",
    "Andrew Fuller", "William Carey", "Charles Spurgeon", "B. H. Carroll",
    "J. M. Pendleton", "John Broadus", "A. H. Strong", "E. Y. Mullins",
]
PRIORITY_C = [
    "Baptism", "Believer's Baptism", "Church Covenant", "Church Discipline",
    "Lord's Supper", "Confession", "1689 Confession", "Philadelphia Confession",
    "New Hampshire Confession", "Baptist Catechism",
]

DOWNLOAD_FORMAT_PRIORITY = ["pdf", "epub", "djvu", "txt"]

CATEGORY_KEYWORDS = {
    "tracts": ["tract"],
    "journals": ["journal", "quarterly", "review", "magazine", "record"],
    "pamphlets": ["pamphlet"],
}
DEFAULT_CATEGORY = "books"


@dataclass
class CollectorConfig:
    download_root: Path = field(default_factory=lambda: DOWNLOAD_ROOT)
    max_results: int = MAX_RESULTS
    max_download: int = MAX_DOWNLOAD
    threads: int = THREADS
    retry: int = RETRY
    timeout: int = TIMEOUT
