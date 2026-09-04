#!/usr/bin/env python3
"""Night Shift Order 003 - NAE TSU -> Embedding -> Qdrant Production Ingestion.

Order 002에서 Registration 10건이 QUALITY_PASSED로 완료된 상태로부터 시작하여,
실제 TSU Processing Pipeline 연결부를 구현·검증한다.

Pipeline:
  Registration (QUALITY_PASSED)
    -> processing.py::process_one_file() (extraction + chunking + registry)
    -> tsu_builder.py::build_tsu_records() (TSU record generation)
    -> NAE/pipeline/ingest/pipeline.py::apply() (embedding + Qdrant upsert)
    -> verification

Usage:
    cd ~/DBMA && source ~/envs/dbma311/bin/activate
    python scripts/ns003_nae_ingestion.py --phase all
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback as tb_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

NS_DIR = PROJECT_ROOT / ".automation" / "night-shift"
LOG_DIR = NS_DIR / "logs" / "ns003"
REG_STATE_PATH = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "registration_state.json"
BASELINE_PATH = PROJECT_ROOT / "output" / "adr021_phase_ef_evidence" / "baseline.json"
PROD_REGISTRY = PROJECT_ROOT / "data" / "제련완성본" / "registry" / "documents.json"
PROD_OUTPUT_DIR = PROJECT_ROOT / "data" / "제련완성본"
QDRANT_URL = "http://localhost:7333"
QDRANT_COLLECTION = "nae_tsu_v1"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ns003")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_registration_state():
    return load_json(REG_STATE_PATH)


def get_quality_passed_sources(state):
    from NAE.pipeline.registration.state import RegistrationState
    return [
        sid for sid, entry in state.items()
        if isinstance(entry, dict) and entry.get("state") == RegistrationState.QUALITY_PASSED.value
    ]


def load_baseline():
    if BASELINE_PATH.exists():
        return load_json(BASELINE_PATH)
    return {}


def process_single_source(source_id):
    """Run one QUALITY_PASSED source through processing -> TSU."""
    logs = []
    error = None
    document_id = None
    chunk_count = 0
    tsu_records_list = []

    try:
        # 1. Find raw source directory from raw_checksum_ledger.jsonl
        ledger_path = REG_STATE_PATH.parent / "raw_checksum_ledger.jsonl"
        raw_paths = {}
        if ledger_path.exists():
            for line in ledger_path.read_text(encoding="utf-8").strip().split("\n"):
                try:
                    entry = json.loads(line)
                    sid = entry.get("source_id", "")
                    rpath = entry.get("raw_path", "")
                    if sid and rpath:
                        raw_paths[sid] = Path(rpath).parent
                except json.JSONDecodeError:
                    continue

        raw_dir = raw_paths.get(source_id)
        if not raw_dir:
            error = f"No raw_path in ledger for {source_id}"
            logger.error(error)
            return {"source_id": source_id, "success": False, "error": error, "logs": logs}

        if not raw_dir.exists():
            error = f"Raw directory does not exist: {raw_dir}"
            logger.error(error)
            return {"source_id": source_id, "success": False, "error": error, "logs": logs}

        logs.append(f"[Phase 1] Raw dir: {raw_dir}")
        files_in_dir = [f.name for f in raw_dir.iterdir()]
        logs.append(f"[Phase 1] Files: {files_in_dir}")

        # 2. Find the PDF file (original.pdf or any .pdf)
        pdf_files = list(raw_dir.glob("*.pdf"))
        if not pdf_files:
            error = f"No PDF found in {raw_dir}"
            logger.error(error)
            return {"source_id": source_id, "success": False, "error": error, "logs": logs}

        pdf_path = pdf_files[0]
        source_name = pdf_path.name
        logs.append(f"[Phase 1] Processing PDF: {source_name}")

        # 3. Run through core/processing.py::process_one_file
        from core.processing import build_converter, build_splitter, process_one_file

        converter = build_converter(use_ocr=False)
        splitter = build_splitter(chunk_size=1200, chunk_overlap=200)
        file_info = {
            "name": source_name,
            "path": str(pdf_path),
            "size": pdf_path.stat().st_size,
            "ext": "pdf",
        }

        result = process_one_file(
            file_info=file_info,
            converter=converter,
            splitter=splitter,
            output_dir=str(PROD_OUTPUT_DIR),
            chunk_size=1200,
            chunk_overlap=200,
        )

        logs.append(f"[Phase 1] process_one_file success={result.get('success')}, skipped={result.get('skipped')}")

        if not result.get("success"):
            error = f"process_one_file failed: {result.get('reason', 'unknown')}"
            logger.error(error)
            return {"source_id": source_id, "success": False, "error": error, "logs": logs}

        # 4. Extract document_id from result artifacts
        artifacts = result.get("artifacts", {})
        md_path = artifacts.get("md_path")
        if md_path:
            document_id = Path(md_path).stem
            logs.append(f"[Phase 1] MD saved: {md_path}")

        # 5. Check registry for the new document
        from core.identity_registry import load_identity_registry
        registry = load_identity_registry(str(PROD_REGISTRY))
        docs = registry.get("documents", {})

        new_docs = [
            (doc_id, doc) for doc_id, doc in docs.items()
            if doc.get("chunk_count", 0) > 0
            and doc.get("source_file") == source_name
        ]

        if new_docs:
            document_id = new_docs[0][0]
            chunk_count = new_docs[0][1].get("chunk_count", 0)
            logs.append(f"[Phase 1] Registry: doc_id={document_id}, chunks={chunk_count}")
        else:
            logs.append(f"[Phase 1] No new docs in registry for {source_name} — may be SKIP/duplicate")

        # 6. Build TSU records — filter registry to current source only (avoids
        #    scanning all 82+ docs in production registry on every single-source run)
        from core.tsu_builder import build_tsu_records

        filtered_docs = {
            doc_id: doc for doc_id, doc in docs.items()
            if doc.get("source_file") == source_name
        }
        if not filtered_docs:
            logs.append(f"[Phase 1] No registry docs for {source_name}, building TSU from scratch")
            # Use the full registry but note that no new docs were found
            all_records = build_tsu_records(registry, PROD_OUTPUT_DIR)
        else:
            filtered_registry = {"documents": filtered_docs}
            
            # Count total chunks to estimate time
            total_chunks = sum(d.get("chunk_count", 0) for d in filtered_docs.values())
            logs.append(f"[Phase 1] Building TSU for {len(filtered_docs)} doc(s), {total_chunks} total chunks...")
            logger.info(f"ns003: TSU building started for {source_name} ({total_chunks} chunks)")
            
            all_records = build_tsu_records(filtered_registry, PROD_OUTPUT_DIR)
            
            logger.info(f"ns003: TSU building completed for {source_name}: {len(all_records)} records")
            logs.append(f"[Phase 1] TSU records built: {len(all_records)} total")

        source_records = [
            r for r in all_records
            if source_name.replace(".pdf", "") in str(r.get("source_file", ""))
            or r.get("source_file") == source_name
        ]
        tsu_records_list = source_records

        logs.append(f"[Phase 1] TSU records built: {len(all_records)} total, {len(source_records)} for this source")

        if source_records:
            sample = source_records[0]
            logs.append(f"[Phase 1] Sample TSU record keys: {list(sample.keys())}")
            logs.append(f"[Phase 1] Sample claim length: {len(sample.get('claim', ''))}")

        return {
            "source_id": source_id,
            "success": True,
            "document_id": document_id,
            "chunk_count": chunk_count,
            "tsu_records": len(source_records),
            "tsu_source_records": source_records,
            "logs": logs,
            "error": None,
        }

    except Exception as e:
        error = f"Unexpected error: {e}\n{tb_module.format_exc()}"
        logger.error(error)
        return {"source_id": source_id, "success": False, "error": error, "logs": logs}


def embed_and_index_tsu(tsu_records, source_id):
    """Run TSU records through embedding -> Qdrant upsert."""
    logs = []

    try:
        if not tsu_records:
            return {"source_id": source_id, "success": False, "error": "No TSU records to embed", "logs": logs}

        logs.append(f"[Phase 2] Embedding {len(tsu_records)} TSU records for {source_id}")

        from NAE.pipeline.ingest import pipeline as ingest_pipeline
        from NAE.pipeline.ingest.state import IncrementalStateStore
        from qdrant_client import QdrantClient

        state_store_path = PROJECT_ROOT / "NAE" / "corpus" / "embeddings" / "state.json"
        state_store = IncrementalStateStore(path=state_store_path)

        # Map TSU records to NAE pipeline format
        nae_records = []
        for rec in tsu_records:
            nae_rec = {
                "id": rec.get("id", rec.get("tsu_id", "")),
                "claim": rec.get("claim", ""),
                "book": rec.get("book", ""),
                "page": rec.get("page", 0),
                "scriptures": rec.get("scriptures", []),
                "source_text": rec.get("source_text", ""),
                "author": rec.get("author", ""),
                "citations": rec.get("citations", []),
                "review_status": rec.get("review_status", "unverified"),
                "overall_score": rec.get("overall_score", 0.0),
                "tsu_schema_version": rec.get("tsu_schema_version", "1"),
                "collector_version": rec.get("collector_version", "1.1.0"),
                "canonical_version": rec.get("canonical_version", "2.0.0"),
                "source_id": rec.get("source_id", ""),
                "author_id": rec.get("author_id", ""),
                "work_id": rec.get("work_id", ""),
                "edition_id": rec.get("edition_id", ""),
            }
            nae_records.append(nae_rec)

        # Get existing Qdrant point count
        client = QdrantClient(url=QDRANT_URL)
        collection_info = client.get_collection(QDRANT_COLLECTION)
        pre_count = collection_info.points_count
        logs.append(f"[Phase 2] Qdrant pre-count: {pre_count} points")

        # Run incremental ingestion
        result = ingest_pipeline.apply(
            records=nae_records,
            state_store=state_store,
            qdrant_client=client,
        )

        logs.append(f"[Phase 2] Ingestion result: embedded={result.get('embedded', [])}, "
                    f"UNCHANGED={result.get('UNCHANGED', 0)}, indexed={result.get('indexed_count', 0)}")

        # Verify post-count
        post_collection_info = client.get_collection(QDRANT_COLLECTION)
        post_count = post_collection_info.points_count
        delta = post_count - pre_count
        logs.append(f"[Phase 2] Qdrant post-count: {post_count} points (delta: +{delta})")

        return {
            "source_id": source_id,
            "success": True,
            "embedded": result.get("embedded", []),
            "skipped": result.get("UNCHANGED", 0),
            "indexed_count": result.get("indexed_count", 0),
            "pre_qdrant_count": pre_count,
            "post_qdrant_count": post_count,
            "qdrant_delta": delta,
            "logs": logs,
            "error": None,
        }

    except Exception as e:
        error = f"Unexpected error in embedding/indexing: {e}\n{tb_module.format_exc()}"
        logger.error(error)
        return {"source_id": source_id, "success": False, "error": error, "logs": logs}


def verify_e2e(source_id, processing_result, embedding_result):
    """Verify end-to-end pipeline result."""
    logs = []
    green = True
    issues = []

    if not processing_result.get("success"):
        green = False
        issues.append(f"Processing failed: {processing_result.get('error')}")
    else:
        logs.append(f"[Verify] Processing: OK (doc_id={processing_result.get('document_id')}, chunks={processing_result.get('chunk_count')})")

    if not embedding_result.get("success"):
        green = False
        issues.append(f"Embedding failed: {embedding_result.get('error')}")
    else:
        logs.append(f"[Verify] Embedding: OK (embedded={len(embedding_result.get('embedded', []))}, delta={embedding_result.get('qdrant_delta')})")

    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(url=QDRANT_URL)
        points, _ = client.scroll(
            QDRANT_COLLECTION, limit=100, with_payload=True, with_vectors=False,
        )
        tsu_ids_in_qdrant = {p.payload.get("tsu_id") for p in points}
        logs.append(f"[Verify] Qdrant scroll: {len(points)} points sampled")

        if processing_result.get("tsu_source_records"):
            our_tsu_ids = {r.get("id") for r in processing_result["tsu_source_records"]}
            found = our_tsu_ids & tsu_ids_in_qdrant
            missing = our_tsu_ids - tsu_ids_in_qdrant
            if missing:
                green = False
                issues.append(f"TSU IDs not in Qdrant: {missing}")
            logs.append(f"[Verify] TSU IDs found in Qdrant: {len(found)}/{len(our_tsu_ids)}")

    except Exception as e:
        green = False
        issues.append(f"Qdrant verification error: {e}")

    return {"source_id": source_id, "green": green, "issues": issues, "logs": logs}


def process_all_sources():
    """Process all 10 QUALITY_PASSED sources incrementally."""
    state = load_registration_state()
    sources = get_quality_passed_sources(state)
    logger.info(f"Found {len(sources)} QUALITY_PASSED sources")

    baseline = load_baseline()
    pre_qdrant_count = baseline.get("qdrant_points", 0)
    logger.info(f"Baseline Qdrant points: {pre_qdrant_count}")

    results = {}
    total_tsu = 0
    total_embedded = 0
    total_indexed = 0
    failures = []

    for source_id in sources:
        logger.info(f"=== Processing {source_id} ===")

        proc_result = process_single_source(source_id)
        results[source_id] = {"processing": proc_result}

        if not proc_result.get("success"):
            failures.append(source_id)
            logger.warning(f"Skipping {source_id} due to processing failure")
            continue

        tsu_records = proc_result.get("tsu_source_records", [])
        total_tsu += len(tsu_records)

        emb_result = embed_and_index_tsu(tsu_records, source_id)
        results[source_id]["embedding"] = emb_result

        if emb_result.get("success"):
            total_embedded += len(emb_result.get("embedded", []))
            total_indexed += emb_result.get("indexed_count", 0)
        else:
            failures.append(source_id)

    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL)
    post_collection_info = client.get_collection(QDRANT_COLLECTION)
    post_count = post_collection_info.points_count

    return {
        "total_sources": len(sources),
        "successful": len(sources) - len(failures),
        "failures": failures,
        "total_tsu_records": total_tsu,
        "total_embedded": total_embedded,
        "total_indexed": total_indexed,
        "pre_qdrant_count": pre_qdrant_count,
        "post_qdrant_count": post_count,
        "qdrant_delta": post_count - pre_qdrant_count,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Night Shift Order 003")
    parser.add_argument("--phase", choices=["1", "2", "3", "4", "all"], default="all")
    parser.add_argument("--source", default=None, help="Specific source_id to process")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Night Shift Order 003 - NAE TSU -> Embedding -> Qdrant")
    logger.info("=" * 60)

    state = load_registration_state()
    quality_passed = get_quality_passed_sources(state)
    logger.info(f"QUALITY_PASSED sources: {quality_passed}")

    if args.phase in ("1", "2", "3") and not args.source:
        args.source = quality_passed[0] if quality_passed else None

    if args.source:
        logger.info(f"Target source: {args.source}")

    # Phase 1
    if args.phase in ("1", "all"):
        logger.info("\\n" + "=" * 40)
        logger.info("PHASE 1: Registration -> Extraction -> TSU")
        logger.info("=" * 40)
        source = args.source or quality_passed[0] if quality_passed else None
        if source:
            proc_result = process_single_source(source)
            save_json(LOG_DIR / f"phase1_{source}.json", proc_result)
            logger.info(f"Phase 1: success={proc_result.get('success')}, tsu={proc_result.get('tsu_records', 0)}")
            for log in proc_result.get("logs", []):
                logger.info(f"  {log}")
        else:
            logger.warning("No QUALITY_PASSED source available")

    # Phase 2
    if args.phase in ("2", "all"):
        logger.info("\\n" + "=" * 40)
        logger.info("PHASE 2: TSU -> BGE-M3 Embedding -> Qdrant")
        logger.info("=" * 40)
        source = args.source or quality_passed[0] if quality_passed else None
        if source:
            phase1_path = LOG_DIR / f"phase1_{source}.json"
            if phase1_path.exists():
                phase1 = load_json(phase1_path)
                tsu_records = phase1.get("tsu_source_records", [])
                emb_result = embed_and_index_tsu(tsu_records, source)
                save_json(LOG_DIR / f"phase2_{source}.json", emb_result)
                logger.info(f"Phase 2: success={emb_result.get('success')}, "
                           f"embedded={len(emb_result.get('embedded', []))}, "
                           f"qdrant_delta={emb_result.get('qdrant_delta')}")
            else:
                logger.warning(f"Phase 1 result not found for {source}")

    # Phase 3
    if args.phase in ("3", "all"):
        logger.info("\\n" + "=" * 40)
        logger.info("PHASE 3: End-to-End Verification")
        logger.info("=" * 40)
        source = args.source or quality_passed[0] if quality_passed else None
        if source:
            p1 = LOG_DIR / f"phase1_{source}.json"
            p2 = LOG_DIR / f"phase2_{source}.json"
            if p1.exists() and p2.exists():
                verify_result = verify_e2e(source, load_json(p1), load_json(p2))
                save_json(LOG_DIR / f"phase3_{source}.json", verify_result)
                status = "GREEN" if verify_result["green"] else "RED"
                logger.info(f"Phase 3: {status}")
                for issue in verify_result.get("issues", []):
                    logger.warning(f"  ISSUE: {issue}")
            else:
                logger.warning("Phase 1 or Phase 2 result not found")

    # Phase 4
    if args.phase in ("4", "all"):
        logger.info("\\n" + "=" * 40)
        logger.info("PHASE 4: Incremental Processing - All 10 Sources")
        logger.info("=" * 40)
        final_result = process_all_sources()
        save_json(LOG_DIR / "phase4_all_sources.json", final_result)

        logger.info("\\n" + "=" * 40)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 40)
        logger.info(f"Total sources: {final_result['total_sources']}")
        logger.info(f"Successful: {final_result['successful']}")
        logger.info(f"Failures: {final_result['failures']}")
        logger.info(f"TSU records: {final_result['total_tsu_records']}")
        logger.info(f"Embedded: {final_result['total_embedded']}")
        logger.info(f"Indexed: {final_result['total_indexed']}")
        logger.info(f"Qdrant delta: {final_result['qdrant_delta']}")

        report = {"order": "NS003", "timestamp": now_iso(), "summary": final_result}
        save_json(LOG_DIR / "ns003_final_report.json", report)

    logger.info("\\nNight Shift Order 003 complete.")


if __name__ == "__main__":
    main()
