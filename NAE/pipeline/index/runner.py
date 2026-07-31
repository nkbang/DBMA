"""CLI for Phase 4 - BGE-M3 Vector Indexing."""
from __future__ import annotations

import argparse
import json

from . import config, indexer


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE TSU Vector Indexer (Qdrant)")
    parser.add_argument("--identifier", help="Index a single identifier only")
    parser.add_argument("--qdrant-url", default=config.QDRANT_URL)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.identifier:
        report = indexer.index_identifier(args.identifier, qdrant_url=args.qdrant_url)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = indexer.index_all(qdrant_url=args.qdrant_url)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
