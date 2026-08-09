"""CLI for the TSU Builder (Phase 3).

NAE-TSU-PIPELINE-WIRING-IMPLEMENTATION-001: the default (no
`--identifier`) path now goes through the Crosswalk Gate
(`gate_adapter.py`) instead of scanning `NAE/corpus/canonical/`
directly — only Manifest entries that pass `TSU_ELIGIBLE=READY AND
mapping_status=manual-confirmed` reach `builder.build_tsu_for_identifier`.
`builder.py` itself is unmodified (`build_tsu_for_identifier`/
`build_tsu_for_all` both untouched) — `--legacy-scan` still exposes the
old direct-scan behavior (`build_tsu_for_all`) for debugging/fallback,
so that function stays reachable and is not dead code.
"""
from __future__ import annotations

import argparse
import json

from . import builder, config, gate_adapter


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE TSU Builder")
    parser.add_argument("--identifier", help="Process a single identifier only (bypasses the Gate — explicit override)")
    parser.add_argument("--model", default=config.DEFAULT_CLAIM_MODEL)
    parser.add_argument("--max-candidates", type=int, default=None,
                         help="Limit claim-extraction LLM calls per item (cost/time control)")
    parser.add_argument("--legacy-scan", action="store_true",
                         help="Bypass the Crosswalk Gate and scan NAE/corpus/canonical/ directly "
                              "(pre-wiring behavior, build_tsu_for_all) — for debugging/fallback only")
    return parser


def _run_gate_wired(model: str, max_candidates: int | None) -> dict:
    """Manifest -> Crosswalk Resolver -> TSU Gate -> Builder.
    PASS 판정된 identifier만 build_tsu_for_identifier()로 전달한다."""
    manifest_entries = gate_adapter.load_manifest_entries()
    orchestrator = gate_adapter.build_default_orchestrator()
    gate_summary = gate_adapter.iter_eligible_identifiers(manifest_entries, orchestrator)

    generated_reports = []
    for target_identifier in gate_summary.pass_identifiers:
        result = builder.build_tsu_for_identifier(target_identifier, model=model, max_candidates=max_candidates)
        generated_reports.append(result["report"])

    return {
        "gate_pass": gate_summary.pass_count,
        "gate_block": gate_summary.block_count,
        "gate_error": gate_summary.error_count,
        "gate_block_details": gate_summary.block_details,
        "gate_error_details": gate_summary.error_details,
        "tsu_generated": len(generated_reports),
        "reports": generated_reports,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.identifier:
        # 명시적 단건 지정 — Gate를 의도적으로 우회하는 override 경로
        # (기존 동작 그대로, 이번 Wiring 대상이 아님).
        result = builder.build_tsu_for_identifier(
            args.identifier, model=args.model, max_candidates=args.max_candidates,
        )
        print(json.dumps(result["report"], ensure_ascii=False, indent=2))
    elif args.legacy_scan:
        summary = builder.build_tsu_for_all(model=args.model, max_candidates_per_item=args.max_candidates)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        summary = _run_gate_wired(args.model, args.max_candidates)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
