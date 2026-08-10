# NAE Verified Source Acquisition Specification

**Directive:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**Mode:** Read-only acquisition specification (no download execution)  
**Date:** 2026-08-01  
**C1 Agent Status:** SPECIFICATION COMPLETE — no download executed

---

## Executive Summary

3개 Baptist public-domain source candidate에 대한 재현 가능한 acquisition specification을 작성한다. PBC1765는 Internet Archive catalog metadata를 성공적으로 조회하여 verified manifest를 확보했다. TH1612와 AF1785는 HathiTrust/Internet Archive API 접근 제한으로 catalog-level verification이 불가능했으나, 역사적 bibliographic evidence는 기존에 확인됨.

**모든 download command는 template만 제공 — 실행하지 않음.**

---

## Candidate 1: PBC1765 (The Baptist Confession of Faith)

### Canonical Source Identity
| Field | Value |
|---|---|
| **source_id** | PBC1765 |
| legacy_id | PBC1742 (rejected — error page download) |
| canonical_title | The Baptist confession of faith : first put forth in 1643 ; afterwards enlarged, corrected and published by an assembly of delegates (from the churches in Great Britain) met in London July 3, 1689 ; adopted by the association at Philadelphia September 22, 1742 ; and now received by churches of the same denomination in most of the american colonies ; to which is added, a short treatise of discipline |
| short_title | The Baptist Confession of Faith (1765 Philadelphia edition) |
| author / corporate_author | Philadelphia Association of Baptist Churches (corporate) |
| original_publication_year | 1643 (first); 1689 (London enlarged); 1742 (Philadelphia adoption) |
| digital_manifestation_year | 1765 |
| publisher | Philadelphia : Printed by Ant. Armbruster |
| tradition | Baptist (Reformed) |

### Digital Manifestation (Internet Archive — Verified via API)
| Field | Value |
|---|---|
| **repository** | Internet Archive |
| **stable_identifier** | confeo00phil |
| **ark** | ark:/13960/t0tq76w65 |
| **openlibrary_edition** | OL25504382M |
| **openlibrary_work** | OL16882479W |
| **catalog_url** | https://archive.org/details/confeo00phil |
| **access_url** | https://archive.org/download/confeo00phil (base download URL) |
| **mediatype** | texts |
| **language** | eng |
| **page_count** | 108 p. ; 14 cm |
| **imagecount** | 114 images |
| **ppi** | 650 |
| **scanner** | scribe6.nj.archive.org |
| **camera** | Canon EOS 5D Mark II |
| **scandate** | 20121220193400 |
| **republisher** | associate-joseph-ondreicka@archive.org |
| **republisher_date** | 20130102113322 |
| **sponsor** | Princeton Theological Seminary Library |
| **rights_basis** | Published 1765 → public domain (US law: pre-1929) |
| **identifier-access** | http://archive.org/details/confeo00phil |

### Available Derivatives (from catalog metadata — 25 files total)
| derivative_filename | format | size_bytes | source_type | priority |
|---|---|---|---|---|
| confeo00phil.pdf | Text PDF | 8,238,629 | derivative | **P1 (preferred)** |
| confeo00phil_djvu.txt | DjVuTXT | 159,350 | derivative | P2 |
| confeo00phil.djvu | DjVu | 6,756,496 | derivative | P3 |
| confeo00phil_hocr.html | hOCR | 3,795,207 | derivative | P4 |
| confeo00phil_abbyy.gz | Abbyy GZ | 2,490,533 | derivative | P5 |
| confeo00phil.epub | EPUB | 738,432 | derivative | P6 |
| confeo00phil_djvu.xml | Djvu XML | 1,998,917 | derivative | — |
| confeo00phil_chocr.html.gz | chOCR | 1,869,289 | derivative | — |
| confeo00phil_jp2.zip | JP2 ZIP | 42,483,818 | derivative | — |
| confeo00phil_orig_jp2.tar | JP2 Tar | 68,157,440 | original | — |

### Preferred Derivative
**Priority order:** scan PDF with OCR → plain UTF-8 OCR text → DjVu text → ALTO/XML → HTML

| Priority | derivative_filename | format | size_bytes | MIME type (expected) |
|---|---|---|---|---|
| **P1 (selected)** | confeo00phil.pdf | Text PDF with OCR | 8,238,629 | application/pdf |
| P2 | confeo00phil_djvu.txt | DjVuTXT (plain text) | 159,350 | text/plain |
| P3 | confeo00phil.djvu | DjVu image | 6,756,496 | application/djvu |

### Selected Derivative: confeo00phil.pdf
| Field | Value |
|---|---|
| **filename** | confeo00phil.pdf |
| **format** | Text PDF (OCR) |
| **size_bytes** | 8,238,629 |
| **md5** | 3d082f0d1a1b095b9f020022e0256d68 |
| **sha1** | 9eb0e423669637e6de4d736491e43c631d24b8c1 |
| **crc32** | b9ca8516 |
| **original** | confeo00phil_page_numbers.json |
| **mtime** | 1699412349 (Unix: 2023-11-08) |

### Expected Minimum File-Size Sanity Threshold
- **PDF:** >= 1,000,000 bytes (actual: 8,238,629 — PASS)
- **DjVuTXT:** >= 10,000 bytes (actual: 159,350 — PASS)
- **Reject if < 1,000 bytes** (likely error/empty)

### Expected Content Identity Markers
| Marker | Expected Value | Verification Method |
|---|---|---|
| Title page text | "The Baptist confession of faith" | PDF text extraction / first page OCR |
| Author / corporate_author | "Philadelphia Association of Baptist Churches" OR "An assembly of delegates..." | Title page metadata |
| Publication year string | "1765" | Title page / imprint |
| Publisher string | "Printed by Ant. Armbruster" OR "Philadelphia" | Imprint page |
| Adoption date | "September 22, 1742" | Content verification |

### Error-Page Detection Rule
A downloaded artifact must be rejected before canonical ingestion if any applies:

| Condition | Detection |
|---|---|
| HTML title contains `Internet Archive: Error` | `<title>Internet Archive: Error</title>` |
| MIME type is HTML when selected derivative was PDF/text | `text/html` for `.pdf` download |
| Body contains access-denied, not-found, login, rate-limit | grep body for these strings |
| File size < 1,000 bytes | `stat -f%z` or `wc -c` |
| SHA256 mismatch with catalog md5/sha1 | Compare checksums |

### Download Command Template (DO NOT EXECUTE)
```bash
# PBC1765 — Preferred derivative: PDF
cd NAE/corpus/raw/archive_org/items/PBC1765
curl -L -o confeo00phil.pdf \
  "https://archive.org/download/confeo00phil/confeo00phil.pdf"

# Verify checksum
shasum -a 256 confeo00phil.pdf
# Expected SHA256: (catalog provides md5/sha1; recompute after download)

# Verify file size
stat -f%z confeo00phil.pdf
# Expected: 8,238,629 (± 1% tolerance for CDN edge caching)

# Verify MIME type
file -b --mime-type confeo00phil.pdf
# Expected: application/pdf
```

### Provenance Manifest Fields (PBC1765)
| Field | Value |
|---|---|
| source_id | PBC1765 |
| legacy_id | PBC1742 |
| canonical_title | The Baptist confession of faith (1765 Philadelphia edition) |
| digital_manifestation_year | 1765 |
| repository | Internet Archive |
| stable_identifier | confeo00phil |
| ark | ark:/13960/t0tq76w65 |
| catalog_url | https://archive.org/details/confeo00phil |
| access_url | https://archive.org/download/confeo00phil/confeo00phil.pdf |
| selected_derivative | confeo00phil.pdf |
| derivative_format | Text PDF with OCR |
| derivative_size_bytes | 8,238,629 |
| derivative_md5 | 3d082f0d1a1b095b9f020022e0256d68 |
| derivative_sha1 | 9eb0e423669637e6de4d736491e43c631d24b8c1 |
| rights_basis | Public domain (published 1765, pre-1929) |
| provenance_chain | Princeton Theological Seminary → Internet Archive (2012) → republished (2013) |
| content_identity_status | VERIFIED (catalog metadata confirmed) |
| admission_status | READY FOR DOWNLOAD (pending HQ download execution) |

---

## Candidate 2: TH1612 (Thomas Helwys, A Short Declaration)

### Canonical Source Identity
| Field | Value |
|---|---|
| **source_id** | TH1612 |
| legacy_id | TH1612 (same — no rename needed) |
| canonical_title | A Short Declaration of the Mystery of Iniquity, Containing the Seed of all Pharisaical Hypocrisies |
| author | Thomas Helwys (d. ~1616) |
| original_publication_year | 1611 or 1612 (sources vary) |
| tradition | Baptist (General/Early — First religious liberty tract in English) |
| historical_significance | First defense of religious liberty in English; foundational Baptist theological text |

### Digital Manifestation — CATALOG VERIFICATION BLOCKED
| Field | Status |
|---|---|
| **repository** | HathiTrust / Internet Archive / CCEL (candidates) |
| **stable_identifier** | A02915.0001.001 (HathiTrust EEBO2 candidate — UNVERIFIED) |
| **catalog_url** | https://www.hathitrust.org/catalog/a02915.0001.001 (HathiTrust — Cloudflare protected, API inaccessible) |
| **IA_candidate_url** | SEARCH REQUIRED (archive.org에서 "Helwys Short Declaration" 검색 필요) |
| **CCEL_candidate_url** | https://www.ccel.org/ccel/helwys/declaration.html (possible — UNVERIFIED) |
| **rights_basis** | Author died ~1616 → well beyond PD threshold (life + 70 = 1686+) |

### Catalog Verification Status
| Check | Result |
|---|---|
| HathiTrust API lookup | BLOCKED — Cloudflare challenge page returned |
| Internet Archive search API | BLOCKED — advancedsearch endpoint returned 404 |
| Historical catalog evidence | HELMYS, Thomas. "A Short Declaration of the Mystery of Iniquity." 1611/1612. ESTC N3654; EEBO-TCP A02915 |

### TH1612 — Acquisition Strategy (PENDING HQ/CUE Action)
| Step | Action | Owner |
|---|---|---|
| 1 | archive.org에서 "Helwys Short Declaration" 검색 | HQ/CUE |
| 2 | CCEL에서 https://www.ccel.org/ccel/helwys/declaration.html 검증 | HQ/CUE |
| 3 | Internet Archive item identifier 확인 | HQ/CUE |
| 4 | derivative inventory 확인 (PDF, txt, djvu) | HQ/CUE |
| 5 | download command template 작성 | C1 (post-verification) |

### TH1612 — Uncertainty and HQ Decision Needed
| Question | Status |
|---|---|
| 올바른 Internet Archive item identifier는? | UNVERIFIED — search required |
| CCEL 텍스트 버전이 신뢰할 만한 OCR/text인지? | UNVERIFIED — content review required |
| EEBO-TCP A02915 텍스트를 Google Books에서 접근 가능한지? | UNVERIFIED — catalog lookup required |
| preferred derivative는? | HQ decision needed (PDF vs plain text) |

### Provenance Manifest Fields (TH1612 — PENDING)
| Field | Status |
|---|---|
| source_id | TH1612 |
| canonical_title | A Short Declaration of the Mystery of Iniquity |
| author | Thomas Helwys |
| publication_year | 1611 or 1612 |
| repository | PENDING HQ catalog lookup |
| stable_identifier | PENDING |
| catalog_url | PENDING |
| access_url | PENDING |
| selected_derivative | PENDING |
| derivative_format | PENDING |
| derivative_size_bytes | PENDING |
| derivative_md5/sha1 | PENDING |
| rights_basis | Public domain (author died ~1616) |
| provenance_chain | PENDING |
| content_identity_status | UNVERIFIED (catalog blocked) |
| admission_status | QUARANTINE (pending catalog verification) |

---

## Candidate 3: AF1785 (Andrew Fuller, The Gospel Worthy of All Acceptation)

### Canonical Source Identity
| Field | Value |
|---|---|
| **source_id** | AF1785 |
| legacy_id | AF1815 (REJECTED — do not reuse without explicit HQ decision) |
| canonical_title | The Gospel Worthy of All Acceptation: Particularly Considered in the Text, Romans ix. 16 |
| author | Andrew Fuller (1754–1815) |
| original_publication_year | 1785 (first edition) |
| tradition | Baptist (Particular/Revival) |
| historical_significance | Influential Particular Baptist theology; Fuller's major work on divine sovereignty and human responsibility |

**NOTE:** source_candidates.csv에서 claimed_year가 1785와 1815로 혼재됨. 1785는 publication year, 1815는 author death year일 가능성. AF1785가 올바른 source_id (1785 = publication year).

### Digital Manifestation — CATALOG VERIFICATION BLOCKED
| Field | Status |
|---|---|
| **repository** | Internet Archive / Google Books (candidates) |
| **IA_candidate_url** | SEARCH REQUIRED (archive.org에서 "Fuller Gospel Worthy" 검색 필요) |
| **GB_candidate_url** | SEARCH REQUIRED |
| **rights_basis** | Author died 1815 → well beyond PD threshold (life + 70 = 1885) |

### AF1785 — Acquisition Strategy (PENDING HQ/CUE Action)
| Step | Action | Owner |
|---|---|---|
| 1 | archive.org에서 "Fuller Gospel Worthy of All Acceptation" 검색 | HQ/CUE |
| 2 | Google Books에서 "Fuller Gospel Worthy" 검색 | HQ/CUE |
| 3 | Internet Archive item identifier 확인 | HQ/CUE |
| 4 | derivative inventory 확인 (PDF, txt, djvu) | HQ/CUE |
| 5 | download command template 작성 | C1 (post-verification) |

### AF1785 — Uncertainty and HQ Decision Needed
| Question | Status |
|---|---|
| 올바른 Internet Archive item identifier는? | UNVERIFIED — search required |
| Google Books에서 접근 가능한 버전은? | UNVERIFIED — catalog lookup required |
| 1785 first edition vs later editions 중 어느 것을 선택할지? | HQ decision needed |
| preferred derivative는? | HQ decision needed (PDF vs plain text) |

### Provenance Manifest Fields (AF1785 — PENDING)
| Field | Status |
|---|---|
| source_id | AF1785 |
| legacy_id | AF1815 (REJECTED) |
| canonical_title | The Gospel Worthy of All Acceptation |
| author | Andrew Fuller |
| publication_year | 1785 |
| repository | PENDING HQ catalog lookup |
| stable_identifier | PENDING |
| catalog_url | PENDING |
| access_url | PENDING |
| selected_derivative | PENDING |
| derivative_format | PENDING |
| derivative_size_bytes | PENDING |
| derivative_md5/sha1 | PENDING |
| rights_basis | Public domain (author died 1815) |
| provenance_chain | PENDING |
| content_identity_status | UNVERIFIED (catalog blocked) |
| admission_status | QUARANTINE (pending catalog verification) |

---

## Summary: Acquisition Readiness

| source_id | catalog_verified | download_ready | admission_status | blocker |
|---|---|---|---|---|
| **PBC1765** | YES (IA API) | YES (spec complete) | READY FOR DOWNLOAD | None — awaiting HQ download execution |
| **TH1612** | NO (HathiTrust blocked) | NO | QUARANTINE | HQ/CUE: IA/Google Books/CCEL catalog lookup |
| **AF1785** | NO (IA API 404) | NO | QUARANTINE | HQ/CUE: IA/Google Books catalog lookup |

---

## Evidence Package Location
- `evidence/phase5_2/C1-DOWNLOAD-SPEC-007.md` (this file)
- `evidence/phase5_2/C1-SOURCE-IDENTITY-REGISTRY-006.md`
- `evidence/phase5_2/preflight/manifest.json`
- `evidence/phase5_2/preflight/source_inventory.csv`

---

## C1 Sign-off

**TASK:** HQ-C1-DIRECTIVE-NAE-DOWNLOAD-SPEC-007  
**STATUS:** COMPLETE (specification only — no download executed)  
**BLOCKED:** TH1612, AF1785 — catalog verification blocked by external API restrictions  
**NEXT ACTION:** HQ/CUE에서 TH1612와 AF1785의 Internet Archive / Google Books / CCEL catalog lookup 후 C1에 download spec 전달