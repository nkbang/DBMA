"""Author/Work Authority lookup and registration (ADR-021 SS4, Option C).

Two physically separate stores:
  - Legacy snapshot (NAE/authority/legacy_snapshot/*.yaml) — READ ONLY,
    generated once by scripts/generate_legacy_authority_snapshot.py from
    the 4,117 existing TSU records. This module never writes to it.
  - New registry (NAE/authority/{authors,works}.yaml) — the only write
    target for newly registered sources. Starts empty; nothing is
    back-derived into it from the legacy snapshot.

Merge is never automatic — a name-normalization match against either
store is surfaced as a *candidate* for a human to confirm, per
NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 4 (misattribution risk).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

from . import config

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize(name: str) -> str:
    return _NORMALIZE_RE.sub("", name.lower())


def _load_yaml(path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@dataclass(frozen=True)
class AuthorCandidate:
    author_id: str
    canonical_name: str
    source: str  # "legacy_snapshot" | "new_registry"


def find_author_candidates(name: str) -> list[AuthorCandidate]:
    """Read-only lookup across both stores. Never merges automatically —
    returns candidates for a human to confirm or reject."""
    target = _normalize(name)
    candidates: list[AuthorCandidate] = []

    legacy = _load_yaml(config.LEGACY_SNAPSHOT_DIR / "authors.yaml")
    for a in legacy.get("authors", []) or []:
        if _normalize(a.get("canonical_name", "")) == target:
            candidates.append(AuthorCandidate(a["author_id"], a["canonical_name"], "legacy_snapshot"))

    new = _load_yaml(config.NEW_AUTHORS_PATH)
    for a in new.get("authors", []) or []:
        if _normalize(a.get("canonical_name", "")) == target:
            candidates.append(AuthorCandidate(a["author_id"], a["canonical_name"], "new_registry"))

    return candidates


def register_author(author_id: str, canonical_name: str) -> None:
    """Writes ONLY to the new registry. Never touches the legacy snapshot."""
    data = _load_yaml(config.NEW_AUTHORS_PATH)
    authors = data.get("authors") or []
    if any(a["author_id"] == author_id for a in authors):
        return  # idempotent — already registered
    authors.append({"author_id": author_id, "canonical_name": canonical_name})
    data["authors"] = authors
    config.NEW_AUTHORS_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@dataclass(frozen=True)
class WorkCandidate:
    work_id: str
    canonical_title: str
    author_id: str
    source: str


def find_work_candidates(title: str, author_id: str) -> list[WorkCandidate]:
    target = _normalize(title)
    candidates: list[WorkCandidate] = []

    legacy = _load_yaml(config.LEGACY_SNAPSHOT_DIR / "works.yaml")
    for w in legacy.get("works", []) or []:
        if _normalize(w.get("canonical_title", "")) == target and w.get("author_id") == author_id:
            candidates.append(WorkCandidate(w["work_id"], w["canonical_title"], w["author_id"], "legacy_snapshot"))

    new = _load_yaml(config.NEW_WORKS_PATH)
    for w in new.get("works", []) or []:
        if _normalize(w.get("canonical_title", "")) == target and w.get("author_id") == author_id:
            candidates.append(WorkCandidate(w["work_id"], w["canonical_title"], w["author_id"], "new_registry"))

    return candidates


def register_work(work_id: str, canonical_title: str, author_id: str) -> None:
    """Writes ONLY to the new registry. Never touches the legacy snapshot."""
    data = _load_yaml(config.NEW_WORKS_PATH)
    works = data.get("works") or []
    if any(w["work_id"] == work_id for w in works):
        return
    works.append({"work_id": work_id, "canonical_title": canonical_title, "author_id": author_id})
    data["works"] = works
    config.NEW_WORKS_PATH.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
