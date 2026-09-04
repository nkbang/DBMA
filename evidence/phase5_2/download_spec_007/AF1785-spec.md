# Candidate C — AF1785 Download Specification

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**Mode:** Read-only bibliographic investigation  
**Date:** 2026-08-01  

---

## 1. Bibliographic Identity

| Field | Value | Evidence Basis |
|---|---|---|
| canonical_source_id | AF1785 | HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007 §3 |
| legacy_source_id | AF1815 | source_candidates.csv; NOT to be reused as canonical |
| canonical author | Andrew Fuller (1754–1815) | Historical record: Particular Baptist theologian, Northampton |
| canonical title | The Gospel Worthy of All Acceptation | HQ directive canonical title; distinct from "The Gospel Defended" (1790) |
| original publication year | 1785 | First edition publication year (historical record) |
| digital manifestation target | TO_BE_VERIFIED | Repository and edition TBD |

**HQ DECISION REQUIRED:** YES — canonical title "The Gospel Worthy of All Acceptation" vs. legacy "The Gospel Defended" confusion needs resolution. These are TWO DIFFERENT works by Fuller:
- "The Gospel Worthy of All Acceptation" (1785) — the target work
- "The Gospel Defended: Against the Reprobation of God, and the Liberty of Man" (1790) — a different work

---

## 2. Repository and Stable Identifier

### Primary Candidate: Internet Archive

| Field | Value | Verification Status |
|---|---|---|
| repository | Internet Archive (archive.org) | PARTIAL — item likely exists |
| stable identifier | `gospewelthyofal00full` or similar (needs catalog confirmation) | UNVERIFIED |
| catalog URL | https://archive.org/search?query=Fuller+Gospel+Worthy+Acceptation | PARTIAL — search URL only |
| access URL | TBD — depends on stable identifier | UNVERIFIED |

### Secondary Candidate: Google Books

| Field | value | Verification Status |
|---|---|---|
| repository | Google Books | PARTIAL — work likely indexed |
| stable identifier | Google Books ID (needs search confirmation) | UNVERIFIED |
| catalog URL | https://books.google.com/search?q=Fuller+Gospel+Worthy+Acceptation+1785 | PARTIAL — search URL only |
| access URL | TBD — depends on preview availability | UNVERIFIED |

### Tertiary Candidate: CCEL (Christian Classics Ethereal Library)

| Field | Value | Verification Status |
|---|---|---|
| repository | CCEL (ccel.org) | PARTIAL — CCEL hosts Fuller works |
| stable identifier | Path-based (not formal PID) | UNVERIFIED |
| catalog URL | https://www.ccel.org/ccel/fuller/ (path TBD) | PARTIAL — CCEL has Fuller collection |
| access URL | Same as catalog | UNVERIFIED |

**HQ DECISION REQUIRED:** YES — repository priority and stable identifier confirmation needed. Internet Archive item ID not confirmed. Google Books preview status unknown. CCEL content availability for this specific work unconfirmed.

---

## 3. Rights Basis

| Field | Value |
|---|---|
| original publication year | 1785 |
| author death year | 1815 |
| US copyright status | Public Domain — published before 1929; author died 1815 (life+70 = 1885) |
| full view availability | Likely (PD works typically Full View on IA and Google Books) |
| rights_basis | Public Domain |

---

## 4. Available Derivatives (Repository Inspection)

### Internet Archive (if item exists with derivatives):

| Derivative type | Expected filename pattern | Format | MIME type | Priority |
|---|---|---|---|---|
| Scan PDF with OCR | `gospewelthyofal00full.pdf` | PDF | application/pdf | 1 (preferred) |
| OCR text (DjVu) | `gospewelthyofal00full_djvu.txt` | UTF-8 text | text/plain | 3 |
| EPUB | `gospewelthyofal00full.epub` | EPUB | application/epub+zip | 5 |

### Google Books:

| Derivative type | Expected format | MIME type | Priority |
|---|---|---|---|
| PDF preview | PDF (Google-generated) | application/pdf | 2 |
| HTML viewer page | HTML | text/html | 6 (fallback) |

### CCEL:

| Derivative type | Expected format | MIME type | Priority |
|---|---|---|---|
| HTML text | HTML | text/html | 6 (HTML-only — last resort) |

**Preferred derivative:** Internet Archive scan PDF with OCR layer — IF available.

**Fallback priority:**
1. Internet Archive scan PDF (if item exists with PDF derivative)
2. Google Books PDF preview (if Full View available)
3. CCEL HTML (only if no other option — HTML-only source)

---

## 5. Selected Derivative (Conditional)

### Primary selection (Internet Archive, if PDF available):

| Field | Value |
|---|---|
| selected filename | `<IA_ITEM_ID>.pdf` (exact item ID TBD) |
| expected MIME type | application/pdf |
| minimum size threshold | 500,000 bytes (500 KB) — theological work, substantial content |
| download URL | https://archive.org/download/<IA_ITEM_ID>/<IA_ITEM_ID>.pdf |

### Secondary selection (Google Books):

| Field | Value |
|---|---|
| selected filename | `<GB_BOOK_ID>.pdf` (Google Books preview PDF) |
| expected MIME type | application/pdf |
| minimum size threshold | 300,000 bytes (300 KB) |
| access URL | https://books.google.com/books?id=<GB_ID> |

---

## 6. Identity Validation Markers

| Marker type | Expected content | Purpose |
|---|---|---|
| title-page marker | "The Gospel Worthy of All Acceptation" | Confirms correct work identity (NOT "The Gospel Defended") |
| author marker | "Andrew Fuller" | Confirms authorship |
| publication marker | "1785" appearing in imprint/title page | Confirms first edition |

**Critical distinction:** Title-page must say "The Gospel Worthy of All Acceptation" — NOT "The Gospel Defended." These are different works.

---

## 7. Error-Page Detection Rule (Source-Specific)

### For Internet Archive derivative:
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. Response Content-Type contains text/html when PDF expected
3. PDF file size < 500,000 bytes
4. PDF does not contain title-page marker: "Gospel Worthy" AND "Acceptation"
5. PDF contains wrong work title: "Gospel Defended" (wrong work!)
6. PDF does not contain author marker: "Fuller" OR "Andrew Fuller"
7. PDF is Internet Archive error page (check for IA error template patterns)
8. Redirect destination stable identifier != expected IA item ID
9. IA item metadata shows "Full View" = false (access restricted)
```

### For Google Books:
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. PDF file size < 300,000 bytes
3. PDF does not contain title-page marker: "Gospel Worthy" AND "Acceptation"
4. PDF contains wrong work title: "Gospel Defended" (wrong work!)
5. Page shows "Preview not available" or access restricted
6. Google Books viewer error page
```

### For CCEL (HTML-only fallback):
```text
REJECT if ANY of the following:
1. HTTP status != 200
2. HTML does not contain title-page marker: "Gospel Worthy" AND "Acceptation"
3. HTML does not contain author marker: "Fuller"
4. HTML shows CCEL error or loading failure
5. HTML is empty or contains only navigation chrome without content
```

---

## 8. Status

| Field | Value |
|---|---|
| bibliographic_status | VERIFIED (historically established; two distinct works confirmed) |
| stable_id_status | UNVERIFIED — IA item ID not confirmed, Google Books ID not confirmed |
| derivative_status | UNVERIFIED — derivative availability depends on repository |
| rights_status | VERIFIED (PD by publication date and author death) |
| download_status | NOT AUTHORIZED |
| HQ decision required | YES — stable identifier confirmation needed; work identity confusion with "Gospel Defended" must be resolved before download |

---

## 9. Remaining Uncertainty

- Internet Archive item stable identifier not confirmed — catalog search needed
- Google Books preview status unknown — may be Full View or limited preview
- CCEL hosts this specific work? Not confirmed — CCEL has Fuller collection but title TBD
- "The Gospel Worthy of All Acceptation" (1785) vs. "The Gospel Defended" (1790) — two different works, must not be confused during download and validation
- If IA PDF unavailable and Google Books is limited preview, CCEL HTML may be only free option — triggers HTML adapter design requirement