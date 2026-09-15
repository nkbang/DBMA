"""NAE Baptist Commentary Ingestion CLI.

Ingests a verse-anchored Baptist commentary volume (e.g. Spurgeon's
"The Treasury of David") into the isolated `nae_ref_commentary_v1` Qdrant
collection — separate from Smith Bible Dictionary's `nae_ref_v1`
(ADR-013 collection isolation).

Reuses `NAE.pipeline.reference.ingest.ingest()` unmodified aside from
passing `collection_name=config.COMMENTARY_COLLECTION_NAME` and
`chunker_fn=chunker.chunk_canonical_verse_anchored` — no ingestion logic
is duplicated here.

Usage:
    python scripts/nae_commentary_ingest.py --identifier Spurgeon_TreasuryOfDavid_Vol1 --dry-run
    python scripts/nae_commentary_ingest.py --identifier Spurgeon_TreasuryOfDavid_Vol1 --apply

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
}


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
    args = parser.parse_args()

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

    source_id = _COMMENTARY_SOURCE_IDS.get(args.identifier, "")

    if args.apply:
        result = ref_ingest.ingest(
            canonical_path=canonical_path,
            identifier=args.identifier,
            source_id=source_id,
            volume="vol_1",
            apply=True,
            collection_name=ref_config.COMMENTARY_COLLECTION_NAME,
            chunker_fn=chunker.chunk_canonical_verse_anchored,
            content_type="reference_commentary",
        )
    else:
        result = ref_ingest.ingest(
            canonical_path=canonical_path,
            identifier=args.identifier,
            source_id=source_id,
            volume="vol_1",
            apply=False,
            collection_name=ref_config.COMMENTARY_COLLECTION_NAME,
            chunker_fn=chunker.chunk_canonical_verse_anchored,
            content_type="reference_commentary",
        )

    output = {
        "identifier": result.identifier,
        "collection": ref_config.COMMENTARY_COLLECTION_NAME,
        "chunks_total": result.chunks_total,
        "chunks_embedded": result.chunks_embedded,
        "chunks_skipped": result.chunks_skipped,
        "points_upserted": result.points_upserted,
        "errors": result.errors[:5],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
