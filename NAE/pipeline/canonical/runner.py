"""CLI for the Canonical Normalization Pipeline (Phase 2)."""
from __future__ import annotations

import argparse
import json

from . import config, pipeline


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE Canonical Normalization Pipeline")
    parser.add_argument("--identifier", help="Process a single identifier only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.identifier:
        result = pipeline.process_identifier(args.identifier)
        print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    else:
        summary = pipeline.process_all()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
