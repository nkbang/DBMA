"""Thin CLI driver for n8n Execute Command node (ADR-023).

Calls NAE.pipeline.registration.pipeline.register_source() as-is.
Does NOT import or touch:
  - NAE.pipeline.tsu.*
  - NAE.pipeline.ingest.*
  - NAE.pipeline.embed.*
  - NAE.pipeline.index.*
  - Qdrant

Exit code contract (ADR-023 \u00a712):
  0 \u2014 register_source() completed normally (result verdict is in stdout JSON)
  1 \u2014 Python exception
  2 \u2014 Input validation failure (processing_input parse error / missing required fields)
  3 \u2014 raw_item_dir inaccessible

stdout = JSON result only. stderr = diagnostic info only. Never mix them.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

# ADR-023 \u00a79 boundary: ONLY register_source import allowed.
# NO tsu/ingest/embed/index/Qdrant imports.
from NAE.pipeline.registration.pipeline import (
    RegistrationRequest,
    RegistrationResult,
    register_source,
)
from NAE.pipeline.registration.state import (
    ExceptionQueue,
    RegistrationStateStore,
)

# ADR-023 \u00a74: Authority file loading is READ-ONLY.
from NAE.pipeline.registration.authority import _load_yaml as _load_authority_yaml
from NAE.pipeline.registration import config
from NAE.pipeline.registration.raw_preservation import ChecksumLedger


def _load_existing_ids(
    source_id: str,
) -> tuple[set[str], set[str], set[str], set[str]]:
    """Load existing_*_ids from Authority files (read-only).

    Returns (author_ids, work_ids, edition_ids, source_ids).
    """
    authors_data = _load_authority_yaml(config.NEW_AUTHORS_PATH)
    works_data = _load_authority_yaml(config.NEW_WORKS_PATH)

    author_ids: set[str] = {
        a["author_id"]
        for a in (authors_data.get("authors") or [])
        if isinstance(a, dict) and "author_id" in a
    }
    work_ids: set[str] = {
        w["work_id"]
        for w in (works_data.get("works") or [])
        if isinstance(w, dict) and "work_id" in w
    }

    edition_ids: set[str] = set()
    editions_path = config.AUTHORITY_ROOT / "editions.yaml"
    if editions_path.exists():
        editions_data = _load_authority_yaml(editions_path)
        edition_ids = {
            e["edition_id"]
            for e in (editions_data.get("editions") or [])
            if isinstance(e, dict) and "edition_id" in e
        }

    # Load existing source_ids from sources.yaml if available;
    # otherwise return empty set (no authoritative source for
    # source_ids in the authority directory — duplicate detection
    # happens at the TSU layer, not here).
    sources_path = config.AUTHORITY_ROOT / "sources.yaml"
    source_ids: set[str] = set()
    if sources_path.exists():
        sources_data = _load_authority_yaml(sources_path)
        source_ids = {
            s["source_id"]
            for s in (sources_data.get("sources") or [])
            if isinstance(s, dict) and "source_id" in s
        }

    return author_ids, work_ids, edition_ids, source_ids


def _build_state_store_and_queue(
    work_dir: Path,
    production: bool = False,
) -> tuple[RegistrationStateStore, ExceptionQueue]:
    """Create state store and exception queue.

    In dry-run mode (production=False), uses a temp work dir.
    In production mode (production=True), writes to the actual
    registration_state.json path.
    """
    if production:
        state_path = config.DEFAULT_REGISTRATION_STATE_PATH
        queue_path = config.DEFAULT_EXCEPTION_QUEUE_PATH
    else:
        state_path = work_dir / "reg_state.json"
        queue_path = work_dir / "reg_queue.json"
    return (
        RegistrationStateStore(state_path),
        ExceptionQueue(queue_path),
    )


def _validate_processing_input(task: dict[str, Any]) -> dict[str, Any] | None:
    """Validate automation.processing_input. Returns error dict or None."""
    automation = task.get("automation")
    if not isinstance(automation, dict):
        return {"error": "missing field: automation"}

    pi = automation.get("processing_input")
    if not isinstance(pi, dict):
        return {"error": "missing field: automation.processing_input"}

    required_fields = [
        "raw_item_dir",
        "surname",
        "given_name",
        "title",
        "edition_slug",
        "publication_year",
        "copyright_status",
        "archive_source",
        "source_id",
    ]
    for field in required_fields:
        if field not in pi:
            return {"error": f"missing processing_input field: {field}"}

    return pi


def main() -> int:
    """CLI entry point. Returns exit code per \u00a712 contract."""
    try:
        # Parse arguments
        args = sys.argv[1:]
        request_json_path = None
        production = False
        for i, arg in enumerate(args):
            if arg == "--request-json" and i + 1 < len(args):
                request_json_path = args[i + 1]
            elif arg == "--production":
                production = True

        if not request_json_path:
            print(
                json.dumps({"error": "missing --request-json argument"}),
                file=sys.stderr,
            )
            return 2

        task_path = Path(request_json_path)
        if not task_path.exists():
            print(
                json.dumps({"error": f"task file not found: {request_json_path}"}),
                file=sys.stderr,
            )
            return 2

        # Load task JSON
        try:
            task = json.loads(task_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(json.dumps({"error": f"task parse error: {e}"}), file=sys.stderr)
            return 2

        # Validate processing_input
        pi = _validate_processing_input(task)
        if pi is not None and "error" in pi:
            print(json.dumps(pi), file=sys.stderr)
            return 2

        # Check raw_item_dir accessibility
        raw_item_dir = Path(pi["raw_item_dir"])
        if not raw_item_dir.exists() or not raw_item_dir.is_dir():
            print(
                json.dumps({"error": f"raw_item_dir inaccessible: {pi['raw_item_dir']}"}),
                file=sys.stderr,
            )
            return 3

        # Load existing IDs from Authority files (read-only)
        author_ids, work_ids, edition_ids, source_ids = _load_existing_ids(pi["source_id"])

        # Create state store and exception queue
        # In production mode, writes to actual registration_state.json
        # In dry-run mode, uses temp dir (default behavior)
        tmp_work = Path(tempfile.mkdtemp(prefix="cli_driver_"))
        manifest_path = config.DEFAULT_SOURCE_MANIFEST_PATH
        state_store, exception_queue = _build_state_store_and_queue(tmp_work, production=production)

        # Build RegistrationRequest
        request = RegistrationRequest(
            raw_item_dir=raw_item_dir,
            surname=pi["surname"],
            given_name=pi["given_name"],
            title=pi["title"],
            edition_slug=pi["edition_slug"],
            publication_year=pi["publication_year"],
            copyright_status=pi["copyright_status"],
            archive_source=pi["archive_source"],
            source_id=pi["source_id"],
            manifest_path=manifest_path,
        )

        # Call register_source() \u2014 unmodified ADR-021 code
        result = register_source(
            request,
            existing_author_ids=author_ids,
            existing_work_ids=work_ids,
            existing_edition_ids=edition_ids,
            existing_source_ids=source_ids,
            ledger=ChecksumLedger(config.DEFAULT_CHECKSUM_LEDGER_PATH),
            state_store=state_store,
            exception_queue=exception_queue,
        )

        # Persist state store to production (only meaningful in --production mode)
        if production:
            state_store.save()

        # Output result as JSON to stdout
        output = {
            "source_id": result.source_id,
            "final_state": result.final_state.value,
            "page_count": result.page_count,
            "notes": result.notes,
        }
        if result.identity:
            output["identity"] = {
                "author_id": result.identity.author_id,
                "work_id": result.identity.work_id,
                "edition_id": result.identity.edition_id,
                "source_id": result.identity.source_id,
                "author_collided": result.identity.author_collided,
                "work_collided": result.identity.work_collided,
                "edition_collided": result.identity.edition_collided,
            }
        if result.preservation:
            output["preservation"] = {
                "checksum": result.preservation.checksum,
                "preserved_path": str(result.preservation.raw_path),
                "duplicate_of": result.preservation.duplicate_of,
            }
        if result.validation:
            output["validation"] = {
                "passed": result.validation.passed,
                "errors": result.validation.errors,
            }
        if result.gate_result:
            verdict_val = (
                result.gate_result.verdict.value
                if hasattr(result.gate_result.verdict, "value")
                else str(result.gate_result.verdict)
            )
            output["gate_result"] = {
                "verdict": verdict_val,
                "warnings": result.gate_result.warning_reasons,
                "fail_reasons": result.gate_result.fail_reasons,
            }

        print(json.dumps(output, ensure_ascii=False))
        return 0

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
