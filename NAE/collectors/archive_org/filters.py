"""Filtering rules: media type, language, license, exclusion keywords."""
from __future__ import annotations

from . import config
from .search import SearchResult


def is_allowed_mediatype(result: SearchResult) -> bool:
    return result.mediatype.lower() not in config.EXCLUDED_MEDIATYPES


def is_allowed_language(result: SearchResult) -> bool:
    if not result.language:
        return True
    langs = {tok.strip().lower() for tok in result.language.replace(";", ",").split(",") if tok.strip()}
    if not langs:
        return True
    return bool(langs & config.ALLOWED_LANGUAGES)


def has_excluded_keyword(result: SearchResult) -> bool:
    haystack = " ".join([result.title or "", " ".join(result.collection)]).lower()
    return any(kw in haystack for kw in config.EXCLUDED_TITLE_KEYWORDS)


def is_allowed_license(result: SearchResult) -> bool:
    """Public Domain / CC0 / CC-BY / Open Library free -> allowed. Unknown/In-copyright/Borrow -> excluded."""
    url = (result.licenseurl or "").lower()
    if not url:
        return False
    if any(bad in url for bad in config.DISALLOWED_LICENSE_KEYWORDS):
        return False
    return any(good in url for good in config.ALLOWED_LICENSE_KEYWORDS)


def passes_all_filters(result: SearchResult) -> tuple[bool, str]:
    if not is_allowed_mediatype(result):
        return False, f"excluded_mediatype:{result.mediatype}"
    if has_excluded_keyword(result):
        return False, "excluded_keyword"
    if not is_allowed_language(result):
        return False, f"excluded_language:{result.language}"
    if not is_allowed_license(result):
        return False, f"excluded_license:{result.licenseurl or 'unknown'}"
    return True, "ok"


def filter_results(results: list[SearchResult]) -> tuple[list[SearchResult], dict[str, int]]:
    accepted: list[SearchResult] = []
    reasons: dict[str, int] = {}
    for r in results:
        ok, reason = passes_all_filters(r)
        if ok:
            accepted.append(r)
        else:
            key = reason.split(":")[0]
            reasons[key] = reasons.get(key, 0) + 1
    return accepted, reasons
