# Stage A — Metadata Preflight Decision

**Directive:** HQ-C1-DIRECTIVE-NAE-PBC1765-ACQUIRE-008
**Date:** 2026-08-01
**Source ID:** PBC1765 (legacy: PBC1742)
**Expected Identifier:** plainbookofconfe00phil

## Preflight Check Results

| # | Condition | Expected | Actual | Result | Evidence Path |
|---|-----------|----------|--------|--------|---------------|
| 1 | HTTP status = 200 | 200 | Item page: 404, Metadata API: 200+{} | **FAIL** | stage-a-metadata-response.json (item_page_response.http_status=404) |
| 2 | Identifier matches `plainbookofconfe00phil` | plainbookofconfe00phil | Item does not exist at this identifier | **FAIL** | stage-a-metadata-request.txt (Request 1: HTTP 404; Request 2: empty body {}) |
| 3 | Title matches "The Baptist Confession of Faith" | Match | Cannot verify — no item found | **UNVERIFIED** | stage-a-metadata-response.json (openlibrary_response) |
| 4 | Philadelphia + 1765 manifestation confirmed | Confirmed | No 1765 manifestation found anywhere | **FAIL** | stage-a-metadata-request.txt (Request 6: Open Library closest=1743, not 1765) |
| 5 | Public domain or accessible | Yes | Cannot verify — no item found | **UNVERIFIED** | stage-a-metadata-response.json (registry_check.PBC1765_found=false) |
| 6 | PDF or OCR/DjVu text derivative exists | Exists | Cannot verify — no item found | **FAIL** | stage-a-metadata-response.json (metadata_api_response.body={}) |
| 7 | Not error/access-denied/borrow-only/viewer-only | Available | Item does not exist (404) | **FAIL** | stage-a-metadata-request.txt (Request 1: HTTP 404) |

## Preflight Summary

- Condition 1 (HTTP 200): **FAIL** — Item page returns 404
- Condition 2 (Identifier match): **FAIL** — plainbookofconfe00phil does not resolve to any item
- Condition 3 (Title identity): **UNVERIFIED** — No item to inspect
- Condition 4 (Philadelphia 1765): **FAIL** — No manifestation found on IA or Open Library
- Condition 5 (Public domain): **UNVERIFIED** — No item exists to check rights
- Condition 6 (PDF/OCR derivative): **FAIL** — No files inventory available
- Condition 7 (Not restricted): **FAIL** — Item does not exist

## Preflight Decision: FAILED

**Exact reason:** The expected Internet Archive identifier `plainbookofconfe00phil` does not resolve to any existing item. The metadata API returns an empty JSON object `{}` and the item page returns HTTP 404. No alternative identifier matching "The Baptist Confession of Faith" + "Philadelphia" + "1765" was found on Internet Archive or Open Library.

**Stage B executed:** NO

## Alternative Findings

Open Library found related Philadelphia Baptist confession works, but none match the expected 1765 manifestation:
- OL997746W: "A confession of faith" (1743) — closest year but not 1765
- OL27760574W: "The Philadelphia confession of faith" (1900) — title match but wrong year

Source registry (`source_candidates.csv`) contains PBC1742 but NOT PBC1765. The canonical ID PBC1765 may be incorrect or the item may have been removed/renamed on Internet Archive.

## HQ Decision Requested

**Option C:** Reject PBC1765 candidate and correct registry identifier
**Option D:** Escalate bibliographic or rights ambiguity to HQ

The identifier `plainbookofconfe00phil` should be verified against the actual Internet Archive catalog before proceeding. The legacy ID `PBC1742` exists in the registry but its Internet Archive item URL needs confirmation.