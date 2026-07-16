#!/usr/bin/env python3
"""scripts/build_tsu_dataset.py — TSU v1 batch builder (skeleton).

SPRINT17-RG-6A: minimal batch post-processing step that turns already-processed
documents (identity registry + saved chunk text) into TSU records.

Design decisions (per SPRINT17-RG-5):
  - Batch post-processing, run separately from ingest (core/processing.py
    untouched) and separately from query time (core/retrieval.py untouched).
  - TSU schema is additive to what core/retrieval.py::RetrievalEngine already
    reads (tsu_id, content, verse_mapping, themes) plus two new link fields
    (document_id, chunk_id) that close the mapping gap identified in
    SPRINT17-RG-1/RG-4.
  - chunk_id is synthesized deterministically via
    core.document_identity.generate_chunk_id(document_id, idx) for
    idx in range(chunk_count) — the registry does not store chunk texts, so
    this script does not invent a new storage format for them; it reads the
    existing {stem}_chunks.txt file (save_chunks() output) when present.

Usage:
    python scripts/build_tsu_dataset.py --output-dir output
    python scripts/build_tsu_dataset.py --output-dir output --dry-run
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

from core.identity_registry import load_identity_registry
from core.document_identity import generate_chunk_id
from core.utils import make_safe_stem
from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_TSU_DATASET_PATH, DEFAULT_TSU_MANIFEST_PATH
from core.retrieval import NAME_TO_BOOK_ID

_CHUNK_HEADER_RE = re.compile(r"\[chunk \d+\]\n")


def _resolve_book_id(source_file: str) -> Optional[str]:
    """Derive a book_id from source_file by substring match against
    core.retrieval.NAME_TO_BOOK_ID (the ADR-001 authoritative Korean/
    English book-name table QueryParser already uses to interpret user
    queries — reused here read-only, not redefined).

    [SPRINT17-Phase6A-1] registry.book is None for every currently
    registered document (Dataset Quality Audit finding), so every TSU
    record was previously tagged "GEN" regardless of actual content.
    This is a best-effort filename match, not a substitute for populating
    registry.book at ingest time (out of scope here — see Phase6A-1 plan
    §2, Location A).

    Longer names are checked first so e.g. "2 kings" doesn't shadow a
    later, more specific match; ties within the same length keep dict
    iteration order.

    Single-character aliases (e.g. "마" as a short-form query alias for
    MAT) are excluded — QueryParser only ever matches them via a
    word-boundary regex against short user queries (core/retrieval.py
    L405), never as a raw substring against arbitrary text. Applying the
    same substring test used for full book names here produced a false
    positive: "마가복음" (Mark) contains "마" and was silently
    misresolved to MAT (Matthew) before this guard was added.

    source_file is normalized to NFC before matching — macOS stores
    Korean filenames in NFD (decomposed) form in the registry, while
    NAME_TO_BOOK_ID's keys are NFC (composed); without this, byte-level
    substring matching silently fails for every Korean filename despite
    looking identical when printed (same fix pattern as
    ui/pages/library.py's PT-SEARCH-001 search-query normalization).
    """
    text = unicodedata.normalize("NFC", source_file).lower()
    candidates = [name for name in NAME_TO_BOOK_ID if len(name) >= 2]
    for name in sorted(candidates, key=len, reverse=True):
        if name in text:
            return NAME_TO_BOOK_ID[name]
    return None


def _read_chunk_texts(output_dir: Path, source_file: str) -> Optional[list[str]]:
    """Read per-chunk text from the deprecated {stem}_chunks.txt output, if present.

    Returns None if the file does not exist (e.g. SPRINT1_ONLY_MD_OUTPUT=True
    was in effect when the document was processed).
    """
    stem = make_safe_stem(source_file)
    txt_path = output_dir / f"{stem}_chunks.txt"
    if not txt_path.exists():
        return None

    raw = txt_path.read_text(encoding="utf-8")
    parts = [p.strip() for p in _CHUNK_HEADER_RE.split(raw) if p.strip()]
    return parts or None


def _read_md_fallback(output_dir: Path, source_file: str) -> Optional[str]:
    """Fallback content source: the canonical {stem}.md file.

    Used only when per-chunk text is unavailable. Coarser than real chunk
    boundaries — acceptable for a v1 skeleton, not a substitute for proper
    chunk-level TSU content in a later phase.
    """
    stem = make_safe_stem(source_file)
    md_path = output_dir / f"{stem}.md"
    if not md_path.exists():
        return None
    return md_path.read_text(encoding="utf-8")


def build_tsu_records(registry: dict, output_dir: Path) -> list[dict[str, Any]]:
    """Build TSU v1 records from identity registry documents.

    Read-only with respect to the registry and to core/processing.py output —
    this function only reads existing files, it does not call
    save_identity_registry() or otherwise mutate the registry.
    """
    records: list[dict[str, Any]] = []

    for document_id, doc in registry.get("documents", {}).items():
        source_file = doc.get("source_file", "")
        chunk_count = doc.get("chunk_count", 0)
        if chunk_count <= 0:
            continue

        chunk_ids = [generate_chunk_id(document_id, idx) for idx in range(chunk_count)]

        chunk_texts = _read_chunk_texts(output_dir, source_file)
        if chunk_texts is None:
            fallback_text = _read_md_fallback(output_dir, source_file) or ""
            chunk_texts = [fallback_text] * chunk_count

        # [SPRINT17-Phase6A-1] registry.book takes priority if a future
        # ingest-time fix populates it (see Phase6A-1 plan §2, Location A);
        # until then, fall back to filename-based resolution instead of the
        # previous unconditional "GEN" default, which mislabeled every
        # record regardless of actual content (Dataset Quality Audit
        # finding). "UNK" means no match was found — never invented.
        book_id = doc.get("book") or _resolve_book_id(source_file) or "UNK"

        for idx, chunk_id in enumerate(chunk_ids):
            content = chunk_texts[idx] if idx < len(chunk_texts) else ""
            records.append({
                "tsu_id": f"TSU-{book_id}-{len(records) + 1:06d}",
                "document_id": document_id,
                "chunk_id": chunk_id,
                "content": content,
                "verse_mapping": {"book_id": book_id} if book_id != "UNK" else {},
                "themes": [],
                # [SPRINT17-Phase5-C1] M1-a — propagate document metadata
                # already present in identity_registry/DocumentContext
                # (Phase1-2) into TSU records, closing the gap identified in
                # Phase5-C0 preflight (dbma.py's 2026-07-15 metadata commits
                # were write-only and never consumed; this is the intended
                # target path instead).
                "title": doc.get("title"),
                "author": doc.get("author"),
                "chapter": doc.get("chapter"),
                "page": doc.get("page"),
            })

    return records


def write_tsu_dataset(records: list[dict[str, Any]], dataset_path: Path) -> None:
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dataset_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def write_manifest(records: list[dict[str, Any]], registry: dict, manifest_path: Path) -> dict:
    source_document_count = len({
        doc_id for doc_id, doc in registry.get("documents", {}).items()
        if doc.get("chunk_count", 0) > 0
    })
    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "tsu_count": len(records),
        "source_document_count": source_document_count,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build TSU v1 dataset from the identity registry.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Processing output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--dry-run", action="store_true", help="Build in memory only; do not write files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    registry_path = output_dir / "registry" / "documents.json"
    dataset_path = Path(DEFAULT_TSU_DATASET_PATH)
    manifest_path = Path(DEFAULT_TSU_MANIFEST_PATH)

    registry = load_identity_registry(str(registry_path))
    records = build_tsu_records(registry, output_dir)

    if args.dry_run:
        print(f"[DRY-RUN] would write {len(records)} TSU records to {dataset_path}")
        for rec in records[:3]:
            print(json.dumps(rec, ensure_ascii=False))
        manifest = {
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "tsu_count": len(records),
            "source_document_count": len({r["document_id"] for r in records}),
        }
        print(f"[DRY-RUN] manifest: {json.dumps(manifest, ensure_ascii=False)}")
        return

    write_tsu_dataset(records, dataset_path)
    manifest = write_manifest(records, registry, manifest_path)
    print(f"Wrote {len(records)} TSU records to {dataset_path}")
    print(f"Wrote manifest to {manifest_path}: {manifest}")


if __name__ == "__main__":
    main()
