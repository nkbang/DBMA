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


def _is_fuller_source(
    source_id: str | None, identifier: str | None, author: str | None
) -> bool:
    """Andrew Fuller의 `historical_witness` 자료인지 결정론적으로 판별한다.

    Amendment A §6의 고정 고지문(`HISTORICAL_WITNESS_DISCLOSURE`)은 Fuller
    OCR 원본의 성격(페이지 번호 없음, 신뢰도 미교정, 성구 추출 누락)을 서술한다.
    다른 소스(예: 페이지 번호가 있는 Dagg/Hiscox)에 그대로 붙이면 사실과 다른
    저자·성격을 표시하게 된다(EUAT-001 Issue 5). 성(姓)만으로 판별하지 않는다 —
    동성이인(예: Thomas Fuller)을 Fuller 고지로 오분류하지 않기 위해 소스 ID
    접두사 / 코퍼스 identifier 접두사 / 저자 전체 이름만 본다.
    """
    if (source_id or "").upper().startswith("BAP-MISS-FULLER"):
        return True
    if (identifier or "").startswith("Fuller_Complete_Works"):
        return True
    return (author or "").strip().lower() == "andrew fuller"


def _generic_historical_witness_disclosure(author: str | None, work: str | None) -> str:
    """Fuller 이외의 `historical_witness` 소스용 고지 — 메타데이터에서만 만든다.

    페이지 번호·신뢰도·성구 추출 상태 같은 소스별 성격은 Amendment A가 Fuller에
    대해서만 정의했으므로, 여기서는 그런 주장을 하지 않는다(사실이 아닐 수
    있다). 저자·문헌과 권한 등급 라벨만 결정론적으로 표시한다.
    """
    who = f"{author}, *{work}*" if author and work else (author or work or "이 자료")
    who_en = f"{author}, *{work}*" if author and work else (author or work or "this source")
    return (
        f"**출처 고지 (KR)** — 이 근거는 {who}에서 가져온 원문 문단입니다. "
        "권한 등급: 역사적 증언(historical_witness).\n\n"
        f"**Provenance Notice (EN)** — This evidence is a passage from {who_en}. "
        "Authority class: historical witness."
    )


def get_disclosure(
    authority_class: str | None,
    *,
    source_id: str | None = None,
    identifier: str | None = None,
    author: str | None = None,
    work: str | None = None,
) -> str | None:
    """Return the disclosure text for a citation's authority_class, or None
    when no disclosure applies (e.g. verified/curated sources).

    소스 정보(`source_id`/`identifier`/`author`/`work`)를 주지 않으면 종전과
    동일하게 Fuller 고정 고지문을 반환한다(하위 호환). 소스 정보를 주면
    Fuller에게만 Fuller 고정 고지문을, 그 외 `historical_witness` 소스에는
    저자·문헌을 그대로 밝히는 일반 고지문을 반환한다.
    """
    if authority_class != "historical_witness":
        return None
    if source_id is None and identifier is None and author is None and work is None:
        return HISTORICAL_WITNESS_DISCLOSURE
    if _is_fuller_source(source_id, identifier, author):
        return HISTORICAL_WITNESS_DISCLOSURE
    return _generic_historical_witness_disclosure(author, work)


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
