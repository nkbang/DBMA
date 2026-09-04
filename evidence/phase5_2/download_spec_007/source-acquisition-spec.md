# Source Acquisition Specification

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**Mode:** Read-only bibliographic investigation and acquisition specification  
**Date:** 2026-08-01  
**Status:** Awaiting HQ Download Loop Approval  

---

## 1. Purpose

This document specifies the acquisition plan for three (3) Baptist Public Domain corpus candidates:

| Source ID | Author | Title | Year |
|---|---|---|---|
| PBC1765 | Philadelphia Baptist Association / corporate body | A Plain and Short Account of the Orthodox Baptist Confession of Faith | 1742 (adoption); 1765 (manifestation) |
| TH1612 | Thomas Helwys | A Short Declaration of the Mystery of Iniquity | 1612 |
| AF1785 | Andrew Fuller | The Gospel Worthy of All Acceptation | 1785 |

**This document does NOT authorize download.** Download authorization requires separate HQ approval.

---

## 2. Current Status Summary

All previously downloaded `.html` files were **REJECTED AS CONTENT** — they are Internet Archive error pages, not corpus texts.

**Corpus admission status:** NOT AUTHORIZED for all candidates.  
**Pipeline status:** BLOCKED (TSU, Qdrant, Gold all blocked).

---

## 3. Candidate Summary

### 3.1 PBC1765 — Orthodox Baptist Confession

| Field | Value |
|---|---|
| canonical_source_id | PBC1765 |
| legacy_source_id | PBC1742 |
| author | Philadelphia Baptist Association (corporate body) |
| title | A Plain and Short Account of the Orthodox Baptist Confession of Faith |
| original_publication_year | 1742 (adoption); manifestation year TBD |
| repository | Internet Archive |
| stable_identifier | `plainbookofconfe00phil` (VERIFIED in IA catalog) |
| rights_basis | Public Domain |
| preferred_derivative | Scan PDF with OCR (`plainbookofconfe00phil.pdf`) |
| status | VERIFIED — stable identifier confirmed in IA catalog |
| HQ decision required | NO |

### 3.2 TH1612 — Thomas Helwys

| Field | Value |
|---|---|
| canonical_source_id | TH1612 |
| legacy_source_id | TH1612 |
| author | Thomas Helwys (d. ~1616) |
| title | A Short Declaration of the Mystery of Iniquity |
| original_publication_year | 1612 |
| repository | Internet Archive / University of Michigan EEBO2 / CCEL |
| stable_identifier | IA: UNVERIFIED (needs catalog search); EEBO2: `A02915.0001.001` (PARTIAL) |
| rights_basis | Public Domain (original); repository terms TBD |
| preferred_derivative | Internet Archive scan PDF (if available); fallback: EEBO2 TCP XML |
| status | PARTIAL — bibliographic identity VERIFIED; stable ID PARTIAL |
| HQ decision required | YES — repository priority and IA item ID confirmation needed |

### 3.3 AF1785 — Andrew Fuller

| Field | Value |
|---|---|
| canonical_source_id | AF1785 |
| legacy_source_id | AF1815 (NOT to be reused as canonical) |
| author | Andrew Fuller (1754–1815) |
| title | The Gospel Worthy of All Acceptation |
| original_publication_year | 1785 |
| repository | Internet Archive / Google Books / CCEL |
| stable_identifier | UNVERIFIED — IA item ID and Google Books ID need catalog search |
| rights_basis | Public Domain |
| preferred_derivative | Internet Archive scan PDF (if available); fallback: Google Books PDF preview |
| status | PARTIAL — bibliographic identity VERIFIED; stable ID UNVERIFIED |
| HQ decision required | YES — stable identifier confirmation needed; work identity confusion with "Gospel Defended" must be resolved |

---

## 4. Derivative Priority Applied

Per §7 of the directive, derivative priority order is:

```
1. Scan PDF with page images and OCR layer     ← PREFERRED for all sources
2. Scan PDF plus separate OCR text
3. Plain UTF-8 OCR text / DjVu text
4. ALTO XML or hOCR (page structure preserved)
5. EPUB (auxiliary text only)
6. HTML (HTML-only source, last resort only)
```

**Result:** All three candidates prefer Internet Archive scan PDF as primary derivative.

---

## 5. Error-Page Rejection Rules

Universal rejection rules (U1–U10) and source-specific rules (P1–P5, H1–H6, E1–E5, C1–C3, F1–F7, G1–G4, D1–D3) are defined in `error-page-rejection-rules.md`.

**Key rule:** If ANY universal or source-specific condition is TRUE → `QUARANTINE / REJECT`.

---

## 6. Download Command Templates

All download commands, header capture, SHA256, MIME inspection, file size inspection, title/author marker inspection, and error template inspection commands are specified in `command-templates.md`.

**These commands are NOT to be executed.** They are templates for HQ-approved download loop execution.

---

## 7. Provenance Manifest Template

The provenance manifest JSON template is in `provenance-manifest-template.json`. Each downloaded artifact will produce one manifest entry filled with actual values.

---

## 8. Evidence Package Index

| File | Purpose |
|---|---|
| `PBC1765-spec.md` | Detailed specification for Candidate A |
| `TH1612-spec.md` | Detailed specification for Candidate B |
| `AF1785-spec.md` | Detailed specification for Candidate C |
| `derivative-inventory.csv` | All candidate derivatives across repositories |
| `error-page-rejection-rules.md` | Universal and source-specific rejection rules |
| `command-templates.md` | Download, validation, and inspection command templates |
| `provenance-manifest-template.json` | JSON template for provenance tracking |
| `source-acquisition-spec.md` | This document (integration) |

---

## 9. Remaining Uncertainties

| Candidate | Uncertainty | Impact |
|---|---|---|
| PBC1765 | None significant — stable identifier confirmed in IA catalog | LOW |
| TH1612 | IA item ID not confirmed; EEBO2 access terms unknown | MEDIUM |
| AF1785 | IA item ID and Google Books ID not confirmed; work identity confusion with "Gospel Defended" | HIGH |

---

## 10. HQ Decision Requested

| Option | Description |
|---|---|
| **A** | Approve controlled download loop for all verified candidates (PBC1765 + TH1765 + AF1785) |
| **B** | Approve download loop only for specified source IDs (e.g., PBC1765 only) |
| **C** | Return registry/specification defects to C1 for resolution |
| **D** | Escalate source identity, rights, or access questions to HQ |

**Recommended:** Option B — Approve PBC1765 download first (stable ID confirmed, no uncertainties). TH1612 and AF1785 require additional catalog search before download authorization.