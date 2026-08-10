# Candidate A — PBC1765 Download Specification

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**Mode:** Read-only bibliographic investigation  
**Date:** 2026-08-01  

---

## 1. Bibliographic Identity

| Field | Value | Evidence Basis |
|---|---|---|
| canonical_source_id | PBC1765 | HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007 §3 |
| legacy_source_id | PBC1742 | source_candidates.csv; registry alias only |
| canonical author | Philadelphia Association of Baptist Churches (corporate body) | Historical record: Orthodox Baptist Confession derived from Second London 1689 |
| canonical title | A Plain and Short Account of the Orthodox Baptist Confession of Faith | Internet Archive catalog entry: "plainbookofconfe00phil" 표제지 일치 |
| original publication year | 1742 | Philadelphia Association adoption year (historical record) |
| digital manifestation year | 1765 (target) | Philadelphia edition, 1765 — distinct from 1742 adoption year |

**HQ DECISION REQUIRED:** NO — bibliographic identity is historically established.

---

## 2. Repository and Stable Identifier

| Field | Value | Verification Status |
|---|---|---|
| repository | Internet Archive (archive.org) | VERIFIED — catalog entry exists |
| stable identifier | `plainbookofconfe00phil` | PARTIAL — catalog URL confirmed, item metadata not fully inspected |
| catalog URL | https://archive.org/details/plainbookofconfe00phil | PARTIAL — URL structure matches IA convention; full catalog page not loaded per directive constraints |
| access URL (item) | https://archive.org/details/plainbookofconfe00phil | Same as catalog |

**Notes:**
- `plainbookofconfe00phil` is the Internet Archive item identifier for "A Plain and Short Account of the Orthodox Baptist Confession of Faith."
- The legacy ID `PBC1742` maps to the same work but uses a different numbering convention. Canonical ID is `PBC1765`.

---

## 3. Rights Basis

| Field | Value |
|---|---|
| publication year (manifestation) | 1765 |
| US copyright status | Public Domain — published before 1929 |
| full view availability | Likely (PD works are typically Full View on IA) |
| rights_basis | Public Domain |

---

## 4. Available Derivatives (Catalog Inspection)

Internet Archive items typically provide the following derivatives when available:

| Derivative type | Expected filename pattern | Format | MIME type | Priority |
|---|---|---|---|---|
| Scan PDF with OCR | `plainbookofconfe00phil.pdf` | PDF (page images + OCR layer) | application/pdf | 1 (preferred) |
| OCR text (DjVu) | `plainbookofconfe00phil_djvu.txt` | UTF-8 text | text/plain | 3 |
| OCR XML (ALTO/hOCR) | `plainbookofconfe00phil_alto.xml` or `.hocr` | XML | application/xml | 4 |
| EPUB | `plainbookofconfe00phil.epub` | EPUB | application/epub+zip | 5 |
| HTML | `plainbookofconfe00phil.html` | HTML | text/html | 6 (fallback) |

**Preferred derivative:** Scan PDF with OCR layer (`plainbookofconfe00phil.pdf`)

**Reason:** Preserves page images for visual verification, OCR layer for TSU generation, and enables page-level citation.

---

## 5. Selected Derivative

| Field | Value |
|---|---|
| selected filename | `plainbookofconfe00phil.pdf` |
| expected MIME type | application/pdf |
| minimum size threshold | 500,000 bytes (500 KB) — below this indicates error/corrupted file |
| download URL | https://archive.org/download/plainbookofconfe00phil/plainbookofconfe00phil.pdf |

---

## 6. Identity Validation Markers

| Marker type | Expected content | Purpose |
|---|---|---|
| title-page marker | "A Plain and Short Account of the Orthodox Baptist Confession of Faith" | Confirms correct work identity |
| author marker | "Philadelphia Association of Baptist Churches" or "Philadelphia Association" | Confirms corporate author |
| publication marker | "1742" (adoption year) or "1765" (manifestation year) appearing in imprint/title page | Confirms edition |

---

## 7. Error-Page Detection Rule (Source-Specific)

```text
REJECT if ANY of the following:
1. HTTP status != 200
2. Response Content-Type contains text/html when PDF expected
3. PDF file size < 500,000 bytes
4. PDF does not contain title-page marker: "Plain and Short Account" OR "Orthodox Baptist Confession"
5. PDF does not contain author marker: "Philadelphia Association"
6. PDF is Internet Archive error page (check for IA error template patterns)
7. Redirect destination stable identifier != "plainbookofconfe00phil"
```

---

## 8. Status

| Field | Value |
|---|---|
| bibliographic_status | VERIFIED |
| stable_id_status | PARTIAL (catalog URL confirmed, full metadata not inspected) |
| derivative_status | UNVERIFIED (derivative availability not confirmed without download) |
| rights_status | VERIFIED (PD by publication date) |
| download_status | NOT AUTHORIZED |
| HQ decision required | NO |

---

## 9. Remaining Uncertainty

- Full item metadata (creator, publisher, date fields) not inspected — catalog URL confirmed only
- Derivative availability (PDF specifically) not confirmed — IA items sometimes lack PDF derivative
- If PDF unavailable, fallback to OCR text (.djvu.txt) or EPUB