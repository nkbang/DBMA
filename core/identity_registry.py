"""core/identity_registry.py — Persistent Document Identity Registry.

Manages document identity persistence across processing sessions.
Provides duplicate detection via content hash comparison.

Registry file location: output/registry/documents.json

Usage:
    from core.identity_registry import (
        load_identity_registry,
        register_document,
        find_by_document_id,
        find_by_file_hash,
        save_identity_registry,
    )

    registry = load_identity_registry("output/registry/documents.json")
    record, is_new = register_document(registry, document_meta)
    save_identity_registry(registry, "output/registry/documents.json")
"""

from __future__ import annotations

import json
import os
import datetime
from typing import Optional, Dict, Tuple, Literal
from core.document_identity import PROCESSING_VERSION


def load_identity_registry(registry_path: str) -> dict:
    """Load registry from disk. Creates empty if not exists.

    Args:
        registry_path: Full path to documents.json

    Returns:
        Registry dictionary (always valid, never None)
    """
    if not os.path.exists(registry_path):
        return _empty_registry()

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        sv = data.get("schema_version", "1.0")
        if sv not in ("1.0", "2.0"):
            return _empty_registry()  # Incompatible schema → start fresh

        # Migration needed for v1.0 → v2.0
        migrate_registry_schema(data)

        return data
    except (json.JSONDecodeError, OSError):
        return _empty_registry()  # Corruption → recover by rebuilding


def _empty_registry() -> dict:
    """Create a fresh empty registry structure."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    return {
        "schema_version": "2.0",
        "processing_version": PROCESSING_VERSION,
        "created_at": now,
        "updated_at": now,
        "documents": {},
        "_meta": {"total_documents": 0},
    }


def register_document(
    registry: dict,
    metadata: dict,
    output_dir: str = "",
) -> Tuple[dict, bool]:
    """Register document or detect duplicate.

    Args:
        registry: Current registry dict (mutated if new document)
        metadata: Document metadata from build_document_metadata()
        output_dir: Output directory (for context/logging)

    Returns:
        (document_record, is_new_entry)
    """
    doc_id = metadata.get("document_id", "")
    file_hash = metadata.get("file_hash", "")

    # Check 1: Exact document_id match
    if doc_id and doc_id in registry["documents"]:
        return (registry["documents"][doc_id], False)

    # Check 2: Content hash match (handles filename changes)
    if file_hash:
        for existing_doc in registry["documents"].values():
            if existing_doc.get("file_hash") == file_hash:
                return (existing_doc, False)

    # New document — build record
    record = {
        "document_id": doc_id,
        "file_hash": file_hash,
        "source_file": metadata.get("source_file", ""),
        "created_at": metadata.get(
            "created_at", datetime.datetime.now().isoformat(timespec="seconds")
        ),
        "processing_version": metadata.get(
            "processing_version", PROCESSING_VERSION
        ),
        "status": "processed",
        # Conditional fields (defaults if unknown)
        "chunk_count": metadata.get("chunk_count", 0),
        "language": metadata.get("language", "-"),
        "noise_score": metadata.get("noise_score", 0.0),
        "noise_mode": metadata.get("noise_mode", "-"),
        "source_type": metadata.get("source_type", ""),
        "is_ocr": metadata.get("is_ocr", False),
        # Optional fields (None = unknown — never invent)
        "book": metadata.get("book"),
        "chapter": metadata.get("chapter"),
        "page": metadata.get("page"),
        "title": metadata.get("title"),
        "author": metadata.get("author"),
    }

    registry["documents"][doc_id] = record
    registry["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    registry["_meta"]["total_documents"] = len(registry["documents"])

    return (record, True)


def find_by_document_id(registry: dict, document_id: str) -> Optional[dict]:
    """Lookup by document ID.

    Returns the document record if found, None otherwise.
    """
    return registry["documents"].get(document_id)


def find_by_file_hash(registry: dict, file_hash: str) -> Optional[dict]:
    """Lookup by content hash (for filename-change detection).

    Returns the document record if found, None otherwise.
    """
    for doc in registry["documents"].values():
        if doc.get("file_hash") == file_hash:
            return doc
    return None


def migrate_registry_schema(registry: dict) -> bool:
    """Upgrade v1.0 → v2.0, backward-compatible.

    Appends new ingest processing fields to all documents if missing.
    Always idempotent — safe to call multiple times.

    Args:
        registry: Registry dict (possibly v1.0)

    Returns:
        True if any changes were made, False otherwise
    """
    changed = False

    # Upgrade top-level schema version if needed
    sv = registry.get("schema_version", "1.0")
    if sv not in ("1.0", "2.0"):
        sv = "1.0"  # default fallback for truly unknown schemas

    if sv != "2.0":
        registry["schema_version"] = "2.0"
        changed = True

    # Document-level migration (append-only — never modifies existing fields)
    for doc_id, record in registry["documents"].items():
        if "last_content_hash" not in record:
            record["last_content_hash"] = record.get("file_hash")
            changed = True

        if "ingest_status" not in record:
            # Default from old "processed" status
            record["ingest_status"] = "PROCESSED"
            changed = True

        if "retry_count" not in record:
            record["retry_count"] = 0
            changed = True

        if "max_retries" not in record:
            record["max_retries"] = 3
            changed = True

        if "last_failure_reason" not in record:
            record["last_failure_reason"] = None
            changed = True

        if "last_processed_at" not in record:
            record["last_processed_at"] = record.get("updated_at", record.get("created_at"))
            changed = True

    return changed


# ── Ingest Decision Engine (PT-PROCESSING-012) ──────────────


def classify_ingest_decision(
    registry: dict,
    doc_id: Optional[str],
    current_hash: str,
) -> Tuple[Literal["PROCESS", "SKIP", "REPROCESS", "RETRY"], Optional[dict]]:
    """Classify ingest decision for a document.

    Decision logic (PT-011 design):

        B1  No match by doc_id or hash → PROCESS (new document)
        B2  Status = ABANDONED → SKIP (manual intervention required)
        B3  Status = FAILED, retries < max → RETRY
        B4  Status = FAILED, retries >= max → REPROCESS
        B5  last_content_hash == current_hash → SKIP (unchanged)
        B6  last_content_hash != current_hash → REPROCESS (modified)
        B7  No last_content_hash set (pre-migration) → PROCESS

    Args:
        registry: Current registry dict (read-only)
        doc_id: Document ID from generate_document_id()
        current_hash: SHA-256 content hash of the file

    Returns:
        (decision, record) where record may be None for B1
    """
    # Look up existing record by doc_id or hash
    record = None
    if doc_id:
        record = registry["documents"].get(doc_id)
    if record is None and current_hash:
        for _r in registry["documents"].values():
            if _r.get("file_hash") == current_hash:
                record = _r
                break

    # B1: No existing record → new document
    if record is None:
        return ("PROCESS", None)

    status = record.get("ingest_status", "PROCESSED")

    # B2: Abandoned → skip (do not auto-retry forever)
    if status == "ABANDONED":
        return ("SKIP", record)

    # B3/B4: Failed status — check retry count
    if status == "FAILED":
        retries = record.get("retry_count", 0)
        max_r = record.get("max_retries", 3)
        if retries < max_r:
            return ("RETRY", record)
        else:
            return ("REPROCESS", record)

    # B5/B6: PROCESSED status — check content hash
    last_hash = record.get("last_content_hash")
    if last_hash is None:
        # B7: Pre-migration document — treat as new
        return ("PROCESS", record)

    if last_hash == current_hash:
        return ("SKIP", record)  # B5
    else:
        return ("REPROCESS", record)  # B6


def update_content_hash(registry: dict, doc_id: str, hash_value: str) -> bool:
    """Update last_content_hash and file_hash for a document.

    Args:
        registry: Registry dict (mutated if found)
        doc_id: Document ID
        hash_value: New content hash value

    Returns:
        True if record was found and updated, False otherwise
    """
    record = registry["documents"].get(doc_id)
    if record is None:
        return False

    record["last_content_hash"] = hash_value
    record["file_hash"] = hash_value
    record["ingest_status"] = "PROCESSED"
    record["retry_count"] = 0
    record["last_failure_reason"] = None
    record["last_processed_at"] = datetime.datetime.now().isoformat(timespec="seconds")

    return True


def transition_ingest_status(
    registry: dict,
    doc_id: str,
    new_status: Literal["PROCESSED", "FAILED", "ABANDONED"],
    failure_reason: Optional[str] = None,
) -> bool:
    """Transition document ingest status in the registry.

    Args:
        registry: Registry dict (mutated if found)
        doc_id: Document ID
        new_status: Target status value
        failure_reason: Failure description (for FAILED status)

    Returns:
        True if record was found and transitioned, False otherwise
    """
    record = registry["documents"].get(doc_id)
    if record is None:
        return False

    record["ingest_status"] = new_status

    if new_status == "PROCESSED":
        record["retry_count"] = 0
        record["last_failure_reason"] = None
        record["last_processed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    elif new_status == "FAILED":
        record["retry_count"] = record.get("retry_count", 0) + 1
        record["last_failure_reason"] = failure_reason
    # ABANDONED: no additional side effects

    return True


def save_identity_registry(registry: dict, registry_path: str) -> bool:
    """Save registry to disk atomically.

    Uses .tmp + os.replace() for atomic swap on POSIX systems.

    Args:
        registry: Registry dictionary to persist
        registry_path: Target file path

    Returns:
        True on success, False on failure
    """
    tmp_path: Optional[str] = None
    try:
        os.makedirs(os.path.dirname(registry_path), exist_ok=True)

        # Write to temp file first
        tmp_path = registry_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        # Atomic swap (POSIX guarantees this is indivisible)
        os.replace(tmp_path, registry_path)
        return True

    except (IOError, OSError):
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return False
