"""Citation disclosure text for NAE sources with provenance or doctrinal
authority limitations.

This module holds two independent, deterministic label axes. Neither axis
is derived by the LLM at answer time — both are fixed text keyed off source
metadata, so a citation's disclosure can never be dropped, reworded, or
spoofed by a prompt or a model response.

Axis 1 — `authority_class` (ADR-030 §7.3, provenance/genre):
    primary_doctrinal / historical_witness / reference / application.
    Already populated in the M2 source registry for admitted corpora.
    ADR-030 Amendment A §6 requires that, when Fuller (`authority_class:
    historical_witness`) content is surfaced as a search result or citation,
    the UI shows a fixed KR/EN provenance notice — page numbers are
    unavailable, confidence values are uncalibrated, and scripture-reference
    extraction may have residual gaps. This module holds that fixed text so
    callers (F6 UI wiring) don't restate or drift from the Amendment A
    wording.

    Currently only one `historical_witness` source (Andrew Fuller) is
    admitted, so the text below names him directly per Amendment A §6. If a
    second `historical_witness` source is admitted later, this needs a
    per-work lookup instead of one fixed string — not built now because
    there is nothing to key it on yet (YAGNI).

Axis 2 — `authority_tier` (T1-T4, doctrinal orthodoxy relative to the
    user's own tradition — see DBMA/NAE personal-RAG proposal §11/§13):
    T1 canon/confession, T2 vetted own-tradition theology, T3 comparative/
    apologetics source (other tradition, other religion, or heterodox —
    cited only for comparison, never as orthodox teaching), T4 unreviewed.
    This is a SEPARATE axis from `authority_class` — one tags source genre
    and provenance quality, the other tags doctrinal standing. A document
    may carry both independently (e.g. a T3 primary_doctrinal text: a
    heterodox group's own confession, doctrinally non-orthodox but not a
    provenance/OCR-quality concern).

    No document in the corpus carries an `authority_tier` value yet — no
    M2 registry entry, no ingestion step sets it. This module only
    implements the deterministic label-lookup half of the proposal's §13
    pipeline (step ⑥, post-processing render). Wiring a real
    `authority_tier` field into the source registry / TSU metadata and the
    retrieval-scope filter (proposal §13.2 steps ①-⑤) is a separate,
    not-yet-approved change — see proposal §14.5.
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


# ─────────────────────────────────────────────────────────────────────────
# Axis 2 — authority_tier (T1-T4) disclosure labels
# ─────────────────────────────────────────────────────────────────────────

AUTHORITY_TIERS = ("T1", "T2", "T3", "T4")

TIER_LABELS_KO = {
    "T1": "정경/신조",
    "T2": "검증된 신학",
    "T3": "비교/변증 참고",
    "T4": "미검증/보류",
}

_T3_DISCLOSURE_TEMPLATE = (
    "⚠️ **[비교/변증 자료 · T3]** 이 인용은 정통 교리로 제시된 것이 아니라 "
    "비교·변증 목적의 1차 자료입니다{tradition_ko}.\n"
    "**Comparative/Apologetics Source · T3** — cited for comparison or "
    "apologetic reference only, not as orthodox teaching{tradition_en}."
)

_T4_DISCLOSURE = (
    "**[미검증 자료 · T4]** 이 자료는 아직 큐레이션 검토를 거치지 않았습니다. "
    "정상 검색 결과에는 포함되지 않으며, 검토 후 등급이 확정되기 전까지는 "
    "설교·교육 근거로 사용할 수 없습니다.\n"
    "**Unreviewed Source · T4** — not yet curated; excluded from normal "
    "retrieval and not citable until reviewed and re-tiered."
)


def get_tier_disclosure(
    authority_tier: str | None,
    *,
    tradition: str | None = None,
    counter_refs: list[str] | None = None,
) -> str | None:
    """Return the fixed disclosure text for a citation's `authority_tier`
    (T1-T4), or None when no disclosure applies (T1/T2 need no warning).

    Deterministic lookup only, mirroring `get_disclosure()` above — the
    caller supplies metadata already resolved from the source registry;
    this function never inspects LLM output and never generates wording
    itself, so the warning cannot be silently dropped or reworded.

    T3 sources must carry at least one `counter_ref` (proposal §11.4 hard
    constraint: a comparative/apologetics source cannot be surfaced without
    a linked rebuttal). This function re-asserts that constraint at display
    time as a defense-in-depth check — it does not replace enforcing it at
    ingestion/indexing time.
    """
    if not authority_tier:
        return None
    if authority_tier not in AUTHORITY_TIERS:
        raise ValueError(f"Unknown authority_tier: {authority_tier!r}")

    if authority_tier in ("T1", "T2"):
        return None

    if authority_tier == "T4":
        return _T4_DISCLOSURE

    # T3
    if not counter_refs:
        raise ValueError(
            "T3 citation missing counter_refs — a comparative/apologetics "
            "source cannot be disclosed without at least one linked "
            "rebuttal/counter-reference (proposal §11.4)."
        )
    tradition_ko = f" (전통: {tradition})" if tradition else ""
    tradition_en = f" (tradition: {tradition})" if tradition else ""
    text = _T3_DISCLOSURE_TEMPLATE.format(
        tradition_ko=tradition_ko, tradition_en=tradition_en
    )
    refs = ", ".join(counter_refs)
    text += f"\n↳ 반박/비교 자료 (counter_ref): {refs}"
    return text
