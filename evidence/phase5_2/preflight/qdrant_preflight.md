# Qdrant Preflight Report — NAE Corpus

**Date:** 2026-08-01
**Agent:** C1 (Local Implementation Engineer)
**Task:** NAE-CORPUS-002

## Health Check

```json
{
    "title": "qdrant - vector search engine",
    "version": "1.18.2",
    "commit": "44ad62f8cd69642be5afa6441612525e24a0d063"
}
```

**Status:** OK (running, healthy)

## Collection Status

**Collection Name:** `nae_tsu_v1`

**Status:** green
**Optimizer Status:** ok
**Update Queue Length:** 0

### Points / Vectors

| Metric | Value |
|--------|-------|
| points_count | **0** |
| indexed_vectors_count | **0** |
| segments_count | 8 |

**Result:** Collection exists but is **EMPTY**. No vectors indexed.

### Vector Configuration

| Parameter | Value |
|-----------|-------|
| vector size | 1024 |
| distance | Cosine |
| shard_number | 1 |
| replication_factor | 1 |
| write_consistency_factor | 1 |
| on_disk_payload | true |

### HNSW Configuration

| Parameter | Value |
|-----------|-------|
| m | 16 |
| ef_construct | 100 |
| full_scan_threshold | 10000 |
| max_indexing_threads | 0 |
| on_disk | false |

### Optimizer Configuration

| Parameter | Value |
|-----------|-------|
| deleted_threshold | 0.2 |
| vacuum_min_vector_number | 1000 |
| default_segment_number | 0 |
| max_segment_size | null |
| memmap_threshold | null |
| indexing_threshold | 10000 |
| flush_interval_sec | 5 |
| max_optimization_threads | null |

### WAL Configuration

| Parameter | Value |
|-----------|-------|
| wal_capacity_mb | 32 |
| wal_segments_ahead | 0 |
| wal_retain_closed | 1 |

### Quantization

**Config:** null (disabled)

### Payload Schema

**Status:** empty (no payload fields defined)

## Persistent Storage

**Volume Name:** `nae_qdrant_storage` (Docker external volume)
**Mount Path:** `/qdrant/storage` inside container
**External Volume:** Yes (must exist separately from dbma_qdrant_storage)

## Docker Compose Configuration

```yaml
services:
  nae_qdrant:
    image: qdrant/qdrant:latest
    container_name: nae_qdrant
    restart: unless-stopped
    ports:
      - "7333:6333"   # HTTP API
      - "7334:6334"   # gRPC API
    volumes:
      - nae_qdrant_storage:/qdrant/storage
```

## Summary

| Item | Value |
|------|-------|
| Endpoint | http://localhost:7333 |
| Version | 1.18.2 |
| Collection | nae_tsu_v1 (exists) |
| Points | 0 (EMPTY) |
| Vector Size | 1024 |
| Distance | Cosine |
| Storage | Docker external volume (nae_qdrant_storage) |
| Health | OK |

## BLOCKER

**Corpus build cannot proceed because:**
1. NAE/corpus/raw/ is EMPTY (0 files) — no source documents to process
2. NAE/corpus/tsu/ is EMPTY (only .gitkeep) — no TSU data
3. NAE/corpus/metadata/ is EMPTY — no metadata
4. NAE/corpus/embeddings/ is EMPTY — no embeddings
5. Qdrant collection nae_tsu_v1 exists but has 0 points

**Next Step:** Source documents must be collected into NAE/corpus/raw/ before any corpus build or indexing can occur.