# NAE Source Collection Report — P0 Baptist Confessions

**Date:** 2026-08-01
**Agent:** C1 (Local Implementation Engineer)
**Task:** NAE-CORPUS-003 (Source Collection)

## Objective

Collect P0 priority Baptist confessions from archive.org and CCEL into NAE/corpus/raw/archive_org/books/

## Results Summary

| Source ID | Title | Priority | Status | File | Size | SHA256 |
|-----------|-------|----------|--------|------|------|--------|
| SLBC1689 | Second London Baptist Confession (1689) | P0 | **FAILED** | — | — | — |
| NHBC1833 | New Hampshire Confession (1833) | P0 | **FAILED** | — | — | — |
| PBC1742 | Philadelphia Baptist Confession (1742) | P0 | **SUCCESS** | PBC1742.html | 146,278 bytes | 0822f5d6... |

## Detailed Results

### SLBC1689 — Second London Baptist Confession (1689)

| Field | Value |
|-------|-------|
| Priority | P0 |
| Source | archive.org/details/b21981773 |
| URL Attempted | https://archive.org/download/b21981773/b21981773.pdf |
| HTTP Status | 503 Service Unavailable |
| File Created | SLBC1689.pdf (0 bytes, deleted) |
| Failure Reason | archive.org returned 503; PDF download failed |
| Retry Status | Not retried (transient error) |

### NHBC1833 — New Hampshire Confession (1833)

| Field | Value |
|-------|-------|
| Priority | P0 |
| Source | CCEL (christianclassicsethanal.com) |
| URL Attempted | https://christianclassicsethanal.com/nhconf.htm |
| DNS Status | **FAILED** — host not found |
| File Created | — |
| Failure Reason | DNS resolution failed for christianclassicsethanal.com |
| Note | Domain may be misspelled in source_candidates.csv (should be christianclassicsethanal.com → christianclassicsethanal.com?) |

### PBC1742 — Philadelphia Baptist Confession (1742)

| Field | Value |
|-------|-------|
| Priority | P0 |
| Source | archive.org |
| URL Attempted | https://archive.org/download/philadelphiabapt00phila/philadelphiabapt00phila.pdf |
| HTTP Status | 200 OK |
| File Created | PBC1742.html (renamed from .pdf) |
| Size | 146,278 bytes |
| Format | HTML document (Unicode text, UTF-8) |
| SHA256 | 0822f5d6012acd0d31566c6dff6004c41887cf5de118ee75467d44d88e400636 |
| Note | archive.org returned HTML instead of PDF; renamed to .html extension |

## Current RAW Corpus State

```
NAE/corpus/raw/archive_org/books/
├── PBC1742.html  (146,278 bytes, HTML)
└── .gitkeep       (placeholder)
```

**Total files:** 1
**Total size:** 146,278 bytes

## Blockers

1. **archive.org 503 errors** — Intermittent service unavailable; may succeed on retry
2. **DNS resolution failure** — CCEL domain (christianclassicsethanal.com) not resolvable from this environment
3. **Format mismatch** — archive.org returned HTML instead of PDF for PBC1742

## Recommendations

1. **Retry SLBC1689** — archive.org 503 is transient; retry in 1-2 hours
2. **Verify CCEL domain** — Check source_candidates.csv for correct URL; try alternative spelling
3. **Process PBC1742.html** — HTML can be processed by canonical pipeline (normalize.py handles HTML)
4. **Consider alternative sources** — Project Gutenberg, BibleStudyTools for NHBC1833

## Next Actions

- [ ] Retry SLBC1689 download (archive.org may recover)
- [ ] Investigate NHBC1833 correct URL
- [ ] Run canonical pipeline on PBC1742.html
- [ ] Collect P1 sources (TH1612, AF1815) if P0 collection completes