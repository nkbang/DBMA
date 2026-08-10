# Commands and Outputs — NAE-CORPUS-002 Preflight

**Date:** 2026-08-01
**Agent:** C1 (Local Implementation Engineer)

## Command 1: NAE directory listing

```bash
cd ~/DBMA && ls -la NAE/
```

**Output:**
```
total 24
drwxr-xr-x@ 10 David  staff   320 Jul 31 22:14 .
drwxr-xr-x@ 81 David  staff  2592 Jul 31 21:47 ..
-rw-r--r--@  1 David  staff  6148 Jul 31 22:14 .DS_Store
-rw-r--r--@  1 David  staff     0 Jul 31 10:17 __init__.py
drwxr-xr-x@  3 David  staff    96 Jul 31 11:35 __pycache__
drwxr-xr-x@ 12 David  staff   384 Jul 31 19:57 benchmark
drwxr-xr-x@  3 David  staff    96 Jul 31 10:15 collectors
drwxr-xr-x@ 11 David  staff   352 Jul 31 22:14 corpus
-rw-r--r--@  1 David  staff   712 Jul 31 11:28 docker-compose.yml
drwxr-xr-x@  9 David  staff   288 Jul 31 11:35 pipeline
```

## Command 2: NAE/corpus directory listing

```bash
cd ~/DBMA && ls -la NAE/corpus/
```

**Output:**
```
total 16
drwxr-xr-x@ 11 David  staff   352 Jul 31 22:14 .
drwxr-xr-x@ 10 David  staff   320 Jul 31 22:14 ..
-rw-r--r--@  1 David  staff  6148 Jul 31 22:14 .DS_Store
drwxr-xr-x@  3 David  staff    96 Jul 31 10:27 cache
drwxr-xr-x@  3 David  staff    96 Jul 31 11:35 canonical
drwxr-xr-x@  4 David  staff   128 Jul 31 11:16 embeddings
drwxr-xr-x@  3 David  staff    96 Jul 31 11:35 manifests
drwxr-xr-x@  2 David  staff    64 Jul 31 11:35 metadata
drwxr-xr-x@  4 David  staff   128 Jul 31 22:14 raw
drwxr-xr-x@  3 David  staff    96 Jul 31 11:35 reports
drwxr-xr-x@  3 David  staff    96 Jul 31 11:35 tsu
```

## Command 3: NAE/corpus file count by directory

```bash
cd ~/DBMA && find NAE/corpus -type f -not -name '.DS_Store' | sort
```

**Output:**
```
NAE/corpus/cache/.gitkeep
NAE/corpus/canonical/.gitkeep
NAE/corpus/embeddings/.gitkeep
NAE/corpus/manifests/.gitkeep
NAE/corpus/reports/.gitkeep
NAE/corpus/tsu/.gitkeep
```

## Command 4: Qdrant health check

```bash
curl -s http://localhost:7333 | python3 -m json.tool
```

**Output:**
```json
{
    "title": "qdrant - vector search engine",
    "version": "1.18.2",
    "commit": "44ad62f8cd69642be5afa6441612525e24a0d063"
}
```

## Command 5: Qdrant collections list

```bash
curl -s http://localhost:7333/collections | python3 -m json.tool
```

**Output:**
```json
{
    "result": {
        "collections": [
            {
                "name": "nae_tsu_v1"
            }
        ]
    },
    "status": "ok",
    "time": 3.959e-06
}
```

## Command 6: Qdrant collection detail

```bash
curl -s http://localhost:7333/collections/nae_tsu_v1 | python3 -m json.tool
```

**Output:**
```json
{
    "result": {
        "status": "green",
        "optimizer_status": "ok",
        "indexed_vectors_count": 0,
        "points_count": 0,
        "segments_count": 8,
        "config": {
            "params": {
                "vectors": {
                    "size": 1024,
                    "distance": "Cosine"
                },
                "shard_number": 1,
                "replication_factor": 1,
                "write_consistency_factor": 1,
                "on_disk_payload": true
            },
            "hnsw_config": {
                "m": 16,
                "ef_construct": 100,
                "full_scan_threshold": 10000,
                "max_indexing_threads": 0,
                "on_disk": false
            },
            "optimizer_config": {
                "deleted_threshold": 0.2,
                "vacuum_min_vector_number": 1000,
                "default_segment_number": 0,
                "max_segment_size": null,
                "memmap_threshold": null,
                "indexing_threshold": 10000,
                "flush_interval_sec": 5,
                "max_optimization_threads": null,
                "prevent_unoptimized": null
            },
            "wal_config": {
                "wal_capacity_mb": 32,
                "wal_segments_ahead": 0,
                "wal_retain_closed": 1
            },
            "quantization_config": null
        },
        "payload_schema": {},
        "update_queue": {
            "length": 0
        }
    },
    "status": "ok",
    "time": 0.000298709
}
```

## Command 7: Source candidates CSV (first 30 lines)

```bash
cd ~/DBMA && cat resources/theological_sources/baptist/source_candidates.csv | head -30
```

**Output:**
```
source_id,title,author,year,tradition,language,license,availability,source_location,priority,notes
SLBC1689,Second London Baptist Confession of Faith (1689),John Spurstow et al. (Baptist Assembly),1689,Baptist (Second London),English,public_domain_original,Free Access,"Internet Archive (archive.org/details/b21981773); Project Gutenberg; CCEL",P0,"Reformed Baptist confession. Widely available as public domain."
NHBC1833,New Hampshire Confession of Faith (1833),New Hampshire Baptist Convention,1833,Baptist (Reformed),English,public_domain_original,Free Access,"CCEL (christianclassicsethanal.com); BibleStudyTools; multiple Reformed archives",P0,"Abridgment of London 1689 adapted for New Baptisteries. Public domain."
BFM2000,Baptist Faith and Message 2000,Southern Baptist Convention,2000,Baptist (Southern),English,copyright_restricted,Restricted Access,"SBC official website (sbc.net); Ligonier Ministries",P0,"SBC official doctrinal statement. Future permission/license review required."
PBC1742,Philadelphia Baptist Confession (1742),Philadelphia Association of Baptist Churches,1742,Baptist (Reformed),English,public_domain_original,Free Access,"Internet Archive; Google Books; Reformed archives",P0,"Substantially derived from London 1689 with Baptist modifications. Public domain."
TH1612,A Short Declaration of the Mystery of Iniquity,Thomas Helwys,1612,Baptist (General/Early),English,public_domain_original,Free Access,"Google Books; CCEL; historical archives",P1,"Foundational Baptist work on religious liberty. Author died ~1616."
JS1608,The Book of the First Baptist Church at Amsterdam (1608-1614),John Smyth,1608,Baptist (Founder),"English, Dutch",public_domain_possible,Free Access,"Amsterdam City Archives; historical manuscript collections",P1,"Original Baptist church covenant. Author died 1630. Verify Dutch copyright."
AF1815,The Gospel Defended (and other theological works),Andrew Fuller,1785,Baptist (Particular/Revival),English,public_domain_original,Free Access,"Google Books; CCEL; historical Baptist archives",P1,"Influential Particular Baptist theologian. Died 1815."
```

## Command 8: NAE/corpus directory tree

```bash
cd ~/DBMA && find NAE/corpus -type d | sort
```

**Output:**
```
NAE/corpus
NAE/corpus/cache
NAE/corpus/canonical
NAE/corpus/embeddings
NAE/corpus/embeddings/cache
NAE/corpus/manifests
NAE/corpus/metadata
NAE/corpus/raw
NAE/corpus/raw/archive_org
NAE/corpus/raw/archive_org/books
NAE/corpus/reports
NAE/corpus/tsu
```

## Command 9: File count per directory

```bash
cd ~/DBMA && for d in NAE/corpus/raw NAE/corpus/raw/archive_org NAE/corpus/raw/archive_org/books NAE/corpus/tsu NAE/corpus/metadata NAE/corpus/embeddings NAE/corpus/canonical NAE/corpus/manifests NAE/corpus/reports NAE/corpus/cache; do count=$(find "$d" -type f -not -name '.DS_Store' | wc -l); echo "$d: $count files"; done
```

**Output:**
```
NAE/corpus/raw:        0 files
NAE/corpus/raw/archive_org:        0 files
NAE/corpus/raw/archive_org/books:        0 files
NAE/corpus/tsu:        1 files
NAE/corpus/metadata:        0 files
NAE/corpus/embeddings:        1 files
NAE/corpus/canonical:        1 files
NAE/corpus/manifests:        1 files
NAE/corpus/reports:        1 files
NAE/corpus/cache:        1 files
```

## Command 10: Pipeline file listing

```bash
cd ~/DBMA && find NAE/pipeline -type f -not -name '.DS_Store' -not -name '__pycache__*' | sort
```

**Output (key modules):**
```
NAE/pipeline/__init__.py
NAE/pipeline/canonical/__init__.py
NAE/pipeline/canonical/annotate.py
NAE/pipeline/canonical/config.py
NAE/pipeline/canonical/extract.py
NAE/pipeline/canonical/normalize.py
NAE/pipeline/canonical/pipeline.py
NAE/pipeline/canonical/reflow.py
NAE/pipeline/canonical/runner.py
NAE/pipeline/canonical/structure.py
NAE/pipeline/embed/__init__.py
NAE/pipeline/embed/client.py
NAE/pipeline/embed/config.py
NAE/pipeline/embed/hashing.py
NAE/pipeline/embed/similarity.py
NAE/pipeline/index/__init__.py
NAE/pipeline/index/config.py
NAE/pipeline/index/indexer.py
NAE/pipeline/index/qdrant_store.py
NAE/pipeline/index/runner.py
NAE/pipeline/tsu/__init__.py
NAE/pipeline/tsu/builder.py
NAE/pipeline/tsu/citation.py
NAE/pipeline/tsu/claim.py
NAE/pipeline/tsu/config.py
NAE/pipeline/tsu/doctrine.py
NAE/pipeline/tsu/parser.py
NAE/pipeline/tsu/runner.py
NAE/pipeline/tsu/scripture.py
NAE/pipeline/verify/__init__.py
NAE/pipeline/verify/config.py
NAE/pipeline/verify/consistency.py
NAE/pipeline/verify/contradiction.py
NAE/pipeline/verify/duplicate.py
NAE/pipeline/verify/evidence.py
NAE/pipeline/verify/runner.py
NAE/pipeline/verify/score.py