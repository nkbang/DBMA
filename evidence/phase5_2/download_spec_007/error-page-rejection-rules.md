# Error-Page Rejection Rules

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007 §8  
**Mode:** Read-only specification  
**Date:** 2026-08-01  

---

## 1. Universal Rejection Rules (All Sources)

The following rules apply to ALL source downloads. If ANY condition is TRUE, the artifact is immediately `QUARANTINE / REJECT`.

| # | Rule | Rationale |
|---|------|-----------|
| U1 | HTTP response status != 200 | Non-200 indicates server error, not found, or access denied |
| U2 | Selected derivative's expected MIME != response Content-Type | MIME mismatch indicates wrong content type (e.g., HTML returned instead of PDF) |
| U3 | HTML returned when PDF/text was expected AND HTML is not an approved HTML-only source | Prevents corpus ingestion of catalog/viewer/error pages |
| U4 | HTML title contains "Internet Archive: Error" or "Error" + "Archive" pattern | Internet Archive error page indicator |
| U5 | Body contains access denied, not found, login, rate limit, or error template keywords | Direct error signal |
| U6 | File size < source-specific minimum threshold | Too small to be valid content |
| U7 | Title-page marker NOT FOUND in content | Work identity cannot be confirmed |
| U8 | Author or corporate-author marker NOT FOUND in content | Author identity cannot be confirmed |
| U9 | Publication/edition marker NOT FOUND in content | Edition identity cannot be confirmed |
| U10 | Redirect destination stable identifier != expected stable identifier | Redirected to wrong item or error page |

---

## 2. Source-Specific Rejection Rules

### 2.1 PBC1765 (Philadelphia Baptist Confession)

| # | Rule | Condition |
|---|------|-----------|
| P1 | MIME check | Expected: `application/pdf`. If `text/html` returned → REJECT |
| P2 | Size check | PDF file size < 500,000 bytes → REJECT |
| P3 | Title marker | Content must contain "Plain and Short Account" OR "Orthodox Baptist Confession" → REJECT if absent |
| P4 | Author marker | Content must contain "Philadelphia Association" → REJECT if absent |
| P5 | IA error pattern | HTML body contains "Internet Archive" AND ("error" OR "not found" OR "corrupted") → REJECT |

### 2.2 TH1612 (Thomas Helwys)

#### For Internet Archive derivative:

| # | Rule | Condition |
|---|------|-----------|
| H1 | MIME check | Expected: `application/pdf`. If `text/html` returned → REJECT |
| H2 | Size check | PDF file size < 300,000 bytes → REJECT |
| H3 | Title marker | Content must contain "Short Declaration" AND "Mystery of Iniquity" → REJECT if absent |
| H4 | Author marker | Content must contain "Helwys" OR "T.H." → REJECT if absent |
| H5 | IA error pattern | HTML body contains "Internet Archive" AND ("error" OR "not found") → REJECT |
| H6 | Full View check | IA metadata `full_view` = false → REJECT (access restricted) |

#### For University of Michigan EEBO2:

| # | Rule | Condition |
|---|------|-----------|
| E1 | MIME check | Expected: `application/xml`. If `text/html` returned → REJECT |
| E2 | Size check | XML file size < 50,000 bytes → REJECT |
| E3 | Title marker | TEI header must contain title "Short Declaration" → REJECT if absent |
| E4 | Author marker | TEI header must contain author "Helwys" OR "Thomas" → REJECT if absent |
| E5 | Access wall | Page contains login form, subscription prompt, or "access denied" → REJECT |

#### For CCEL (HTML-only fallback):

| # | Rule | Condition |
|---|------|-----------|
| C1 | Title marker | HTML must contain "Short Declaration" AND "Mystery of Iniquity" → REJECT if absent |
| C2 | Author marker | HTML must contain "Helwys" → REJECT if absent |
| C3 | Content check | HTML contains only navigation chrome without substantive content → REJECT |

### 2.3 AF1785 (Andrew Fuller)

#### For Internet Archive derivative:

| # | Rule | Condition |
|---|------|-----------|
| F1 | MIME check | Expected: `application/pdf`. If `text/html` returned → REJECT |
| F2 | Size check | PDF file size < 500,000 bytes → REJECT |
| F3 | Title marker | Content must contain "Gospel Worthy" AND "Acceptation" → REJECT if absent |
| F4 | Wrong work check | Content contains "Gospel Defended" (wrong work!) → REJECT |
| F5 | Author marker | Content must contain "Fuller" OR "Andrew Fuller" → REJECT if absent |
| F6 | IA error pattern | HTML body contains "Internet Archive" AND ("error" OR "not found") → REJECT |
| F7 | Full View check | IA metadata `full_view` = false → REJECT (access restricted) |

#### For Google Books:

| # | Rule | Condition |
|---|------|-----------|
| G1 | Size check | PDF file size < 300,000 bytes → REJECT |
| G2 | Title marker | Content must contain "Gospel Worthy" AND "Acceptation" → REJECT if absent |
| G3 | Wrong work check | Content contains "Gospel Defended" (wrong work!) → REJECT |
| G4 | Preview check | Page shows "Preview not available" or access restricted → REJECT |

#### For CCEL (HTML-only fallback):

| # | Rule | Condition |
|---|------|-----------|
| D1 | Title marker | HTML must contain "Gospel Worthy" AND "Acceptation" → REJECT if absent |
| D2 | Author marker | HTML must contain "Fuller" → REJECT if absent |
| D3 | Content check | HTML contains only navigation chrome without substantive content → REJECT |

---

## 3. Rejection Decision Logic

```
FOR EACH downloaded artifact:
    
    // Universal checks first
    IF NOT universal_check(U1..U10):
        REJECT → QUARANTINE
        reason = "Universal rule violation: <rule_id>"
        continue
    
    // Source-specific checks
    IF source == PBC1765:
        IF NOT source_check(P1..P5):
            REJECT → QUARANTINE
            reason = "PBC1765 rule violation: <rule_id>"
    
    ELSE IF source == TH1612:
        IF repository == Internet_Archive AND NOT source_check(H1..H6):
            REJECT → QUARANTINE
        ELSE IF repository == Michigan_EEBO2 AND NOT source_check(E1..E5):
            REJECT → QUARANTINE
        ELSE IF repository == CCEL AND NOT source_check(C1..C3):
            REJECT → QUARANTINE
    
    ELSE IF source == AF1785:
        IF repository == Internet_Archive AND NOT source_check(F1..F7):
            REJECT → QUARANTINE
        ELSE IF repository == Google_Books AND NOT source_check(G1..G4):
            REJECT → QUARANTINE
        ELSE IF repository == CCEL AND NOT source_check(D1..D3):
            REJECT → QUARANTINE
    
    ELSE:
        REJECT → QUARANTINE
        reason = "Unknown source — manual review required"
    
    // If all checks pass
    ACCEPT → quarantine/verified/
```

---

## 4. Quarantine Classification

| Condition | Quarantine classification |
|-----------|--------------------------|
| Universal rule violation | `QUARANTINE/REJECT/universal` |
| Source-specific rule violation | `QUARANTINE/REJECT/source-specific/<source_id>` |
| Wrong work identified | `QUARANTINE/REJECT/wrong-work` |
| Access restricted | `QUARANTINE/REJECT/access-restricted` |
| All checks pass | `QUARANTINE/VERIFIED/<source_id>` |

---

## 5. Notes

- `text/html` is NOT automatically rejected — it is only accepted if the source was pre-approved as HTML-only (per §7 derivative priority)
- All rejection decisions must be logged with: source_id, rule_violated, actual_content_type, file_size, timestamp
- Verified artifacts move to `corpus_raw/verified/` for downstream pipeline processing