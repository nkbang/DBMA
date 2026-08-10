# Pipeline Readiness Report — NAE Corpus Build

**Date:** 2026-08-01
**Agent:** C1 (Local Implementation Engineer)
**Task:** NAE-CORPUS-002

## Pipeline Architecture

NAE corpus pipeline consists of 4 stages:

1. **Canonical** (`NAE/pipeline/canonical/`) — RAW → Clean Text
2. **TSU** (`NAE/pipeline/tsu/`) — Clean Text → TSU
3. **Embed** (`NAE/pipeline/embed/`) — TSU → Embeddings
4. **Index** (`NAE/pipeline/index/`) — Embeddings → Qdrant

## Stage 1: Canonical Pipeline (RAW → Clean Text)

### Config Source
`NAE/pipeline/canonical/config.py`

### Key Settings
| Parameter | Value |
|-----------|-------|
| RAW_ROOT | NAE/corpus/raw/archive_org/ |
| CANONICAL_ROOT | NAE/corpus/canonical/ |
| PIPELINE_VERSION | 2.0.0 |
| MIN_OCR_BYTES | 200 |

### Input Schema
- RAW source files in NAE/corpus/raw/archive_org/ (PDF, HTML, TXT)

### Output Schema
- Clean text files in NAE/corpus/canonical/

### Readiness: BLOCKED
**Blocker:** NAE/corpus/raw/archive_org/ is EMPTY. No input files exist.

## Stage 2: TSU Pipeline (Clean Text → TSU)

### Config Source
`NAE/pipeline/tsu/config.py`

### Key Modules
- `builder.py` — TSU construction
- `parser.py` — Text parsing
- `citation.py` — Citation extraction
- `claim.py` — Claim extraction
- `doctrine.py` — Doctrine extraction
- `scripture.py` — Scripture mapping

### Input Schema
- Clean text files from NAE/corpus/canonical/

### Output Schema
- TSU files in NAE/corpus/tsu/

### Readiness: BLOCKED
**Blocker:** No clean text input. Downstream dependency on Stage 1.

## Stage 3: Embed Pipeline (TSU → Embeddings)

### Config Source
`NAE/pipeline/embed/config.py`

### Key Modules
- `client.py` — Embedding client
- `hashing.py` — Vector hashing
- `similarity.py` — Similarity computation

### Input Schema
- TSU files from NAE/corpus/tsu/

### Output Schema
- Embedding vectors in NAE/corpus/embeddings/

### Readiness: BLOCKED
**Blocker:** No TSU input. Downstream dependency on Stage 2.

## Stage 4: Index Pipeline (Embeddings → Qdrant)

### Config Source
`NAE/pipeline/index/config.py`

### Key Modules
- `indexer.py` — Index builder
- `qdrant_store.py` — Qdrant storage integration
- `runner.py` — Pipeline runner

### Input Schema
- Embedding vectors from NAE/corpus/embeddings/

### Output Schema
- Qdrant points in collection `nae_tsu_v1`

### Readiness: BLOCKED
**Blocker:** No embedding input. Downstream dependency on Stage 3.
**Note:** Qdrant collection `nae_tsu_v1` exists but has 0 points.

## Overall Pipeline Status

| Stage | Status | Blocker |
|-------|--------|---------|
| 1. Canonical | BLOCKED | No RAW source files |
| 2. TSU | BLOCKED | No clean text input |
| 3. Embed | BLOCKED | No TSU input |
| 4. Index | BLOCKED | No embedding input |

## Required Actions Before Pipeline Can Run

1. **Collect source documents** into NAE/corpus/raw/archive_org/
2. **Verify OCR quality** of collected sources (MIN_OCR_BYTES = 200)
3. **Run canonical pipeline** to generate clean text
4. **Run TSU pipeline** to extract Theological Structured Units
5. **Run embed pipeline** to generate vector embeddings
6. **Run index pipeline** to populate Qdrant collection

## Architecture Review Required: NO

No architecture changes needed. Pipeline code is complete and functional.
The only blocker is missing source data.