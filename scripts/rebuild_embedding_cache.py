"""
scripts/rebuild_embedding_cache.py — Explicit Embedding Cache Maintenance
Command.

Context (docs/diagnostics/embedding_cache_lifecycle_audit.md): core.
retrieval.EmbeddingCache only fills lazily at query time (BM25 top-K
candidates of whatever queries have actually run), and its existing
rebuild()/batch_insert() methods have never had a call site anywhere in
the codebase. This script is that missing connection point — Option B
from the audit (explicit maintenance command), not an automatic/startup
mechanism, so it does not touch core/retrieval.py, core/tsu_builder.py,
core/chunking_optimizer.py, or dbma_ui.py.

Embedding authority (confirmed with HQ before implementation): the same
path core.retrieval.RetrievalEngine.retrieve() uses at query time --
core.embedder.get_embedder() -> _OllamaEmbedder.encode(text,
normalize_embeddings=True), model "bge-m3:latest"
(core.config.DEFAULT_EMBED_MODEL), 1024-dim (core.config.
EMBEDDING_DIMENSION). Unlike the query-time path, this script calls
get_embedder(fallback=False) -- a bulk maintenance run must not silently
mix in the MiniLM fallback mid-run (the historical 384-vs-1024 dimension
incident HQ flagged); a real Ollama outage should abort loudly instead.

Commit-per-item, NOT batch (Gate C): the first real run used
EmbeddingCache.rebuild(), which accumulates every computed vector in
memory and writes them all at the end -- so a single oversized-input
failure (core.embedder's 1800-token guard, SPRINT20-I) discarded the
whole run. This script instead walks the TSU dataset itself and calls
EmbeddingCache.lookup(content, embed_fn) per item -- lookup() is the exact
production code path RetrievalEngine.retrieve() uses, and it inserts each
embedding the moment it is computed, so a mid-run failure loses nothing
already done. core/retrieval.py and core/embedder.py are unchanged; only
this maintenance script switched from the batch method to the per-item
method.

Skip policy (Gate C): a TSU whose content exceeds core.embedder's
_MAX_SAFE_EMBED_TOKENS guard is classified SKIPPED_LARGE_TEXT and left
uncached. It is NEVER truncated and NEVER re-chunked here (that would
change the embedding authority / the stored unit). Those documents keep
retrieval's query-time TF-IDF fallback (RetrievalEngine.retrieve STEP 3).

Orphan policy (HQ-approved acceptance criteria): cache files whose hash
does not match any current TSU's content hash are reported only, never
deleted here.

Usage:
    python scripts/rebuild_embedding_cache.py --dry-run
    python scripts/rebuild_embedding_cache.py
"""

from __future__ import annotations

import argparse
import json
import time
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import DEFAULT_TSU_DATASET_PATH, DEFAULT_BENCH_DIR
from core.retrieval import EmbeddingCache
# Reuse the exact oversized-input guard core.embedder enforces, so this
# script classifies SKIPPED_LARGE_TEXT identically to how the embedder
# would reject it (single source of truth -- no re-hardcoded threshold).
from core.embedder import _APPROX_CHARS_PER_TOKEN, _MAX_SAFE_EMBED_TOKENS

_REPORT_PATH = Path(DEFAULT_BENCH_DIR) / "rebuild_embedding_cache_report.json"


def _is_oversized(content: str) -> bool:
    return (len(content) // _APPROX_CHARS_PER_TOKEN) > _MAX_SAFE_EMBED_TOKENS


def _iter_tsu_contents(tsu_dataset_path: Path):
    with open(tsu_dataset_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("$"):
                continue
            try:
                tsu = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = tsu.get("content", "")
            if content:
                yield content


def compute_coverage(cache: EmbeddingCache, tsu_dataset_path: Path) -> dict:
    """Read-only pass. EmbeddingCache is content-addressed (SHA256(content)
    [:16], not keyed by TSU id), so the correct coverage denominator is
    DISTINCT content hashes, not the raw TSU record count -- multiple TSU
    records can share identical content (measured: 3,671 duplicate content
    occurrences across 50,789 records, 47,118 distinct hashes) and only
    need one cache entry between them. `total_tsu` is reported separately
    for provenance/comparison against the TSU manifest count, but matched/
    missing/coverage are all computed against distinct_hashes."""
    tsu_hashes = set()
    total_tsu = 0
    for content in _iter_tsu_contents(tsu_dataset_path):
        total_tsu += 1
        tsu_hashes.add(cache._hash_text(content))

    cache_hashes = {p.stem for p in cache.cache_dir.glob("*.json")}

    distinct_hashes = len(tsu_hashes)
    matched = len(tsu_hashes & cache_hashes)
    orphaned = len(cache_hashes - tsu_hashes)
    missing = distinct_hashes - matched

    return {
        "total_tsu": total_tsu,
        "distinct_hashes": distinct_hashes,
        "cache_files": len(cache_hashes),
        "matched": matched,
        "missing": missing,
        "orphaned": orphaned,
        "coverage_pct": round(100.0 * matched / distinct_hashes, 2) if distinct_hashes else 0.0,
    }


def _print_report(title: str, stats: dict) -> None:
    print(f"=== {title} ===")
    print(f"  TSU records:       {stats['total_tsu']}")
    print(f"  Distinct content:  {stats['distinct_hashes']} "
          f"(cache is content-addressed, not TSU-id-addressed)")
    print(f"  Cache files:       {stats['cache_files']}")
    print(f"  Matched:           {stats['matched']}")
    print(f"  Missing:           {stats['missing']}")
    print(f"  Orphaned:          {stats['orphaned']} (reported only, not deleted)")
    print(f"  Coverage (of distinct content): {stats['coverage_pct']}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report coverage/missing/orphan counts without embedding anything.",
    )
    parser.add_argument(
        "--tsu-dataset", default=str(DEFAULT_TSU_DATASET_PATH),
        help="Path to the TSU JSONL dataset (default: config.DEFAULT_TSU_DATASET_PATH).",
    )
    parser.add_argument(
        "--progress-every", type=int, default=500,
        help="Print a progress line every N embeddings computed (0 disables).",
    )
    args = parser.parse_args()

    tsu_path = Path(args.tsu_dataset)
    if not tsu_path.exists():
        print(f"TSU dataset not found: {tsu_path}")
        sys.exit(1)

    cache = EmbeddingCache()

    before = compute_coverage(cache, tsu_path)
    _print_report("Before", before)

    # Count how many of the missing entries are oversized (would be
    # skipped) so the dry-run is honest about how far coverage can reach.
    cache_hashes_before = {p.stem for p in cache.cache_dir.glob("*.json")}
    seen: set = set()
    missing_oversized = 0
    for content in _iter_tsu_contents(tsu_path):
        h = cache._hash_text(content)
        if h in seen or h in cache_hashes_before:
            seen.add(h)
            continue
        seen.add(h)
        if _is_oversized(content):
            missing_oversized += 1

    if args.dry_run:
        print()
        print(f"Dry-run: {before['missing']} distinct contents missing; of those "
              f"{missing_oversized} exceed the {_MAX_SAFE_EMBED_TOKENS}-token guard "
              f"and would be SKIPPED_LARGE_TEXT (never truncated). No files written.")
        return

    if before["missing"] == 0:
        print()
        print("Nothing to do -- all distinct contents already have a cache entry.")
        return

    from core.embedder import get_embedder

    embedder = get_embedder(fallback=False)

    def embed_fn(text: str):
        return embedder.encode(text, normalize_embeddings=True)

    already_cached = 0
    newly_embedded = 0
    skipped_large_text = 0
    failed_embedding = 0
    failed_examples: list = []
    processed_hashes: set = set()

    print()
    print(f"Rebuilding per-item via lookup() (missing={before['missing']}, "
          f"model=bge-m3:latest, fallback=False)...")
    t_start = time.time()

    for content in _iter_tsu_contents(tsu_path):
        h = cache._hash_text(content)
        if h in processed_hashes:
            continue  # identical content already handled this run
        processed_hashes.add(h)

        if h in cache_hashes_before:
            already_cached += 1
            continue

        if _is_oversized(content):
            skipped_large_text += 1
            if len(failed_examples) < 20:
                failed_examples.append({
                    "reason": "SKIPPED_LARGE_TEXT",
                    "chars": len(content),
                    "est_tokens": len(content) // _APPROX_CHARS_PER_TOKEN,
                    "preview": content[:80],
                })
            continue

        # Per-item commit: lookup() computes + inserts atomically, so a
        # failure here loses only this one item, never prior progress.
        try:
            vector = cache.lookup(content, embed_fn)
        except Exception as e:  # defensive -- lookup() already swallows most
            vector = None
            _reason = f"{type(e).__name__}: {e}"
        else:
            _reason = "embed returned None"

        if vector is not None:
            newly_embedded += 1
            if args.progress_every and newly_embedded % args.progress_every == 0:
                print(f"  ... {newly_embedded} embedded "
                      f"(skipped_large={skipped_large_text}, failed={failed_embedding})")
        else:
            failed_embedding += 1
            if len(failed_examples) < 20:
                failed_examples.append({
                    "reason": _reason,
                    "chars": len(content),
                    "preview": content[:80],
                })

    elapsed = round(time.time() - t_start, 1)
    after = compute_coverage(cache, tsu_path)

    report = {
        "total_tsu": before["total_tsu"],
        "unique_content": before["distinct_hashes"],
        "already_cached": already_cached,
        "newly_embedded": newly_embedded,
        "skipped_large_text": skipped_large_text,
        "failed_embedding": failed_embedding,
        "elapsed_seconds": elapsed,
        "cache_before": before["cache_files"],
        "cache_after": after["cache_files"],
        "coverage_before_pct": before["coverage_pct"],
        "coverage_after_pct": after["coverage_pct"],
        "orphaned": after["orphaned"],
        "embedding_model": "bge-m3:latest",
        "vector_dimension": 1024,
        "failed_examples": failed_examples,
    }
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("Embedding Cache Rebuild")
    print(f"  TSU unique:       {before['distinct_hashes']}")
    print(f"  Cached before:    {before['cache_files']}")
    print(f"  Embedded:         {newly_embedded}")
    print(f"  Already cached:   {already_cached}")
    print(f"  Skipped (large):  {skipped_large_text}")
    print(f"  Failed:           {failed_embedding}")
    print(f"  Cache after:      {after['cache_files']}")
    print(f"  Coverage:         {after['coverage_pct']}% "
          f"(of {before['distinct_hashes']} distinct contents)")
    print(f"  Elapsed:          {elapsed}s")
    print(f"  Report:           {_REPORT_PATH}")


if __name__ == "__main__":
    main()
