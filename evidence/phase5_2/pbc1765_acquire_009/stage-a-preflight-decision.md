# Stage A — Corrected Metadata Preflight Decision

## Source
- Canonical ID: PBC1765
- Legacy ID: PBC1742
- Work: The Baptist Confession of Faith
- Approved preflight identifier: `confeo00phil`

## Evidence Sources
| Source | URL | Status |
|--------|-----|--------|
| Item page | https://archive.org/details/confeo00phil | HTTP 200 |
| Metadata API | https://archive.org/metadata/confeo00phil | HTTP 200 |

## Seven Condition Evaluation

| # | Condition | Result | Evidence |
|---|-----------|--------|----------|
| 1 | HTTP response = 200 | **PASS** | Item page: 200; Metadata API: 200 |
| 2 | Returned identifier = `confeo00phil` | **PASS** | metadata.identifier = "confeo00phil" |
| 3 | Title matches "The Baptist Confession of Faith" | **PASS** | "The Baptist confession of faith : first put forth in 1643 ; afterwards enlarged, corrected and published by an assembly of delegates (from the churches in Great Britain) met in London July 3, 1689 ; adopted by the association at Philadelphia September 22, 1742 ; and nowreceived by churches of the same denomination in most of the american colonies ; to which is added, a short treatise of discipline" |
| 4 | Philadelphia Association 1742 adoption mentioned | **PASS** | Title contains: "adopted by the association at Philadelphia September 22, 1742" |
| 5 | Digital manifestation = Philadelphia, 1765 | **PASS** | metadata.date = "1765"; metadata.publisher = "Philadelphia : Printed by Ant. Armbruster" |
| 6 | Imprint/publisher = Ant. or Anthony Armbruster | **PASS** | metadata.publisher = "Philadelphia : Printed by Ant. Armbruster" |
| 7 | Public domain scan PDF or OCR/DjVu derivative exists | **PASS** | PDF: confeo00phil.pdf (8,238,629 bytes, Text PDF); DjVu TXT: confeo00phil_djvu.txt (159,350 bytes); hOCR: confeo00phil_hocr.html (3,795,207 bytes) |

## Preflight Decision

**PREFLIGHT PASS** — All 7 conditions satisfied.

Stage B is authorized for controlled quarantine acquisition.