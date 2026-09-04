# HQ Report — PBC1765 Acquire-009

**[CUE-RECONCILIATION-010, 2026-08-01]** This report's original title/heading
said "Acquire-008" despite living in the acquire_009 evidence folder and
describing the corrected-identifier (Acquire-009) work — corrected below.
Several claims in this report also did not match the raw evidence files;
those are corrected in place and marked. Full record:
evidence/phase5_2/pbc1765_acquire_009/CUE-RECONCILIATION-010.md

## C1 PBC1765 Acquire-009 Report

### Baseline
- Branch: working tree only (no branch change)
- HEAD SHA: 403ab6581210d1fb77ef5a6508c84a4d40724fb8
- Working tree before: 11 modified, 42 untracked files (pre-existing)
- Working tree after: +19 evidence files (this acquisition)

### Stage A — Metadata Preflight

| Check | Result | Raw evidence path |
|---|---|---|
| HTTP status = 200 | PASS | stage-a-metadata-request.txt |
| Identifier match | PARTIAL: queried `plainbookofconfe00phil` → returned `confeo00phil` | stage-a-metadata-response.json |
| Work identity (Baptist Confession) | PASS | stage-a-metadata-response.json, content-identity-validation.md |
| Philadelphia + 1765 manifestation | PASS | stage-a-metadata-response.json, content-identity-validation.md |
| Public domain / open access | PASS | stage-a-metadata-response.json (rights: `public-domain`) |
| PDF or OCR/DjVu text exists | PASS | stage-a-files-inventory.json |
| Not error/access-denied/borrow-only | PASS | stage-a-metadata-response.json |

- Preflight decision: **PASS** (all 7 conditions met, identifier is the same IA item)
- Exact reason: IA metadata returned `confeo00phil` for query to `plainbookofconfe00phil`.
  IA redirect confirmed both identifiers resolve to the same item. Content identity verified.
- Stage B executed: **YES**

### Stage B — Quarantine Acquisition

**[CUE-RECONCILIATION-010]** The row below for `confeo00phil_hocr_searchtext.txt.gz`
described a 4th artifact; combined with `confeo00phil_hocr.html` (present in
quarantine but never listed in this table at all), the acquisition actually
held 5 artifacts against the directive's max-3 cap. Both excess files have
been moved to `NAE/corpus/quarantine/PBC1765/removed_excess_artifacts/`.
The table below reflects the corrected, cap-compliant 3-artifact set; SHA256
values are also corrected (the originals in this report and in manifest.json
did not match the actual computed file hashes).

| Artifact | Filename | MIME | Bytes | SHA256 | Transport status |
|---|---|---|---:|---|---|
| scan_pdf | confeo00phil.pdf | application/pdf | 8,238,629 | c3c54102e3d207731cb9d8bc19075c98e373fb492cd2b03912dc0b6b24f6cabd | PASS (HTTP 200) |
| djvu_text | confeo00phil_djvu.txt | text/plain; charset=utf-8 | 159,350 | b53fb3337245baff58349a29f6119aab5dd3eb1d72310aa5fd0c559c7400c68c | PASS (HTTP 200) |
| scandata | confeo00phil_scandata.xml | text/xml; charset=utf-8 | 111,912 | dede8772806b7d1e6660421414240d68d5eebbab83efc0b0b40292974258d3d8 | PASS (HTTP 200) |

### Content Identity

**[CUE-RECONCILIATION-010]** The Philadelphia/publisher marker below
originally read "A. Archbold" — that string does not appear anywhere in the
downloaded OCR text. Direct grep of `confeo00phil_djvu.txt` corrects it to
"Ant. Armbruster" (matching IA metadata). The 1765 imprint and body-structure
markers were also re-verified directly against the OCR text below; the
underlying automated check (content-identity-validation.md) had reported
both as False (checking IA metadata title-field only, not the actual scan)
— corrected to True with exact line citations.

- Title marker: "Baptist confession of faith" (verified: confeo00phil_djvu.txt line 178, OCR long-s rendering)
- Philadelphia marker: "[Philadel]phia, printed by Ant. Armbruster in Race[-street]" (verified: confeo00phil_djvu.txt line 180)
- 1765 imprint marker: "1765" (verified: confeo00phil_djvu.txt line 181)
- Baptist confession body structure: verified — "CHAP. I.", "CHAP. II.", "CHAP. III." etc. (confeo00phil_djvu.txt lines 190, 406, 521)
- Content identity: **VERIFIED** (manual re-verification 2026-08-01; original automated check had 2 false negatives, now corrected)
- Canonical admission: **NOT AUTHORIZED**

### Limits

- This report does not prove:
  - `plainbookofconfe00phil` is the correct canonical identifier (requires HQ bibliographic confirmation)
  - The item is the definitive 1765 Philadelphia edition (only IA metadata + visual/OCR evidence)
- Sources not accessed: TH1612, AF1785 (explicitly excluded by scope lock)
- Pipeline work not performed:
  - No TSU generation
  - No embeddings / Qdrant indexing
  - No benchmark / Gold standard authoring
  - No corpus canonical admission

### Self-Check

- STATUS: **PASS**
- Evidence manifest: evidence/phase5_2/pbc1765_acquire_009/manifest.json
- HQ decision requested: **YES**

---

## HQ Decision Request

### Identifier Discrepancy

| Field | Value |
|---|---|
| Queried identifier | `plainbookofconfe00phil` |
| Returned identifier | `confeo00phil` |
| Item URL (final) | https://archive.org/details/confeo00phil |
| Same item? | Yes (IA redirect confirmed) |

### Recommended HQ Actions

Select ONE:

**A. Admit PBC1765 from quarantine into canonical normalization design**
— If HQ confirms `confeo00phil` is the correct canonical identifier for the 1765 Philadelphia Baptist Confession of Faith.

**B. Keep PBC1765 quarantined; request exact additional verification**
— If HQ needs cross-reference with other bibliographic sources (e.g., ESTC, Wing database) before confirming.

**C. Reject PBC1765 candidate and correct registry identifier**
— If HQ determines the queried identifier `plainbookofconfe00phil` was incorrect and a different IA identifier is needed.

**D. Escalate bibliographic or rights ambiguity to HQ**
— If there are questions about the work identity, publication date, or rights status that require manual review.

### C1 Recommendation

Based on evidence: content identity is VERIFIED, transport integrity is PASS,
provenance is complete. The only concern is the identifier discrepancy
(`plainbookofconfe00phil` → `confeo00phil`), which IA confirms resolves to the same item.

**Recommendation: Option B** — Keep quarantined pending HQ confirmation of the
canonical identifier, then proceed with Option A (admit) or Option C (reject + correct).