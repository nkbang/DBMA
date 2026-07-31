"""Fetch item metadata from the Internet Archive metadata API and build metadata.json."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from . import config

logger = logging.getLogger("nae.collector.metadata")


@dataclass
class FileEntry:
    name: str
    format: str
    size: int | None = None


@dataclass
class ItemMetadata:
    identifier: str
    title: str = ""
    creator: str = ""
    publisher: str = ""
    year: str = ""
    language: str = ""
    subjects: list[str] = field(default_factory=list)
    downloads: int = 0
    collection: list[str] = field(default_factory=list)
    license: str = ""
    source_url: str = ""
    files: list[FileEntry] = field(default_factory=list)


def _get(url: str, *, retry: int = config.RETRY, timeout: int = config.TIMEOUT) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(1, retry + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code in (404, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            wait = config.BACKOFF_BASE ** attempt
            logger.warning("[metadata] attempt %d/%d failed for %s: %s (retry in %.1fs)",
                            attempt, retry, url, exc, wait)
            if attempt < retry:
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def fetch_item_metadata(identifier: str, *, retry: int = config.RETRY,
                         timeout: int = config.TIMEOUT) -> ItemMetadata:
    url = config.METADATA_API_URL.format(identifier=identifier)
    data = _get(url, retry=retry, timeout=timeout)
    meta = data.get("metadata", {})

    def as_str(v: Any) -> str:
        if isinstance(v, list):
            return "; ".join(str(x) for x in v)
        return str(v) if v is not None else ""

    def as_list(v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    files = []
    for f in data.get("files", []):
        fmt = (f.get("format") or "").lower()
        files.append(FileEntry(name=f.get("name", ""), format=fmt,
                                size=int(f["size"]) if f.get("size") else None))

    return ItemMetadata(
        identifier=identifier,
        title=as_str(meta.get("title")),
        creator=as_str(meta.get("creator")),
        publisher=as_str(meta.get("publisher")),
        year=as_str(meta.get("year") or meta.get("date")),
        language=as_str(meta.get("language")),
        subjects=as_list(meta.get("subject")),
        downloads=int(data.get("item", {}).get("downloads", 0) or 0),
        collection=as_list(meta.get("collection")),
        license=as_str(meta.get("licenseurl")),
        source_url=f"https://archive.org/details/{identifier}",
        files=files,
    )


def select_download_files(item: ItemMetadata) -> dict[str, FileEntry]:
    """Pick best PDF/EPUB/DJVU/TXT plus OCR txt when available."""
    chosen: dict[str, FileEntry] = {}

    for fmt in config.DOWNLOAD_FORMAT_PRIORITY:
        candidates = [f for f in item.files if fmt in f.format.lower() or f.name.lower().endswith(f".{fmt}")]
        if candidates:
            chosen["primary"] = candidates[0]
            break

    for f in item.files:
        if "djvu.txt" in f.name.lower() or (f.format == "dwn" or "ocr" in f.name.lower()):
            chosen["ocr_txt"] = f
            break
    if "ocr_txt" not in chosen:
        for f in item.files:
            if f.format == "txt":
                chosen["ocr_txt"] = f
                break

    return chosen


def build_metadata_dict(item: ItemMetadata, *, license_ok: str, download_url: str,
                         checksum: str, downloaded: bool) -> dict[str, Any]:
    return {
        "identifier": item.identifier,
        "title": item.title,
        "creator": item.creator,
        "publisher": item.publisher,
        "year": item.year,
        "language": item.language,
        "subjects": item.subjects,
        "downloads": item.downloads,
        "collection": item.collection,
        "license": license_ok or item.license,
        "source_url": item.source_url,
        "download_url": download_url,
        "checksum": checksum,
        "downloaded": downloaded,
    }
