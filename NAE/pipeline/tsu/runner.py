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

Phase 3 worker wiring:
- `--enqueue <identifier>`: enqueue candidates from canonical.json as READY
- `--worker-mode`: process READY candidates through the TSU Extraction Queue Worker
- `--retry-failed <id>`: manually retry a FAILED candidate (explicit human trigger only)
"""
from __future__ import annotations

import argparse
import json

from . import builder, config, gate_adapter
from .worker import worker as tsu_worker
from .worker import loader as tsu_loader


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NAE TSU Builder")

    # Existing options (unchanged — backward compatible)
    parser.add_argument("--identifier", help="Process a single identifier only (bypasses the Gate — explicit override)")
    parser.add_argument("--model", default=config.DEFAULT_CLAIM_MODEL)
    parser.add_argument("--max-candidates", type=int, default=None,
                        help="Limit claim-extraction LLM calls per item (cost/time control)")
    parser.add_argument("--legacy-scan", action="store_true",
                        help="Bypass the Crosswalk Gate and scan NAE/corpus/canonical/ directly "
                             "(pre-wiring behavior, build_tsu_for_all) — for debugging/fallback only")

    # Phase 3 worker options (separate steps — no auto-chaining)
    parser.add_argument("--enqueue", type=str, metavar="IDENTIFIER",
                        help="Enqueue candidates from canonical.json as READY state. "
                             "Does NOT process them — use --worker-mode separately.")
    parser.add_argument("--worker-mode", action="store_true",
                        help="Process READY candidates through the TSU Extraction Queue Worker "
                             "(process_batch with READY candidates)")
    parser.add_argument("--retry-failed", type=str, metavar="ID",
                        help="Manually retry a FAILED candidate by candidate_id. "
                             "Requires explicit human trigger — no batch auto-retry.")

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


def _run_enqueue(identifier: str, max_candidates: int | None) -> dict:
    """Enqueue candidates from canonical.json as READY state."""
    state_store = tsu_worker.TSUExtractionStateStore()
    before_summary = state_store.summary()

    new_count = tsu_loader.enqueue_from_canonical(
        identifier=identifier,
        state_store=state_store,
        max_candidates=max_candidates,
    )

    after_summary = state_store.summary()

    return {
        "enqueue": True,
        "identifier": identifier,
        "new_ready": new_count,
        "before_summary": before_summary,
        "after_summary": after_summary,
    }


def _run_worker_mode(model: str) -> dict:
    """Worker mode: process READY candidates through the TSU Extraction Queue."""
    state_store = tsu_worker.TSUExtractionStateStore()
    exception_queue = tsu_worker.TSUExtractionExceptionQueue()

    # Get READY candidates from state store
    ready_ids = state_store.entries_by_state(tsu_worker.TSUExtractionState.READY)

    if not ready_ids:
        return {
            "worker_mode": True,
            "ready_candidates": 0,
            "processed": 0,
            "message": "No READY candidates in queue.",
        }

    # Build candidate list from state store entries (use real text from metadata)
    candidates = []
    for cid in ready_ids:
        entry = state_store.get_entry(cid)
        if entry and entry.state == tsu_worker.TSUExtractionState.READY:
            meta = entry.metadata or {}
            candidates.append({
                "candidate_id": cid,
                "text": meta.get("text", f"candidate_text_for_{cid}"),
                "context_before": meta.get("context_before", ""),
                "context_after": meta.get("context_after", ""),
                "candidate_scriptures": meta.get("candidate_scriptures", []),
                "candidate_citations": meta.get("candidate_citations", []),
            })

    result = tsu_worker.process_batch(
        candidates=candidates,
        model=model,
        state_store=state_store,
        exception_queue=exception_queue,
    )

    return {
        "worker_mode": True,
        "total": result.total,
        "extracted": result.extracted,
        "failed": result.failed,
        "success_rate": result.success_rate,
        "elapsed_seconds": round(result.elapsed_seconds, 3),
        "queue_depth_after": tsu_worker.get_queue_depth(state_store),
    }


def _run_retry_failed(candidate_id: str) -> dict:
    """Manually retry a FAILED candidate (explicit human trigger only)."""
    state_store = tsu_worker.TSUExtractionStateStore()
    exception_queue = tsu_worker.TSUExtractionExceptionQueue()

    current_state = state_store.get_state(candidate_id)
    if current_state is None:
        return {
            "retry_failed": True,
            "candidate_id": candidate_id,
            "success": False,
            "message": f"candidate_id '{candidate_id}' not found in state store.",
        }

    ok, msg = tsu_worker.retry_failed(
        candidate_id=candidate_id,
        state_store=state_store,
        exception_queue=exception_queue,
    )

    new_state = state_store.get_state(candidate_id)

    return {
        "retry_failed": True,
        "candidate_id": candidate_id,
        "previous_state": current_state.value,
        "new_state": new_state.value if new_state else None,
        "success": ok,
        "message": msg if not ok else f"Retried {candidate_id}: FAILED -> READY",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    # Priority: --retry-failed > --enqueue > --worker-mode > existing paths
    if args.retry_failed:
        result = _run_retry_failed(args.retry_failed)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.enqueue:
        result = _run_enqueue(args.enqueue, args.max_candidates)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.worker_mode:
        result = _run_worker_mode(args.model)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.identifier:
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
