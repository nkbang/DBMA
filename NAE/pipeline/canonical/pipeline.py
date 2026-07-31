"""Phase 2 - Canonical Normalization Pipeline orchestrator.

Stage 2.1 extract + normalize -> Stage 2.2 structure cleanup ->
Stage 2.3 paragraph reflow -> Stage 2.4 canonical output.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config, extract, normalize, reflow, structure

logger = logging.getLogger("nae.canonical.pipeline")


def normalize_item(item_dir: Path, *, identifier: str | None = None) -> dict[str, Any]:
    """Run the full canonical pipeline for one collected item directory."""
    identifier = identifier or item_dir.name

    extraction = extract.extract_pages(item_dir)
    if extraction.source == "none" or not extraction.pages:
        report = {
            "identifier": identifier,
            "status": "failed",
            "reason": "no_extractable_source",
            "pipeline_version": config.PIPELINE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "failed", "report": report}

    chars_before = sum(len(p) for p in extraction.pages)

    normalized_pages = [normalize.normalize_page(p) for p in extraction.pages]
    line_pages = [p.split("\n") for p in normalized_pages]

    cleaned_pages, structure_report = structure.apply_structure_cleanup(line_pages)
    paragraphs = reflow.reconstruct_paragraphs(cleaned_pages)

    canonical_text = "\n\n".join(p.text for p in paragraphs if p.text)
    chars_after = len(canonical_text)

    scripture_refs: list[str] = []
    for p in paragraphs:
        scripture_refs.extend(reflow.find_scripture_references(p.text))

    canonical_json = {
        "identifier": identifier,
        "pipeline_version": config.PIPELINE_VERSION,
        "source": extraction.source,
        "page_count": len(extraction.pages),
        "paragraphs": [asdict(p) for p in paragraphs],
        "footnotes": structure_report.footnotes_extracted,
        "scripture_references": sorted(set(scripture_refs)),
    }

    normalize_report = {
        "identifier": identifier,
        "status": "ok",
        "pipeline_version": config.PIPELINE_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": extraction.source,
        "page_count": len(extraction.pages),
        "characters_before": chars_before,
        "characters_after": chars_after,
        "paragraph_count": len(paragraphs),
        "verse_paragraph_count": sum(1 for p in paragraphs if p.type == "verse"),
        "headers_footers_removed": structure_report.headers_footers_removed,
        "page_numbers_removed": structure_report.page_numbers_removed,
        "toc_pages_removed": structure_report.toc_pages_removed,
        "scan_noise_lines_removed": structure_report.scan_noise_lines_removed,
        "footnotes_extracted": len(structure_report.footnotes_extracted),
        "scripture_references_found": len(canonical_json["scripture_references"]),
    }

    return {
        "status": "ok",
        "canonical_text": canonical_text,
        "canonical_json": canonical_json,
        "report": normalize_report,
    }


def write_canonical_output(result: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if result["status"] == "ok":
        (out_dir / "canonical.txt").write_text(result["canonical_text"], encoding="utf-8")
        with open(out_dir / "canonical.json", "w", encoding="utf-8") as fh:
            json.dump(result["canonical_json"], fh, ensure_ascii=False, indent=2)
    with open(out_dir / "normalize_report.json", "w", encoding="utf-8") as fh:
        json.dump(result["report"], fh, ensure_ascii=False, indent=2)


def process_identifier(identifier: str, *, raw_root: Path = config.RAW_ROOT,
                        canonical_root: Path = config.CANONICAL_ROOT) -> dict[str, Any]:
    item_dir = None
    for category_dir in raw_root.iterdir() if raw_root.exists() else []:
        candidate = category_dir / identifier
        if candidate.exists():
            item_dir = candidate
            break
    if item_dir is None:
        report = {
            "identifier": identifier,
            "status": "failed",
            "reason": "raw_item_not_found",
            "pipeline_version": config.PIPELINE_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "failed", "report": report}

    result = normalize_item(item_dir, identifier=identifier)
    write_canonical_output(result, canonical_root / identifier)
    return result


def process_all(*, raw_root: Path = config.RAW_ROOT, canonical_root: Path = config.CANONICAL_ROOT) -> dict[str, Any]:
    if not raw_root.exists():
        return {"processed": 0, "ok": 0, "failed": 0, "identifiers": []}

    identifiers = [
        item_dir.name
        for category_dir in raw_root.iterdir() if category_dir.is_dir()
        for item_dir in category_dir.iterdir() if item_dir.is_dir()
    ]

    summary = {"processed": 0, "ok": 0, "failed": 0, "identifiers": []}
    for identifier in identifiers:
        result = process_identifier(identifier, raw_root=raw_root, canonical_root=canonical_root)
        summary["processed"] += 1
        summary["ok" if result["status"] == "ok" else "failed"] += 1
        summary["identifiers"].append({"identifier": identifier, "status": result["status"]})
    return summary
