"""Internet Archive Advanced Search API client."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from . import config

logger = logging.getLogger("nae.collector.search")

SEARCH_FIELDS = [
    "identifier", "title", "creator", "year", "language",
    "licenseurl", "publicdate", "mediatype", "downloads", "collection",
]


@dataclass
class SearchResult:
    identifier: str
    title: str = ""
    creator: str = ""
    year: str = ""
    language: str = ""
    licenseurl: str = ""
    publicdate: str = ""
    mediatype: str = ""
    downloads: int = 0
    collection: list[str] = field(default_factory=list)


def _request_with_retry(params: dict[str, Any], *, retry: int = config.RETRY,
                         timeout: int = config.TIMEOUT) -> dict[str, Any]:
    last_exc: Exception | None = None
    for attempt in range(1, retry + 1):
        try:
            resp = requests.get(config.SEARCH_API_URL, params=params, timeout=timeout)
            if resp.status_code in (404, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            wait = config.BACKOFF_BASE ** attempt
            logger.warning("[search] attempt %d/%d failed: %s (retry in %.1fs)",
                            attempt, retry, exc, wait)
            if attempt < retry:
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def search_keyword(keyword: str, *, rows: int = config.MAX_RESULTS,
                    retry: int = config.RETRY, timeout: int = config.TIMEOUT) -> list[SearchResult]:
    """Search Internet Archive for a keyword restricted to English-language texts."""
    query = f'(subject:"{keyword}" OR title:"{keyword}") AND mediatype:texts AND language:eng'
    params: dict[str, Any] = {
        "q": query,
        "rows": rows,
        "page": 1,
        "output": "json",
    }
    for f in SEARCH_FIELDS:
        params.setdefault("fl[]", [])
    params["fl[]"] = SEARCH_FIELDS

    logger.info("[search] keyword=%r rows=%d", keyword, rows)
    data = _request_with_retry(params, retry=retry, timeout=timeout)
    docs = data.get("response", {}).get("docs", [])
    results = []
    for doc in docs:
        collection = doc.get("collection", [])
        if isinstance(collection, str):
            collection = [collection]
        results.append(SearchResult(
            identifier=doc.get("identifier", ""),
            title=doc.get("title", "") if isinstance(doc.get("title"), str) else str(doc.get("title", "")),
            creator=doc.get("creator", "") if isinstance(doc.get("creator"), str) else str(doc.get("creator", "")),
            year=str(doc.get("year", "")),
            language=doc.get("language", "") if isinstance(doc.get("language"), str) else str(doc.get("language", "")),
            licenseurl=doc.get("licenseurl", ""),
            publicdate=doc.get("publicdate", ""),
            mediatype=doc.get("mediatype", ""),
            downloads=int(doc.get("downloads", 0) or 0),
            collection=collection,
        ))
    logger.info("[search] keyword=%r found=%d", keyword, len(results))
    return results


def search_all(keywords: list[str], *, rows: int = config.MAX_RESULTS,
                retry: int = config.RETRY, timeout: int = config.TIMEOUT) -> dict[str, list[SearchResult]]:
    return {kw: search_keyword(kw, rows=rows, retry=retry, timeout=timeout) for kw in keywords}
