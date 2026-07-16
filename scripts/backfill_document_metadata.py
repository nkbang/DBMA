#!/usr/bin/env python3
"""scripts/backfill_document_metadata.py — one-time registry metadata backfill.

SPRINT17-Phase6A-4: title/author/book were None for every currently
registered document because core/processing.py's incremental-ingest gate
(classify_ingest_decision) SKIPs unchanged files and never re-runs
extraction — simply reprocessing does not fill these fields (Phase6A-3
Dataset Quality Audit finding §3).

This script bypasses full reprocessing: it reads each raw source file
directly with the same extractors already wired into the pipeline
(core.extractors PDF docinfo / DOCX core_properties, and
scripts.build_tsu_dataset's filename-based book_id resolver) and writes
the results straight into the identity registry — the same registry
core/processing.py and scripts/build_tsu_dataset.py already read from.

Read-only with respect to raw source files. Only fills fields that are
currently None — never overwrites a value a human already set via
ui/pages/library.py's manual correction form.

Usage:
    python -m scripts.backfill_document_metadata --dry-run
    python -m scripts.backfill_document_metadata
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

from core.identity_registry import load_identity_registry, save_identity_registry
from core.config import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_DIR
from core.extractors import _extract_pdf_title_author, _extract_docx_title_author
from scripts.build_tsu_dataset import _resolve_book_id

# [SPRINT17-Phase6A-4] Known-junk values seen in embedded PDF metadata on
# this corpus's scanned documents — a scanner/OCR tool's internal document
# ID stamped into the title field, and a generic placeholder author. Both
# are worse than leaving the field None (None is honestly "unknown"; these
# look like real data but are not), so they are rejected rather than
# accepted like any other extracted value.
_SCANNER_ID_TITLE_RE = re.compile(r"^\d{2}[A-Za-z]-\d[a-z]-\d{14}$")
_JUNK_AUTHOR_VALUES = {"holy bible"}


def _is_usable_title(title: Optional[str]) -> bool:
    if not title:
        return False
    return not _SCANNER_ID_TITLE_RE.match(title.strip())


def _is_usable_author(author: Optional[str]) -> bool:
    if not author:
        return False
    return author.strip().lower() not in _JUNK_AUTHOR_VALUES


def _extract_title_author(raw_path: Path) -> tuple[Optional[str], Optional[str]]:
    ext = raw_path.suffix.lower()
    if ext == ".pdf":
        title, author = _extract_pdf_title_author(str(raw_path))
    elif ext == ".docx":
        title, author = _extract_docx_title_author(str(raw_path))
    else:
        return None, None
    return (
        title if _is_usable_title(title) else None,
        author if _is_usable_author(author) else None,
    )


def backfill(registry: dict, raw_dir: Path) -> list[dict]:
    """Fill title/author/book for documents that are missing them.

    Returns a list of per-document change summaries (dry-run and real
    run share this so --dry-run output matches what would actually happen).
    """
    changes = []
    for doc_id, doc in registry.get("documents", {}).items():
        source_file = doc.get("source_file", "")
        needs_title = doc.get("title") is None
        needs_author = doc.get("author") is None
        needs_book = doc.get("book") is None
        if not (needs_title or needs_author or needs_book):
            continue

        raw_path = raw_dir / source_file
        change = {"document_id": doc_id, "source_file": source_file, "found_file": raw_path.exists()}

        if raw_path.exists():
            if needs_title or needs_author:
                title, author = _extract_title_author(raw_path)
                if needs_title and title:
                    change["title"] = title
                if needs_author and author:
                    change["author"] = author
            if needs_book:
                book_id = _resolve_book_id(source_file)
                if book_id:
                    change["book"] = book_id

        if len(change) > 3:  # more than just document_id/source_file/found_file
            changes.append(change)

    return changes


def apply_changes(registry: dict, changes: list[dict]) -> int:
    applied = 0
    for change in changes:
        doc = registry["documents"].get(change["document_id"])
        if doc is None:
            continue
        for field in ("title", "author", "book"):
            if field in change:
                doc[field] = change[field]
                applied += 1
    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill title/author/book for registered documents.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry_path = Path(args.output_dir) / "registry" / "documents.json"
    raw_dir = Path(args.raw_dir)

    registry = load_identity_registry(str(registry_path))
    changes = backfill(registry, raw_dir)

    print(f"{len(changes)} document(s) have fillable fields:")
    for c in changes:
        fields = {k: v for k, v in c.items() if k not in ("document_id", "source_file", "found_file")}
        print(f"  {c['source_file']}: {fields}")

    if args.dry_run:
        print("[DRY-RUN] no changes written.")
        return

    applied = apply_changes(registry, changes)
    if applied:
        save_identity_registry(registry, str(registry_path))
    print(f"Applied {applied} field update(s) across {len(changes)} document(s). Registry saved: {str(registry_path)}")


if __name__ == "__main__":
    main()
