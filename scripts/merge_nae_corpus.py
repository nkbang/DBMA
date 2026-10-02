#!/usr/bin/env python3
"""scripts/merge_nae_corpus.py — Merge NAE corpus TSU into production TSU.

Safety contract (F-3):
  - Idempotent by tsu_id (never document_id)
  - Atomic dataset write via core.tsu_builder helpers
  - Validation before replace
  - Provenance preservation (scriptures, copyright_status, etc.)
  - Manifest via core.tsu_builder.write_manifest()
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH, registry_path_for
from core.identity_registry import load_identity_registry, save_identity_registry
from core.tsu_builder import (
    tsu_dataset_lock,
    write_tsu_dataset,
    write_manifest,
)


def _transform_nae_record(nae_rec: dict, doc_id: str) -> dict:
    """Transform a NAE corpus TSU record to production TSU format.

    F-3 provenance fix: preserve NAE scriptures instead of discarding them.
    """
    claim = nae_rec.get("claim", "")
    has_korean = any("\uac00" <= c <= "\ud7a3" for c in claim)
    language = "ko" if has_korean else "en"

    doctrine = nae_rec.get("doctrine", "")
    doctrine_category = [doctrine] if doctrine else []

    baptist_themes = []
    if doctrine:
        doc_lower = doctrine.lower()
        if "soteriology" in doc_lower:
            baptist_themes.append("soteriology")
        elif "ecclesiology" in doc_lower:
            baptist_themes.append("ecclesiology")
        elif "pneumatology" in doc_lower:
            baptist_themes.append("pneumatology")
        elif "christology" in doc_lower:
            baptist_themes.append("christology")
        elif "trinitarian" in doc_lower or "trinity" in doc_lower:
            baptist_themes.append("trinitarian_doctrine")
        elif "baptism" in doc_lower:
            baptist_themes.append("baptism")
        elif "covenant" in doc_lower:
            baptist_themes.append("covenant_theology")
        elif "eschatology" in doc_lower:
            baptist_themes.append("eschatology")
        elif "hermeneutics" in doc_lower or "exegesis" in doc_lower:
            baptist_themes.append("biblical_hermeneutics")

    nae_scriptures = nae_rec.get("scriptures")
    verse_mapping = {}
    if nae_scriptures is not None and nae_scriptures:
        verse_mapping = {"_nae_scriptures": nae_scriptures}

    return {
        "tsu_id": f"NAE-{nae_rec['id']}",
        "document_id": doc_id,
        "chunk_id": f"NAE-{nae_rec['id']}",
        "content": nae_rec.get("source_text", ""),
        "verse_mapping": verse_mapping,
        "themes": [],
        "title": nae_rec.get("book", ""),
        "author": nae_rec.get("author", ""),
        "metadata_source": "nae_canonical",
        "chapter": None,
        "page": nae_rec.get("page"),
        "source_file": f"{nae_rec.get('identifier', '')}.jsonl",
        "language": language,
        "source_type": "nae_canonical",
        "content_quality": {
            "noise_type": "NAE_CANONICAL",
            "quality_score": 1.0,
            "section_type": "claim",
        },
        "structure": {},
        "theological_claim": claim,
        "doctrine_category": doctrine_category,
        "baptist_theme": baptist_themes,
        "source_provenance": None,
        "nae_metadata": {
            "nae_id": nae_rec.get("id"),
            "nae_doctrine": doctrine,
            "nae_confidence": nae_rec.get("confidence"),
            "nae_extraction_method": nae_rec.get("extraction_method"),
            "nae_review_status": nae_rec.get("review_status"),
            "source_type": nae_rec.get("source_type"),
            "copyright_status": nae_rec.get("copyright_status"),
            "author_id": nae_rec.get("author_id"),
            "work_id": nae_rec.get("work_id"),
            "scriptures": nae_scriptures,
        },
    }


def _read_existing_dataset(dataset_path: Path) -> list[dict]:
    """Read existing TSU dataset, return list of records.

    Returns [] for missing files or empty content — never crashes on
    empty/invalid input.
    """
    p = Path(dataset_path)
    if not p.exists():
        return []
    records = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _validate_dataset(records: list[dict], dataset_path: Path) -> None:
    """Validate candidate dataset before atomic replace. Raises ValueError on failure."""
    if not records:
        raise ValueError("Dataset contains zero records")
    for i, rec in enumerate(records):
        if "tsu_id" not in rec or not rec["tsu_id"]:
            raise ValueError(f"Record {i} missing tsu_id")
    tsu_ids = [rec["tsu_id"] for rec in records]
    if len(tsu_ids) != len(set(tsu_ids)):
        duplicates = [tid for tid in tsu_ids if tsu_ids.count(tid) > 1]
        raise ValueError(f"Duplicate tsu_id found: {set(duplicates)}")
    if dataset_path.exists():
        existing = _read_existing_dataset(dataset_path)
        existing_ids = {r["tsu_id"] for r in existing}
        new_ids = {rec["tsu_id"] for rec in records}
        preserved = existing_ids & new_ids
        if len(preserved) != len(existing_ids):
            missing = existing_ids - preserved
            raise ValueError(f"Unrelated TSU not preserved: {missing}")


def merge_nae_corpus(
    nae_corpus_dir: Path | None = None,
    tsu_dataset_path: Path | None = None,
    manifest_path: Path | None = None,
    registry_path: Path | None = None,
) -> dict:
    """Merge NAE corpus TSU into production TSU (F-3 safe).

    F-3 contract:
      - Idempotent by tsu_id
      - Atomic dataset write
      - Validation before replace
      - Manifest via core.tsu_builder.write_manifest()
      - Provenance preservation
    """
    # NEW-1 fix: use Path for / operator; default corpus path = NAE/corpus/tsu
    # (matches process_unprocessed_nae.py convention)
    nae_corpus_dir = Path(nae_corpus_dir or (Path("NAE") / "corpus" / "tsu"))
    tsu_dataset_path = Path(tsu_dataset_path or DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(manifest_path or DEFAULT_TSU_MANIFEST_PATH)
    registry_path = Path(registry_path or registry_path_for(DEFAULT_OUTPUT_DIR))

    # NEW-4 fix: entire read-modify-write inside single lock
    with tsu_dataset_lock(tsu_dataset_path):
        # 1. Read existing dataset (moved inside lock)
        print(f"Reading existing TSU dataset from {tsu_dataset_path}...")
        existing_records = _read_existing_dataset(tsu_dataset_path)
        print(f"  Found {len(existing_records)} existing records")

        # 2. Read NAE corpus TSU records
        print(f"\nScanning NAE corpus TSU at {nae_corpus_dir}...")
        if not nae_corpus_dir.exists():
            raise FileNotFoundError(f"NAE corpus directory not found: {nae_corpus_dir}")

        nae_records = []
        nae_docs_info = {}

        for item in sorted(nae_corpus_dir.iterdir()):
            if not item.is_dir():
                continue
            tsu_file = item / "tsu.json"
            if not tsu_file.exists():
                print(f"  Skipping {item.name} (no tsu.json)")
                continue

            with open(tsu_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # NEW-3 fix: guard against empty/invalid tsu.json
            if not isinstance(data, list) or len(data) == 0:
                print(f"  Skipping {item.name} (empty or invalid tsu.json)")
                continue

            # NEW-2 fix: document_id must use 'nae_' prefix for compatibility
            doc_id = f"nae_{item.name}"
            nae_docs_info[item] = {
                "document_id": doc_id,
                "title": data[0].get("book", ""),
                "author": data[0].get("author", ""),
                "record_count": len(data),
            }

            for nae_rec in data:
                prod_rec = _transform_nae_record(nae_rec, doc_id)
                nae_records.append(prod_rec)

        print(f"  Read {len(nae_records)} NAE corpus records from {len(nae_docs_info)} documents")

        # 3. Dedup by tsu_id (F-3 idempotency)
        existing_ids = {r["tsu_id"] for r in existing_records}
        new_records = [
            rec for rec in nae_records
            if rec["tsu_id"] not in existing_ids
        ]

        # 4. Compose candidate dataset
        all_records = existing_records + new_records

        # 5. Validation before replace (F-3)
        print("\nValidating candidate dataset...")
        _validate_dataset(all_records, tsu_dataset_path)
        print(f"  Validation passed: {len(all_records)} records, no duplicates")

        # 6. Atomic write (F-3) — now inside lock
        print(f"\nWriting merged TSU to {tsu_dataset_path}...")
        write_tsu_dataset(all_records, tsu_dataset_path)
        print(f"  Written {len(all_records)} records atomically")

        # 7. Update registry (F-3: corpus_membership="default")
        print(f"\nUpdating registry at {registry_path}...")
        registry = load_identity_registry(registry_path)

        for item, info in nae_docs_info.items():
            doc_id = info["document_id"]
            if doc_id not in registry["documents"]:
                registry["documents"][doc_id] = {
                    "document_id": doc_id,
                    "source_file": f"{item.name}.jsonl",
                    "title": info["title"],
                    "author": info["author"],
                    "status": "processed",
                    "chunk_count": info["record_count"],
                    "language": "en",
                    "source_type": "nae_canonical",
                    "doc_type": "신학",
                    "ingest_status": "PROCESSED",
                    "pipeline_state": "INDEXED",
                    "created_at": datetime.now().isoformat(),
                    "last_processed_at": datetime.now().isoformat(),
                    "last_content_hash": f"nae_{item.name}",
                    "corpus_membership": "default",
                    "pipeline_flags": {
                        "ingested": True,
                        "copied": True,
                        "extracted": True,
                        "cleaned": True,
                        "chunked": True,
                        "output_generated": True,
                        "verified": True,
                    },
                }

        save_identity_registry(registry, str(registry_path))
        print(f"  Updated registry with {len(nae_docs_info)} new documents")

        # 8. Update manifest via core.tsu_builder.write_manifest() (F-3)
        print(f"\nUpdating manifest at {manifest_path}...")
        manifest = write_manifest(
            records=all_records,
            registry=registry,
            manifest_path=manifest_path,
            registry_path=registry_path,
            dataset_path=tsu_dataset_path,
        )
        print(f"  Updated manifest (tsu_count={manifest['tsu_count']})")

    return {
        "existing_records": len(existing_records),
        "nae_records": len(nae_records),
        "new_records_after_dedup": len(new_records),
        "total_records": len(all_records),
        "new_documents": len(nae_docs_info),
    }


if __name__ == "__main__":
    result = merge_nae_corpus()
    print(f"\n=== Merge Result ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
