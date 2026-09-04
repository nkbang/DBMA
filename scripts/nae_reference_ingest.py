"""NAE Reference Corpus Ingestion CLI.

Ingests a reference corpus (dictionary, encyclopedia, etc.) into Qdrant
via a separate pipeline from TSU.

Usage:
    python scripts/nae_reference_ingest.py --identifier Smith_Bible_Dictionary_HackettAbbot_Vol1 --dry-run
    python scripts/nae_reference_ingest.py --identifier Smith_Bible_Dictionary_HackettAbbot_Vol1 --apply

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

from NAE.pipeline.reference import ingest as ref_ingest
from NAE.pipeline.reference import config as ref_config


# Canonical paths for known reference corpora
_REFERENCE_CANONICALS: dict[str, Path] = {
    "Smith_Bible_Dictionary_HackettAbbot_Vol1": (
        REPO_ROOT / "NAE" / "corpus" / "canonical"
        / "Smith_Bible_Dictionary_HackettAbbot_Vol1" / "canonical.json"
    ),
    "Smith_Bible_Dictionary_HackettAbbot_Vol2": (
        REPO_ROOT / "NAE" / "corpus" / "canonical"
        / "Smith_Bible_Dictionary_HackettAbbot_Vol2" / "canonical.json"
    ),
    "Smith_Bible_Dictionary_HackettAbbot_Vol3": (
        REPO_ROOT / "NAE" / "corpus" / "canonical"
        / "Smith_Bible_Dictionary_HackettAbbot_Vol3" / "canonical.json"
    ),
    "Smith_Bible_Dictionary_HackettAbbot_Vol4": (
        REPO_ROOT / "NAE" / "corpus" / "canonical"
        / "Smith_Bible_Dictionary_HackettAbbot_Vol4" / "canonical.json"
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="NAE Reference Corpus Ingestion")
    parser.add_argument(
        "--identifier", required=True,
        help="Reference corpus identifier (e.g. Smith_Bible_Dictionary_HackettAbbot_Vol1)",
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument(
        "--canonical-path", default=None,
        help="Override canonical.json path (for custom corpora)",
    )
    args = parser.parse_args()

    if args.apply and "--dry-run" in sys.argv and "--apply" not in sys.argv:
        # argparse handles this, but be explicit
        pass

    # Resolve canonical path
    if args.canonical_path:
        canonical_path = Path(args.canonical_path)
    else:
        canonical_path = _REFERENCE_CANONICALS.get(args.identifier)
        if canonical_path is None:
            print(f"Error: Unknown identifier '{args.identifier}'. "
                  f"Use --canonical-path to specify a custom path.", file=sys.stderr)
            sys.exit(1)

    if not canonical_path.exists():
        print(f"Error: Canonical file not found: {canonical_path}", file=sys.stderr)
        sys.exit(1)

    # Determine source_id and volume from identifier
    source_id = ""
    volume = ""
    if args.identifier.startswith("Smith_Bible_Dictionary"):
        vol_num = args.identifier[-1]  # Vol1, Vol2, etc.
        source_id = f"BAP-REF-SMITH-VOL{int(vol_num):02d}"
        volume = f"vol_{int(vol_num)}"

    if args.apply:
        result = ref_ingest.ingest(
            canonical_path=canonical_path,
            identifier=args.identifier,
            source_id=source_id,
            volume=volume,
            apply=True,
        )
    else:
        result = ref_ingest.dry_run(
            canonical_path=canonical_path,
            identifier=args.identifier,
        )

    output = {
        "identifier": result.identifier,
        "chunks_total": result.chunks_total,
        "chunks_embedded": result.chunks_embedded,
        "chunks_skipped": result.chunks_skipped,
        "points_upserted": result.points_upserted,
        "errors": result.errors[:5],  # Limit error display
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
