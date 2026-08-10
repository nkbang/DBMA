# Candidate B — TH1612 Download Specification

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**Mode:** Read-only bibliographic investigation  
**Date:** 2026-08-01  

---

## 1. Bibliographic Identity

| Field | Value | Evidence Basis |
|---|---|---|
| canonical_source_id | TH1612 | HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007 §3 |
| legacy_source_id | TH1612 | source_candidates.csv (same as canonical) |
| canonical author | Thomas Helwys (d. ~1616) | Historical record: first Baptist theologian in England |
| canonical title | A Short Declaration of the Mystery of Iniquity, Containing the Seed of all Pharisaical Hypocrisies | EEBO-TCP, Internet Archive, CCEL catalog entries |
| original publication year | 1612 (some sources say 1611) | First Baptist tract in English; historical consensus |
| digital manifestation target | EEPO-TCP text or Internet Archive scan | Repository-dependent |

**HQ DECISION REQUIRED:** NO — bibliographic identity is historically established and universally attributed to Thomas Helwys.

---

## 2. Repository and Stable Identifier

### Primary Candidate: Internet Archive

| Field | Value | Verification Status |
|---|---|---|
| repository | Internet Archive (archive.org) | PARTIAL — item likely exists but not fully inspected |
| stable identifier | `shortdeclarationofm00helw` or similar (needs catalog confirmation) | UNVERIFIED |
| catalog URL | https://archive.org/search?query=Helwys+Short+Declaration | PARTIAL — search URL only; specific item ID needs confirmation |
| access URL | TBD — depends on stable identifier | UNVERIFIED |

### Secondary Candidate: EEBO2 (Early English Books Online, 2nd edition) / University of Michigan Digital Collections

| Field | Value | Verification Status |
|---|---|---|
| repository | University of Michigan Deep Green II / EEBO-TCP | PARTIAL — EEBO-TCP record exists |
| stable identifier | `A02915.0001.001` (EEBO-TCP number) | PARTIAL — TCP number format verified, item content not inspected |
| catalog URL | https://name.umdl.umich.edu/ A02915.0001.001 | PARTIAL — URL structure matches UM Digital Collections convention |
| access URL | https://name.umdl.umich.edu/A02915.0001.001 | Same as catalog |

### Tertiary Candidate: CCEL (Christian Classics Ethereal Library)

| Field | Value | Verification Status |
|---|---|---|
| repository | CCEL (ccel.org) | PARTIAL — CCEL hosts Helwys works |
| stable identifier | `helwys/declaration` (path-based, not formal PID) | UNVERIFIED |
| catalog URL | https://www.ccel.org/ccel/helwys/declaration.html | PARTIAL — URL structure matches CCEL convention |
| access URL | Same as catalog (HTML-only) | UNVERIFIED |

**HQ DECISION REQUIRED:** YES — repository priority needs HQ decision:
- Internet Archive may have scan PDF derivative
- University of Michigan EEBO2 provides verified TCP text but access restrictions may apply
- CCEL provides HTML-only free access but format priority is lowest (per §7)

---

## 3. Rights Basis

| Field | Value |
|---|---|
| original publication year | 1612 |
| author death year | ~1616 |
| US copyright status | Public Domain — well beyond life+70 threshold |
| EEBO2 access restrictions | May require institutional subscription for full text |
| CCEL access | Free access, public domain |
| rights_basis | Public Domain (original); repository access terms may vary |

---

## 4. Available Derivatives (Repository Inspection)

### Internet Archive (if item exists with derivatives):

| Derivative type | Expected filename pattern | Format | MIME type | Priority |
|---|---|---|---|---|
| Scan PDF with OCR | `shortdeclarationofm00helw.pdf` | PDF | application/pdf | 1 (preferred) |
| OCR text (DjVu) | `shortdeclarationofm00helw_djvu.txt` | UTF-8 text | text/plain | 3 |
| EPUB | `shortdeclarationofm00helw.epub` | EPUB | application/epub+zip | 5 |

### University of Michigan EEBO2:

| Derivative type | Expected format | MIME type | Priority |
|---|---|---|---|
| TCP XML text | XML (TEI-encoded) | application/xml | 4 |
| HTML viewer page | HTML | text/html | 6 (fallback, HTML-only source) |

### CCEL:

| Derivative type | Expected format | MIME type | Priority |
|---|---|---|---|
| HTML text | HTML | text/html | 6 (HTML-only — last resort) |

**Preferred derivative:** Internet Archive scan PDF with OCR layer — IF available.

**Fallback priority:**
1. Internet Archive scan PDF (if item exists with PDF derivative)
2. University of Michigan EEBO2 TCP XML (if access available)
3. CCEL HTML (only if no other option — HTML-only source)

---

## 5. Selected Derivative (Conditional)

### Primary selection (Internet Archive, if PDF available):

| Field | Value |
|---|---|
| selected filename | `<IA_ITEM_ID>.pdf` (exact item ID TBD) |
| expected MIME type | application/pdf |
| minimum size threshold | 300,000 bytes (300 KB) — short work, smaller than PBC1765 |
| download URL | https://archive.org/download/<IA_ITEM_ID>/<IA_ITEM_ID>.pdf |

### Secondary selection (University of Michigan EEBO2):

| Field | Value |
|---|---|
| selected filename | `A02915.0001.001.xml` (TCP XML) |
| expected MIME type | application/xml |
| minimum size threshold | 50,000 bytes (50 KB) — TCP text is compact |
| access URL | https://name.umdl.umich.edu/A02915.0001.001 |

---

## 6. Identity Validation Markers

| Marker type | Expected content | Purpose |
|---|---|---|
| title-page marker | "A Short Declaration of the Mystery of Iniquity" OR "Containing the Seed of all Pharisaical Hypocrisies" | Confirms correct work identity |
| author marker | "Thomas Helwys" or "T.H." (common for early 17th c. printing) | Confirms authorship |
| publication marker | "1612" or "1611" appearing in imprint/title page | Confirms edition |

---

## 7. Error-Page Detection Rule (Source-Specific)

### For Internet Archive derivative:
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. Response Content-Type contains text/html when PDF expected
3. PDF file size < 300,000 bytes
4. PDF does not contain title-page marker: "Short Declaration" AND "Mystery of Iniquity"
5. PDF does not contain author marker: "Helwys" OR "T.H."
6. PDF is Internet Archive error page (check for IA error template patterns)
7. Redirect destination stable identifier != expected IA item ID
8. IA item metadata shows "Full View" = false (access restricted)
```

### For University of Michigan EEBO2:
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. Response Content-Type is text/html when XML expected
3. XML file size < 50,000 bytes
4. XML does not contain TEI header with title "A Short Declaration"
5. XML does not contain author "Helwys" OR "Thomas"
6. Page shows login/subscription wall
7. Page shows "not found" or "access denied"
```

### For CCEL (HTML-only fallback):
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. HTML does not contain title-page marker: "Short Declaration" AND "Mystery of Iniquity"
3. HTML does not contain author marker: "Helwys"
4. HTML shows CCEL error or loading failure
5. HTML is empty or contains only navigation chrome without content
```

---

## 8. Status

| Field | Value |
|---|---|
| bibliographic_status | VERIFIED (historically established) |
| stable_id_status | PARTIAL (multiple candidates across repositories; exact IA item ID needs confirmation) |
| derivative_status | UNVERIFIED (derivative availability depends on repository; IA PDF uncertain, EEBO2 XML possible, CCEL HTML confirmed as format but not content verified) |
| rights_status | VERIFIED (PD by publication date); repository access terms TBD |
| download_status | NOT AUTHORIZED |
| HQ decision required | YES — repository and derivative priority needs HQ decision |

---

## 9. Remaining Uncertainty

- Internet Archive item stable identifier not confirmed — search results needed
- Internet Archive PDF derivative availability not confirmed
- University of Michigan EEBO2 access terms (subscription vs. open) not confirmed
- CCEL HTML content verified as Helwys work? Not confirmed without loading the page
- Original publication year: 1611 vs. 1612 discrepancy needs catalog confirmation
- If IA PDF unavailable and EEBO2 requires subscription, CCEL HTML may be only free option — triggers HTML adapter design requirement