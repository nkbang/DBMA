"""CLI for the TSU Builder (Phase 3)."""
from __future__ import annotations

import argparse
import json

from . import builder, config


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE TSU Builder")
    parser.add_argument("--identifier", help="Process a single identifier only")
    parser.add_argument("--model", default=config.DEFAULT_CLAIM_MODEL)
    parser.add_argument("--max-candidates", type=int, default=None,
                         help="Limit claim-extraction LLM calls per item (cost/time control)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.identifier:
        result = builder.build_tsu_for_identifier(
            args.identifier, model=args.model, max_candidates=args.max_candidates,
        )
        print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    else:
        summary = builder.build_tsu_for_all(model=args.model, max_candidates_per_item=args.max_candidates)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
