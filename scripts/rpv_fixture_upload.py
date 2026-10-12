#!/usr/bin/env python3
"""RPV fixture upload — process A/B fixtures through the existing pipeline.

Runs in the isolated c8f7e41a worktree only. Does NOT write to the
original /Users/David/DBMA repository.

Usage:
    cd /Users/David/DBMA-rpv-c8f7e41a
    source ~/envs/dbma311/bin/activate
    python scripts/rpv_fixture_upload.py
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import (DEFAULT_RAW_DIR, DEFAULT_OUTPUT_DIR, registry_path_for,
    DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH)
from core.processing import build_converter, build_splitter, process_batch
from core.identity_registry import load_identity_registry
from core.tsu_builder import build_tsu_records, write_tsu_dataset
from core.index_orchestrator import write_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("rpv_fixture_upload")


def main() -> None:
    raw_dir = Path(DEFAULT_RAW_DIR)
    output_dir = DEFAULT_OUTPUT_DIR

    fixture_files = [
        "rpv_fixture_A_john15_sermon_notes.txt",
        "rpv_fixture_B_spirit_gifts_notes.txt",
    ]

    for fname in fixture_files:
        fpath = raw_dir / fname
        if not fpath.exists():
            logger.error("Fixture file missing: %s", fpath)
            sys.exit(1)
        text = fpath.read_text(encoding="utf-8")
        logger.info("Fixture file: %s (size=%d chars)", fname, len(text))

    file_list = [
        {"path": str(raw_dir / name), "name": name, "ext": "txt", "use_ocr": False}
        for name in fixture_files
    ]

    logger.info("Building converter (no OCR)...")
    converter = build_converter(use_ocr=False)
    logger.info("Building splitter (chunk_size=1200, overlap=120)...")
    splitter = build_splitter(chunk_size=1200, chunk_overlap=120)

    logger.info("Processing %d fixture files → output_dir=%s", len(file_list), output_dir)
    results = process_batch(
        file_list=file_list, converter=converter, splitter=splitter,
        output_dir=output_dir, chunk_size=1200, chunk_overlap=120,
        report=None, force_reingest=False, force_rechunk=False,
    )

    # Promote fixtures to TSU dataset
    logger.info("Promoting fixtures to TSU via build_tsu_records...")
    registry_path = Path(registry_path_for(output_dir))
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"

    registry = load_identity_registry(str(registry_path))
    fixture_docs = {}
    for doc_id, doc in registry.get("documents", {}).items():
        sf = doc.get("source_file", "")
        if any(f in sf for f in fixture_files):
            fixture_docs[doc_id] = doc

    logger.info("Fixture documents in registry: %d", len(fixture_docs))
    for doc_id, doc in fixture_docs.items():
        logger.info("  %s: source=%s chunks=%d state=%s",
                     doc_id, doc.get("source_file"), doc.get("chunk_count"), doc.get("pipeline_state"))

    subset = {"documents": fixture_docs}
    new_records = build_tsu_records(subset, Path(output_dir))
    logger.info("TSU records built: %d", len(new_records))

    existing = []
    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
    existing_ids = {r.get("document_id") for r in existing}
    new_records_filtered = [r for r in new_records if r.get("document_id") not in existing_ids]
    all_records = existing + new_records_filtered
    write_tsu_dataset(all_records, dataset_path)
    logger.info("TSU dataset updated: %d total records (%d new)", len(all_records), len(new_records_filtered))
    write_manifest(all_records, registry, manifest_path,
                   registry_path=registry_path, dataset_path=dataset_path, config_path=config_path)
    logger.info("TSU manifest updated")

    # Read evidence IDs from TSU dataset
    all_tsu_ids = []
    fixture_evidence_A = []
    fixture_evidence_B = []
    seen_A = set()
    seen_B = set()

    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                sf = rec.get("source_file", "")
                doc_id = rec["document_id"]
                if "rpv_fixture_A" in sf and doc_id not in seen_A:
                    seen_A.add(doc_id)
                    fixture_evidence_A.append({"document_id": doc_id, "source_file": sf})
                    all_tsu_ids.append(doc_id)
                elif "rpv_fixture_B" in sf and doc_id not in seen_B:
                    seen_B.add(doc_id)
                    fixture_evidence_B.append({"document_id": doc_id, "source_file": sf})
                    all_tsu_ids.append(doc_id)

    # Report results
    logger.info("=" * 60)
    logger.info("RPV Fixture Upload Results:")
    logger.info("=" * 60)

    for r in results:
        name = r.get("name", "unknown")
        success = r.get("success", False)
        skipped = r.get("skipped", False)
        artifacts = r.get("artifacts", {})
        logs = r.get("logs", [])
        logger.info("-" * 40)
        logger.info("File: %s", name)
        logger.info("  success=%s  skipped=%s", success, skipped)
        chunks = artifacts.get("chunks", 0) or artifacts.get("chunk_count", 0)
        logger.info("  chunks: %d", chunks)
        for log in logs:
            msg = log.get("msg", "")
            cls = log.get("cls", "")
            if cls != "log-info":
                logger.info("  [%s] %s", cls, msg)

    logger.info("-" * 40)
    logger.info("TSU promotion: %d records built, %d added to dataset", len(new_records), len(new_records_filtered))
    logger.info("Evidence IDs found in TSU dataset:")
    logger.info("  fixture_A: %s", json.dumps(fixture_evidence_A, ensure_ascii=False))
    logger.info("  fixture_B: %s", json.dumps(fixture_evidence_B, ensure_ascii=False))

    all_success = all(r.get("success", False) for r in results) and len(all_tsu_ids) > 0
    total_chunks = sum(d.get("chunk_count", 0) for d in fixture_docs.values())

    logger.info("=" * 60)
    logger.info("SUMMARY:")
    logger.info("  All files processed successfully: %s", all_success)
    logger.info("  Total chunks created (from registry): %d", total_chunks)
    logger.info("  Total evidence IDs: %d", len(all_tsu_ids))
    logger.info("  Evidence IDs (all): %s", json.dumps(all_tsu_ids, ensure_ascii=False))
    logger.info("=" * 60)

    result_path = Path(output_dir) / "rpv_fixture_upload_result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_data = {
        "fixture_A": {
            "filename": fixture_files[0],
            "evidence_ids": [e["document_id"] for e in fixture_evidence_A],
            "full_info": fixture_evidence_A,
        },
        "fixture_B": {
            "filename": fixture_files[1],
            "evidence_ids": [e["document_id"] for e in fixture_evidence_B],
            "full_info": fixture_evidence_B,
        },
        "total_chunks": total_chunks,
        "tsu_records_built": len(new_records),
        "tsu_records_added": len(new_records_filtered),
        "all_evidence_ids": all_tsu_ids,
    }
    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Results written to: %s", result_path)


if __name__ == "__main__":
    main()
