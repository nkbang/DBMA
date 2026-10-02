#!/usr/bin/env python3
"""scripts/merge_nae_corpus.py — Merge NAE corpus TSU into production TSU.

Safety contract (F-3):
  - Idempotent by tsu_id (never document_id)
  - Atomic dataset write via core.tsu_builder helpers
  - Validation before replace
  - Provenance preservation (scriptures, copyright_status, etc.)
  - Manifest via core.tsu_builder.write_manifest()

Approval gate (PR #111):
  - Mandatory verify_mutation_gate() before any mutation
  - Fail-closed: no approval -> no mutation
  - CLI option cannot circumvent the gate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Approval gate import — mutation code의 진입점 (PR #111)
from scripts.corpus_approval_gate import (
    CorpusMutationBlockedError,
    verify_corpus_mutation_approval,
    build_approval_manifest,
    validate_merge_plan_against_manifest,
)

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
    source_id: Optional[str] = None,
    nae_corpus_dir: Optional[Path] = None,
    tsu_dataset_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
    registry_path: Optional[Path] = None,
    decisions_dir: Optional[Path] = None,
) -> dict:
    """Merge NAE corpus TSU into production TSU (F-3 safe).

    F-3 contract:
      - Idempotent by tsu_id
      - Atomic dataset write
      - Validation before replace
      - Manifest via core.tsu_builder.write_manifest()
      - Provenance preservation

    Approval gate (PR #111):
      - verify_mutation_gate() is called BEFORE any mutation
      - No CLI option or environment variable can circumvent this gate
      - Function-level enforcement: direct Python call also triggers gate
    """
    # NEW-1 fix: use Path for / operator; default corpus path = NAE/corpus/tsu
    # (matches process_unprocessed_nae.py convention)
    nae_corpus_dir = Path(nae_corpus_dir or (Path("NAE") / "corpus" / "tsu"))
    tsu_dataset_path = Path(tsu_dataset_path or DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(manifest_path or DEFAULT_TSU_MANIFEST_PATH)
    registry_path = Path(registry_path or registry_path_for(DEFAULT_OUTPUT_DIR))
    decisions_dir = Path(decisions_dir or (Path("NAE") / "review" / "human" / "decisions"))

    # 0. TSU planning — planned_tsu_ids 생성 (approval gate용)
    planned_tsu_ids: set[str] = set()
    if source_id is not None and nae_corpus_dir.exists():
        for tsu_dir in sorted(nae_corpus_dir.glob("*")):
            tsu_file = tsu_dir / "tsu.json"
            if tsu_file.exists():
                data = json.loads(tsu_file.read_text(encoding="utf-8"))
                for record in data:
                    # corpus record는 tsu_id 대신 id를 가질 수 있음
                    # _transform_nae_record()가 tsu_id를 "NAE-{id}"로 생성함
                    tid = record.get("tsu_id") or f"NAE-{record.get('id', '')}"
                    if tid and record.get("work_id") == source_id:
                        planned_tsu_ids.add(tid)

    if not planned_tsu_ids:
        return {
            "status": "skipped",
            "reason": f"No TSU records found for source={source_id!r} in {nae_corpus_dir}",
            "merged_count": 0,
            "duplicate_count": 0,
        }

    # 1. APPROVAL GATE — mutation 전 필수 승인 검증 (PR #111)
    print(f"\nVerifying corpus mutation approval gate for source={source_id!r}...")
    gate_result = verify_corpus_mutation_approval(
        source_id, decisions_dir, frozenset(planned_tsu_ids)
    )

    if not gate_result.approved:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED for source={source_id!r}: {gate_result.reason}"
        )

    # Build manifest for audit trail
    approval_manifest = build_approval_manifest(source_id, decisions_dir)
    if approval_manifest is None:
        raise CorpusMutationBlockedError(
            f"Corpus mutation BLOCKED: manifest build failed for source={source_id!r}"
        )

    # Validate merge plan against manifest
    valid, reason = validate_merge_plan_against_manifest(
        approval_manifest, frozenset(planned_tsu_ids)
    )
    if not valid:
        raise CorpusMutationBlockedError(f"Corpus mutation BLOCKED: {reason}")

    print(f"  Gate PASSED: {approval_manifest.approved_count} TSUs approved by {approval_manifest.reviewer_id}")

    # 2. Read existing dataset (moved inside lock)
    with tsu_dataset_lock(tsu_dataset_path):
        print(f"\nReading existing TSU dataset from {tsu_dataset_path}...")
        existing_records = _read_existing_dataset(tsu_dataset_path)
        print(f"  Found {len(existing_records)} existing records")

        # 3. Read NAE corpus TSU records
        print(f"\nScanning NAE corpus TSU at {nae_corpus_dir}...")
        if not nae_corpus_dir.exists():
            raise FileNotFoundError(
                f"NAE corpus directory not found: {nae_corpus_dir}"
            )

        nae_records = []
        nae_docs_info: dict[Path, dict] = {}

        for item in sorted(nae_corpus_dir.glob("*")):
            if not item.is_dir():
                continue
            tsu_file = item / "tsu.json"
            if not tsu_file.exists():
                continue

            # source_id filter: only process matching source
            if source_id is not None:
                data = json.loads(tsu_file.read_text(encoding="utf-8"))
                has_source = any(r.get("work_id") == source_id for r in data)
                if not has_source:
                    continue

            data = json.loads(tsu_file.read_text(encoding="utf-8"))
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

        # 4. Dedup by tsu_id (F-3 idempotency)
        existing_ids = {r["tsu_id"] for r in existing_records}
        new_records = [
            rec for rec in nae_records
            if rec["tsu_id"] not in existing_ids
        ]

        # 5. Compose candidate dataset
        all_records = existing_records + new_records

        # 6. Validation before replace (F-3)
        print("\nValidating candidate dataset...")
        _validate_dataset(all_records, tsu_dataset_path)
        print(f"  Validation passed: {len(all_records)} records, no duplicates")

        # 7. Atomic write (F-3) — now inside lock
        print(f"\nWriting merged TSU to {tsu_dataset_path}...")
        write_tsu_dataset(all_records, tsu_dataset_path)
        print(f"  Written {len(all_records)} records atomically")

        # 8. Update registry (F-3: corpus_membership="default")
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

        # 9. Update manifest via core.tsu_builder.write_manifest() (F-3)
        print(f"\nUpdating manifest at {manifest_path}...")
        final_manifest = write_manifest(
            records=all_records,
            registry=registry,
            manifest_path=manifest_path,
            registry_path=registry_path,
            dataset_path=tsu_dataset_path,
        )
        print(f"  Updated manifest (tsu_count={final_manifest['tsu_count']})")

    return {
        "status": "completed",
        "source_id": source_id,
        "manifest_source": approval_manifest.source_id,
        "approved_count": approval_manifest.approved_count,
        "existing_records": len(existing_records),
        "nae_records": len(nae_records),
        "new_records_after_dedup": len(new_records),
        "duplicate_count": len(nae_records) - len(new_records),
        "total_records": len(all_records),
        "new_documents": len(nae_docs_info),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NAE Corpus Merge with mandatory approval gate"
    )
    parser.add_argument("--source", required=True,
        help="Source ID to merge (e.g., Fuller_Complete_Works_Vol02)")
    parser.add_argument("--corpus-dir", default=None,
        help="NAE corpus TSU directory")
    parser.add_argument("--dataset-path", default=None,
        help="Target TSU dataset path")
    parser.add_argument("--decisions-dir", default=None,
        help="Human decisions directory")
    args = parser.parse_args()

    try:
        result = merge_nae_corpus(
            source_id=args.source,
            nae_corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
            tsu_dataset_path=Path(args.dataset_path) if args.dataset_path else None,
            decisions_dir=Path(args.decisions_dir) if args.decisions_dir else None,
        )
        print(f"\n=== Merge Result ===")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except CorpusMutationBlockedError as e:
        print(f"\n=== MERGE BLOCKED ===", flush=True)
        print(f"Reason: {e}", flush=True)
        print(
            "\nTo proceed, submit source for human review at "
            "NAE/review/human/ and await APPROVED decision.",
            flush=True,
        )
        exit(1)
