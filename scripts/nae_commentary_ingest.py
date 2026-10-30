"""NAE Baptist Commentary Ingestion CLI.

Ingests a Baptist commentary volume (e.g. Spurgeon's "The Treasury of
David") into the isolated `nae_ref_commentary_v1` Qdrant collection —
separate from Smith Bible Dictionary's `nae_ref_v1` (ADR-013 collection
isolation).

Reuses `NAE.pipeline.reference.ingest.ingest()` unmodified aside from
passing `collection_name=config.COMMENTARY_COLLECTION_NAME` and a
`chunker_fn` — no ingestion logic is duplicated here.

Default chunker is `chunk_canonical` (plain heading+prose), NOT
`chunk_canonical_verse_anchored`. Found the hard way on the real
Spurgeon Vol.1 data (2026-09-15, first --apply run, deleted and
re-ingested after discovering this): across all 4,145 canonicalized
paragraphs, exactly ONE contains a fully-spelled-out "Psalms N:M"
citation — Spurgeon writes "Verse 2.—..." for the psalm currently under
discussion (no book/chapter restated) but spells out full citations
when referencing *other* books or psalms in passing. The verse-anchored
chunker's `anchor_book_prefix="Psalms"` filter correctly avoids
mis-anchoring to those cross-references, but then has only that one
citation to anchor to for the entire ~500-page volume — so 1,627 of
1,978 chunks all got tagged with the same wrong value ("Psalms 109:17")
instead of the actual psalm each one expounds. Two aggregate-count
verification passes (at commit time and during C1 review) missed this
because they checked "tagged vs. untagged vs. wrong-book" counts, never
whether the tagged values were actually distinct.
`chunk_canonical_verse_anchored` stays available (`--chunker verse_anchored`)
for a future work whose citation convention actually restates chapter:verse
per section — just isn't Spurgeon's.

Usage:
    python scripts/nae_commentary_ingest.py --identifier Spurgeon_TreasuryOfDavid_Vol1 --dry-run
    python scripts/nae_commentary_ingest.py --identifier Spurgeon_TreasuryOfDavid_Vol1 --apply
    python scripts/nae_commentary_ingest.py --identifier X --chunker verse_anchored --dry-run

`--dry-run` is the default (safe).  `--apply` must be explicitly specified
to actually embed and upsert.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from NAE.pipeline.reference import chunker
from NAE.pipeline.reference import ingest as ref_ingest
from NAE.pipeline.reference import config as ref_config


# Canonical paths for known Baptist commentary volumes. Paths point at
# canonical.json produced by the existing NAE.pipeline.canonical extraction
# stage — this script does not extract/OCR raw source text itself.
_COMMENTARY_CANONICALS: dict[str, Path] = {
    "Spurgeon_TreasuryOfDavid_Vol1": (
        REPO_ROOT / "NAE" / "corpus" / "canonical"
        / "Spurgeon_TreasuryOfDavid_Vol1" / "canonical.json"
    ),
}

# source_id per BAP-COMM-<AUTHOR>-<WORK>-VOL<NN> governance convention
# (see docs/BAPTIST_COMMENTARY_EMBEDDING_PLAN_v1.md).
_COMMENTARY_SOURCE_IDS: dict[str, str] = {
    "Spurgeon_TreasuryOfDavid_Vol1": "BAP-COMM-SPURGEON-TDA-VOL01",
    "Gill_ExpositionNT_Vol1": "BAP-COMM-GILL-ENT-VOL01",
    "Broadus_CommentaryMatthew": "BAP-COMM-BROADUS-MATT-VOL01",
    "Carroll_InterpretationEB_Vol2": "BAP-COMM-CARROLL-IEB-VOL02",
}


def resolve_source_id(identifier: str, override: str | None = None) -> str:
    """identifier에 대응하는 source_id를 반환한다.

    매핑에 없는 identifier를 빈 문자열로 조용히 넘기면 Qdrant 페이로드의
    source_id가 비어 출처 추적이 끊긴다(2026-10-14 실측: nae_ref_commentary_v1
    8,539건). 모르는 identifier는 --source-id로 명시하게 하고, 아니면 중단한다.
    """
    source_id = (override or _COMMENTARY_SOURCE_IDS.get(identifier, "")).strip()
    if not source_id:
        raise ValueError(
            f"Unknown identifier '{identifier}': source_id를 알 수 없습니다. "
            f"_COMMENTARY_SOURCE_IDS에 등록하거나 --source-id를 지정하세요."
        )
    return source_id


def _warn_if_anchor_values_lack_diversity(canonical_path: Path) -> None:
    """--chunker verse_anchored footgun guard (2026-09-15): the anchor
    carries forward whenever the source text doesn't restate chapter:verse,
    so a source with too few qualifying citations produces many chunks all
    tagged with the same (usually wrong) value — exactly what happened on
    the first Spurgeon Vol.1 --apply run (1,627 of 1,978 chunks all tagged
    "Psalms 109:17", the volume's only fully-spelled-out Psalms citation).
    Aggregate tagged/untagged/wrong-book counts alone don't catch this —
    only checking that the tagged values are actually diverse does."""
    canonical = chunker.load_canonical(canonical_path)
    chunks = chunker.chunk_canonical_verse_anchored(canonical)
    tagged = [c.scripture_reference for c in chunks if c.scripture_reference]
    unique = set(tagged)
    if tagged and len(unique) / len(tagged) < 0.5:
        print(
            f"WARNING: {len(tagged)} chunks got a scripture_reference anchor, "
            f"but only {len(unique)} distinct value(s) among them "
            f"(most common: {max(unique, key=tagged.count)!r}, "
            f"{tagged.count(max(unique, key=tagged.count))} chunks). "
            f"This usually means the source rarely restates chapter:verse "
            f"for its own subject and the anchor is stuck on one stray "
            f"cross-reference — verse_anchored is probably the wrong "
            f"chunker for this source. Use --chunker heading instead.",
            file=sys.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="NAE Baptist Commentary Ingestion")
    parser.add_argument(
        "--identifier", required=True,
        help="Commentary volume identifier (e.g. Spurgeon_TreasuryOfDavid_Vol1)",
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument(
        "--canonical-path", default=None,
        help="Override canonical.json path (for custom corpora)",
    )
    parser.add_argument(
        "--source-id", default=None,
        help="Override source_id (매핑에 없는 identifier용, "
             "NAE/pipeline/registration/state/source_manifest.yaml 값 사용)",
    )
    parser.add_argument(
        "--chunker", choices=["heading", "verse_anchored"], default="heading",
        help="Chunking strategy. 'heading' (default, safe) groups by "
             "heading+prose like the Smith dictionary chunker. "
             "'verse_anchored' anchors chunks to Psalms scripture "
             "references — only meaningful for a source that actually "
             "restates chapter:verse per section (Spurgeon's Treasury of "
             "David does not; see module docstring).",
    )
    args = parser.parse_args()

    chunker_fn = (
        chunker.chunk_canonical_verse_anchored
        if args.chunker == "verse_anchored"
        else chunker.chunk_canonical
    )

    if args.canonical_path:
        canonical_path = Path(args.canonical_path)
    else:
        canonical_path = _COMMENTARY_CANONICALS.get(args.identifier)
        if canonical_path is None:
            print(f"Error: Unknown identifier '{args.identifier}'. "
                  f"Use --canonical-path to specify a custom path.", file=sys.stderr)
            sys.exit(1)

    if not canonical_path.exists():
        print(f"Error: Canonical file not found: {canonical_path}\n"
              f"이 원본은 아직 추출되지 않았습니다 — 원문 확보(사용자 승인) 및 "
              f"NAE.pipeline.canonical 추출 단계가 선행되어야 합니다.", file=sys.stderr)
        sys.exit(1)

    try:
        source_id = resolve_source_id(args.identifier, args.source_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.chunker == "verse_anchored":
        _warn_if_anchor_values_lack_diversity(canonical_path)

    result = ref_ingest.ingest(
        canonical_path=canonical_path,
        identifier=args.identifier,
        source_id=source_id,
        volume="vol_1",
        apply=args.apply,
        collection_name=ref_config.COMMENTARY_COLLECTION_NAME,
        chunker_fn=chunker_fn,
        content_type="reference_commentary",
    )

    output = {
        "identifier": result.identifier,
        "collection": ref_config.COMMENTARY_COLLECTION_NAME,
        "chunker": args.chunker,
        "chunks_total": result.chunks_total,
        "chunks_embedded": result.chunks_embedded,
        "chunks_skipped": result.chunks_skipped,
        "points_upserted": result.points_upserted,
        "errors": result.errors[:5],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
