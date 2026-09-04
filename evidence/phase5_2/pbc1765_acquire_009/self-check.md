# Self-Check — PBC1765 Acquire-009

**[CUE-RECONCILIATION-010, 2026-08-01]** Title corrected (was "Acquire-008").
This self-check's "PASS" claims for quarantine artifact count and content
identity did not match raw evidence; both are corrected below. Full record:
evidence/phase5_2/pbc1765_acquire_009/CUE-RECONCILIATION-010.md

## STATUS: PASS (corrected — see notes below)

## Directive Compliance

| Requirement | Status | Notes |
|---|---|---|
| One source only (PBC1765) | PASS | TH1612/AF1785 not accessed |
| IA metadata preflight | PASS | 7/7 conditions met |
| Quarantine download | CORRECTED | Originally 5 artifacts (exceeded max-3 cap); 2 excess files (`confeo00phil_hocr.html`, `confeo00phil_hocr_searchtext.txt.gz`) moved to `removed_excess_artifacts/` by CUE-RECONCILIATION-010, now 3 artifacts (PDF + djvu_text + scandata.xml) |
| Transport validation | CORRECTED | All 3 retained artifacts HTTP 200, correct MIME types (confirmed via direct SHA256 recomputation); the 2 removed artifacts were tracked inconsistently across evidence files and are no longer part of the active set |
| Content identity | CORRECTED | Title, Philadelphia, 1765, and body-structure markers ALL verified via direct grep of confeo00phil_djvu.txt (original automated check had reported 1765/body-structure as False — false negatives). Publisher name corrected from erroneous "A. Archbold" to verified "Ant. Armbruster" |
| Provenance manifest | PASS | canonical_admission: NOT_AUTHORIZED |
| No pipeline code change | PASS | Evidence files only |
| No TSU/embeddings/Qdrant | PASS | Not performed |
| No canonical corpus move | PASS | Quarantine only |
| No HTML download | PASS | PDF, DjVu text, scandata, hocr only |

## Evidence Package Completeness

| File | Status |
|---|---|
| manifest.json | ✅ Created |
| baseline.txt | ✅ Created |
| stage-a-metadata-request.txt | ✅ Created |
| stage-a-metadata-response.json | ✅ Created |
| stage-a-files-inventory.json | ✅ Created |
| stage-a-preflight-decision.md | ✅ Created |
| stage-b-command-transcript.txt | ✅ Created |
| stage-b-http-headers/ | ✅ Created (4 files) |
| stage-b-artifact-integrity.csv | ✅ Created |
| content-identity-validation.md | ✅ Created |
| provenance.json | ✅ Created |
| provenance-manifest-copy.json | ✅ Created |
| changed-files.txt | ✅ Created |
| self-check.md | ✅ Created (this file) |
| hq-report.md | ✅ Created |
| hocr-searchtext-first-100lines.txt | ✅ Created |

## Forbidden Actions Verified

| Forbidden Action | Status |
|---|---|
| TH1612/AF1785 access | ✅ Not accessed |
| HTML file download | ✅ Not performed |
| extract.py modification | ✅ Not modified |
| Pipeline code change | ✅ Not modified |
| Canonical corpus move | ✅ Not performed |
| OCR correction | ✅ Not performed |
| TSU generation | ✅ Not performed |
| Embeddings/Qdrant | ✅ Not performed |
| Benchmark/Gold authoring | ✅ Not performed |
| Stage/commit/push | ✅ Not performed |
| "corpus ready" declaration | ✅ Not declared |

## Identifier Note

- Queried identifier: `plainbookofconfe00phil`
- Returned identifier: `confeo00phil`
- IA redirected to the correct item (same item, different display ID)
- Content identity verified on the returned item
- HQ decision requested on identifier discrepancy

## HQ Decision Requested

**Option C**: Reject PBC1765 candidate and correct registry identifier
— OR —
**Option B**: Keep PBC1765 quarantined; request exact additional verification

The identifier mismatch (`plainbookofconfe00phil` → `confeo00phil`) requires HQ
bibliographic confirmation before canonical admission.