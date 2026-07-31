"""Filtering rules: media type, language, license, exclusion keywords."""
from __future__ import annotations

import re

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


def _extract_year(value: str) -> int | None:
    if not value:
        return None
    match = re.search(r"(1[5-9]\d{2}|20\d{2})", value)
    return int(match.group(1)) if match else None


def is_public_domain(*, licenseurl: str = "", rights: str = "",
                      possible_copyright_status: str = "", year: str = "") -> tuple[bool, str]:
    """Determine public-domain status from multiple signals, not licenseurl alone.

    Internet Archive frequently omits licenseurl on pre-1929 scans even though
    the underlying work is public domain in the US. Checked in order:
    1. licenseurl matches an allowed/disallowed keyword -> decisive.
    2. rights / possible-copyright-status text mentions public domain -> allow.
    3. rights / possible-copyright-status text mentions in-copyright/borrow -> deny.
    4. publication year at or before the US public-domain cutoff -> allow.
    5. otherwise -> deny (unknown, conservative default).
    """
    url = (licenseurl or "").lower()
    if url:
        if any(bad in url for bad in config.DISALLOWED_LICENSE_KEYWORDS):
            return False, f"licenseurl_disallowed:{licenseurl}"
        if any(good in url for good in config.ALLOWED_LICENSE_KEYWORDS):
            return True, f"licenseurl_allowed:{licenseurl}"

    rights_text = " ".join([rights or "", possible_copyright_status or ""]).lower()
    if rights_text:
        if any(bad in rights_text for bad in config.DISALLOWED_LICENSE_KEYWORDS):
            return False, f"rights_disallowed:{rights_text}"
        if any(good in rights_text for good in config.PUBLIC_DOMAIN_RIGHTS_KEYWORDS):
            return True, f"rights_public_domain:{rights_text}"

    parsed_year = _extract_year(year)
    if parsed_year is not None and parsed_year <= config.PUBLIC_DOMAIN_YEAR_CUTOFF:
        return True, f"year_cutoff:{parsed_year}"

    return False, "unknown"


def is_allowed_license(result: SearchResult) -> bool:
    """Backward-compatible wrapper over is_public_domain using search-result fields."""
    ok, _ = is_public_domain(
        licenseurl=result.licenseurl, rights=result.rights,
        possible_copyright_status=result.possible_copyright_status, year=result.year,
    )
    return ok


def passes_all_filters(result: SearchResult) -> tuple[bool, str]:
    if not is_allowed_mediatype(result):
        return False, f"excluded_mediatype:{result.mediatype}"
    if has_excluded_keyword(result):
        return False, "excluded_keyword"
    if not is_allowed_language(result):
        return False, f"excluded_language:{result.language}"
    ok, reason = is_public_domain(
        licenseurl=result.licenseurl, rights=result.rights,
        possible_copyright_status=result.possible_copyright_status, year=result.year,
    )
    if not ok:
        return False, f"excluded_license:{reason}"
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
