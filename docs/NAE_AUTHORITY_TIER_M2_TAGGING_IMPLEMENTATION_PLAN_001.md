# NAE Authority Tier (T1-T4) M2 Tagging — Implementation Plan 001

**Plan ID:** NAE-AUTHORITY-TIER-M2-TAGGING-PLAN-001
**Date:** 2026-09-16
**Author:** CUE (Implementation Agent)
**Status:** §4-§5 IMPLEMENTED (2026-09-17, commit `e3adb94`, ADR-030 Amendment D
now APPROVED). §6-§8 (M2 backfill, `corpus_admissions.jsonl` tagging) remain
NOT YET STARTED — separate HQ decision, out of scope for this implementation.
**Depends on:** commit `d7228074` (`feat(nae): add authority_tier (T1-T4)
disclosure labels to citation_disclosure`) — the label-lookup half of this
feature already exists and is unaffected by this plan.
**Scope:** M2 source registry tagging only. Does NOT touch Retrieval Engine,
RAW corpus, TSU Pipeline, or Production Registry (all forbidden-without-
command per CLAUDE.md).

---

## 1. Problem Definition

`NAE/citation_disclosure.py::get_tier_disclosure()` (merged 2026-09-16)
implements the *display* half of the DBMA/NAE personal-RAG proposal's §11/§13
design: given an `authority_tier` (T1-T4), a `tradition`, and `counter_refs`,
it renders a fixed warning label. But no document in the corpus carries an
`authority_tier` value — the function has nothing to call it with. This plan
designs the *tagging* half: how `authority_tier` gets onto an M2 record in
the first place, safely, without disturbing the existing `authority_class`
axis or any Approved ADR.

## 2. Relationship to Existing Architecture

M2 (`NAE/pipeline/registration/state/source_manifest.yaml`, mirrored
read-only to `NAE/authority/source_manifest.yaml`) already carries an
ADR-030 §7.3 axis:

```
authority_class ∈ {primary_doctrinal, historical_witness, reference, application}
```

This is a **provenance/genre** axis — it answers "what kind of source is
this, and how reliable is its extraction?" It does not answer "is this
doctrinally orthodox relative to the user's own tradition?" That second
question is what `authority_tier` (T1-T4) answers. The two axes are
independent and must remain independent — a `primary_doctrinal` source can
still be `T3` (e.g. a heterodox group's own confession is, for that group,
their primary doctrinal text; for this user it is a comparative/apologetics
source).

`NAE/governance/corpus_admissions.jsonl` already carries a free-text
`tradition` field per source (e.g. `"Particular Baptist"`). This plan does
**not** change that field or its values. It adds a *separate* field,
`tradition_relation`, that classifies the source's tradition *relative to
the user's own configured tradition* — orthogonal to the source's own
tradition label.

## 3. Proposed Additive Fields

Following the exact precedent of ADR-030 Amendment B (2026-09-13, which
added `content_genre`/`authority_class`/`tradition`/`theological_category`
as optional M2 fields without touching the original 10-key record shape),
this plan proposes three new **optional, additive** fields:

| Field | Type | Values | Required when |
|---|---|---|---|
| `authority_tier` | string enum | `T1`, `T2`, `T3`, `T4` | Optional on write; a record without it is treated as `T4` by any future consumer (fail-closed default, mirrors "새 자료는 예외 없이 T4로 시작" from the proposal) |
| `tradition_relation` | string enum | `own`, `allied`, `other_christian`, `non_christian`, `heterodox` | Required when `authority_tier` is present |
| `counter_refs` | list[string] | list of existing `source_id` values | Required (non-empty) when `authority_tier = T3` — hard constraint, mirrors the validator-level check already implemented in `get_tier_disclosure()` |

No existing M2 key is renamed, removed, or reinterpreted. A record omitting
all three fields is byte-identical to today's output — same guarantee
ADR-030 Amendment B gave for its own additive fields.

**Constraint added per C1 Review (`NAE_AUTHORITY_TIER_M2_TAGGING_C1_REVIEW_RESULT_001.md`,
question 5, YELLOW finding):** every id listed in `counter_refs` MUST itself resolve to a
source whose own `authority_tier ∈ {T1, T2}`. This is not just an orphan-reference check
(§5 V11 below) — it rules out a T3 source citing another T3 (or T4) source as its rebuttal,
which would otherwise permit a cycle (A's `counter_refs` names B, B's `counter_refs` names A,
neither ever backed by an actual T1/T2 source). Only T1/T2 sources — sources already vetted as
orthodox/own-tradition — may serve as a `counter_ref` target.

**Tightened per C1 re-review prep (2026-09-17):** the constraint above only closes the cycle if
T1/T2 records are *also* barred from carrying `counter_refs` themselves — otherwise "only T1/T2
may be a target" doesn't yet forbid a T1/T2 record from pointing back into T3. To remove that
residual ambiguity, this is now a normative rule, not just an implication of the field table:
**`counter_refs` is only a valid field on a `T3` record. A record with `authority_tier ∈ {T1,
T2, T4}` MUST NOT carry `counter_refs` at all** — enforced by §5's new V12 below. With T1/T2
barred from having any `counter_refs` of their own, and T3 allowed to point only at T1/T2
(never at T3 or T4), the reference graph has no edge leaving a T1/T2 node — a cycle is
structurally unreachable, not just discouraged.

## 4. `RegistrationRequest` / `pipeline.py` Changes (design only)

Mirrors the existing pattern in `NAE/pipeline/registration/pipeline.py`
exactly:

```python
@dataclass
class RegistrationRequest:
    ...
    # existing ADR-030 Amendment B fields unchanged
    content_genre: list[str] | None = None
    authority_class: str | None = None
    tradition: str | None = None
    theological_category: list[str] | None = None
    # NEW — this plan, pending ADR-030 Amendment D
    authority_tier: str | None = None
    tradition_relation: str | None = None
    counter_refs: list[str] | None = None
```

And in the manifest-entry assembly block (same file, ~line 189):

```python
    if request.authority_tier is not None:
        manifest_entry["authority_tier"] = request.authority_tier
    if request.tradition_relation is not None:
        manifest_entry["tradition_relation"] = request.tradition_relation
    if request.counter_refs is not None:
        manifest_entry["counter_refs"] = request.counter_refs
```

`manifest_writer.write_entry()` itself needs no change — it already writes
whatever keys `manifest_entry` contains (append-only, no schema
enforcement per the validator's own docstring: "M2 는 enforced schema file
이 없다").

## 5. Validator Changes (design only)

`scripts/m2_source_registry_validator.py` gains two checks, added the same
way `VALID_AUTHORITY_CLASSES` / `FORBIDDEN_AUTHORITY_VALUES` already work:

```python
VALID_AUTHORITY_TIERS = frozenset(["T1", "T2", "T3", "T4"])
VALID_TRADITION_RELATIONS = frozenset([
    "own", "allied", "other_christian", "non_christian", "heterodox",
])
```

- **V9** (new): `authority_tier` present but value ∉ 4-enum → FAIL.
- **V10** (new): `authority_tier = T3` present but `counter_refs` absent or
  empty → FAIL. This is the registry-level enforcement of the same rule
  `get_tier_disclosure()` already enforces at display time — two
  independent layers, matching the codebase's existing defense-in-depth
  style (see `citation_disclosure.py` docstring on this point).
- **V11** (new): every id in `counter_refs` must (a) resolve to an existing
  `source_id` in the same M2 registry — orphan reference check, same
  category as the "참조 무결성 검사" flagged as a Priority-2 follow-up in
  `NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md` §4.2 for the Author/Work/
  Edition registry — **and (b) point to a source whose own
  `authority_tier ∈ {T1, T2}`** (§3 constraint above, added per C1 Review
  question 5). (b) makes a `counter_ref` cycle structurally impossible: a
  T3 source can only cite T1/T2 sources, and T1/T2 sources carry no
  `counter_refs` of their own (§3 table — `counter_refs` is only required/
  meaningful for T3), so the reference graph cannot loop back.
- **V12** (new, tightened 2026-09-17): a record with `authority_tier ∈ {T1, T2, T4}` that
  nonetheless carries a non-empty `counter_refs` → FAIL. This is what actually makes V11(b)'s
  cycle-prevention argument hold — without it, "T3 may only point at T1/T2" restricts one
  direction of the graph but leaves T1/T2 free to point back into T3, which V11(b) alone does
  not forbid.
  Edition registry (this plan applies the same discipline to
  `counter_refs`).

`test_m2_source_registry_governance.py` gains matching `test_pos_08`
(tier vocab when present), `test_neg_09` (T3 without counter_refs fails),
`test_neg_10` (orphan counter_ref fails) — following the existing
pos/neg numbering convention in that file's docstring.

## 6. `corpus_admissions.jsonl` Decision Record

Tagging decisions are recorded the same way `authority_class` decisions are
today — as a line in `NAE/governance/corpus_admissions.jsonl`, decided by
HQ, with `rationale` and `evidence_refs`. Example (illustrative, not a real
admission):

```json
{"source_id": "BAP-CHURCH-DAGG-001", "decided_by": "David / HQ", "date": "2026-XX-XX", "authority_tier": "T2", "tradition_relation": "own", "rationale": "Own tradition (Particular Baptist), no doctrinal conflict with user's confessional standard.", "evidence_refs": ["docs/NAE_AUTHORITY_TIER_M2_TAGGING_IMPLEMENTATION_PLAN_001.md"]}
```

This keeps the tier decision auditable in exactly the place existing
`authority_class` decisions already live — no new log file, no parallel
registry (which ADR-030's own V1 check explicitly forbids).

## 7. Tagging Pipeline (7 steps, mirrors §4.1 of the Author/Work/Edition
plan reviewed in `NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md`)

```
1. Candidate generation (auto, non-binding)
   → For each M2 record missing authority_tier, propose a candidate tier
     from existing fields as a HINT ONLY:
       authority_class=primary_doctrinal AND tradition_relation=own → suggest T1/T2
       authority_class=historical_witness → suggest T2 (own) with a flag
         for human confirmation (per ADR-030 Amendment A, these already
         carry provenance caveats independent of doctrinal standing)
       tradition ∉ user's configured tradition list → suggest T3, block
         auto-write (counter_refs cannot be auto-generated)
   → Output: docs/reports/authority_tier_candidates_<date>.md (read-only
     suggestion list, never auto-committed)

2. Human review of candidates (HQ)
   → HQ confirms or overrides each candidate tier.

3. tradition_relation confirmation (HQ)
   → For T3 candidates specifically, HQ must also name the
     tradition_relation value explicitly (no default).

4. counter_ref linking (HQ, T3 only)
   → HQ selects ≥1 existing T1/T2 source_id as counter_ref. If no suitable
     T1/T2 rebuttal source exists yet in the corpus, the T3 source CANNOT
     be tagged — it stays untagged (defaults to T4-equivalent, i.e.
     excluded from normal retrieval) until a rebuttal source is admitted.

5. Registry write
   → RegistrationRequest carries the confirmed fields through the existing
     `register_source()` path (new admissions) OR a dedicated backfill
     script mirroring `manifest_writer.write_entry()`'s append-only
     contract (existing admissions — see §8).

6. Validator gate
   → `python scripts/m2_source_registry_validator.py` must exit 0
     (V9/V10/V11 all pass) before the write is considered complete.

7. corpus_admissions.jsonl entry
   → One line per tagged source_id, per §6 above. This is the audit trail
     step — required, not optional.
```

Steps 1 and 6 are fully automatable; steps 2-4 and 7 are HQ-only by design
(same human-in-the-loop split the reviewed Author/Work/Edition plan used
for its own 7-step pipeline — automation proposes, a human decides
anything that touches doctrinal judgment).

## 8. Backfill Scope (existing corpus)

Per `docs/STATE.md` (2026-09-15 entry), the production corpus is currently
1,363 TSU / effectively 1 admitted work at meaningful scale, plus the 3
`corpus_admissions.jsonl` entries shown in §6's example (Dagg, Hiscox,
Smith — all own-tradition/reference sources, none heterodox). **No existing
admitted source is expected to need T3** under this backfill — the pilot
should confirm that empirically rather than assume it. Recommended pilot:
tag exactly these 3 existing records first (Priority 1, low-risk, same
"small pilot before full rollout" discipline the reviewed Author/Work/
Edition plan used with the 2-work `church_order` pilot).

## 9. Migration & Rollback

| Step | Rollback method | Risk |
|---|---|---|
| §4 RegistrationRequest fields | Remove 3 new dataclass fields + their `if request.X is not None` blocks in `pipeline.py` — no data loss, new admissions simply stop carrying the fields | Low |
| §5 Validator checks V9-V11 | Revert validator script to pre-change version via git — no data mutation, validator is read-only | Low |
| §6 corpus_admissions.jsonl entries | Additive JSONL lines only — delete the specific lines to roll back, original `authority_class` decisions untouched | Low |
| §8 Backfill of 3 existing M2 records | `authority_tier`/`tradition_relation`/`counter_refs` keys removed from the 3 records — original 14-key (10 base + 4 ADR-030 Amendment B) shape restored exactly | Low |

All steps are physically additive (new optional keys, new JSONL lines) —
no RAW file, no existing M2 key, and no Retrieval Engine code path is
touched at any step. This matches the "PASS" rollback profile the C1
review gave the Author/Work/Edition plan (§6 of that review).

## 10. Risk Assessment

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | `tradition_relation=own` mis-tagged for a source that is actually heterodox (human error) | Medium | Step 2/3 require explicit HQ confirmation per source, no bulk auto-approve |
| R2 | T3 source with no available T2 counter_ref stalls tagging indefinitely | Low (by design) | This is the intended fail-closed behavior — an untagged T3 source simply stays excluded from normal retrieval scope, same as any other untagged source |
| R3 | Retrieval Engine changes needed to actually *use* `authority_tier` for scope filtering are a separate, larger change (proposal §13.2 steps ①-⑤) not covered by this plan | Medium | Explicitly out of scope here — flagged as required follow-up in §11 |
| R4 | Schema drift between `NAE/authority/source_manifest.yaml` (read-only mirror) and true M2 if the mirror-sync step is missed | Low | Existing mirror-sync mechanism (ADR-030 §8.3) already handles this for all M2 fields; no new mechanism needed |

## 11. Governance Gate — Required Before Implementation

Per CLAUDE.md CUE Operating Policy (Architecture Freeze Rule): ADR-030 is
Approved, and this plan proposes a **Metadata Model change** (new M2
fields). This requires, in order:

1. **ADR-030 Amendment D** (or a new ADR) formally documenting §3-§7 above,
   following the Amendment A/B precedent already in this repo.
2. **C1 Review** of both the Amendment and this Implementation Plan
   (mirrors `NAE_METADATA_AUTHORITY_PLAN_REVIEW_001.md`'s review of the
   Author/Work/Edition plan) — required per CLAUDE.md's explicit trigger
   list ("Metadata Model 변경").
3. **HQ approval** of the reviewed Amendment.

Only after all three are satisfied does this plan enter the "4개 조건"
promotion path (구현 완료 / 회귀 테스트 통과 / C1 리뷰 / 사용자 승인) that
lets it become Approved. **No code in §4/§5/§6 should be written before
step 1-3 above are complete.** This document is the design artifact for
that process — it is not itself an implementation.

## 12. Open Questions for HQ

- Should `tradition_relation=own` require an exact string match against a
  single configured "my tradition" value, or a small allow-list (e.g. both
  `Particular Baptist` and a broader `Reformed Baptist` bucket)? The
  proposal's §11.2 used fixed codes (`reformed`, `baptist`, ...); the real
  `tradition` field in production is free text (`"Particular Baptist"`).
  This plan defers that decision to the Amendment, not to this plan.
- Does a `historical_witness` source (provenance-caveated but not
  doctrinally suspect) default-suggest T2, or should it always require
  explicit human tiering with no auto-suggestion at all? §7 step 1 above
  proposes the former as a hint only, never an auto-write.

---

**End of Plan 001. Awaiting ADR-030 Amendment D draft + C1 Review before any
implementation step.**
