"""source_manifest.yaml entry writer — reuses the existing v1.2 schema
(resources/theological_sources/*/source_manifest.schema.yaml) unmodified.

Caller supplies the target manifest path explicitly (no hardcoded default
directory) — this follows the same "always explicit, never inferred"
dataset-path discipline as ADR-015 SS3.6-3.7 / ADR-020's --dataset-path
requirement, so a new source can never silently land in the wrong
category/dataset.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {"schema_version": "1.2", "sources": []}
    return yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {"schema_version": "1.2", "sources": []}


def existing_source_ids(manifest_path: Path) -> set[str]:
    data = _load(manifest_path)
    return {s["source_id"] for s in data.get("sources", []) if s.get("source_id")}


def write_entry(manifest_path: Path, entry: dict[str, Any]) -> None:
    """Appends one entry. Raises if source_id already exists — this module
    never overwrites (ADR-021 SS4 collision rule applies at identity
    issuance time; manifest write time is a second, cheap uniqueness
    check)."""
    source_id = entry.get("source_id")
    if not source_id:
        raise ValueError("entry missing source_id")

    data = _load(manifest_path)
    sources = data.setdefault("sources", [])
    if any(s.get("source_id") == source_id for s in sources):
        raise ValueError(f"source_id already registered in {manifest_path}: {source_id}")

    sources.append(entry)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
