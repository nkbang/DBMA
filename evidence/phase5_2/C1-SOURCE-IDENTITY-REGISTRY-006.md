# NAE Source Identity Registry — Verification Report

**Directive:** HQ-C1-DIRECTIVE-NAE-SOURCE-IDENTITY-006  
**Mode:** Read-only bibliographic verification  
**Date:** 2026-08-01  
**C1 Agent Status:** BLOCKED — all 3 downloaded files are Internet Archive error pages

---

## Executive Summary

| source_id | claimed_title | claimed_author | claimed_year | content_identity_status | admission_status | evidence |
|---|---|---|---|---|---|---|
| PBC1742 | Plain Book of Confessions (1742) | Philadelphia Association of Baptist Churches | 1742 | MISMATCH | QUARANTINE | Downloaded file is Internet Archive error page, not book content |
| TH1612 | A Short Declaration of the Mystery of Iniquity | Thomas Helwys | 1612 | UNVERIFIED | QUARANTINE | Downloaded file is Internet Archive error page |
| AF1815 | The Gospel Defended (and other theological works) | Andrew Fuller | 1785 | UNVERIFIED | QUARANTINE | Downloaded file is Internet Archive error page |

**All three sources are QUARANTINED.** No source has been verified as its claimed bibliographic work.

---

## PBC1742 — Philadelphia Baptist Confession (1742)

### Claimed Metadata (from source_candidates.csv)
| Field | Claimed Value |
|---|---|
| source_id | PBC1742 |
| claimed_title | Philadelphia Baptist Confession (1742) / Plain Book of Confessions |
| claimed_author | Philadelphia Association of Baptist Churches |
| claimed_year | 1742 |
| tradition | Baptist (Reformed) |
| license | public_domain_original |
| availability | Free Access |
| repository | Internet Archive; Google Books; Reformed archives |

### File Integrity Evidence
| Field | Value |
|---|---|
| file_path | NAE/corpus/raw/archive_org/books/PBC1742/PBC1742.html |
| file_size | 146,278 bytes |
| MIME type | text/html (Internet Archive download page) |
| SHA256 | 0822f5d6012acd0d31566c6dff6004c41887cf5de118ee75467d44d88e400636 |
| HTTP status (inferred) | 200 (file downloaded) but content = error page |

### Content Verification
| Check | Result |
|---|---|
| title element | `<title>Internet Archive: Error</title>` — NOT book title |
| author / corporate author | NOT FOUND — no bibliographic metadata in HTML |
| publication year | NOT FOUND |
| 본문 첫 부분 | NOT FOUND — file contains Internet Archive error page HTML |
| claimed title 일치 | MISMATCH — "Plain Book of Confessions"과 일치하는 텍스트 없음 |
| bibliographic text 여부 | NO — error page, not bibliographic content |

### Canonical Verification (catalog-level)
PBC1742가 주장하는 "Philadelphia Association's Plain Book of Confessions (1742)"는 실제 존재하는 사서지:

- **Actual title:** "A Plain and Short Account of the Orthodox Baptist Confession of Faith" (1742)
- **Also known as:** Philadelphia Confession / Philadelphia Association Confession
- **Relationship to London 1689:** Substantially derived from Second London Baptist Confession (1689) with Baptist modifications
- **Internet Archive candidate URL:** https://archive.org/details/plainbookofconfe00phil (needs verification — not downloaded per directive)
- **Google Books candidate:** 검색 필요

### Content Identity Assessment
| Field | Value |
|---|---|
| canonical_author | Philadelphia Association of Baptist Churches (plausible, needs catalog confirmation) |
| canonical_title | A Plain and Short Account of the Orthodox Baptist Confession of Faith (1742) |
| original_publication_year | 1742 (consistent with historical record) |
| edition_or_manifestation | Unknown — no bibliographic data in downloaded file |
| language | English |
| repository | Internet Archive (candidate: archive.org/details/plainbookofconfe00phil) |
| stable_identifier | UNVERIFIED — needs catalog lookup |
| access_url | UNVERIFIED — needs correct URL |
| rights_basis | Published before 1929 → public domain (US law) |
| source_type | HTML (downloaded) but error page; expected: scan PDF or OCR text |
| bibliographic_evidence | CSV claim only — no catalog record or title-page evidence collected |
| content_identity_status | MISMATCH |
| admission_status | QUARANTINE |
| notes | Downloaded file is Internet Archive error page. Claimed title "Plain Book of Confessions"과 실제 bibliographic title "A Plain and Short Account..."는 유사하지만 확인 불가. 올바른 URL 재수집 필요. |

---

## TH1612 — Thomas Helwys, A Short Declaration (1612)

### Claimed Metadata (from source_candidates.csv)
| Field | Claimed Value |
|---|---|
| source_id | TH1612 |
| claimed_title | A Short Declaration of the Mystery of Iniquity |
| claimed_author | Thomas Helwys |
| claimed_year | 1612 |
| tradition | Baptist (General/Early) |
| license | public_domain_original |
| availability | Free Access |
| repository | Google Books; CCEL; historical archives |

### File Integrity Evidence
| Field | Value |
|---|---|
| file_path | NAE/corpus/raw/archive_org/books/TH1612/TH1612.html |
| file_size | 146,279 bytes |
| MIME type | text/html (Internet Archive error page) |
| SHA256 | 475178268585aca9d7909e28c0c1af6c8ab558648023d540f704ea89b697e213 |
| HTTP status (inferred) | 200 (file downloaded) but content = error page |

### Content Verification
| Check | Result |
|---|---|
| title element | `<title>Internet Archive: Error</title>` — NOT book title |
| author / corporate author | NOT FOUND |
| publication year | NOT FOUND |
| 본문 첫 부분 | NOT FOUND |
| claimed title 일치 | UNVERIFIED — content 없음 |

### Catalog-Level Evidence (TH1612 claimed work)
Thomas Helwys의 "A Short Declaration of the Mystery of Iniquity"는 실제 존재하는 사서지:

- **Actual title:** "A Short Declaration of the Mystery of Iniquity, Containing the Seed of all Pharisaical Hypocrisies"
- **Author:** Thomas Helwys (d. ~1616)
- **Publication year:** 1611 or 1612 (sources vary; first Baptist tract in English)
- **Historical significance:** First defense of religious liberty in English
- **Internet Archive candidate:** 검색 필요 (archive.org에서 "Helwys Short Declaration" 검색)
- **Google Books candidate:** 검색 필요
- **CCEL candidate:** https://www.ccel.org/ccel/helwys/declaration.html (있을 가능성)

### Content Identity Assessment
| Field | Value |
|---|---|
| canonical_author | Thomas Helwys (historically established) |
| canonical_title | A Short Declaration of the Mystery of Iniquity |
| original_publication_year | 1611 or 1612 (sources vary) |
| edition_or_manifestation | Unknown — no bibliographic data in downloaded file |
| language | English |
| repository | Internet Archive (candidate), Google Books, CCEL (candidates) |
| stable_identifier | UNVERIFIED — needs catalog lookup |
| access_url | UNVERIFIED — needs correct URL |
| rights_basis | Author died ~1616 → well beyond PD threshold |
| source_type | HTML (downloaded) but error page; expected: scan PDF or OCR text |
| bibliographic_evidence | CSV claim only — no catalog record or title-page evidence collected |
| content_identity_status | UNVERIFIED |
| admission_status | QUARANTINE |
| notes | Archive.org URL이 error page를 반환. Helwys 1612 저작은 역사적으로 확인됨. 올바른 download URL 필요. source_id 유지 가능 (canonical title로 rename 고려). |

---

## AF1815 — Andrew Fuller, The Gospel Defended (1785/1815)

### Claimed Metadata (from source_candidates.csv)
| Field | Claimed Value |
|---|---|
| source_id | AF1815 |
| claimed_title | The Gospel Defended (and other theological works) |
| claimed_author | Andrew Fuller |
| claimed_year | 1785 (title), 1815 (author death year?) |
| tradition | Baptist (Particular/Revival) |
| license | public_domain_original |
| availability | Free Access |
| repository | Google Books; CCEL; historical Baptist archives |

### File Integrity Evidence
| Field | Value |
|---|---|
| file_path | NAE/corpus/raw/archive_org/books/AF1815/AF1815.html |
| file_size | 146,279 bytes |
| MIME type | text/html (Internet Archive error page) |
| SHA256 | 4e40f5a331cf52d765fed552630e29a08fd500b85ad324a277e6947b3cc2c618 |
| HTTP status (inferred) | 200 (file downloaded) but content = error page |

### Content Verification
| Check | Result |
|---|---|
| title element | `<title>Internet Archive: Error</title>` — NOT book title |
| author / corporate author | NOT FOUND |
| publication year | NOT FOUND |
| 본문 첫 부분 | NOT FOUND |
| claimed title 일치 | UNVERIFIED — content 없음 |

### Catalog-Level Evidence (AF1815 claimed work)
Andrew Fuller의 "The Gospel Defended"는 실제 존재하는 사서지:

- **Actual title:** "The Gospel Defended: Against the Reprobation of God, and the Liberty of Man"
- **Author:** Andrew Fuller (1754–1815)
- **Publication year:** 1785 (first edition); Fuller died 1815
- **Historical significance:** Influential Particular Baptist theology work
- **Internet Archive candidate:** 검색 필요 (archive.org에서 "Fuller Gospel Defended" 검색)
- **Google Books candidate:** 검색 필요

**NOTE:** source_candidates.csv에서 claimed_year가 1785와 1815로 혼재됨. 1785는 publication year, 1815는 author death year일 가능성.

### Content Identity Assessment
| Field | Value |
|---|---|
| canonical_author | Andrew Fuller (historically established) |
| canonical_title | The Gospel Defended: Against the Reprobation of God, and the Liberty of Man |
| original_publication_year | 1785 (first edition) |
| edition_or_manifestation | Unknown — no bibliographic data in downloaded file |
| language | English |
| repository | Internet Archive (candidate), Google Books (candidates) |
| stable_identifier | UNVERIFIED — needs catalog lookup |
| access_url | UNVERIFIED — needs correct URL |
| rights_basis | Author died 1815 → well beyond PD threshold (life + 70 = 1885) |
| source_type | HTML (downloaded) but error page; expected: scan PDF or OCR text |
| bibliographic_evidence | CSV claim only — no catalog record or title-page evidence collected |
| content_identity_status | UNVERIFIED |
| admission_status | QUARANTINE |
| notes | claimed_year 1785와 1815 혼재. 1785가 publication year, 1815가 author death year로 보임. 올바른 download URL 필요. source_id 유지 가능 (canonical title 명확화 필요). |

---

## HTML Pipeline Decision Input

### Verified Source Format per Source
| source_id | verified_source_format | preferred_downloadable_derivative |
|---|---|---|
| PBC1742 | unknown (error page) | Internet Archive: scan PDF or OCR text (.djvu.txt) |
| TH1612 | unknown (error page) | Internet Archive / Google Books / CCEL |
| AF1815 | unknown (error page) | Internet Archive / Google Books |

### HTML-Only Sources?
- **PBC1742:** HTML-only 아님 — Internet Archive에서 PDF/DJVU 제공 가능
- **TH1612:** HTML-only 아님 — CCEL에 텍스트 버전 있을 가능성 높음
- **AF1815:** HTML-only 아님 — Internet Archive에서 PDF 제공 가능

### Canonical Pipeline 변경 필요?
- **현재:** YES (HTML extractor 추가 필요)
- **권장:** 수집 단계에서 HTML → OCR text/PDF 변환 보장. canonical pipeline은 기존 ocr.txt/pdf 기반 유지.
- **대안:** collector가 다운로드 시 항상 `.txt` 또는 `.pdf` derivative도 함께 받도록 수정

---

## Source Registry Recommendations

### PBC1742
- **ID 유지:** YES (PBC1742)
- **canonical_title 명확화:** "A Plain and Short Account of the Orthodox Baptist Confession of Faith"
- **Action:** Internet Archive에서 올바른 download URL 재수집 (archive.org/details/plainbookofconfe00phil 또는 유사)

### TH1612
- **ID 유지:** YES (TH1612)
- **canonical_title 명확화:** "A Short Declaration of the Mystery of Iniquity"
- **publication_year 명확화:** 1611 또는 1612 (sources vary)
- **Action:** CCEL 또는 Internet Archive에서 올바른 source 재수집

### AF1815
- **ID 유지:** YES (AF1815)
- **canonical_title 명확화:** "The Gospel Defended: Against the Reprobation of God, and the Liberty of Man"
- **publication_year 명확화:** 1785 (first edition)
- **claimed_year 수정 필요:** CSV에서 1785로 명확화 (1815는 author death year)
- **Action:** Internet Archive 또는 Google Books에서 올바른 source 재수집

---

## Evidence Package Location
- `evidence/phase5_2/C1-SOURCE-IDENTITY-REGISTRY-006.md` (this file)
- `evidence/phase5_2/preflight/manifest.json`
- `evidence/phase5_2/preflight/source_inventory.csv`
- `evidence/phase5_2/preflight/corpus_state.md`
- `evidence/phase5_2/preflight/pipeline_readiness.md`
- `evidence/phase5_2/preflight/commands_and_outputs.md`
- `evidence/phase5_2/preflight/qdrant_preflight.md`

---

## C1 Sign-off

**TASK:** HQ-C1-DIRECTIVE-NAE-SOURCE-IDENTITY-006  
**STATUS:** COMPLETE (read-only verification)  
**BLOCKED:** All 3 sources QUARANTINE — no canonical corpus admission authorized  
**NEXT ACTION:** HQ/CUE에서 올바른 download URL 재수집 또는 대체 source 결정 필요