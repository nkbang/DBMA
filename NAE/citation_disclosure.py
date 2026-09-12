"""Citation disclosure text for NAE sources with provenance limitations.

ADR-030 Amendment A §6 requires that, when Fuller (`authority_class:
historical_witness`) content is surfaced as a search result or citation,
the UI shows a fixed KR/EN provenance notice — page numbers are unavailable,
confidence values are uncalibrated, and scripture-reference extraction may
have residual gaps. This module holds that fixed text so callers (F6 UI
wiring) don't restate or drift from the Amendment A wording.

Currently only one `historical_witness` source (Andrew Fuller) is admitted,
so the text below names him directly per Amendment A §6. If a second
`historical_witness` source is admitted later, this needs a per-work lookup
instead of one fixed string — not built now because there is nothing to key
it on yet (YAGNI).
"""
from __future__ import annotations

HISTORICAL_WITNESS_DISCLOSURE = (
    "**출처 고지 (KR)** — 이 claim은 Andrew Fuller, *The Works of the Rev. "
    "Andrew Fuller* (공개 도메인 OCR 원본)에서 자동 추출되었습니다. 페이지 "
    "번호가 없어 인용 위치는 heading·문단 기준입니다. 신뢰도 값은 교정되지 "
    "않았습니다. 자동 성구 추출에 일부 누락이 있을 수 있습니다. 권한 등급: "
    "역사적 증언(historical_witness).\n\n"
    "**Provenance Notice (EN)** — This claim was auto-extracted from Andrew "
    "Fuller, *The Works of the Rev. Andrew Fuller* (public-domain OCR). "
    "No page numbers — citations use heading/paragraph locators. Confidence "
    "values are uncalibrated. Some scripture references may be missing. "
    "Authority class: historical witness."
)


def get_disclosure(authority_class: str | None) -> str | None:
    """Return the fixed disclosure text for a citation's authority_class, or
    None when no disclosure applies (e.g. verified/curated sources)."""
    if authority_class == "historical_witness":
        return HISTORICAL_WITNESS_DISCLOSURE
    return None
