"""core/bible_index.py — Bible reference posting-list index (Stage 1, independent of Vector Index).

DBMA-SEARCH-INFRA-001 Phase 2-3 (docs/architecture/DBMA-SEARCH-INFRA-001-PHASE2-PLAN.md §2-3).

HQ design: `Bible.{Book}.{Chapter}.{Verse}` canonical key -> posting list of
tsu_ids, built independently of the vector/BM25 indexes so a scripture-
reference query resolves in an O(1)-ish SQLite lookup instead of scanning
the corpus.

Reference normalization is NOT reimplemented here — `core.retrieval.QueryParser`
already parses both "Romans 8:28" and "롬 8:28"/"롬8:28" into the same
`ScriptureReference(book_id, chapter, verse_start, verse_end)` (see
QueryParser._extract_scripture_refs), and TSU records already carry the same
structure in `verse_mapping` (core/tsu_builder.py). This module only adds the
canonical-key posting-list storage on top of both.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from core.retrieval import BOOK_ID_TO_NAMES, QueryParser, ScriptureReference

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bible_posting (
    canonical_key TEXT NOT NULL,
    tsu_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    granularity TEXT NOT NULL  -- 'book' | 'chapter' | 'verse'
);
CREATE INDEX IF NOT EXISTS idx_bible_posting_key ON bible_posting(canonical_key);
CREATE INDEX IF NOT EXISTS idx_bible_posting_document ON bible_posting(document_id);
"""


def _canonical_book_name(book_id: str) -> str:
    """book_id ("ROM") -> canonical display name ("Romans"). Derived from
    core.retrieval.BOOK_ID_TO_NAMES's first (fullest) alias — not a second
    hand-typed book list."""
    aliases = BOOK_ID_TO_NAMES.get(book_id)
    if not aliases:
        return book_id
    return aliases[0].title()


def canonical_key(book_id: str, chapter: Optional[int] = None, verse: Optional[int] = None) -> str:
    """Build a `Bible.{Book}.{Chapter}.{Verse}` canonical key. Omitting
    `chapter`/`verse` produces the coarser `Bible.{Book}` / `Bible.{Book}.{Chapter}`
    key (used when a TSU only has book-level or chapter-level evidence)."""
    name = _canonical_book_name(book_id)
    parts = [f"Bible.{name}"]
    if chapter is not None:
        parts.append(str(chapter))
        if verse is not None:
            parts.append(str(verse))
    return ".".join(parts)


def keys_for_scripture_ref(ref: ScriptureReference) -> list[str]:
    """All canonical keys a query's scripture reference should look up —
    the book-level and chapter-level keys always, plus one verse-level key
    per verse in [verse_start, verse_end] when a verse is given. A ref
    without a verse (chapter-only) returns just the book/chapter keys."""
    keys = [
        canonical_key(ref.book_id),
        canonical_key(ref.book_id, ref.chapter),
    ]
    if ref.verse_start:
        verse_end = ref.verse_end or ref.verse_start
        keys.extend(
            canonical_key(ref.book_id, ref.chapter, v)
            for v in range(ref.verse_start, verse_end + 1)
        )
    return keys


def _keys_for_verse_mapping(verse_mapping: dict) -> list[tuple[str, str]]:
    """(canonical_key, granularity) pairs to index for one TSU's
    `verse_mapping` dict — mirrors whatever granularity the TSU actually
    carries (book-only for ~76% of the corpus per SPRINT19-C comment in
    core/tsu_builder.py, book+chapter+verse when the Scripture Evidence
    Resolver found one)."""
    book_id = verse_mapping.get("book_id")
    if not book_id:
        return []

    pairs = [(canonical_key(book_id), "book")]
    chapter = verse_mapping.get("chapter")
    if chapter is None:
        return pairs

    pairs.append((canonical_key(book_id, chapter), "chapter"))
    verse_start = verse_mapping.get("verse_start")
    if verse_start is None:
        return pairs

    verse_end = verse_mapping.get("verse_end") or verse_start
    pairs.extend(
        (canonical_key(book_id, chapter, v), "verse")
        for v in range(verse_start, verse_end + 1)
    )
    return pairs


class BibleIndex:
    """SQLite-backed canonical-key -> tsu_id posting list."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def add_tsus(self, tsus: list[dict]) -> int:
        """Insert posting rows for a batch of TSU records. Returns the
        number of posting rows added (a TSU with book+chapter+verse produces
        multiple rows — one per granularity/verse)."""
        rows = []
        for tsu in tsus:
            tsu_id = tsu.get("tsu_id", "")
            document_id = tsu.get("document_id", "")
            for key, granularity in _keys_for_verse_mapping(tsu.get("verse_mapping") or {}):
                rows.append((key, tsu_id, document_id, granularity))
        if rows:
            self._conn.executemany(
                "INSERT INTO bible_posting (canonical_key, tsu_id, document_id, granularity) VALUES (?, ?, ?, ?)",
                rows,
            )
            self._conn.commit()
        return len(rows)

    def delete_document(self, document_id: str) -> None:
        self._conn.execute("DELETE FROM bible_posting WHERE document_id = ?", (document_id,))
        self._conn.commit()

    def replace_document(self, document_id: str, new_tsus: list[dict]) -> int:
        """Delete all rows for `document_id`, then add `new_tsus` — same
        replace semantics as CandidateGenerator.replace_document() (Phase 2-4),
        so a document edit never requires a full index rebuild."""
        self.delete_document(document_id)
        return self.add_tsus(new_tsus)

    def lookup(self, key: str) -> list[str]:
        """tsu_ids posted under an exact canonical key."""
        cur = self._conn.execute(
            "SELECT DISTINCT tsu_id FROM bible_posting WHERE canonical_key = ?", (key,)
        )
        return [row[0] for row in cur.fetchall()]

    def lookup_scripture_ref(self, ref: ScriptureReference) -> list[str]:
        """tsu_ids matching a parsed query's scripture reference — tries the
        most specific verse-level key(s) first; if none match (common, since
        ~76% of TSUs only carry book-level evidence), falls back to the
        chapter key, then the book key, so a reference resolves to *some*
        candidates whenever the book is present in the corpus at all."""
        keys = keys_for_scripture_ref(ref)
        verse_keys = [k for k in keys if k.count(".") == 3]
        chapter_key = canonical_key(ref.book_id, ref.chapter)
        book_key = canonical_key(ref.book_id)

        for key in verse_keys:
            hits = self.lookup(key)
            if hits:
                return hits

        hits = self.lookup(chapter_key)
        if hits:
            return hits

        return self.lookup(book_key)


def _row_count(db_path: str | Path) -> int:
    """Return the number of rows in bible_posting without opening a full
    BibleIndex instance — used to detect empty/stale index files.

    Catches sqlite3.Error (not just OSError) because the exact case this
    exists for — a file that exists but was never populated with the
    bible_posting schema — raises sqlite3.OperationalError ("no such
    table"), which is not an OSError subclass and would otherwise crash
    here uncaught."""
    import sqlite3 as _sqlite3

    try:
        conn = _sqlite3.connect(str(db_path))
        try:
            cur = conn.execute("SELECT COUNT(*) FROM bible_posting")
            return cur.fetchone()[0]
        finally:
            conn.close()
    except (OSError, _sqlite3.Error):
        return 0


def build_index(tsu_dataset_path: str | Path, db_path: str | Path) -> int:
    """Build a fresh BibleIndex from a TSU JSONL dataset. Returns the number
    of posting rows written. Overwrites any existing index at db_path."""
    import json

    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()

    index = BibleIndex(db_path)
    total = 0
    with open(tsu_dataset_path, "r", encoding="utf-8") as f:
        batch = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            batch.append(json.loads(line))
            if len(batch) >= 5000:
                total += index.add_tsus(batch)
                batch = []
        if batch:
            total += index.add_tsus(batch)
    index.close()
    return total


def resolve_query(index: BibleIndex, query_text: str) -> list[str]:
    """Convenience entry point: parse `query_text` with the existing
    QueryParser (reused, not reimplemented) and return tsu_ids for every
    scripture reference detected — this is what CandidateGenerator's
    Bible-reference fast path (HQ Query Planner "Bible?" branch) calls."""
    parsed = QueryParser().parse(query_text)
    tsu_ids: list[str] = []
    seen = set()
    for ref in parsed.scripture_refs:
        for tsu_id in index.lookup_scripture_ref(ref):
            if tsu_id not in seen:
                seen.add(tsu_id)
                tsu_ids.append(tsu_id)
    return tsu_ids
