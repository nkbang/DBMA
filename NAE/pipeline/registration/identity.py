"""Identity issuance for new sources (ADR-021 SS4).

Mirrors NAE/pipeline/ingest/identity.py's layer (Author -> Work -> Edition
-> Source File) but runs in the opposite direction: that module *extracts*
identity from TSU records that already exist; this module *issues* identity
for a source that doesn't have one yet.

Collision handling: never silently overwrite. A slug collision gets a
numeric suffix (-2, -3, ...) and the caller is expected to record the
collision in the entry's notes (ADR-021 SS4 / NAE_CORPUS_INGESTION_STANDARD_v1.md
Phase 3).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase, non-alnum runs collapsed to a single underscore, trimmed."""
    return _SLUG_RE.sub("_", text.strip().lower()).strip("_")


@dataclass(frozen=True)
class CollisionResult:
    id: str
    collided: bool
    original_candidate: str


def resolve_collision(candidate: str, existing_ids: set[str]) -> CollisionResult:
    """Returns `candidate` unchanged if free; otherwise appends -2, -3, ...
    until a free id is found. Never mutates `existing_ids`."""
    if candidate not in existing_ids:
        return CollisionResult(id=candidate, collided=False, original_candidate=candidate)
    n = 2
    while f"{candidate}-{n}" in existing_ids:
        n += 1
    return CollisionResult(id=f"{candidate}-{n}", collided=True, original_candidate=candidate)


def make_author_id(surname: str, given_name: str, *, existing_ids: set[str] = frozenset()) -> CollisionResult:
    candidate = f"{slugify(surname)}_{slugify(given_name)}" if given_name else slugify(surname)
    return resolve_collision(candidate, existing_ids)


def make_work_id(author_id: str, title: str, *, existing_ids: set[str] = frozenset()) -> CollisionResult:
    candidate = f"{author_id}-{slugify(title)}"
    return resolve_collision(candidate, existing_ids)


def make_edition_id(work_id: str, edition_slug: str, *, existing_ids: set[str] = frozenset()) -> CollisionResult:
    candidate = f"{work_id}-{slugify(edition_slug)}" if edition_slug else work_id
    return resolve_collision(candidate, existing_ids)


def check_source_id_unique(source_id: str, existing_ids: set[str]) -> bool:
    """source_id is checked for uniqueness only — no format is enforced
    (existing convention, NAE_CORPUS_INGESTION_STANDARD_v1.md Phase 3)."""
    return source_id not in existing_ids


@dataclass(frozen=True)
class NewIdentity:
    """Result of issuing identity for one new source. All fields carry a
    `collided` flag so the caller can decide whether to write a notes entry."""
    author_id: str
    author_collided: bool
    work_id: str
    work_collided: bool
    edition_id: str
    edition_collided: bool
    source_id: str


def issue_identity(
    *,
    surname: str,
    given_name: str,
    title: str,
    edition_slug: str,
    source_id: str,
    existing_author_ids: set[str],
    existing_work_ids: set[str],
    existing_edition_ids: set[str],
    existing_source_ids: set[str],
) -> NewIdentity:
    if not check_source_id_unique(source_id, existing_source_ids):
        raise ValueError(f"source_id already in use: {source_id}")

    author = make_author_id(surname, given_name, existing_ids=existing_author_ids)
    work = make_work_id(author.id, title, existing_ids=existing_work_ids)
    edition = make_edition_id(work.id, edition_slug, existing_ids=existing_edition_ids)

    return NewIdentity(
        author_id=author.id,
        author_collided=author.collided,
        work_id=work.id,
        work_collided=work.collided,
        edition_id=edition.id,
        edition_collided=edition.collided,
        source_id=source_id,
    )
