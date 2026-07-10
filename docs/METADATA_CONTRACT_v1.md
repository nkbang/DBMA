# DBMA Metadata Contract v1.0

**Effective Date:** 2026-07-09  
**Pipeline Version:** 1.1.x  
**Status:** Canoncial metadata schema for Processing Engine  

---

## 1. Purpose

This document defines the canonical metadata contract for all documents processed by the DBMA Processing Engine. It establishes required fields, optional fields, and their semantics.

---

## 2. Metadata Schema

### 2.1 Mandatory Fields (always present)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `document_id` | `str` | Content-based SHA-256 prefix (32 hex chars). Deterministic: same content → same ID. | `"a1b2c3d4e5f67890abcdef1234567890"` |
| `source_file` | `str` | Original filename of the input document. Used for traceability. | `"1 Kings The Wisdom and the Folly _Dale Ralph Davis.pdf"` |
| `file_hash` | `str` | Full SHA-256 content hash (64 hex chars). Complete fingerprint. | `"a1b2c3d4e5f67890abcdef1234567890...ef1234567890abcdef1234567890"` |
| `created_at` | `str` | ISO 8601 timestamp of processing. | `"2026-07-09T10:26:00-05:00"` |
| `processing_version` | `str` | DBMA pipeline version that created this document. | `"1.1.x"` |

### 2.2 Structural Fields (unknown → null)

These fields represent the document's structural context within a larger work. If undetectable during processing, set to `null`.

| Field | Type | Description | Unknown Value |
|-------|------|-------------|---------------|
| `title` | `str \| null` | Document title (if detectable from source) | `null` |
| `author` | `str \| null` | Author name (if detectable) | `null` |
| `book` | `str \| null` | Book/section identifier (e.g., "Genesis", "Romans") | `null` |
| `chapter` | `int \| null` | Chapter number (if detectable) | `null` |
| `page` | `int \| null` | Page reference in original source | `null` |
| `batch_id` | `str \| null` | Batch processing identifier | `null` |

### 2.3 Processing Fields (always present)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `language` | `str` | Detected language code (ISO 639-1) | `"ko"`, `"en"`, `"ja"` |
| `noise_score` | `float` | Text noise metric, 0-100 (higher = noisier) | `23.5` |
| `noise_mode` | `str` | Noise classification | `"pdf"`, `"pdf_ocr"`, `"plain_text"` |
| `source_type` | `str` | File extension without dot | `"pdf"`, `"docx"`, `"txt"` |
| `is_ocr` | `bool` | Whether OCR was used during extraction | `true`, `false` |
| `chunk_count` | `int` | Number of chunks produced | `42` |
| `chunk_id_prefix` | `str` | Document ID used as prefix for chunk IDs | `"a1b2c3d4e5f67890abcdef1234567890"` |

---

## 3. Metadata Output Formats

### 3.1 Markdown Frontmatter (canonical `.md` output)

```yaml
---
source: <filename>                    # preserved from existing format
source_type: <ext>                   # preserved from existing format
language: <detected_lang>            # preserved from existing format
created_at: <ISO timestamp>          # preserved from existing format
noise_score: <float>                 # preserved from existing format
noise_mode: <mode_string>            # preserved from existing format
# NEW fields (additive):
document_id: <32-char hex>           # content-based ID
file_hash: <64-char hex>            # full SHA-256
processing_version: "1.1.x"          # pipeline version
title: <title or null>              # detectable or null
author: <author or null>            # detectable or null
book: <book or null>                # detectable or null
chapter: <int or null>              # detectable or null
page: <int or null>                 # detectable or null
chunk_count: <int>                   # number of chunks
chunk_id_prefix: <doc_id>           # prefix for chunk IDs
---
```

### 3.2 Metadata JSON Sidecar (optional future)

```json
{
  "document_id": "a1b2c3d4e5f67890abcdef1234567890",
  "source_file": "1 Kings The Wisdom and the Folly _Dale Ralph Davis.pdf",
  "file_hash": "a1b2c3d4e5f67890abcdef1234567890...",
  "created_at": "2026-07-09T10:26:00-05:00",
  "processing_version": "1.1.x",
  "title": null,
  "author": null,
  "book": null,
  "chapter": null,
  "page": null,
  "batch_id": null,
  "language": "en",
  "noise_score": 23.5,
  "noise_mode": "pdf",
  "source_type": "pdf",
  "is_ocr": false,
  "chunk_count": 42,
  "chunk_id_prefix": "a1b2c3d4e5f67890abcdef1234567890"
}
```

---

## 4. Chunk Identity Schema

### 4.1 chunk_id Format

```
{document_id}_chunk_{index:05d}
```

**Example:** `a1b2c3d4e5f67890abcdef1234567890_chunk_00042`

### 4.2 Properties

| Property | Value |
|----------|-------|
| Deterministic | ✅ Same doc + same index → same chunk_id |
| Traceable | ✅ Embeds document_id prefix |
| Readable | ✅ Human-parseable format |
| Gap-safe | ✅ Zero-padded index survives gaps |

---

## 5. Field Semantics Rules

### 5.1 Never Invent Values

If a field's value is undetectable during processing:
- Set to `null` (JSON) / null (YAML frontmatter)
- Never set to `"Unknown"`, `"N/A"`, `"-"`, or empty string
- Document detection capability separately if needed

### 5.2 Content-Based Identity

- `document_id` is derived from **content**, not filename
- Same content at different paths → same `document_id` ✅
- Modified content (even by one character) → new `document_id` ✅
- File renamed/moved → same `document_id` (if content unchanged) ✅

### 5.3 Traceability

- `source_file` always preserves the original filename
- This ensures humans can trace back to the input regardless of content-based ID

---

## 6. Validation Rules

| Rule | Condition | Severity |
|------|-----------|----------|
| document_id present | Always | CRITICAL |
| document_id length = 32 hex chars | Always | CRITICAL |
| file_hash present | Always | HIGH |
| file_hash length = 64 hex chars | Always | HIGH |
| created_at ISO 8601 valid | Always | MEDIUM |
| processing_version present | Always | HIGH |
| language code present | Always | LOW |
| noise_score in [0, 100] | Always | MEDIUM |
| chunk_count ≥ 0 | Always | MEDIUM |

---

## 7. Migration Policy

### 7.1 Backward Compatibility

- Old documents (pre-v1.1.x) remain valid
- New fields are additive only
- No breaking changes to existing `.md` frontmatter format
- `source`, `source_type`, `language`, `created_at`, `noise_score`, `noise_mode` preserved from v1.0

### 7.2 Null vs Empty

| Value | Usage |
|-------|-------|
| `null` | Unknown/undetectable value |
| `""` (empty string) | Intentionally empty (should not occur) |
| `"Unknown"` | NEVER use for missing values |

---

*End of METADATA_CONTRACT_v1.0*